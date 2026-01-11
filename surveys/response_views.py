# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg
from django.http import JsonResponse, Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from core.models import *
from .forms import SurveyResponseForm
import uuid

logger = logging.getLogger(__name__)


# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.http import JsonResponse, Http404, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django import forms
from datetime import timedelta
import logging
import uuid

from core.models import *
from .forms import SurveyResponseForm

logger = logging.getLogger(__name__)

class SurveyResponseCreateView(CreateView):
    """
    Unified view for collecting survey responses from both registered and anonymous customers.
    ALL customers inherit the survey's organization.
    """
    template_name = 'survey_response/survey-response-form.html'
    form_class = SurveyResponseForm
    
    def dispatch(self, request, *args, **kwargs):
        """
        Initialize survey and ensure organization is always available
        """
        try:
            # Get survey from URL
            survey_id = kwargs.get('survey_id')
            
            # Get active survey with organization
            self.survey = get_object_or_404(
                Survey.objects.select_related('organization'),
                pk=survey_id,
                status='active'
            )
            
            # CRITICAL: Store organization from survey - ALL customers inherit this
            self.organization = self.survey.organization
            
            if not self.organization:
                logger.error(f"Survey {survey_id} has no organization")
                raise Http404(_("Survey has no organization"))
            
            # Check survey accessibility
            if not self._is_survey_accessible():
                return self._handle_inaccessible_survey()
            
            return super().dispatch(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error initializing survey: {str(e)}", exc_info=True)
            messages.error(request, _("An error occurred. Please try again."))
            return render(request, 'survey_response/survey-error.html', status=500)
    
    def _is_survey_accessible(self):
        """Check if survey is accessible"""
        if not self.survey or not self.organization:
            return False
        
        # Check status
        if self.survey.status != 'active':
            logger.warning(f"Survey {self.survey.id} is not active")
            return False
        
        # Check dates
        if self.survey.start_date and timezone.now() < self.survey.start_date:
            logger.warning(f"Survey {self.survey.id} has not started yet")
            return False
        
        if self.survey.end_date and timezone.now() > self.survey.end_date:
            logger.warning(f"Survey {self.survey.id} has ended")
            return False
        
        # Check response limit
        if (self.survey.response_limit and 
            self.survey.total_responses >= self.survey.response_limit):
            logger.warning(f"Survey {self.survey.id} has reached response limit")
            return False
        
        return True
    
    def _handle_inaccessible_survey(self):
        """Handle inaccessible survey"""
        context = {
            'survey': self.survey,
            'organization': self.organization,
            'message': _("This survey is not currently available.")
        }
        return render(self.request, 'survey_response/survey-unavailable.html', context, status=404)
    
    def get_customer(self, request):
        """
        Get or create customer for this survey's organization
        Returns a customer instance ALWAYS tied to survey.organization
        """
        try:
            # CRITICAL: Every customer must belong to this organization
            organization = self.organization
            
            # Priority 1: Check for authenticated user with Customer profile
            if request.user.is_authenticated:
                try:
                    # Check if user has a customer profile in this organization
                    customer = Customer.objects.get(
                        organization=organization,
                        user=request.user
                    )
                    logger.info(f"Found authenticated customer: {customer.email}")
                    return customer
                except Customer.DoesNotExist:
                    # Create customer from authenticated user
                    customer = Customer.objects.create(
                        organization=organization,  # Inherit survey's organization
                        user=request.user,
                        customer_id=f"auth_{uuid.uuid4().hex[:8]}",
                        email=request.user.email,
                        customer_type='authenticated',
                        segment='authenticated',
                        first_name=request.user.first_name or '',
                        last_name=request.user.last_name or '',
                        language_preference=request.GET.get('language', 'en'),
                        metadata={
                            'source': 'survey_response',
                            'survey_id': str(self.survey.id),
                            'created_at': timezone.now().isoformat(),
                            'user_id': str(request.user.id),
                        }
                    )
                    logger.info(f"Created authenticated customer: {customer.email}")
                    return customer
            
            # Priority 2: Check for customer token (for invited surveys)
            customer_token = request.GET.get('token')
            if customer_token:
                try:
                    customer = Customer.objects.get(
                        organization=organization,  # Must be in same organization
                        metadata__contains={'access_token': customer_token}
                    )
                    logger.info(f"Found customer by token: {customer.customer_id}")
                    return customer
                except Customer.DoesNotExist:
                    logger.warning(f"No customer found with token in org {organization.name}")
            
            # Priority 3: Check for customer ID
            customer_id = request.GET.get('customer_id')
            if customer_id:
                try:
                    customer = Customer.objects.get(
                        organization=organization,  # Must be in same organization
                        customer_id=customer_id
                    )
                    logger.info(f"Found customer by ID: {customer.customer_id}")
                    return customer
                except Customer.DoesNotExist:
                    logger.warning(f"No customer found with ID {customer_id} in org {organization.name}")
            
            # Priority 4: Check for email (identified customer)
            email = request.GET.get('email', '').strip().lower()
            if email and '@' in email:
                try:
                    # Try to get existing customer by email in THIS organization
                    customer = Customer.objects.get(
                        organization=organization,  # CRITICAL: Same organization
                        email=email
                    )
                    logger.info(f"Found existing customer by email: {email}")
                    return customer
                except Customer.DoesNotExist:
                    # Create new identified customer in THIS organization
                    customer = Customer.objects.create(
                        organization=organization,  # Inherit survey's organization
                        customer_id=f"id_{uuid.uuid4().hex[:8]}",
                        email=email,
                        customer_type='identified',
                        segment='new',
                        first_name=request.GET.get('first_name', ''),
                        last_name=request.GET.get('last_name', ''),
                        language_preference=request.GET.get('language', 'en'),
                        metadata={
                            'source': 'survey_response',
                            'survey_id': str(self.survey.id),
                            'created_at': timezone.now().isoformat(),
                            'registration_source': 'survey_link'
                        }
                    )
                    logger.info(f"Created new identified customer: {email}")
                    return customer
                except Exception as e:
                    logger.error(f"Error with email customer {email}: {str(e)}")
                    # Fall through to anonymous
            
            # Priority 5: Create anonymous customer (default case)
            return self._create_anonymous_customer(request)
            
        except Exception as e:
            logger.error(f"Error in get_customer: {str(e)}", exc_info=True)
            # Emergency fallback - MUST have organization
            return self._create_emergency_customer()
    
    def _create_anonymous_customer(self, request):
        """
        Create anonymous customer ALWAYS tied to survey's organization
        """
        try:
            # CRITICAL: Use survey's organization
            organization = self.organization
            
            # Use the Customer model's method if available
            if hasattr(Customer, 'get_or_create_anonymous'):
                customer, created = Customer.get_or_create_anonymous(
                    organization=organization,  # Inherit survey's organization
                    request=request,
                    metadata={
                        'source': 'survey_response',
                        'survey_id': str(self.survey.id),
                        'survey_title': self.survey.title,
                        'created_at': timezone.now().isoformat(),
                        'registration_source': 'survey_link',
                        'is_anonymous': True,
                    }
                )
                return customer
            
            # Fallback: Direct creation
            customer_id = f"anon_{uuid.uuid4().hex[:8]}"
            
            # Get client IP
            ip_address = self._get_client_ip(request)
            session_key = request.session.session_key or str(uuid.uuid4())
            
            customer = Customer.objects.create(
                organization=organization,  # CRITICAL: Set organization
                customer_id=customer_id,
                customer_type='anonymous',
                segment='anonymous',
                email=f"{customer_id}@anonymous.com",
                first_name='Anonymous',
                last_name='User',
                language_preference=request.GET.get('language', 'en'),
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=session_key,
                metadata={
                    'source': 'survey_response',
                    'survey_id': str(self.survey.id),
                    'survey_title': self.survey.title,
                    'created_at': timezone.now().isoformat(),
                    'registration_source': 'survey_link',
                    'is_anonymous': True,
                    'client_ip': ip_address,
                    'session_id': session_key,
                }
            )
            
            logger.info(f"Created anonymous customer: {customer.customer_id}")
            return customer
            
        except Exception as e:
            logger.error(f"Error creating anonymous customer: {str(e)}", exc_info=True)
            return self._create_emergency_customer()
    
    def _create_emergency_customer(self):
        """
        Emergency fallback - create customer with survey's organization
        This should NEVER fail
        """
        try:
            organization = self.organization
            
            customer_id = f"emergency_{uuid.uuid4().hex[:8]}"
            
            customer = Customer.objects.create(
                organization=organization,  # CRITICAL: Set organization
                customer_id=customer_id,
                customer_type='anonymous',
                segment='anonymous',
                email=f"{customer_id}@anonymous.com",
                first_name='Emergency',
                last_name='Customer',
                metadata={
                    'source': 'survey_response_emergency',
                    'survey_id': str(self.survey.id) if hasattr(self, 'survey') else 'unknown',
                    'created_at': timezone.now().isoformat(),
                    'is_emergency': True,
                }
            )
            
            logger.warning(f"Created emergency customer: {customer.customer_id}")
            return customer
            
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to create emergency customer: {str(e)}")
            # If even emergency creation fails, raise error
            raise ValueError(f"Cannot create customer for survey: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_form_kwargs(self):
        """Pass survey, customer, and request to form"""
        kwargs = super().get_form_kwargs()
        
        # Get or create customer (this happens when form is initialized)
        customer = self.get_customer(self.request)
        
        # Get questions from survey
        questions = self.survey.questions if hasattr(self.survey, 'questions') else []
        
        kwargs.update({
            'questions': questions,
            'survey': self.survey,
            'customer': customer,
            'request': self.request,
            'organization': self.organization  # Pass organization to form
        })
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add survey and customer to template context"""
        context = super().get_context_data(**kwargs)
        
        # Get customer for context
        customer = self.get_customer(self.request)
        
        is_anonymous = customer.customer_type == 'anonymous'
        
        context.update({
            'survey': self.survey,
            'organization': self.organization,
            'customer': customer,
            'page_title': self.survey.title,
            'is_anonymous': is_anonymous,
            'welcome_message': self.survey.welcome_message or _("Thank you for participating!"),
            'completion_message': self.survey.completion_message or _("Thank you for your feedback!"),
        })
        
        # Add question count for progress
        if hasattr(self.survey, 'questions'):
            context['total_questions'] = len(self.survey.questions)
        
        return context
    
    def form_valid(self, form):
        """
        Handle successful form submission
        Ensures ALL foreign keys are properly set
        """
        try:
            with transaction.atomic():
                # Get or create customer
                customer = self.get_customer(self.request)
                
                # Save the survey response using form
                survey_response = form.save_response()
                
                # CRITICAL: Ensure all relationships are set
                survey_response.survey = self.survey
                survey_response.customer = customer
                survey_response.organization = self.organization  # Explicitly set
                
                # Mark as complete
                survey_response.is_complete = True
                survey_response.completed_at = timezone.now()
                
                # Calculate completion time if available
                if hasattr(form, 'start_time') and form.start_time:
                    completion_seconds = (timezone.now() - form.start_time).total_seconds()
                    survey_response.completion_time = timedelta(seconds=completion_seconds)
                
                # Set device type
                user_agent = self.request.META.get('HTTP_USER_AGENT', '').lower()
                if 'mobile' in user_agent:
                    survey_response.device_type = 'mobile'
                elif 'tablet' in user_agent:
                    survey_response.device_type = 'tablet'
                else:
                    survey_response.device_type = 'desktop'
                
                # Set language
                survey_response.language = self.request.GET.get('language', 'en')
                
                # Try to set channel if available
                try:
                    survey_response.channel = Channel.objects.get(
                        organization=self.organization,
                        channel_type='web_form'
                    )
                except (Channel.DoesNotExist, Channel.MultipleObjectsReturned):
                    # If no specific channel, leave null
                    pass
                
                # Save the response
                survey_response.save()
                
                # Store for success URL
                self.object = survey_response
                
                # Update survey statistics
                self._update_survey_statistics()
                
                # Update customer interaction count
                self._update_customer_interactions(customer)
                
                # Trigger sentiment analysis if needed
                if survey_response.has_text_responses:
                    try:
                        success = survey_response.analyze_sentiment_sync()
                        if success:
                            logger.info(f"Sentiment analysis completed for response {survey_response.id}")
                    except Exception as e:
                        logger.error(f"Sentiment analysis error: {str(e)}")
                
                # Log successful submission
                logger.info(
                    f"Survey response submitted: ID={survey_response.id} | "
                    f"Customer={customer.customer_id} | "
                    f"Organization={self.organization.name} | "
                    f"Survey={self.survey.title}"
                )
                
                # Set success message
                messages.success(
                    self.request, 
                    _("Thank you for completing the survey! Your feedback has been recorded.")
                )
                
                return redirect(self.get_success_url())
                
        except Exception as e:
            logger.error(f"Error submitting survey response: {str(e)}", exc_info=True)
            messages.error(
                self.request, 
                _("There was an error submitting your response. Please try again.")
            )
            return self.form_invalid(form)
    
    def _update_survey_statistics(self):
        """Update survey response statistics"""
        try:
            from django.db.models import F
            
            # Use atomic update to prevent race conditions
            self.survey.total_responses = F('total_responses') + 1
            
            # Recalculate response rate
            if self.survey.total_sent > 0:
                new_total = self.survey.total_responses + 1
                self.survey.response_rate = (new_total / self.survey.total_sent) * 100
            
            self.survey.save(update_fields=['total_responses', 'response_rate', 'updated_at'])
            
        except Exception as e:
            logger.error(f"Error updating survey statistics: {str(e)}")
            # Don't fail the response if stats update fails
    
    def _update_customer_interactions(self, customer):
        """Update customer interaction count"""
        try:
            if hasattr(customer, 'increment_interactions'):
                customer.increment_interactions(interaction_type='survey_response')
            else:
                # Manual update if method doesn't exist
                customer.total_interactions += 1
                customer.last_interaction_date = timezone.now()
                customer.save(update_fields=['total_interactions', 'last_interaction_date', 'updated_at'])
                
        except Exception as e:
            logger.warning(f"Error updating customer interactions: {str(e)}")
    
    def form_invalid(self, form):
        """Handle invalid form submission"""
        logger.warning(f"Invalid form submission: {form.errors}")
        
        # Show field-specific errors
        for field, errors in form.errors.items():
            for error in errors:
                if field != '__all__':
                    messages.error(
                        self.request, 
                        f"{field.replace('_', ' ').title()}: {error}"
                    )
                else:
                    messages.error(self.request, error)
        
        return super().form_invalid(form)
    
    def get_success_url(self):
        """Redirect to thank you page"""
        try:
            if hasattr(self, 'object') and self.object:
                return reverse('survey_response:thank_you', kwargs={'pk': self.object.pk})
        except Exception as e:
            logger.error(f"Error getting success URL: {str(e)}")
        
        # Fallback URLs
        try:
            return reverse('surveys:thank_you')
        except:
            return reverse('home')
        
class SurveyResponseCreateView1(CreateView):
    """
    Unified view for collecting survey responses from both registered and anonymous customers.
    ALL customers inherit the survey's organization.
    """
    template_name = 'survey_response/survey-response-form.html'
    form_class = SurveyResponseForm
    
    def dispatch(self, request, *args, **kwargs):
        """
        Initialize survey and ensure organization is always available
        """
        try:
            # Get survey from URL
            survey_id = kwargs.get('survey_id')
            
            # Get active survey with organization
            self.survey = get_object_or_404(
                Survey.objects.select_related('organization'),
                pk=survey_id,
                status='active'
            )
            
            # CRITICAL: Store organization from survey - ALL customers inherit this
            self.organization = self.survey.organization
            
            if not self.organization:
                logger.error(f"Survey {survey_id} has no organization")
                raise Http404(_("Survey has no organization"))
            
            # Check survey accessibility
            if not self._is_survey_accessible():
                return self._handle_inaccessible_survey()
            
            return super().dispatch(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error initializing survey: {str(e)}", exc_info=True)
            messages.error(request, _("An error occurred. Please try again."))
            return render(request, 'survey_response/survey-error.html', status=500)
    
    def _is_survey_accessible(self):
        """Check if survey is accessible"""
        if not self.survey or not self.organization:
            return False
        
        # Check status
        if self.survey.status != 'active':
            logger.warning(f"Survey {self.survey.id} is not active")
            return False
        
        # Check dates
        if self.survey.start_date and timezone.now() < self.survey.start_date:
            logger.warning(f"Survey {self.survey.id} has not started yet")
            return False
        
        if self.survey.end_date and timezone.now() > self.survey.end_date:
            logger.warning(f"Survey {self.survey.id} has ended")
            return False
        
        # Check response limit
        if (self.survey.response_limit and 
            self.survey.total_responses >= self.survey.response_limit):
            logger.warning(f"Survey {self.survey.id} has reached response limit")
            return False
        
        return True
    
    def _handle_inaccessible_survey(self):
        """Handle inaccessible survey"""
        context = {
            'survey': self.survey,
            'organization': self.organization,
            'message': _("This survey is not currently available.")
        }
        return render(self.request, 'survey_response/survey-unavailable.html', context, status=404)
    
    def get_customer(self, request):
        """
        Get or create customer for this survey's organization
        Returns a customer instance ALWAYS tied to survey.organization
        """
        try:
            # CRITICAL: Every customer must belong to this organization
            organization = self.organization
            
            # Priority 1: Check for authenticated user with Customer profile
            if request.user.is_authenticated:
                try:
                    # Check if user has a customer profile in this organization
                    customer = Customer.objects.get(
                        organization=organization,
                        user=request.user
                    )
                    logger.info(f"Found authenticated customer: {customer.email}")
                    return customer
                except Customer.DoesNotExist:
                    # Create customer from authenticated user
                    customer = Customer.objects.create(
                        organization=organization,  # Inherit survey's organization
                        user=request.user,
                        customer_id=f"auth_{uuid.uuid4().hex[:8]}",
                        email=request.user.email,
                        customer_type='authenticated',
                        segment='authenticated',
                        first_name=request.user.first_name or '',
                        last_name=request.user.last_name or '',
                        language_preference=request.GET.get('language', 'en'),
                        metadata={
                            'source': 'survey_response',
                            'survey_id': str(self.survey.id),
                            'created_at': timezone.now().isoformat(),
                            'user_id': str(request.user.id),
                        }
                    )
                    logger.info(f"Created authenticated customer: {customer.email}")
                    return customer
            
            # Priority 2: Check for customer token (for invited surveys)
            customer_token = request.GET.get('token')
            if customer_token:
                try:
                    customer = Customer.objects.get(
                        organization=organization,  # Must be in same organization
                        metadata__contains={'access_token': customer_token}
                    )
                    logger.info(f"Found customer by token: {customer.customer_id}")
                    return customer
                except Customer.DoesNotExist:
                    logger.warning(f"No customer found with token in org {organization.name}")
            
            # Priority 3: Check for customer ID
            customer_id = request.GET.get('customer_id')
            if customer_id:
                try:
                    customer = Customer.objects.get(
                        organization=organization,  # Must be in same organization
                        customer_id=customer_id
                    )
                    logger.info(f"Found customer by ID: {customer.customer_id}")
                    return customer
                except Customer.DoesNotExist:
                    logger.warning(f"No customer found with ID {customer_id} in org {organization.name}")
            
            # Priority 4: Check for email (identified customer)
            email = request.GET.get('email', '').strip().lower()
            if email and '@' in email:
                try:
                    # Try to get existing customer by email in THIS organization
                    customer = Customer.objects.get(
                        organization=organization,  # CRITICAL: Same organization
                        email=email
                    )
                    logger.info(f"Found existing customer by email: {email}")
                    return customer
                except Customer.DoesNotExist:
                    # Create new identified customer in THIS organization
                    customer = Customer.objects.create(
                        organization=organization,  # Inherit survey's organization
                        customer_id=f"id_{uuid.uuid4().hex[:8]}",
                        email=email,
                        customer_type='identified',
                        segment='new',
                        first_name=request.GET.get('first_name', ''),
                        last_name=request.GET.get('last_name', ''),
                        language_preference=request.GET.get('language', 'en'),
                        metadata={
                            'source': 'survey_response',
                            'survey_id': str(self.survey.id),
                            'created_at': timezone.now().isoformat(),
                            'registration_source': 'survey_link'
                        }
                    )
                    logger.info(f"Created new identified customer: {email}")
                    return customer
                except Exception as e:
                    logger.error(f"Error with email customer {email}: {str(e)}")
                    # Fall through to anonymous
            
            # Priority 5: Create anonymous customer (default case)
            return self._create_anonymous_customer(request)
            
        except Exception as e:
            logger.error(f"Error in get_customer: {str(e)}", exc_info=True)
            # Emergency fallback - MUST have organization
            return self._create_emergency_customer()
    
    def _create_anonymous_customer(self, request):
        """
        Create anonymous customer ALWAYS tied to survey's organization
        """
        try:
            # CRITICAL: Use survey's organization
            organization = self.organization
            
            # Use the Customer model's method if available
            if hasattr(Customer, 'get_or_create_anonymous'):
                customer, created = Customer.get_or_create_anonymous(
                    organization=organization,  # Inherit survey's organization
                    request=request,
                    metadata={
                        'source': 'survey_response',
                        'survey_id': str(self.survey.id),
                        'survey_title': self.survey.title,
                        'created_at': timezone.now().isoformat(),
                        'registration_source': 'survey_link',
                        'is_anonymous': True,
                    }
                )
                return customer
            
            # Fallback: Direct creation
            customer_id = f"anon_{uuid.uuid4().hex[:8]}"
            
            customer = Customer.objects.create(
                organization=organization,  # CRITICAL: Set organization
                customer_id=customer_id,
                customer_type='anonymous',
                segment='anonymous',
                email=f"{customer_id}@anonymous.com",
                first_name='Anonymous',
                last_name='User',
                language_preference=request.GET.get('language', 'en'),
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=request.session.session_key or str(uuid.uuid4()),
                metadata={
                    'source': 'survey_response',
                    'survey_id': str(self.survey.id),
                    'survey_title': self.survey.title,
                    'created_at': timezone.now().isoformat(),
                    'registration_source': 'survey_link',
                    'is_anonymous': True,
                    'client_ip': self._get_client_ip(request),
                }
            )
            
            logger.info(f"Created anonymous customer: {customer.customer_id}")
            return customer
            
        except Exception as e:
            logger.error(f"Error creating anonymous customer: {str(e)}", exc_info=True)
            return self._create_emergency_customer()
    
    def _create_emergency_customer(self):
        """
        Emergency fallback - create customer with survey's organization
        This should NEVER fail
        """
        try:
            organization = self.organization
            
            customer_id = f"emergency_{uuid.uuid4().hex[:8]}"
            
            customer = Customer.objects.create(
                organization=organization,  # CRITICAL: Set organization
                customer_id=customer_id,
                customer_type='anonymous',
                segment='anonymous',
                email=f"{customer_id}@anonymous.com",
                first_name='Emergency',
                last_name='Customer',
                metadata={
                    'source': 'survey_response_emergency',
                    'survey_id': str(self.survey.id) if hasattr(self, 'survey') else 'unknown',
                    'created_at': timezone.now().isoformat(),
                    'is_emergency': True,
                }
            )
            
            logger.warning(f"Created emergency customer: {customer.customer_id}")
            return customer
            
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to create emergency customer: {str(e)}")
            # If even emergency creation fails, raise error
            raise ValueError(f"Cannot create customer for survey: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_form_kwargs(self):
        """Pass survey, customer, and request to form"""
        kwargs = super().get_form_kwargs()
        
        # Get or create customer (this happens when form is initialized)
        customer = self.get_customer(self.request)
        
        # Get questions from survey
        questions = self.survey.questions if hasattr(self.survey, 'questions') else []
        
        kwargs.update({
            'questions': questions,
            'survey': self.survey,
            'customer': customer,
            'request': self.request,
            'organization': self.organization  # Pass organization to form
        })
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add survey and customer to template context"""
        context = super().get_context_data(**kwargs)
        
        # Get customer for context
        customer = self.get_customer(self.request)
        
        is_anonymous = customer.customer_type == 'anonymous'
        
        context.update({
            'survey': self.survey,
            'organization': self.organization,
            'customer': customer,
            'page_title': self.survey.title,
            'is_anonymous': is_anonymous,
            'welcome_message': self.survey.welcome_message or _("Thank you for participating!"),
            'completion_message': self.survey.completion_message or _("Thank you for your feedback!"),
        })
        
        # Add question count for progress
        if hasattr(self.survey, 'questions'):
            context['total_questions'] = len(self.survey.questions)
        
        return context
    
    def form_valid(self, form):
        """
        Handle successful form submission
        Ensures ALL foreign keys are properly set
        """
        try:
            with transaction.atomic():
                # Get or create customer
                customer = self.get_customer(self.request)
                
                # Save the survey response using form
                survey_response = form.save_response()
                
                # CRITICAL: Ensure all relationships are set
                survey_response.survey = self.survey
                survey_response.customer = customer
                survey_response.organization = self.organization  # Explicitly set
                
                # Mark as complete
                survey_response.is_complete = True
                survey_response.completed_at = timezone.now()
                
                # Calculate completion time if available
                if hasattr(form, 'start_time') and form.start_time:
                    completion_seconds = (timezone.now() - form.start_time).total_seconds()
                    survey_response.completion_time = timedelta(seconds=completion_seconds)
                
                # Set device type
                user_agent = self.request.META.get('HTTP_USER_AGENT', '').lower()
                if 'mobile' in user_agent:
                    survey_response.device_type = 'mobile'
                elif 'tablet' in user_agent:
                    survey_response.device_type = 'tablet'
                else:
                    survey_response.device_type = 'desktop'
                
                # Set language
                survey_response.language = self.request.GET.get('language', 'en')
                
                # Try to set channel if available
                try:
                    survey_response.channel = Channel.objects.get(
                        organization=self.organization,
                        channel_type='web_form'
                    )
                except (Channel.DoesNotExist, Channel.MultipleObjectsReturned):
                    # If no specific channel, leave null
                    pass
                
                # Save the response
                survey_response.save()
                
                # Store for success URL
                self.object = survey_response
                
                # Update survey statistics
                self._update_survey_statistics()
                
                # Update customer interaction count
                self._update_customer_interactions(customer)
                
                # Trigger sentiment analysis if needed
                if survey_response.has_text_responses:
                    try:
                        success = survey_response.analyze_sentiment_sync()
                        if success:
                            logger.info(f"Sentiment analysis completed for response {survey_response.id}")
                    except Exception as e:
                        logger.error(f"Sentiment analysis error: {str(e)}")
                
                # Log successful submission
                logger.info(
                    f"Survey response submitted: ID={survey_response.id} | "
                    f"Customer={customer.customer_id} | "
                    f"Organization={self.organization.name} | "
                    f"Survey={self.survey.title}"
                )
                
                # Set success message
                messages.success(
                    self.request, 
                    _("Thank you for completing the survey! Your feedback has been recorded.")
                )
                
                return redirect(self.get_success_url())
                
        except Exception as e:
            logger.error(f"Error submitting survey response: {str(e)}", exc_info=True)
            messages.error(
                self.request, 
                _("There was an error submitting your response. Please try again.")
            )
            return self.form_invalid(form)
    
    def _update_survey_statistics(self):
        """Update survey response statistics"""
        try:
            from django.db.models import F
            
            # Use atomic update to prevent race conditions
            self.survey.total_responses = F('total_responses') + 1
            
            # Recalculate response rate
            if self.survey.total_sent > 0:
                new_total = self.survey.total_responses + 1
                self.survey.response_rate = (new_total / self.survey.total_sent) * 100
            
            self.survey.save(update_fields=['total_responses', 'response_rate', 'updated_at'])
            
        except Exception as e:
            logger.error(f"Error updating survey statistics: {str(e)}")
            # Don't fail the response if stats update fails
    
    def _update_customer_interactions(self, customer):
        """Update customer interaction count"""
        try:
            if hasattr(customer, 'increment_interactions'):
                customer.increment_interactions(interaction_type='survey_response')
            else:
                # Manual update if method doesn't exist
                customer.total_interactions += 1
                customer.last_interaction_date = timezone.now()
                customer.save(update_fields=['total_interactions', 'last_interaction_date', 'updated_at'])
                
        except Exception as e:
            logger.warning(f"Error updating customer interactions: {str(e)}")
    
    def form_invalid(self, form):
        """Handle invalid form submission"""
        logger.warning(f"Invalid form submission: {form.errors}")
        
        # Show field-specific errors
        for field, errors in form.errors.items():
            for error in errors:
                if field != '__all__':
                    messages.error(
                        self.request, 
                        f"{field.replace('_', ' ').title()}: {error}"
                    )
                else:
                    messages.error(self.request, error)
        
        return super().form_invalid(form)
    
    def get_success_url(self):
        """Redirect to thank you page"""
        try:
            if hasattr(self, 'object') and self.object:
                return reverse('survey_response:thank_you', kwargs={'pk': self.object.pk})
        except Exception as e:
            logger.error(f"Error getting success URL: {str(e)}")
        
        # Fallback URLs
        try:
            return reverse('surveys:thank_you')
        except:
            return reverse('home')
        
class SurveyResponseCreateView1(CreateView):
    """
    Consolidated and corrected view for customers to complete surveys
    """
    template_name = 'survey_response/survey-response-form.html'
    
    def dispatch(self, request, *args, **kwargs):
        """
        Initialize survey, organization, and customer before processing the view
        """
        try:
            # Get survey from URL parameters
            survey_id = kwargs.get('survey_id')
            
            # Get survey with organization prefetch
            self.survey = get_object_or_404(
                Survey.objects.select_related('organization'),
                pk=survey_id,
                status='active'
            )
            
            # Store organization from survey (CRITICAL)
            self.organization = self.survey.organization
            
            if not self.organization:
                logger.error(f"Survey {survey_id} has no organization")
                raise Http404(_("Survey has no organization"))
            
            # Get or create customer (FIXED: pass organization)
            self.customer = self._get_or_create_customer(request)
            
            # Check if survey is accessible
            if not self._is_survey_accessible():
                return self._handle_inaccessible_survey()
            
            logger.info(
                f"Survey access: {self.survey.title} | "
                f"Customer: {self.customer.customer_id if self.customer else 'None'} | "
                f"Organization: {self.organization.name}"
            )
            
            return super().dispatch(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in survey dispatch: {str(e)}", exc_info=True)
            messages.error(
                request,
                _("An error occurred while loading the survey. Please try again.")
            )
            return render(request, 'survey_response/survey-error.html', status=500)
    
    def _get_or_create_customer(self, request):
        """
        FIXED: Get or create customer with organization properly passed
        """
        try:
            organization = self.organization  # This is set in dispatch
            
            if not organization:
                logger.error("No organization available for customer creation")
                return self._create_emergency_customer()
            
            # Priority: Token > Customer ID > Email > Anonymous
            
            # 1. Try by token
            customer_token = request.GET.get('token')
            if customer_token:
                try:
                    customer = Customer.objects.get(
                        organization=organization,
                        metadata__contains={'access_token': customer_token}
                    )
                    return customer
                except Customer.DoesNotExist:
                    pass
            
            # 2. Try by customer ID
            customer_id = request.GET.get('customer_id')
            if customer_id:
                try:
                    customer = Customer.objects.get(
                        organization=organization,
                        customer_id=customer_id
                    )
                    return customer
                except Customer.DoesNotExist:
                    pass
            
            # 3. Try by email
            email = request.GET.get('email', '').strip().lower()
            if email and '@' in email:
                try:
                    # Check if customer exists in this organization
                    customer = Customer.objects.get(
                        organization=organization,
                        email=email
                    )
                    return customer
                except Customer.DoesNotExist:
                    # Create new identified customer in this organization
                    try:
                        customer = Customer.objects.create(
                            organization=organization,  # CRITICAL: Set organization
                            customer_id=f"id_{uuid.uuid4().hex[:8]}",
                            email=email,
                            customer_type='identified',
                            segment='new',
                            first_name=request.GET.get('first_name', ''),
                            last_name=request.GET.get('last_name', ''),
                            language_preference=request.GET.get('language', 'en'),
                            metadata={
                                'source': 'survey_response',
                                'survey_id': str(self.survey.id),
                                'created_at': timezone.now().isoformat(),
                                'registration_source': 'survey_link'
                            }
                        )
                        return customer
                    except Exception as e:
                        logger.error(f"Error creating customer with email {email}: {str(e)}")
                        # Fall through to anonymous
            
            # 4. Create anonymous customer (most common case)
            # FIXED: Pass organization explicitly
            return self._create_anonymous_customer(request, organization)
            
        except Exception as e:
            logger.error(f"Error in _get_or_create_customer: {str(e)}", exc_info=True)
            # Emergency fallback - ensure organization is passed
            return self._create_emergency_customer()
    
    def _create_anonymous_customer(self, request, organization=None):
        """
        FIXED: Create anonymous customer with organization parameter
        """
        # Use the provided organization or fall back to self.organization
        org = organization or self.organization
        
        if not org:
            logger.error("No organization available for anonymous customer creation")
            return self._create_emergency_customer()
        
        try:
            # Use the Customer model's get_or_create_anonymous method (which handles organization)
            customer, created = Customer.get_or_create_anonymous(
                organization=org,  # CRITICAL: Pass organization
                request=request,
                metadata={
                    'source': 'survey_response',
                    'survey_id': str(self.survey.id),
                    'survey_title': self.survey.title,
                    'created_at': timezone.now().isoformat(),
                    'registration_source': 'survey_link',
                    'is_anonymous': True,
                }
            )
            return customer
            
        except Exception as e:
            logger.error(f"Error in get_or_create_anonymous: {str(e)}", exc_info=True)
            # Fallback to direct creation
            return self._create_anonymous_customer_direct(request, org)
    
    def _create_anonymous_customer_direct(self, request, organization=None):
        """
        Direct creation of anonymous customer when other methods fail
        """
        org = organization or self.organization
        
        if not org:
            logger.error("No organization available for direct customer creation")
            return self._create_emergency_customer()
        
        try:
            # Generate unique identifiers
            customer_id = f"anon_direct_{uuid.uuid4().hex[:8]}"
            email = f"{customer_id}@anonymous.com"
            
            # Get client IP
            ip_address = self._get_client_ip(request)
            
            # Create customer directly WITH ORGANIZATION
            customer = Customer.objects.create(
                organization=org,  # CRITICAL: Set organization
                customer_id=customer_id,
                customer_type='anonymous',
                segment='anonymous',
                email=email,
                first_name='Anonymous',
                last_name='User',
                language_preference=request.GET.get('language', 'en'),
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=request.session.session_key or str(uuid.uuid4()),
                metadata={
                    'source': 'survey_response',
                    'survey_id': str(self.survey.id),
                    'survey_title': self.survey.title,
                    'created_at': timezone.now().isoformat(),
                    'registration_source': 'survey_link',
                    'is_anonymous': True,
                    'created_method': 'direct_creation',
                    'client_ip': ip_address,
                }
            )
            
            return customer
            
        except Exception as e:
            logger.error(f"Error in direct customer creation: {str(e)}", exc_info=True)
            return self._create_emergency_customer(org)
    
    def _create_emergency_customer(self, organization=None):
        """
        Emergency fallback when all other methods fail
        """
        org = organization or self.organization
        
        if not org:
            # Last resort - try to get organization from survey
            if hasattr(self, 'survey') and self.survey:
                org = self.survey.organization
            
            if not org:
                logger.critical("CRITICAL: No organization available for emergency customer creation")
                # This should never happen in normal operation
                raise ValueError("Cannot create customer: No organization available")
        
        try:
            customer_id = f"emergency_{uuid.uuid4().hex[:8]}"
            
            customer = Customer.objects.create(
                organization=org,  # CRITICAL: Set organization
                customer_id=customer_id,
                customer_type='anonymous',
                segment='anonymous',
                email=f"{customer_id}@anonymous.com",
                first_name='Emergency',
                last_name='Customer',
                metadata={
                    'source': 'survey_response_emergency',
                    'survey_id': str(self.survey.id) if hasattr(self, 'survey') else 'unknown',
                    'created_at': timezone.now().isoformat(),
                    'is_emergency': True,
                }
            )
            
            logger.warning(f"Created emergency customer: {customer.customer_id} in org: {org.name}")
            return customer
            
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to create emergency customer: {str(e)}")
            # This is a critical failure
            raise ValueError(f"Cannot create customer: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _is_survey_accessible(self):
        """Check if survey is accessible"""
        if not self.survey:
            return False
        
        if self.survey.status != 'active':
            return False
        
        if self.survey.start_date and timezone.now() < self.survey.start_date:
            return False
        
        if self.survey.end_date and timezone.now() > self.survey.end_date:
            return False
        
        if (self.survey.response_limit and 
            self.survey.total_responses >= self.survey.response_limit):
            return False
        
        return True
    
    def _handle_inaccessible_survey(self):
        """Handle cases where survey is not accessible"""
        context = {
            'survey': self.survey,
            'organization': self.organization,
            'message': _("This survey is not currently available.")
        }
        return render(self.request, 'survey_response/survey-unavailable.html', context, status=404)
    
    def get_form_kwargs(self):
        """Pass survey, customer, and request to form"""
        kwargs = super().get_form_kwargs()
        
        # Get questions from survey
        questions = self.survey.questions if hasattr(self.survey, 'questions') else []
        
        kwargs.update({
            'questions': questions,
            'survey': self.survey,
            'customer': self.customer,
            'request': self.request,
            'organization': self.organization
        })
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add survey and customer to template context"""
        context = super().get_context_data(**kwargs)
        
        is_anonymous = self.customer and self.customer.customer_type == 'anonymous'
        
        context.update({
            'survey': self.survey,
            'organization': self.organization,
            'customer': self.customer,
            'page_title': self.survey.title,
            'is_anonymous': is_anonymous,
            'welcome_message': self.survey.welcome_message or _("Thank you for participating!"),
        })
        
        return context
    
    def form_valid(self, form):
        """
        Handle successful form submission
        """
        try:
            with transaction.atomic():
                # Ensure customer exists
                if not self.customer:
                    self.customer = self._create_emergency_customer()
                
                # Save the survey response using the form
                survey_response = form.save_response()
                
                # CRITICAL: Ensure all relationships are set
                survey_response.survey = self.survey
                survey_response.customer = self.customer
                
                # Mark as complete
                survey_response.is_complete = True
                survey_response.completed_at = timezone.now()
                
                # Set device type
                user_agent = self.request.META.get('HTTP_USER_AGENT', '').lower()
                if 'mobile' in user_agent:
                    survey_response.device_type = 'mobile'
                elif 'tablet' in user_agent:
                    survey_response.device_type = 'tablet'
                else:
                    survey_response.device_type = 'desktop'
                
                # Save the response
                survey_response.save()
                
                # Store for success URL
                self.object = survey_response
                
                # Update survey statistics
                self._update_survey_statistics()
                
                # Log successful submission
                logger.info(
                    f"Survey response submitted: ID={survey_response.id} | "
                    f"Customer={self.customer.customer_id} | "
                    f"Organization={self.organization.name}"
                )
                
                messages.success(
                    self.request, 
                    _("Thank you for completing the survey! Your feedback has been recorded.")
                )
                
                return redirect(self.get_success_url())
                
        except Exception as e:
            logger.error(f"Error submitting survey response: {str(e)}", exc_info=True)
            messages.error(
                self.request, 
                _("There was an error submitting your response. Please try again.")
            )
            return self.form_invalid(form)
    
    def _update_survey_statistics(self):
        """Update survey response statistics"""
        try:
            from django.db.models import F
            
            self.survey.total_responses = F('total_responses') + 1
            if self.survey.total_sent > 0:
                self.survey.response_rate = (self.survey.total_responses / self.survey.total_sent) * 100
            self.survey.save(update_fields=['total_responses', 'response_rate', 'updated_at'])
        except Exception as e:
            logger.error(f"Error updating survey statistics: {str(e)}")
    
    def get_success_url(self):
        """Redirect to thank you page"""
        try:
            if hasattr(self, 'object') and self.object:
                return reverse('surveys:survey-response-thank-you', kwargs={'pk': self.object.pk})
        except Exception:
            pass
        
        # Fallback URLs
        if hasattr(self, 'survey') and self.survey:
            return reverse('surveys:survey-response-thank-you', kwargs={'survey_id': self.survey.id})
        
        return '/thank-you/'
 

class SurveyResponseThankYouView(DetailView):
    """Thank you page after survey completion"""
    model = SurveyResponse
    template_name = 'survey_responses/survey-thank-you.html'
    context_object_name = 'survey_response'
    
    def get_queryset(self):
        return SurveyResponse.objects.select_related('survey', 'customer')

class SurveyResponseDetailView(LoginRequiredMixin, DetailView):
    """View for organization members to see individual responses"""
    model = SurveyResponse
    template_name = 'survey_responses/survey-response-detail.html'
    context_object_name = 'response'
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        # Check if user has permission to view this response
        if not self._has_permission(request.user, self.object):
            raise PermissionDenied(_("You don't have permission to view this survey response."))
        
        return response
    
    def _has_permission(self, user, survey_response):
        """Check if user can view this survey response"""
        try:
            membership = OrganizationMember.objects.get(
                organization=survey_response.survey.organization,
                user=user,
                is_active=True
            )
            return membership.role in ['owner', 'admin', 'manager', 'analyst', 'viewer']
        except OrganizationMember.DoesNotExist:
            return False
    
    def get_queryset(self):
        return SurveyResponse.objects.select_related(
            'survey', 
            'customer', 
            'survey__organization', 
            'channel'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        response_obj = self.object
        survey = response_obj.survey
        
        # Get organization_pk and survey_id from the response's survey
        context['organization_pk'] = survey.organization.pk
        context['survey_id'] = survey.pk
        
        # Parse response data and match with questions
        response_data = response_obj.response_data or {}
        
        # Try different possible relationships for questions
        try:
            # Try common relationship names
            if hasattr(survey, 'questions'):
                questions = survey.questions.all().order_by('order')
            elif hasattr(survey, 'survey_questions'):
                questions = survey.survey_questions.all().order_by('order')
            elif hasattr(survey, 'question_set'):
                questions = survey.question_set.all().order_by('order')
            elif hasattr(survey, 'surveyquestion_set'):
                questions = survey.surveyquestion_set.all().order_by('order')
            else:
                # If no relationship found, try to get questions from the Question model
                from .models import SurveyQuestion
                questions = SurveyQuestion.objects.filter(survey=survey).order_by('order')
        except Exception as e:
            logger.error(f"Error fetching questions for survey {survey.id}: {str(e)}")
            questions = []
        
        # Create a structured list of questions with their answers
        questions_with_answers = []
        for question in questions:
            question_id = str(question.id)
            answer = response_data.get(question_id, None)
            
            questions_with_answers.append({
                'question': question,
                'question_text': getattr(question, 'question_text', getattr(question, 'text', str(question))),
                'question_type': getattr(question, 'question_type', getattr(question, 'type', 'text')),
                'answer': answer,
                'answer_display': self._format_answer(question, answer)
            })
        
        context['questions_with_answers'] = questions_with_answers
        context['survey'] = survey
        context['customer'] = response_obj.customer
        
        # Add sentiment color class
        if response_obj.sentiment_score is not None:
            if response_obj.sentiment_score > 0.3:
                context['sentiment_class'] = 'success'
            elif response_obj.sentiment_score < -0.3:
                context['sentiment_class'] = 'danger'
            else:
                context['sentiment_class'] = 'warning'
        else:
            context['sentiment_class'] = 'secondary'
        
        return context
    
    def _format_answer(self, question, answer):
        """Format answer based on question type"""
        if answer is None or answer == '':
            return _('No answer provided')
        
        question_type = getattr(question, 'question_type', getattr(question, 'type', 'text'))
        
        if question_type in ['text', 'textarea', 'short_text', 'long_text']:
            return str(answer)
        
        elif question_type in ['rating', 'star_rating']:
            # Assuming rating is a number
            try:
                rating = int(answer)
                max_rating = getattr(question, 'max_rating', 5)
                stars = '★' * rating + '☆' * (max_rating - rating)
                return f"{stars} ({rating}/{max_rating})"
            except (ValueError, TypeError):
                return str(answer)
        
        elif question_type in ['multiple_choice', 'radio', 'select', 'dropdown']:
            # Answer could be a single value
            return str(answer)
        
        elif question_type in ['checkbox', 'multi_select', 'checkboxes']:
            # Answer could be a list
            if isinstance(answer, list):
                return ', '.join(str(item) for item in answer)
            return str(answer)
        
        elif question_type in ['yes_no', 'boolean']:
            if isinstance(answer, bool):
                return _('Yes') if answer else _('No')
            elif isinstance(answer, str):
                answer_lower = answer.lower()
                if answer_lower in ['yes', 'true', '1', 'y']:
                    return _('Yes')
                elif answer_lower in ['no', 'false', '0', 'n']:
                    return _('No')
            return str(answer)
        
        elif question_type in ['nps', 'net_promoter_score']:
            # Net Promoter Score (0-10)
            try:
                score = int(answer)
                if score >= 9:
                    category = _('Promoter')
                    badge_class = 'success'
                elif score >= 7:
                    category = _('Passive')
                    badge_class = 'warning'
                else:
                    category = _('Detractor')
                    badge_class = 'danger'
                return f"{score}/10 <span class='badge bg-{badge_class}'>{category}</span>"
            except (ValueError, TypeError):
                return str(answer)
        
        elif question_type in ['scale', 'slider']:
            try:
                value = float(answer)
                min_val = getattr(question, 'min_value', 0)
                max_val = getattr(question, 'max_value', 10)
                return f"{value} (on a scale of {min_val} to {max_val})"
            except (ValueError, TypeError):
                return str(answer)
        
        elif question_type in ['date', 'datetime']:
            try:
                from django.utils import timezone
                from datetime import datetime
                if isinstance(answer, str):
                    # Try to parse date string
                    date_obj = datetime.fromisoformat(answer.replace('Z', '+00:00'))
                    return date_obj.strftime('%B %d, %Y')
                return str(answer)
            except:
                return str(answer)
        
        elif question_type in ['email', 'url', 'phone']:
            return str(answer)
        
        else:
            # Default formatting for unknown types
            if isinstance(answer, dict):
                return ', '.join(f"{k}: {v}" for k, v in answer.items())
            elif isinstance(answer, list):
                return ', '.join(str(item) for item in answer)
            return str(answer)
      
    
class SurveyResponseDetailView1(LoginRequiredMixin, DetailView):
    """View for organization members to see individual responses"""
    model = SurveyResponse
    template_name = 'survey_responses/survey-response-detail.html'
    context_object_name = 'response'
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        # Check if user has permission to view this response
        if not self._has_permission(request.user, self.object):
            raise PermissionDenied(_("You don't have permission to view this survey response."))
        
        return response
    
    def _has_permission(self, user, survey_response):
        """Check if user can view this survey response"""
        try:
            membership = OrganizationMember.objects.get(
                organization=survey_response.survey.organization,
                user=user,
                is_active=True
            )
            return membership.role in ['owner', 'admin', 'manager', 'analyst', 'viewer']
        except OrganizationMember.DoesNotExist:
            return False
    
    def get_queryset(self):
        return SurveyResponse.objects.select_related(
            'survey', 
            'customer', 
            'survey__organization', 
            'channel'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Parse response data and match with questions
        response_obj = self.object
        survey = response_obj.survey
        response_data = response_obj.response_data or {}
        
        # Try different possible relationships for questions
        # Adjust the relationship name based on your actual Survey model
        try:
            # Try common relationship names
            if hasattr(survey, 'questions'):
                questions = survey.questions.all().order_by('order')
            elif hasattr(survey, 'survey_questions'):
                questions = survey.survey_questions.all().order_by('order')
            elif hasattr(survey, 'question_set'):
                questions = survey.question_set.all().order_by('order')
            elif hasattr(survey, 'surveyquestion_set'):
                questions = survey.surveyquestion_set.all().order_by('order')
            else:
                # If no relationship found, try to get questions from the Question model
                from .models import SurveyQuestion  # Adjust import based on your models
                questions = SurveyQuestion.objects.filter(survey=survey).order_by('order')
        except Exception as e:
            # Log the error and return empty questions list
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching questions for survey {survey.id}: {str(e)}")
            questions = []
        
        # Create a structured list of questions with their answers
        questions_with_answers = []
        for question in questions:
            question_id = str(question.id)
            answer = response_data.get(question_id, None)
            
            questions_with_answers.append({
                'question': question,
                'question_text': getattr(question, 'question_text', getattr(question, 'text', str(question))),
                'question_type': getattr(question, 'question_type', getattr(question, 'type', 'text')),
                'answer': answer,
                'answer_display': self._format_answer(question, answer)
            })
        
        context['questions_with_answers'] = questions_with_answers
        context['survey'] = survey
        context['customer'] = response_obj.customer
        
        # Add sentiment color class
        if response_obj.sentiment_score is not None:
            if response_obj.sentiment_score > 0.3:
                context['sentiment_class'] = 'success'
            elif response_obj.sentiment_score < -0.3:
                context['sentiment_class'] = 'danger'
            else:
                context['sentiment_class'] = 'warning'
        else:
            context['sentiment_class'] = 'secondary'
        
        return context
    
    def _format_answer(self, question, answer):
        """Format answer based on question type"""
        if answer is None or answer == '':
            return _('No answer provided')
        
        # Get question type safely
        question_type = getattr(question, 'question_type', getattr(question, 'type', 'text'))
        
        if question_type in ['text', 'textarea', 'short_text', 'long_text']:
            return str(answer)
        
        elif question_type in ['rating', 'star_rating']:
            # Assuming rating is a number
            try:
                rating = int(answer)
                max_rating = getattr(question, 'max_rating', 5)
                stars = '★' * rating + '☆' * (max_rating - rating)
                return f"{stars} ({rating}/{max_rating})"
            except (ValueError, TypeError):
                return str(answer)
        
        elif question_type in ['multiple_choice', 'radio', 'select', 'dropdown']:
            # Answer could be a single value
            return str(answer)
        
        elif question_type in ['checkbox', 'multi_select', 'checkboxes']:
            # Answer could be a list
            if isinstance(answer, list):
                return ', '.join(str(item) for item in answer)
            return str(answer)
        
        elif question_type in ['yes_no', 'boolean']:
            if isinstance(answer, bool):
                return _('Yes') if answer else _('No')
            elif isinstance(answer, str):
                answer_lower = answer.lower()
                if answer_lower in ['yes', 'true', '1', 'y']:
                    return _('Yes')
                elif answer_lower in ['no', 'false', '0', 'n']:
                    return _('No')
            return str(answer)
        
        elif question_type in ['nps', 'net_promoter_score']:
            # Net Promoter Score (0-10)
            try:
                score = int(answer)
                if score >= 9:
                    category = _('Promoter')
                    badge_class = 'success'
                elif score >= 7:
                    category = _('Passive')
                    badge_class = 'warning'
                else:
                    category = _('Detractor')
                    badge_class = 'danger'
                return f"{score}/10 <span class='badge bg-{badge_class}'>{category}</span>"
            except (ValueError, TypeError):
                return str(answer)
        
        elif question_type in ['scale', 'slider']:
            try:
                value = float(answer)
                min_val = getattr(question, 'min_value', 0)
                max_val = getattr(question, 'max_value', 10)
                return f"{value} (on a scale of {min_val} to {max_val})"
            except (ValueError, TypeError):
                return str(answer)
        
        elif question_type in ['date', 'datetime']:
            try:
                from django.utils import timezone
                from datetime import datetime
                if isinstance(answer, str):
                    # Try to parse date string
                    date_obj = datetime.fromisoformat(answer.replace('Z', '+00:00'))
                    return date_obj.strftime('%B %d, %Y')
                return str(answer)
            except:
                return str(answer)
        
        elif question_type in ['email', 'url', 'phone']:
            return str(answer)
        
        else:
            # Default formatting for unknown types
            if isinstance(answer, dict):
                return ', '.join(f"{k}: {v}" for k, v in answer.items())
            elif isinstance(answer, list):
                return ', '.join(str(item) for item in answer)
            return str(answer)

from django.utils import timezone
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth

class SurveyResponseListView(LoginRequiredMixin, ListView):
    """View for organization members to list survey responses"""
    model = SurveyResponse
    template_name = 'survey_responses/survey-response-list.html'
    context_object_name = 'responses'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        # Get organization_pk and survey_id from URL
        self.organization_pk = kwargs.get('organization_pk')
        self.survey_id = kwargs.get('survey_id')
        
        # Get filter parameters
        self.time_filter = request.GET.get('time_filter', 'all')
        self.sentiment_filter = request.GET.get('sentiment_filter', 'all')
        self.status_filter = request.GET.get('status_filter', 'all')
        self.device_filter = request.GET.get('device_filter', 'all')
        
        # Verify user has access to this organization and survey
        if not self._has_permission(request.user):
            raise PermissionDenied(_("You don't have permission to view these survey responses."))
        
        return super().dispatch(request, *args, **kwargs)
    
    def _has_permission(self, user):
        """Check if user can access this organization and survey"""
        try:
            # Check organization membership
            membership = OrganizationMember.objects.get(
                organization_id=self.organization_pk,
                user=user,
                is_active=True
            )
            
            # Check if survey exists and belongs to this organization
            survey = Survey.objects.filter(
                id=self.survey_id,
                organization_id=self.organization_pk
            ).exists()
            
            return membership.role in ['owner', 'admin', 'manager', 'analyst', 'viewer'] and survey
            
        except OrganizationMember.DoesNotExist:
            return False
    
    def get_queryset(self):
        # Start with all responses for this survey and organization
        queryset = SurveyResponse.objects.filter(
            survey_id=self.survey_id,
            survey__organization_id=self.organization_pk
        ).select_related('survey', 'customer').order_by('-created_at')
        
        # Apply time filter
        now = timezone.now()
        if self.time_filter == 'today':
            queryset = queryset.filter(created_at__date=now.date())
        elif self.time_filter == 'yesterday':
            queryset = queryset.filter(created_at__date=now.date() - timedelta(days=1))
        elif self.time_filter == 'week':
            queryset = queryset.filter(created_at__gte=now - timedelta(days=7))
        elif self.time_filter == 'month':
            queryset = queryset.filter(created_at__gte=now - timedelta(days=30))
        elif self.time_filter == 'quarter':
            queryset = queryset.filter(created_at__gte=now - timedelta(days=90))
        
        # Apply sentiment filter
        if self.sentiment_filter == 'positive':
            queryset = queryset.filter(sentiment_score__gt=0.1)
        elif self.sentiment_filter == 'negative':
            queryset = queryset.filter(sentiment_score__lt=-0.1)
        elif self.sentiment_filter == 'neutral':
            queryset = queryset.filter(
                Q(sentiment_score__gte=-0.1) & Q(sentiment_score__lte=0.1)
            )
        elif self.sentiment_filter == 'not_analyzed':
            queryset = queryset.filter(sentiment_score__isnull=True)
        
        # Apply status filter
        if self.status_filter == 'completed':
            queryset = queryset.filter(is_complete=True)
        elif self.status_filter == 'incomplete':
            queryset = queryset.filter(is_complete=False)
        elif self.status_filter == 'analyzed':
            queryset = queryset.filter(ai_analyzed=True)
        elif self.status_filter == 'pending_analysis':
            queryset = queryset.filter(
                Q(ai_analyzed=False) & Q(analysis_status='pending')
            )
        
        # Apply device filter
        if self.device_filter != 'all':
            queryset = queryset.filter(device_type=self.device_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add organization and survey context
        context['organization_pk'] = self.organization_pk
        context['survey_id'] = self.survey_id
        
        # Get the survey object
        try:
            context['survey'] = Survey.objects.get(
                id=self.survey_id,
                organization_id=self.organization_pk
            )
        except Survey.DoesNotExist:
            context['survey'] = None
        
        # Get statistics
        queryset = self.get_queryset()
        
        # Total responses count
        total_responses = queryset.count()
        context['total_responses'] = total_responses
        
        # Completed responses count
        completed_responses = queryset.filter(is_complete=True).count()
        context['completed_responses'] = completed_responses
        
        # Average sentiment score
        avg_sentiment = queryset.filter(
            sentiment_score__isnull=False
        ).aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0.0
        context['avg_sentiment'] = round(avg_sentiment, 2)
        
        # Pending analysis count
        pending_analysis = queryset.filter(
            ai_analyzed=False,
            analysis_status='pending',
            is_complete=True
        ).count()
        context['pending_analysis'] = pending_analysis
        
        # Positive responses count (sentiment > 0.1)
        positive_responses = queryset.filter(
            sentiment_score__gt=0.1
        ).count()
        context['positive_responses'] = positive_responses
        
        # Negative responses count (sentiment < -0.1)
        negative_responses = queryset.filter(
            sentiment_score__lt=-0.1
        ).count()
        context['negative_responses'] = negative_responses
        
        # Get other surveys in the same organization for filtering
        user_organizations = OrganizationMember.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('organization', flat=True)
        
        context['available_surveys'] = Survey.objects.filter(
            organization_id__in=user_organizations
        ).order_by('title')
        
        # Add filter context for template
        context['time_filter'] = self.time_filter
        context['sentiment_filter'] = self.sentiment_filter
        context['status_filter'] = self.status_filter
        context['device_filter'] = self.device_filter
        
        # Add filter options for dropdowns
        context['time_filters'] = [
            {'value': 'all', 'label': _('All Time')},
            {'value': 'today', 'label': _('Today')},
            {'value': 'yesterday', 'label': _('Yesterday')},
            {'value': 'week', 'label': _('Last 7 Days')},
            {'value': 'month', 'label': _('Last 30 Days')},
            {'value': 'quarter', 'label': _('Last 90 Days')},
        ]
        
        context['sentiment_filters'] = [
            {'value': 'all', 'label': _('All Sentiments')},
            {'value': 'positive', 'label': _('Positive (> 0.1)')},
            {'value': 'negative', 'label': _('Negative (< -0.1)')},
            {'value': 'neutral', 'label': _('Neutral (-0.1 to 0.1)')},
            {'value': 'not_analyzed', 'label': _('Not Analyzed')},
        ]
        
        context['status_filters'] = [
            {'value': 'all', 'label': _('All Statuses')},
            {'value': 'completed', 'label': _('Completed')},
            {'value': 'incomplete', 'label': _('Incomplete')},
            {'value': 'analyzed', 'label': _('AI Analyzed')},
            {'value': 'pending_analysis', 'label': _('Pending Analysis')},
        ]
        
        context['device_filters'] = [
            {'value': 'all', 'label': _('All Devices')},
            {'value': 'desktop', 'label': _('Desktop')},
            {'value': 'mobile', 'label': _('Mobile')},
            {'value': 'tablet', 'label': _('Tablet')},
            {'value': 'other', 'label': _('Other')},
        ]
        
        # Get device distribution for chart
        device_distribution = queryset.exclude(device_type__isnull=True).values(
            'device_type'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        context['device_distribution'] = list(device_distribution)
        
        # Get sentiment distribution
        sentiment_distribution = []
        sentiment_ranges = [
            {'label': 'Very Negative (< -0.5)', 'min': -1.0, 'max': -0.5},
            {'label': 'Negative (-0.5 to -0.1)', 'min': -0.5, 'max': -0.1},
            {'label': 'Neutral (-0.1 to 0.1)', 'min': -0.1, 'max': 0.1},
            {'label': 'Positive (0.1 to 0.5)', 'min': 0.1, 'max': 0.5},
            {'label': 'Very Positive (> 0.5)', 'min': 0.5, 'max': 1.0},
            {'label': 'Not Analyzed', 'min': None, 'max': None},
        ]
        
        for sentiment_range in sentiment_ranges:
            if sentiment_range['min'] is None:
                count = queryset.filter(sentiment_score__isnull=True).count()
            else:
                count = queryset.filter(
                    sentiment_score__gte=sentiment_range['min'],
                    sentiment_score__lt=sentiment_range['max']
                ).count()
            
            sentiment_distribution.append({
                'label': sentiment_range['label'],
                'count': count
            })
        
        context['sentiment_distribution'] = sentiment_distribution
        
        return context

from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import DetailView
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.translation import gettext as _
from datetime import timedelta


class SurveyAnalyticsView(LoginRequiredMixin, DetailView):
    """Analytics view for survey responses with comprehensive metrics"""
    model = Survey
    template_name = 'surveys/survey-analytics.html'
    context_object_name = 'survey'
    
    def get_object(self, queryset=None):
        """Get survey with organization context"""
        if queryset is None:
            queryset = self.get_queryset()
        
        # Get organization_pk from URL
        organization_pk = self.kwargs.get('organization_pk')
        
        # Get survey with organization check
        survey = get_object_or_404(
            queryset,
            pk=self.kwargs.get('pk'),
            organization__pk=organization_pk
        )
        
        return survey
    
    def dispatch(self, request, *args, **kwargs):
        """Check permissions before processing the request"""
        survey = self.get_object()
        
        # Check permissions
        if not self._has_permission(request.user, survey):
            raise PermissionDenied(_("You don't have permission to view this survey."))
        
        return super().dispatch(request, *args, **kwargs)
    
    def _has_permission(self, user, survey):
        """Check if user can view survey analytics"""
        try:
            membership = OrganizationMember.objects.get(
                organization=survey.organization,
                user=user,
                is_active=True
            )
            # Allow owners, admins, managers, and analysts
            return membership.role in ['owner', 'admin', 'manager', 'analyst']
        except OrganizationMember.DoesNotExist:
            return False
    
    def _get_questions_data(self, survey):
        """Extract and format questions from JSONField"""
        questions = survey.questions or []
        
        # Calculate question statistics
        question_count = len(questions) if isinstance(questions, list) else 0
        
        # Count required questions
        required_questions = 0
        if isinstance(questions, list):
            for question in questions:
                if isinstance(question, dict) and question.get('required'):
                    required_questions += 1
        
        return {
            'questions_list': questions,
            'question_count': question_count,
            'required_questions': required_questions
        }
    
    def _get_response_trends(self, survey, days=30):
        """Get daily response trends for the last N days"""
        thirty_days_ago = timezone.now() - timedelta(days=days)
        
        # Get completed responses with date grouping
        response_trends = survey.responses.filter(
            created_at__gte=thirty_days_ago,
            is_complete=True
        ).annotate(
            date_only=TruncDate('created_at')
        ).values('date_only').annotate(
            count=Count('id')
        ).order_by('date_only')
        
        # Format for chart
        formatted_trends = []
        for trend in response_trends:
            if trend['date_only']:
                formatted_trends.append({
                    'date': trend['date_only'].strftime('%Y-%m-%d'),
                    'count': trend['count']
                })
        
        # If no trends found, create empty data for visualization
        if not formatted_trends:
            for i in range(days):
                date = (timezone.now() - timedelta(days=i)).date()
                formatted_trends.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'count': 0
                })
            formatted_trends.reverse()  # Oldest to newest
        
        return formatted_trends
    
    def _get_device_breakdown(self, responses):
        """Get device type distribution"""
        device_breakdown = responses.values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Format device types for display
        formatted_breakdown = []
        for device in device_breakdown:
            device_type = device['device_type'] or 'unknown'
            formatted_breakdown.append({
                'device_type': device_type,
                'count': device['count']
            })
        
        return formatted_breakdown
    
    def _get_sentiment_analysis(self, responses):
        """Calculate sentiment metrics"""
        # Average sentiment
        avg_sentiment = responses.aggregate(
            avg_sentiment=Avg('sentiment_score')
        )['avg_sentiment'] or 0
        
        # Count total responses for distribution calculation
        total_count = responses.count()
        
        # Sentiment distribution
        positive_count = responses.filter(sentiment_score__gte=0.5).count()
        negative_count = responses.filter(sentiment_score__lte=-0.5).count()
        neutral_count = total_count - positive_count - negative_count
        
        sentiment_distribution = {
            'positive': positive_count,
            'neutral': neutral_count,
            'negative': negative_count,
        }
        
        return {
            'avg_sentiment': round(avg_sentiment, 2),
            'distribution': sentiment_distribution
        }
    
    def _get_completion_metrics(self, responses):
        """Calculate completion time metrics"""
        avg_completion_minutes = None
        completion_data = []
        
        # Get responses with completion time
        completed_with_time = responses.filter(completion_time__isnull=False)
        
        if completed_with_time.exists():
            # Calculate total completion time in seconds
            total_seconds = 0
            valid_responses = 0
            
            for response in completed_with_time:
                time_value = response.completion_time
                if time_value is not None:
                    if isinstance(time_value, timedelta):
                        total_seconds += time_value.total_seconds()
                    elif isinstance(time_value, (int, float)):
                        total_seconds += float(time_value)
                    valid_responses += 1
            
            if valid_responses > 0:
                avg_completion_minutes = round(total_seconds / valid_responses / 60, 1)
                
                # Get completion time distribution
                fast_responses = 0
                medium_responses = 0
                slow_responses = 0
                
                for response in completed_with_time:
                    time_value = response.completion_time
                    if time_value is not None:
                        if isinstance(time_value, timedelta):
                            minutes = time_value.total_seconds() / 60
                        else:
                            minutes = float(time_value) / 60
                        
                        if minutes < 2:
                            fast_responses += 1
                        elif minutes < 5:
                            medium_responses += 1
                        else:
                            slow_responses += 1
                
                completion_data = [
                    {'range': '< 2 min', 'count': fast_responses},
                    {'range': '2-5 min', 'count': medium_responses},
                    {'range': '> 5 min', 'count': slow_responses}
                ]
        
        return {
            'avg_completion_minutes': avg_completion_minutes,
            'completion_distribution': completion_data
        }
    
    def _get_response_channels(self, survey):
        """Get response distribution by channel"""
        channels = survey.responses.filter(
            is_complete=True
        ).values('channel').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return list(channels)
    
    def _get_survey_specific_metrics(self, survey, responses):
        """Get survey-specific metrics based on survey type"""
        metrics = {}
        
        # Get all completed responses
        total_responses = responses.count()
        
        # CSAT metrics (for CSAT surveys)
        if survey.survey_type == 'csat':
            csat_scores = []
            for response in responses:
                if response.response_data and isinstance(response.response_data, dict):
                    # Look for CSAT score in response data
                    for key, value in response.response_data.items():
                        if isinstance(value, (int, float)) and 1 <= value <= 10:
                            csat_scores.append(value)
                            break
            
            if csat_scores:
                avg_csat = sum(csat_scores) / len(csat_scores)
                
                # Categorize responses
                promoters = len([s for s in csat_scores if s >= 9])
                passives = len([s for s in csat_scores if 7 <= s <= 8])
                detractors = len([s for s in csat_scores if s <= 6])
                
                metrics['csat'] = {
                    'avg_score': round(avg_csat, 1),
                    'promoters': promoters,
                    'passives': passives,
                    'detractors': detractors,
                    'total': len(csat_scores)
                }
        
        # NPS metrics (for NPS surveys)
        elif survey.survey_type == 'nps':
            nps_scores = []
            for response in responses:
                if response.response_data and isinstance(response.response_data, dict):
                    # Look for NPS score in response data (0-10 scale)
                    for key, value in response.response_data.items():
                        if isinstance(value, (int, float)) and 0 <= value <= 10:
                            nps_scores.append(value)
                            break
            
            if nps_scores:
                avg_nps = sum(nps_scores) / len(nps_scores)
                
                # Categorize responses for NPS calculation
                promoters = len([s for s in nps_scores if s >= 9])
                passives = len([s for s in nps_scores if 7 <= s <= 8])
                detractors = len([s for s in nps_scores if s <= 6])
                
                nps_score = ((promoters - detractors) / len(nps_scores)) * 100 if nps_scores else 0
                
                metrics['nps'] = {
                    'avg_score': round(avg_nps, 1),
                    'nps_score': round(nps_score, 1),
                    'promoters': promoters,
                    'passives': passives,
                    'detractors': detractors,
                    'total': len(nps_scores)
                }
        
        return metrics
    
    def get_context_data(self, **kwargs):
        """Prepare all analytics data for the template"""
        context = super().get_context_data(**kwargs)
        survey = self.object
        
        # Get organization from survey
        organization = survey.organization
        
        # Get all completed responses
        responses = survey.responses.filter(is_complete=True)
        total_responses = responses.count()
        
        # Response rate calculation
        total_sent = survey.total_sent or 0
        completion_rate = (total_responses / total_sent * 100) if total_sent > 0 else 0
        
        # Get questions data
        questions_data = self._get_questions_data(survey)
        
        # Get analytics data
        response_trends = self._get_response_trends(survey)
        device_breakdown = self._get_device_breakdown(responses)
        sentiment_metrics = self._get_sentiment_analysis(responses)
        completion_metrics = self._get_completion_metrics(responses)
        response_channels = self._get_response_channels(survey)
        survey_specific_metrics = self._get_survey_specific_metrics(survey, responses)
        
        # Get recent responses for activity feed
        recent_responses = responses.select_related('customer').order_by('-created_at')[:10]
        
        # Response status breakdown
        total_surveys_sent = survey.total_sent or 0
        incomplete_responses = survey.responses.filter(is_complete=False).count()
        
        # Calculate not started responses
        if total_sent > 0:
            not_started = max(0, total_sent - total_responses - incomplete_responses)
        else:
            not_started = 0
        
        # Prepare context data
        context.update({
            'organization': organization,
            'total_responses': total_responses,
            'completion_rate': round(completion_rate, 1),
            'response_trends': response_trends,
            'device_breakdown': device_breakdown,
            'avg_sentiment': sentiment_metrics['avg_sentiment'],
            'sentiment_distribution': sentiment_metrics['distribution'],
            'avg_completion_minutes': completion_metrics['avg_completion_minutes'],
            'completion_distribution': completion_metrics['completion_distribution'],
            'response_channels': response_channels,
            'responses': recent_responses,
            'questions': questions_data['questions_list'],
            'question_count': questions_data['question_count'],
            'required_questions': questions_data['required_questions'],
            'total_sent': total_surveys_sent,
            'incomplete_responses': incomplete_responses,
            'response_rate_data': {
                'completed': total_responses,
                'incomplete': incomplete_responses,
                'not_started': not_started
            },
            'has_csat_data': 'csat' in survey_specific_metrics,
            'has_nps_data': 'nps' in survey_specific_metrics,
            'has_sentiment_data': sentiment_metrics['avg_sentiment'] != 0 or total_responses > 0,
        })
        
        # Add survey-specific metrics if available
        if 'csat' in survey_specific_metrics:
            context['csat_metrics'] = survey_specific_metrics['csat']
        if 'nps' in survey_specific_metrics:
            context['nps_metrics'] = survey_specific_metrics['nps']
        
        # Add additional survey metadata
        if survey.created_at:
            days_active = (timezone.now() - survey.created_at).days
            avg_daily = round(total_responses / max(days_active, 1), 1) if days_active > 0 else 0
        else:
            days_active = 0
            avg_daily = 0
        
        context.update({
            'survey_duration_days': days_active,
            'avg_daily_responses': avg_daily,
        })
        
        return context
    
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

@login_required
@csrf_exempt
def analyze_sentiment_api(request, pk):
    """API endpoint to trigger sentiment analysis for a response"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        response = SurveyResponse.objects.get(pk=pk)
        
        # Check permission
        if not request.user.has_perm('surveys.view_surveyresponse', response):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Trigger analysis
        success = response.analyze_sentiment_sync()
        
        return JsonResponse({
            'success': success,
            'score': response.sentiment_score,
            'analyzed': response.ai_analyzed,
        })
        
    except SurveyResponse.DoesNotExist:
        return JsonResponse({'error': 'Response not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
import csv
import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.utils import timezone
from django.utils.translation import gettext as _
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io

class ExportSurveyResponsesCSVView(LoginRequiredMixin, View):
    """Export survey responses to CSV format"""
    
    def get(self, request, organization_pk, pk, *args, **kwargs):
        survey = get_object_or_404(
            Survey,
            pk=pk,
            organization__pk=organization_pk
        )
        
        # Check permissions
        if not self._has_permission(request.user, survey):
            return HttpResponse(
                _("You don't have permission to export this survey's data."),
                status=403
            )
        
        # Get all completed responses
        responses = survey.responses.filter(is_complete=True).select_related(
            'customer', 'channel'
        ).order_by('-created_at')
        
        # Create the HttpResponse object with CSV header
        response = HttpResponse(content_type='text/csv')
        filename = f"survey_{survey.pk}_responses_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Create CSV writer
        writer = csv.writer(response)
        
        # Write headers based on survey type
        headers = self._get_csv_headers(survey)
        writer.writerow(headers)
        
        # Write data rows
        for response_obj in responses:
            row = self._format_response_row(response_obj, survey)
            writer.writerow(row)
        
        return response
    
    def _has_permission(self, user, survey):
        """Check if user can export survey data"""
        try:
            membership = OrganizationMember.objects.get(
                organization=survey.organization,
                user=user,
                is_active=True
            )
            return membership.role in ['owner', 'admin', 'manager', 'analyst']
        except OrganizationMember.DoesNotExist:
            return False
    
    def _get_csv_headers(self, survey):
        """Get CSV headers based on survey type and structure"""
        headers = [
            _('Response ID'),
            _('Timestamp'),
            _('Customer Email'),
            _('Customer Name'),
            _('Completed'),
            _('Completion Time (min)'),
            _('Channel'),
            _('Device Type'),
            _('Sentiment Score'),
            _('Language'),
        ]
        
        # Add question headers
        questions = survey.questions or []
        for i, question in enumerate(questions, 1):
            question_text = question.get('text', f'Question {i}')
            # Truncate long question text for header
            if len(question_text) > 50:
                question_text = question_text[:47] + '...'
            headers.append(f'Q{i}: {question_text}')
        
        # Add metadata headers
        headers.append(_('Response Metadata'))
        
        return headers
    
    def _format_response_row(self, response_obj, survey):
        """Format a response object into a CSV row"""
        row = [
            str(response_obj.pk),
            response_obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            response_obj.customer.email if response_obj.customer else _('Anonymous'),
            response_obj.customer.get_full_name() if response_obj.customer and hasattr(response_obj.customer, 'get_full_name') else '',
            _('Yes') if response_obj.is_complete else _('No'),
            round(response_obj.completion_time.total_seconds() / 60, 2) if response_obj.completion_time else '',
            response_obj.channel.name if response_obj.channel else '',
            response_obj.get_device_type_display() if response_obj.device_type else '',
            response_obj.sentiment_score if response_obj.sentiment_score is not None else '',
            response_obj.language,
        ]
        
        # Add question answers
        questions = survey.questions or []
        response_data = response_obj.response_data or {}
        
        for i, question in enumerate(questions, 1):
            question_id = question.get('id', f'q{i}')
            answer = response_data.get(question_id, '')
            
            # Format answer based on type
            if isinstance(answer, list):
                answer = ', '.join(str(item) for item in answer)
            elif isinstance(answer, dict):
                answer = json.dumps(answer, ensure_ascii=False)
            elif answer is None:
                answer = ''
            
            row.append(str(answer))
        
        # Add metadata
        metadata = response_obj.metadata or {}
        row.append(json.dumps(metadata, ensure_ascii=False))
        
        return row


class ExportSurveyAnalyticsReportView(LoginRequiredMixin, View):
    """Export survey analytics as a PDF report"""
    
    def get(self, request, organization_pk, pk, *args, **kwargs):
        survey = get_object_or_404(
            Survey,
            pk=pk,
            organization__pk=organization_pk
        )
        
        # Check permissions
        if not self._has_permission(request.user, survey):
            return HttpResponse(
                _("You don't have permission to export this survey's report."),
                status=403
            )
        
        # Generate PDF
        pdf_buffer = self._generate_pdf_report(survey, request.user)
        
        # Create response
        response = HttpResponse(content_type='application/pdf')
        filename = f"survey_{survey.pk}_analytics_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())
        pdf_buffer.close()
        
        return response
    
    def _has_permission(self, user, survey):
        """Check if user can export survey report"""
        try:
            membership = OrganizationMember.objects.get(
                organization=survey.organization,
                user=user,
                is_active=True
            )
            return membership.role in ['owner', 'admin', 'manager', 'analyst']
        except OrganizationMember.DoesNotExist:
            return False
    
    def _generate_pdf_report(self, survey, user):
        """Generate PDF report for survey analytics"""
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Prepare story (content)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2c3e50')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#34495e')
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=15,
            textColor=colors.HexColor('#7f8c8d')
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 10
        
        # 1. Title and metadata
        story.append(Paragraph(_("Survey Analytics Report"), title_style))
        story.append(Spacer(1, 0.1 * inch))
        
        # Survey info table
        survey_data = [
            [_("Survey Title:"), survey.title],
            [_("Survey Type:"), survey.get_survey_type_display()],
            [_("Status:"), survey.get_status_display()],
            [_("Created_at:"), survey.created_at.strftime('%Y-%m-%d %H:%M:%S')],
            [_("Organization:"), survey.organization.name],
            [_("Generated By:"), user.get_full_name() or user.email],
            [_("Generated On:"), timezone.now().strftime('%Y-%m-%d %H:%M:%S')],
        ]
        
        survey_table = Table(survey_data, colWidths=[2*inch, 4*inch])
        survey_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(survey_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # 2. Key Metrics Section
        story.append(Paragraph(_("Key Metrics"), heading_style))
        
        # Calculate metrics (similar to SurveyAnalyticsView)
        responses = survey.responses.filter(is_complete=True)
        total_responses = responses.count()
        total_sent = survey.total_sent or 0
        completion_rate = (total_responses / total_sent * 100) if total_sent > 0 else 0
        
        # Get device breakdown
        device_breakdown = responses.values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get sentiment metrics
        avg_sentiment = responses.aggregate(
            avg_sentiment=Avg('sentiment_score')
        )['avg_sentiment'] or 0
        
        # Metrics table
        metrics_data = [
            [_("Metric"), _("Value")],
            [_("Total Responses"), str(total_responses)],
            [_("Completion Rate"), f"{completion_rate:.1f}%"],
            [_("Questions"), str(len(survey.questions or []))],
            [_("Average Sentiment"), f"{avg_sentiment:.2f}" if avg_sentiment != 0 else _("N/A")],
            [_("Total Sent"), str(total_sent)],
        ]
        
        metrics_table = Table(metrics_data, colWidths=[3*inch, 3*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # 3. Device Breakdown Section
        if device_breakdown:
            story.append(Paragraph(_("Device Breakdown"), heading_style))
            
            device_data = [[_("Device Type"), _("Count"), _("Percentage")]]
            for device in device_breakdown:
                device_type = device['device_type'] or _('Unknown')
                count = device['count']
                percentage = (count / total_responses * 100) if total_responses > 0 else 0
                device_data.append([
                    device_type.title(),
                    str(count),
                    f"{percentage:.1f}%"
                ])
            
            device_table = Table(device_data, colWidths=[2*inch, 2*inch, 2*inch])
            device_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(device_table)
            story.append(Spacer(1, 0.3 * inch))
        
        # 4. Questions Overview Section
        questions = survey.questions or []
        if questions:
            story.append(Paragraph(_("Questions Overview"), heading_style))
            
            for i, question in enumerate(questions, 1):
                story.append(Paragraph(f"{i}. {question.get('text', _('Untitled Question'))}", subheading_style))
                
                question_details = []
                if question.get('type'):
                    question_details.append(_("Type: ") + question['type'])
                if question.get('required'):
                    question_details.append(_("Required: Yes"))
                if question.get('options'):
                    options = ', '.join(str(opt) for opt in question['options'][:5])
                    if len(question['options']) > 5:
                        options += f" (+{len(question['options']) - 5} more)"
                    question_details.append(_("Options: ") + options)
                
                if question_details:
                    story.append(Paragraph(' | '.join(question_details), normal_style))
                
                story.append(Spacer(1, 0.1 * inch))
        
        # 5. Recent Responses Section (last 20)
        recent_responses = responses.select_related('customer').order_by('-created_at')[:20]
        if recent_responses:
            story.append(Paragraph(_("Recent Responses"), heading_style))
            
            responses_data = [[
                _("Date"),
                _("Customer"),
                _("Sentiment"),
                _("Device")
            ]]
            
            for response_obj in recent_responses:
                customer_info = _("Anonymous")
                if response_obj.customer:
                    if response_obj.customer.get_full_name():
                        customer_info = response_obj.customer.get_full_name()
                    elif response_obj.customer.email:
                        customer_info = response_obj.customer.email
                
                sentiment = f"{response_obj.sentiment_score:.2f}" if response_obj.sentiment_score is not None else _("N/A")
                device = response_obj.get_device_type_display() if response_obj.device_type else _("Unknown")
                
                responses_data.append([
                    response_obj.created_at.strftime('%Y-%m-%d %H:%M'),
                    customer_info[:30],  # Truncate long names
                    sentiment,
                    device
                ])
            
            responses_table = Table(responses_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1.5*inch])
            responses_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(responses_table)
            story.append(Spacer(1, 0.3 * inch))
        
        # 6. Summary Section
        story.append(Paragraph(_("Summary"), heading_style))
        
        summary_text = _(
            "This report provides analytics for the survey '{survey_title}'. "
            "The survey has received {total_responses} complete responses "
            "with a completion rate of {completion_rate:.1f}%. "
            "The overall sentiment score is {sentiment_score:.2f}. "
            "This report was generated on {generation_date}."
        ).format(
            survey_title=survey.title,
            total_responses=total_responses,
            completion_rate=completion_rate,
            sentiment_score=avg_sentiment,
            generation_date=timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # 7. Footer
        footer_text = _(
            "Confidential - For internal use only. "
            "Generated by Survey Analytics System v1.0"
        )
        story.append(Paragraph(footer_text, ParagraphStyle(
            'Footer',
            parent=normal_style,
            fontSize=8,
            textColor=colors.grey,
            alignment=1  # Center aligned
        )))
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer