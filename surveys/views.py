from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from datetime import timedelta

from core.models import *
from .forms import SurveyForm, SurveyResponseForm

class OrganizationMixin:
    """Mixin to handle organization context"""
    
    def get_organization(self):
        organization_pk = self.kwargs.get('organization_pk')
        return get_object_or_404(Organization, pk=organization_pk)

    def test_func(self):
        organization = self.get_organization()
        user_membership = organization.members.filter(
            user=self.request.user,
            is_active=True
        ).first()
        return user_membership is not None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        return context

class SurveyListView(LoginRequiredMixin, OrganizationMixin, ListView):
    model = Survey
    template_name = 'surveys/survey-list.html'
    context_object_name = 'surveys'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Filter by survey type
        survey_type = self.request.GET.get('survey_type', '')
        if survey_type:
            queryset = queryset.filter(survey_type=survey_type)
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.select_related('organization').prefetch_related('responses')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        # Statistics
        total_surveys = self.get_queryset().count()
        active_surveys = self.get_queryset().filter(status='active').count()
        total_responses = SurveyResponse.objects.filter(
            survey__organization=organization
        ).count()
        
        context.update({
            'search_query': self.request.GET.get('search', ''),
            'selected_type': self.request.GET.get('survey_type', ''),
            'selected_status': self.request.GET.get('status', ''),
            'total_surveys': total_surveys,
            'active_surveys': active_surveys,
            'total_responses': total_responses,
        })
        return context

class SurveyCreateView(LoginRequiredMixin, SuccessMessageMixin, OrganizationMixin, CreateView):
    model = Survey
    form_class = SurveyForm
    template_name = 'surveys/survey-form.html'
    success_message = _('Survey "%(title)s" was created successfully!')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.get_organization()
        return kwargs
    
    def form_valid(self, form):
        form.instance.organization = self.get_organization()
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('surveys:survey-list', kwargs={
            'organization_pk': self.get_organization().pk
        })

class SurveyUpdateView(LoginRequiredMixin, SuccessMessageMixin, OrganizationMixin, UpdateView):
    model = Survey
    form_class = SurveyForm
    template_name = 'surveys/survey-form.html'
    success_message = _('Survey "%(title)s" was updated successfully!')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.get_organization()
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('surveys:survey-list', kwargs={
            'organization_pk': self.get_organization().pk
        })

class SurveyDetailView(LoginRequiredMixin, OrganizationMixin, DetailView):
    model = Survey
    template_name = 'surveys/survey-detail.html'
    context_object_name = 'survey'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        survey = self.get_object()
        
        # Response statistics
        responses = survey.responses.filter(is_complete=True)
        total_responses = responses.count()
        
        # Calculate average scores for different survey types
        if survey.survey_type == 'nps':
            nps_scores = []
            for response in responses:
                for answer in response.response_data.values():
                    if isinstance(answer, (int, str)) and str(answer).isdigit():
                        score = int(answer)
                        if 0 <= score <= 10:
                            nps_scores.append(score)
            
            if nps_scores:
                promoters = len([s for s in nps_scores if s >= 9])
                detractors = len([s for s in nps_scores if s <= 6])
                nps = ((promoters - detractors) / len(nps_scores)) * 100
                context['nps_score'] = round(nps, 1)
        
        context.update({
            'total_responses': total_responses,
            'response_rate': survey.response_rate,
            'recent_responses': responses.order_by('-created_at')[:5],
        })
        return context

class SurveyDeleteView(LoginRequiredMixin, SuccessMessageMixin, OrganizationMixin, DeleteView):
    model = Survey
    template_name = 'surveys/survey-confirm-delete.html'
    success_message = _('Survey was deleted successfully!')
    
    def get_success_url(self):
        return reverse_lazy('surveys:survey-list', kwargs={
            'organization_pk': self.get_organization().pk
        })

from uuid import UUID  # Add this import at the top

# ... keep all other imports and views as they are ...

class SurveyPublicView(View):
    """
    Public view for customers to complete surveys.
    Uses survey's primary key (UUID) directly for cleaner URL handling.
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_survey(self, survey_uuid):
        """
        Get survey by UUID - tries pk first, then metadata.public_uuid as fallback.
        Does NOT filter by status here - we check status separately for better error messages.
        """
        survey = None
        
        if not survey_uuid:
            return None
        
        # Convert string to UUID if needed
        if isinstance(survey_uuid, str):
            try:
                survey_uuid = UUID(survey_uuid)
            except (ValueError, AttributeError):
                return None
        
        # Primary approach: Look up by primary key (recommended)
        try:
            survey = Survey.objects.select_related('organization').get(pk=survey_uuid)
            return survey
        except Survey.DoesNotExist:
            pass
        
        # Fallback: Look for metadata.public_uuid (for backward compatibility)
        try:
            survey = Survey.objects.select_related('organization').get(
                metadata__public_uuid=str(survey_uuid)
            )
            return survey
        except Survey.DoesNotExist:
            pass
        
        # Second fallback: metadata contains approach
        try:
            survey = Survey.objects.select_related('organization').get(
                metadata__contains={'public_uuid': str(survey_uuid)}
            )
            return survey
        except Survey.DoesNotExist:
            pass
        
        return None
    
    def check_survey_availability(self, survey):
        """
        Check if survey is available for public access.
        Returns (is_available, error_message) tuple.
        """
        if not survey:
            return False, _('Survey not found.')
        
        # Check survey status
        if survey.status != 'active':
            status_messages = {
                'draft': _('This survey is not yet published.'),
                'paused': _('This survey is currently paused.'),
                'archived': _('This survey has been archived.'),
            }
            return False, status_messages.get(survey.status, _('This survey is not currently available.'))
        
        # Check date range using timezone-aware comparison
        now = timezone.now()
        
        # Check if survey has started
        if survey.start_date:
            # Make sure we're comparing timezone-aware datetimes
            start_date = survey.start_date
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            
            if start_date > now:
                return False, _('This survey has not started yet. It will be available from %(date)s.') % {
                    'date': start_date.strftime('%B %d, %Y')
                }
        
        # Check if survey has ended
        if survey.end_date:
            # Make sure we're comparing timezone-aware datetimes
            end_date = survey.end_date
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
            
            if end_date < now:
                return False, _('This survey ended on %(date)s.') % {
                    'date': end_date.strftime('%B %d, %Y')
                }
        
        # Check response limit if set
        if survey.response_limit and survey.total_responses >= survey.response_limit:
            return False, _('This survey has reached its maximum number of responses.')
        
        return True, None
    
    def get(self, request, survey_uuid=None):
        """Handle GET requests - display the survey form"""
        try:
            # Get the survey
            survey = self.get_survey(survey_uuid)
            
            # Check availability
            is_available, error_message = self.check_survey_availability(survey)
            
            if not is_available:
                return render(request, 'surveys/survey-not-available.html', {
                    'message': error_message,
                    'survey': survey  # Pass survey for branding even on error page
                })
            
            # Create the form
            form = SurveyResponseForm(questions=survey.questions, survey=survey)
            
            # Prepare context
            context = self._prepare_context(survey, form)
            
            return render(request, 'surveys/survey-public.html', context)
            
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading survey {survey_uuid}: {str(e)}", exc_info=True)
            
            return render(request, 'surveys/survey-not-available.html', {
                'message': _('An error occurred while loading the survey. Please try again later.')
            })
    
    def post(self, request, survey_uuid=None):
        """Handle POST requests - process survey submission"""
        try:
            # Get the survey
            survey = self.get_survey(survey_uuid)
            
            # CRITICAL: Check if survey has organization
            if not survey or not survey.organization:
                logger.error(f"Survey {survey_uuid} has no organization")
                return render(request, 'surveys/survey-not-available.html', {
                    'message': _('This survey is not properly configured.')
                })
            
            # Check availability
            is_available, error_message = self.check_survey_availability(survey)
            
            if not is_available:
                return render(request, 'surveys/survey-not-available.html', {
                    'message': error_message,
                    'survey': survey
                })
            
            # Process the form
            form = SurveyResponseForm(
                request.POST, 
                questions=survey.questions, 
                survey=survey,
                organization=survey.organization  # Pass organization to form
            )
            
            if form.is_valid():
                # Build response data
                response_data = {}
                for field_name, value in form.cleaned_data.items():
                    if field_name.startswith('q_'):
                        question_index = int(field_name[2:])
                        if question_index < len(survey.questions):
                            question = survey.questions[question_index]
                            question_id = str(question.get('id', f'question_{question_index}'))
                            response_data[question_id] = value
                
                # Get or create anonymous customer for public surveys
                # CRITICAL: Always pass the survey's organization
                customer = self._get_or_create_anonymous_customer(request, survey)
                
                # Create the survey response
                survey_response = SurveyResponse.objects.create(
                    survey=survey,
                    customer=customer,
                    organization=survey.organization,  # CRITICAL: Set organization
                    response_data=response_data,
                    is_complete=True,
                    completed_at=timezone.now(),
                    language=survey.language,
                    device_type=self._detect_device_type(request)
                )
                
                # Update survey statistics
                survey.total_responses += 1
                if survey.total_sent > 0:
                    survey.response_rate = (survey.total_responses / survey.total_sent) * 100
                survey.save(update_fields=['total_responses', 'response_rate', 'updated_at'])
                
                # Prepare thank you context
                context = self._prepare_context(survey, form)
                context['response'] = survey_response
                
                return render(request, 'surveys/survey-thank-you.html', context)
            
            # Form is invalid - show errors
            context = self._prepare_context(survey, form)
            return render(request, 'surveys/survey-public.html', context)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error submitting survey {survey_uuid}: {str(e)}", exc_info=True)
            
            return render(request, 'surveys/survey-not-available.html', {
                'message': _('An error occurred while submitting the survey. Please try again.')
            })
    
    def _prepare_context(self, survey, form):
        """Prepare template context with survey and organization data"""
        context = {
            'survey': survey,
            'form': form,
            'organization': survey.organization if survey else None,
        }
        return context
    
    def _detect_device_type(self, request):
        """Detect device type from user agent"""
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        if 'mobile' in user_agent or 'android' in user_agent:
            if 'tablet' in user_agent or 'ipad' in user_agent:
                return 'tablet'
            return 'mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            return 'tablet'
        
        return 'desktop'
    
    def _get_or_create_anonymous_customer(self, request, survey):
        """
        Get or create an anonymous customer for public survey submissions.
        CRITICAL: ALWAYS sets organization to survey's organization.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # CRITICAL: Check if survey has organization
            if not survey or not survey.organization:
                logger.error(f"Survey {survey.id if survey else 'unknown'} has no organization")
                raise ValueError("Survey has no organization")
            
            organization = survey.organization
            
            # Try to get existing session-based customer
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            
            # Create a unique anonymous email
            anonymous_email = f"anonymous_{session_key}_{uuid.uuid4().hex[:8]}@survey.local"
            
            # Get client IP
            ip_address = self._get_client_ip(request)
            
            # Try to find existing anonymous customer for this session and organization
            customer = None
            try:
                # Look for session-based anonymous customer in THIS organization
                customer = Customer.objects.filter(
                    organization=organization,
                    customer_type='anonymous',
                    metadata__contains={'session_id': session_key}
                ).first()
                
                if customer:
                    logger.info(f"Found existing anonymous customer: {customer.customer_id}")
                    return customer
            except Exception as e:
                logger.warning(f"Error finding existing anonymous customer: {str(e)}")
            
            # Create new anonymous customer
            customer = Customer.objects.create(
                organization=organization,  # CRITICAL: ALWAYS set organization
                customer_id=f"anon_{uuid.uuid4().hex[:8]}",
                customer_type='anonymous',
                segment='anonymous',
                email=anonymous_email,
                first_name='Anonymous',
                last_name='Respondent',
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=session_key,
                language_preference=request.GET.get('language', survey.language or 'en'),
                metadata={
                    'source': 'public_survey',
                    'survey_id': str(survey.id),
                    'survey_title': survey.title,
                    'created_at': timezone.now().isoformat(),
                    'is_anonymous': True,
                    'client_ip': ip_address,
                    'session_id': session_key,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'survey_uuid': str(survey.id),
                    'registration_source': 'public_survey_link',
                }
            )
            
            logger.info(f"Created new anonymous customer: {customer.customer_id} for org {organization.name}")
            return customer
            
        except Exception as e:
            logger.error(f"Error in _get_or_create_anonymous_customer: {str(e)}", exc_info=True)
            # Emergency fallback - MUST have organization
            return self._create_emergency_customer(survey)
    
    def _create_emergency_customer(self, survey):
        """
        Emergency fallback customer creation.
        This should be called only when normal creation fails.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Check if survey has organization
            if not survey or not survey.organization:
                logger.critical("Cannot create emergency customer - survey has no organization")
                # Last resort: try to get any organization
                try:
                    organization = Organization.objects.first()
                    if not organization:
                        raise ValueError("No organizations exist in database")
                except Exception as org_error:
                    logger.critical(f"No organizations available: {str(org_error)}")
                    raise ValueError("No organization available for customer creation")
            else:
                organization = survey.organization
            
            # Create emergency customer
            customer_id = f"emergency_{uuid.uuid4().hex[:8]}"
            
            customer = Customer.objects.create(
                organization=organization,  # CRITICAL: Set organization
                customer_id=customer_id,
                customer_type='anonymous',
                segment='anonymous',
                email=f"{customer_id}@emergency.local",
                first_name='Emergency',
                last_name='Customer',
                metadata={
                    'source': 'survey_response_emergency',
                    'survey_id': str(survey.id) if survey else 'unknown',
                    'created_at': timezone.now().isoformat(),
                    'is_emergency': True,
                    'error': 'Normal customer creation failed',
                }
            )
            
            logger.warning(f"Created emergency customer: {customer.customer_id}")
            return customer
            
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to create emergency customer: {str(e)}")
            raise ValueError(f"Cannot create customer for survey: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
class SurveyPublicView1(View):
    """
    Public view for customers to complete surveys.
    Uses survey's primary key (UUID) directly for cleaner URL handling.
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_survey(self, survey_uuid):
        """
        Get survey by UUID - tries pk first, then metadata.public_uuid as fallback.
        Does NOT filter by status here - we check status separately for better error messages.
        """
        survey = None
        
        if not survey_uuid:
            return None
        
        # Convert string to UUID if needed
        if isinstance(survey_uuid, str):
            try:
                survey_uuid = UUID(survey_uuid)
            except (ValueError, AttributeError):
                return None
        
        # Primary approach: Look up by primary key (recommended)
        try:
            survey = Survey.objects.select_related('organization').get(pk=survey_uuid)
            return survey
        except Survey.DoesNotExist:
            pass
        
        # Fallback: Look for metadata.public_uuid (for backward compatibility)
        try:
            survey = Survey.objects.select_related('organization').get(
                metadata__public_uuid=str(survey_uuid)
            )
            return survey
        except Survey.DoesNotExist:
            pass
        
        # Second fallback: metadata contains approach
        try:
            survey = Survey.objects.select_related('organization').get(
                metadata__contains={'public_uuid': str(survey_uuid)}
            )
            return survey
        except Survey.DoesNotExist:
            pass
        
        return None
    
    def check_survey_availability(self, survey):
        """
        Check if survey is available for public access.
        Returns (is_available, error_message) tuple.
        """
        if not survey:
            return False, _('Survey not found.')
        
        # Check survey status
        if survey.status != 'active':
            status_messages = {
                'draft': _('This survey is not yet published.'),
                'paused': _('This survey is currently paused.'),
                'archived': _('This survey has been archived.'),
            }
            return False, status_messages.get(survey.status, _('This survey is not currently available.'))
        
        # Check date range using timezone-aware comparison
        now = timezone.now()
        
        # Check if survey has started
        if survey.start_date:
            # Make sure we're comparing timezone-aware datetimes
            start_date = survey.start_date
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            
            if start_date > now:
                return False, _('This survey has not started yet. It will be available from %(date)s.') % {
                    'date': start_date.strftime('%B %d, %Y')
                }
        
        # Check if survey has ended
        if survey.end_date:
            # Make sure we're comparing timezone-aware datetimes
            end_date = survey.end_date
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
            
            if end_date < now:
                return False, _('This survey ended on %(date)s.') % {
                    'date': end_date.strftime('%B %d, %Y')
                }
        
        # Check response limit if set
        if survey.response_limit and survey.total_responses >= survey.response_limit:
            return False, _('This survey has reached its maximum number of responses.')
        
        return True, None
    
    def get(self, request, survey_uuid=None):
        """Handle GET requests - display the survey form"""
        try:
            # Get the survey
            survey = self.get_survey(survey_uuid)
            
            # Check availability
            is_available, error_message = self.check_survey_availability(survey)
            
            if not is_available:
                return render(request, 'surveys/survey-not-available.html', {
                    'message': error_message,
                    'survey': survey  # Pass survey for branding even on error page
                })
            
            # Create the form
            form = SurveyResponseForm(questions=survey.questions, survey=survey)
            
            # Prepare context
            context = self._prepare_context(survey, form)
            
            return render(request, 'surveys/survey-public.html', context)
            
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading survey {survey_uuid}: {str(e)}", exc_info=True)
            
            return render(request, 'surveys/survey-not-available.html', {
                'message': _('An error occurred while loading the survey. Please try again later.')
            })
    
    def post(self, request, survey_uuid=None):
        """Handle POST requests - process survey submission"""
        try:
            # Get the survey
            survey = self.get_survey(survey_uuid)
            
            # Check availability
            is_available, error_message = self.check_survey_availability(survey)
            
            if not is_available:
                return render(request, 'surveys/survey-not-available.html', {
                    'message': error_message,
                    'survey': survey
                })
            
            # Process the form
            form = SurveyResponseForm(request.POST, questions=survey.questions, survey=survey)
            
            if form.is_valid():
                # Build response data
                response_data = {}
                for field_name, value in form.cleaned_data.items():
                    if field_name.startswith('q_'):
                        question_index = int(field_name[2:])
                        if question_index < len(survey.questions):
                            question = survey.questions[question_index]
                            question_id = str(question.get('id', f'question_{question_index}'))
                            response_data[question_id] = value
                
                # Get or create anonymous customer for public surveys
                # You may want to adjust this based on your requirements
                customer = self._get_or_create_anonymous_customer(request, survey)
                
                # Create the survey response
                survey_response = SurveyResponse.objects.create(
                    survey=survey,
                    customer=customer,
                    response_data=response_data,
                    is_complete=True,
                    completed_at=timezone.now(),
                    language=survey.language,
                    device_type=self._detect_device_type(request)
                )
                
                # Update survey statistics
                survey.total_responses += 1
                if survey.total_sent > 0:
                    survey.response_rate = (survey.total_responses / survey.total_sent) * 100
                survey.save(update_fields=['total_responses', 'response_rate'])
                
                # Prepare thank you context
                context = self._prepare_context(survey, form)
                context['response'] = survey_response
                
                return render(request, 'surveys/survey-thank-you.html', context)
            
            # Form is invalid - show errors
            context = self._prepare_context(survey, form)
            return render(request, 'surveys/survey-public.html', context)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error submitting survey {survey_uuid}: {str(e)}", exc_info=True)
            
            return render(request, 'surveys/survey-not-available.html', {
                'message': _('An error occurred while submitting the survey. Please try again.')
            })
    
    def _prepare_context(self, survey, form):
        """Prepare template context with survey and organization data"""
        context = {
            'survey': survey,
            'form': form,
            'organization': survey.organization if survey else None,
        }
        return context
    
    def _detect_device_type(self, request):
        """Detect device type from user agent"""
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        if 'mobile' in user_agent or 'android' in user_agent:
            if 'tablet' in user_agent or 'ipad' in user_agent:
                return 'tablet'
            return 'mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            return 'tablet'
        
        return 'desktop'
    
    def _get_or_create_anonymous_customer(self, request, survey):
        """
        Get or create an anonymous customer for public survey submissions.
        Override this method if you need different behavior.
        """
        # Try to get existing anonymous customer or create new one
        # This is a placeholder - adjust based on your Customer model requirements
        from django.db.models import Q
        
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        # Check if Customer model has organization field
        try:
            customer, created = Customer.objects.get_or_create(
                email=f'anonymous_{session_key[:20]}@survey.local',
                organization=survey.organization,
                defaults={
                    'first_name': 'Anonymous',
                    'last_name': 'Respondent',
                }
            )
        except Exception:
            # Fallback: create without organization if field doesn't exist
            customer, created = Customer.objects.get_or_create(
                email=f'anonymous_{session_key[:20]}@survey.local',
                defaults={
                    'first_name': 'Anonymous',
                    'last_name': 'Respondent',
                }
            )
        
        return customer
            
     
class SurveyAnalyticsView(LoginRequiredMixin, OrganizationMixin, DetailView):
    model = Survey
    template_name = 'surveys/survey-analytics.html'
    context_object_name = 'survey'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        survey = self.get_object()
        responses = survey.responses.filter(is_complete=True)
        
        # Basic statistics
        context['total_responses'] = responses.count()
        context['completion_rate'] = survey.response_rate
        
        # Response trends (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_responses = responses.filter(
            created_at__gte=thirty_days_ago
        ).extra({
            'date': "DATE(created_at)"
        }).values('date').annotate(count=Count('id')).order_by('date')
        
        context['response_trends'] = list(daily_responses)
        
        return context

class SurveyEmbedView(View):
    """View for embedding surveys in other websites"""
    
    def get(self, request, survey_uuid):
        survey = get_object_or_404(Survey, metadata__public_uuid=survey_uuid, status='active')
        
        return render(request, 'surveys/survey-embed.html', {
            'survey': survey,
        })
# Create your views here.
