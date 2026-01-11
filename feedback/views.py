from django.http import JsonResponse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.views.generic import View
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.contrib import messages

@require_POST
@csrf_exempt
def slugify_text(request):
    """
    API endpoint to generate slugs from text
    """
    import json
    data = json.loads(request.body)
    text = data.get('text', '')
    
    if text:
        slug = slugify(text)
        return JsonResponse({'slug': slug})
    
    return JsonResponse({'error': 'No text provided'}, status=400)

# Create your views here.

# views.py
import logging
import csv
import uuid
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q, Count, Avg, Case, When, IntegerField
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, FormView, TemplateView
from django.http import JsonResponse
from core.models import *
from .forms import *
from common.utils import *

logger = logging.getLogger(__name__)

class FeedbackCreateMixin(LoginRequiredMixin):
    """
    Mixin for feedback views to handle organization permissions
    """
    def get_organization(self):
        organization_pk = self.kwargs.get('organization_pk')
        return get_object_or_404(Organization, pk=organization_pk)

    def test_func(self):
        organization = self.get_organization()
        user_membership = organization.members.filter(
            user=self.request.user,
            is_active=True
        ).first()
        # For feedback creation, allow all active members
        return user_membership is not None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        return context

    def handle_no_permission(self):
        messages.error(
            self.request,
            _('You do not have permission to create feedback for this organization.')
        )
        return redirect('accounts:org-detail', pk=self.get_organization().pk)

class FeedbackMixin:
    """
    Mixin for feedback views to handle organization permissions
    """
    def get_organization(self):
        organization_pk = self.kwargs.get('organization_pk')
        return get_object_or_404(Organization, pk=organization_pk)

    def test_func(self):
        organization = self.get_organization()
        user_membership = organization.members.filter(
            user=self.request.user,
            is_active=True
        ).first()
        # For feedback creation, allow all active members
        return user_membership is not None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        return context

    def handle_no_permission(self):
        messages.error(
            self.request,
            _('You do not have permission to create feedback for this organization.')
        )
        return redirect('accounts:org-detail', pk=self.get_organization().pk)
    
class OrganizationMixin(LoginRequiredMixin):
    """
    Mixin to retrieve the organization based on URL kwarg 'organization_pk'.
    Ensures user has access to this organization.
    """
    def get_organization(self):
        if hasattr(self, '_organization'):
            return self._organization
            
        organization_pk = self.kwargs.get('organization_pk')
        # Add your permission logic here (e.g. filter by user membership)
        self._organization = get_object_or_404(Organization, pk=organization_pk)
        return self._organization

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        return context
    
# views.py - Replace the existing FeedbackCreateView with this

# feedback/views.py

from django.http import JsonResponse
from core.models import Customer

class CustomerDetailsAjaxView(LoginRequiredMixin, View):
    """
    AJAX view to get customer details
    """
    def get(self, request, *args, **kwargs):
        customer_id = request.GET.get('customer_id')
        organization_pk = request.GET.get('organization_pk')
        
        if not customer_id or not organization_pk:
            return JsonResponse({'success': False, 'error': 'Missing parameters'})
        
        try:
            customer = Customer.objects.get(
                pk=customer_id,
                organization__pk=organization_pk
            )
            
            return JsonResponse({
                'success': True,
                'email': customer.email,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'customer_id': customer.customer_id,
                'customer_type': customer.customer_type,
            })
        except Customer.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Customer not found'})    

logger = logging.getLogger(__name__)

class FeedbackListView(LoginRequiredMixin, ListView):
    """
    List all feedback for an organization with advanced filtering
    """
    model = Feedback
    template_name = 'feedback/feedback-list.html'
    context_object_name = 'feedbacks'
    paginate_by = 20
    
    def get_organization(self):
        """
        Get organization from URL parameter
        """
        organization_pk = self.kwargs.get('organization_pk')
        if organization_pk:
            try:
                return Organization.objects.get(pk=organization_pk)
            except Organization.DoesNotExist:
                logger.error(f'Organization not found: {organization_pk}')
                return None
        return None
    
    def calculate_statistics(self, organization):
        """
        Calculate all statistics for the organization
        """
        if not organization:
            return {}
        
        try:
            # Get all feedback for the organization
            all_feedbacks = Feedback.objects.filter(organization=organization)
            
            # Basic counts
            total_feedbacks = all_feedbacks.count()
            
            # Status counts using Django's aggregate functions
            new_count = all_feedbacks.filter(status='new').count()
            in_progress_count = all_feedbacks.filter(status='in_progress').count()
            resolved_count = all_feedbacks.filter(status='resolved').count()
            closed_count = all_feedbacks.filter(status='closed').count()
            pending_count = all_feedbacks.filter(status='pending').count()
            
            # AI analyzed count
            ai_analyzed_count = all_feedbacks.filter(ai_analyzed=True).count()
            
            # Average sentiment
            avg_sentiment_result = all_feedbacks.filter(
                sentiment_score__isnull=False
            ).aggregate(avg=Avg('sentiment_score'))
            avg_sentiment = avg_sentiment_result['avg'] or 0
            
            # Origin breakdown (NEW)
            origin_counts = all_feedbacks.values('origin').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Convert to dictionary for easy access
            origin_stats = {}
            for item in origin_counts:
                origin_stats[item['origin']] = item['count']
            
            # Sentiment breakdown
            sentiment_counts = all_feedbacks.values('sentiment_label').annotate(
                count=Count('id')
            ).order_by('-count')
            
            sentiment_stats = {}
            for item in sentiment_counts:
                sentiment_stats[item['sentiment_label']] = item['count']
            
            # Priority breakdown
            priority_counts = all_feedbacks.values('priority').annotate(
                count=Count('id')
            ).order_by('-count')
            
            priority_stats = {}
            for item in priority_counts:
                priority_stats[item['priority']] = item['count']
            
            # Type breakdown
            type_counts = all_feedbacks.values('feedback_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            type_stats = {}
            for item in type_counts:
                type_stats[item['feedback_type']] = item['count']
            
            return {
                'total_feedbacks': total_feedbacks,
                'new_count': new_count,
                'in_progress_count': in_progress_count,
                'resolved_count': resolved_count,
                'closed_count': closed_count,
                'pending_count': pending_count,
                'ai_analyzed_count': ai_analyzed_count,
                'avg_sentiment': round(float(avg_sentiment), 2) if avg_sentiment else 0.0,
                'origin_stats': origin_stats,  # NEW
                'sentiment_stats': sentiment_stats,
                'priority_stats': priority_stats,
                'type_stats': type_stats,
            }
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {str(e)}")
            return {
                'total_feedbacks': 0,
                'new_count': 0,
                'in_progress_count': 0,
                'resolved_count': 0,
                'closed_count': 0,
                'pending_count': 0,
                'ai_analyzed_count': 0,
                'avg_sentiment': 0.0,
                'origin_stats': {},  # NEW
                'sentiment_stats': {},
                'priority_stats': {},
                'type_stats': {},
            }
    
    def get_queryset(self):
        """
        Filter and search feedback with advanced filtering
        """
        organization = self.get_organization()
        if not organization:
            return Feedback.objects.none()
        
        # Start with base queryset
        queryset = Feedback.objects.filter(organization=organization)
        
        # Initialize filter form
        filter_form = FeedbackFilterForm(self.request.GET, organization=organization)
        
        if filter_form.is_valid():
            # Apply search filter
            search_query = filter_form.cleaned_data.get('search')
            
            if search_query:
                queryset = queryset.filter(
                    Q(feedback_id__icontains=search_query) |
                    Q(subject__icontains=search_query) |
                    Q(content__icontains=search_query) |
                    Q(customer__email__icontains=search_query) |
                    Q(customer__first_name__icontains=search_query) |
                    Q(customer__last_name__icontains=search_query) |
                    Q(internal_notes__icontains=search_query)
                )
            
            # Apply origin filter (NEW)
            origin = filter_form.cleaned_data.get('origin')
            if origin:
                queryset = queryset.filter(origin=origin)
            
            # Apply feedback type filter
            feedback_type = filter_form.cleaned_data.get('feedback_type')
            if feedback_type:
                queryset = queryset.filter(feedback_type=feedback_type)
            
            # Apply priority filter
            priority = filter_form.cleaned_data.get('priority')
            if priority:
                queryset = queryset.filter(priority=priority)
            
            # Apply status filter
            status = filter_form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            # Apply sentiment filter
            sentiment = filter_form.cleaned_data.get('sentiment')
            if sentiment:
                queryset = queryset.filter(sentiment_label=sentiment)
            
            # Apply AI analyzed filter
            ai_analyzed = filter_form.cleaned_data.get('ai_analyzed')
            if ai_analyzed == 'true':
                queryset = queryset.filter(ai_analyzed=True)
            elif ai_analyzed == 'false':
                queryset = queryset.filter(ai_analyzed=False)
            
            # Apply assigned to filter
            assigned_to = filter_form.cleaned_data.get('assigned_to')
            if assigned_to:
                queryset = queryset.filter(assigned_to_id=assigned_to)
            
            # Apply date range filter (FIXED)
            date_filters = filter_form.get_date_range_filter()
            if date_filters:
                queryset = queryset.filter(**date_filters)
            
            # Apply custom date range from start_date and end_date
            start_date = filter_form.cleaned_data.get('start_date')
            end_date = filter_form.cleaned_data.get('end_date')
            
            if start_date and end_date:
                # Make end_date inclusive by adding 1 day
                end_date_plus_one = end_date + timedelta(days=1)
                queryset = queryset.filter(
                    created_at__gte=start_date,
                    created_at__lt=end_date_plus_one
                )
            elif start_date:
                queryset = queryset.filter(created_at__date__gte=start_date)
            elif end_date:
                # Make end_date inclusive
                end_date_plus_one = end_date + timedelta(days=1)
                queryset = queryset.filter(created_at__lt=end_date_plus_one)
        
        # Order by created date (newest first)
        queryset = queryset.select_related('customer', 'assigned_to').order_by('-created_at')
        
        # Return the queryset
        return queryset
    
    def get_context_data(self, **kwargs):
        """
        Add context data for template
        """
        context = super().get_context_data(**kwargs)
        
        organization = self.get_organization()
        if not organization:
            return context
        
        # Get filter form with current GET parameters
        filter_form = FeedbackFilterForm(self.request.GET, organization=organization)
        
        # Calculate statistics
        statistics = self.calculate_statistics(organization)
        
        # Get filtered count
        filtered_feedbacks = self.get_queryset()
        filtered_count = filtered_feedbacks.count()
        
        # Check if filters are applied
        has_filters = False
        for key, value in self.request.GET.items():
            if key != 'page' and value:
                has_filters = True
                break
        
        # Get team members for assignment filter (if applicable)
        team_members = []
        try:
            # Check if User model has organization_memberships relationship
            if hasattr(User, 'organization_memberships'):
                team_members = User.objects.filter(
                    organization_memberships__organization=organization,
                    organization_memberships__is_active=True
                ).distinct()
        except Exception as e:
            logger.debug(f"Could not get team members: {str(e)}")
        
        # Update context
        context.update({
            'organization': organization,
            'page_title': _('Feedback List'),
            'filter_form': filter_form,
            'filtered_count': filtered_count,
            'has_filters': has_filters,
            'team_members': team_members,
            'total_feedbacks': statistics.get('total_feedbacks', 0),
            'new': statistics.get('new_count', 0),  # Using 'new' to match template
            'in_progress': statistics.get('in_progress_count', 0),  # Using 'in_progress' to match template
            'resolved': statistics.get('resolved_count', 0),  # Using 'resolved' to match template
            'ai_analyzed': statistics.get('ai_analyzed_count', 0),  # Using 'ai_analyzed' to match template
            'avg_sentiment': statistics.get('avg_sentiment', 0.0),
            'origin_stats': statistics.get('origin_stats', {}),  # NEW
            'sentiment_stats': statistics.get('sentiment_stats', {}),
            'priority_stats': statistics.get('priority_stats', {}),
            'type_stats': statistics.get('type_stats', {}),
        })
        
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """
        Check permissions before processing view
        """
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Get organization and check if it exists
        organization = self.get_organization()
        if not organization:
            messages.error(
                request,
                _('No organization found. Please select an organization first.')
            )
            # Store intended URL to redirect back after organization selection
            request.session['next_url'] = request.get_full_path()
            # Redirect to organization selection or dashboard
            try:
                return redirect('accounts:org-detail')
            except:
                return redirect('dashboard')
        
        # Check membership if OrganizationMember model exists
        # Use a try-except block to handle the case where OrganizationMember might not exist
        try:
            # Try to import OrganizationMember safely
            from django.apps import apps
            if apps.is_installed('accounts'):
                try:
                    OrganizationMember = apps.get_model('accounts', 'OrganizationMember')
                except LookupError:
                    # Try alternative app names
                    try:
                        OrganizationMember = apps.get_model('organizations', 'OrganizationMember')
                    except LookupError:
                        OrganizationMember = None
                
                if OrganizationMember:
                    try:
                        # Check if user is a member of the organization
                        membership = OrganizationMember.objects.get(
                            organization=organization,
                            user=request.user,
                            is_active=True
                        )
                        
                        # Define allowed roles for viewing feedback
                        allowed_roles = ['owner', 'admin', 'manager', 'analyst', 'viewer']
                        if membership.role not in allowed_roles:
                            messages.error(
                                request,
                                _("You don't have permission to view feedback in this organization.")
                            )
                            return redirect('dashboard')
                            
                    except OrganizationMember.DoesNotExist:
                        messages.error(
                            request,
                            _("You are not a member of this organization.")
                        )
                        # Try to redirect to organization detail or dashboard
                        try:
                            return redirect('accounts:org-detail')
                        except:
                            return redirect('dashboard')
                else:
                    # OrganizationMember model not found, skip membership check
                    pass
                    
        except Exception as e:
            # Log the error but continue - don't break the application
            logger.debug(f"Membership check error (non-critical): {str(e)}")
            # Continue without membership check if there's an error
        
        return super().dispatch(request, *args, **kwargs)
    


# views.py - Replace the existing FeedbackCreateView with this
class FeedbackCreateView(LoginRequiredMixin, FeedbackMixin, CreateView):
    """
    Create new feedback with comprehensive organization handling
    """
    model = Feedback
    form_class = FeedbackForm
    template_name = 'feedback/feedback-form.html'
    
    def get_organization(self):
        """
        Get organization from URL parameter (organization_pk)
        """
        organization_pk = self.kwargs.get('organization_pk')
        if organization_pk:
            try:
                return Organization.objects.get(pk=organization_pk)
            except (Organization.DoesNotExist, ValidationError):
                messages.error(
                    self.request,
                    _('Organization not found.')
                )
        
        return None
    
    def get_form_kwargs(self):
        """Pass organization to form"""
        kwargs = super().get_form_kwargs()
        organization = self.get_organization()
        
        if not organization:
            messages.error(
                self.request,
                _('No organization found. Please select an organization first.')
            )
        
        kwargs['organization'] = organization
        
        # Set initial data for organization context
        if 'initial' not in kwargs:
            kwargs['initial'] = {}
        
        # Set default values for new feedback
        kwargs['initial'].update({
            'status': 'new',
            'priority': 'medium',
            'feedback_type': 'general',
        })
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add organization context to template"""
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        if organization:
            context.update({
                'organization': organization,
                'page_title': _('Add Feedback - %(org)s') % {'org': organization.name},
                'submit_text': _('Create Feedback'),
                'organization_pk': organization.pk,
            })
            
            # Add customer statistics for context
            try:
                total_customers = Customer.objects.filter(organization=organization).count()
                recent_feedback = Feedback.objects.filter(
                    organization=organization
                ).order_by('-created_at')[:5]
                
                context.update({
                    'total_customers': total_customers,
                    'recent_feedback': recent_feedback,
                })
            except Exception as e:
                logger.warning(f'Error getting statistics: {str(e)}')
                context.update({
                    'total_customers': 0,
                    'recent_feedback': [],
                })
        else:
            # Set default values if no organization
            context.update({
                'organization': None,
                'page_title': _('Add Feedback'),
                'submit_text': _('Create Feedback'),
                'total_customers': 0,
                'recent_feedback': [],
            })
        
        # Add form field help texts and choices
        context.update({
            'feedback_type_choices': Feedback._meta.get_field('feedback_type').choices,
            'priority_choices': Feedback._meta.get_field('priority').choices,
            'status_choices': Feedback._meta.get_field('status').choices,
        })
        
        return context
    
    def form_valid(self, form):
        """
        Handle successful form submission with transaction safety
        """
        try:
            with transaction.atomic():
                # Get organization context
                organization = self.get_organization()
                if not organization:
                    messages.error(
                        self.request,
                        _("Organization is required for creating feedback.")
                    )
                    return self.form_invalid(form)
                
                # Set organization on feedback instance
                feedback = form.save(commit=False)
                feedback.organization = organization
                
                # Generate unique feedback ID if not already set by form
                if not feedback.feedback_id:
                    feedback.feedback_id = f"FB-{uuid.uuid4().hex[:12].upper()}"
                
                # Handle customer creation/association
                customer_email = form.cleaned_data.get('customer_email', '').strip().lower()
                customer_first_name = form.cleaned_data.get('customer_first_name', '').strip()
                customer_last_name = form.cleaned_data.get('customer_last_name', '').strip()
                
                if customer_email:
                    # Create or find customer with email
                    customer, created = Customer.objects.get_or_create(
                        organization=organization,
                        email=customer_email,
                        defaults={
                            'first_name': customer_first_name,
                            'last_name': customer_last_name,
                            'customer_id': f"CUST-{uuid.uuid4().hex[:8].upper()}",
                            'customer_type': 'identified',
                        }
                    )
                    feedback.customer = customer
                    if created:
                        logger.info(f'Created new customer: {customer.customer_id}')
                    else:
                        logger.info(f'Found existing customer: {customer.customer_id}')
                elif form.cleaned_data.get('customer'):
                    # Use selected existing customer
                    feedback.customer = form.cleaned_data['customer']
                    logger.info(f'Using selected customer: {feedback.customer.customer_id}')
                else:
                    # Create anonymous customer
                    customer = Customer.objects.create(
                        organization=organization,
                        customer_type='anonymous',
                        customer_id=f"ANON-{uuid.uuid4().hex[:12].upper()}",
                        email='',  # Empty email for anonymous
                    )
                    feedback.customer = customer
                    logger.info(f'Created anonymous customer: {customer.customer_id}')
                
                # Set created_by if field exists
                if hasattr(feedback, 'created_by'):
                    feedback.created_by = self.request.user
                
                # Save the feedback
                feedback.save()
                
                # Save many-to-many relationships (tags)
                form.save_m2m()
                
                # Log the creation
                logger.info(
                    f'Feedback created: {feedback.feedback_id} | '
                    f'Organization: {organization.name} | '
                    f'User: {self.request.user.email} | '
                    f'Type: {feedback.feedback_type} | '
                    f'Customer: {feedback.customer.customer_id}'
                )
                
                # Success message
                messages.success(
                    self.request,
                    _('Feedback "%(id)s" has been created successfully!') % {
                        'id': feedback.feedback_id
                    }
                )
                
                # Store the created object for success URL
                self.object = feedback
                
                return redirect(self.get_success_url())
                
        except ValidationError as e:
            messages.error(self.request, str(e))
            logger.error(f'Validation error creating feedback: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f'Error creating feedback: {str(e)}', exc_info=True)
            messages.error(
                self.request,
                _('An error occurred while creating the feedback. Please try again.')
            )
            return self.form_invalid(form)
    
    def get_success_url(self):
        """
        Determine where to redirect after successful creation
        """
        try:
            # Get organization from the created feedback
            if hasattr(self, 'object') and self.object and hasattr(self.object, 'organization'):
                organization = self.object.organization
                
                # CORRECTED: Use organization_pk (UUID) instead of org_slug
                return reverse_lazy('feedback:feedback-list', kwargs={
                    'organization_pk': organization.pk
                })
            
            # Fallback to organization from view
            organization = self.get_organization()
            if organization:
                return reverse_lazy('feedback:feedback-list', kwargs={
                    'organization_pk': organization.pk
                })
        
        except Exception as e:
            logger.error(f'Error determining success URL: {str(e)}')
        
        # Fallback to home or dashboard
        return reverse_lazy('dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        """Check permissions before processing view"""
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Get organization and check if it exists
        organization = self.get_organization()
        if not organization:
            messages.error(
                request,
                _('No organization found. Please select an organization first.')
            )
            # Store intended URL to redirect back after organization selection
            request.session['next_url'] = request.get_full_path()
            # Redirect to organization selection
            return redirect('accounts:org-detail')
        
        # Check membership if OrganizationMember model exists
        try:
            from django.apps import apps
            if apps.is_installed('accounts') and hasattr(apps.get_app_config('accounts'), 'models'):
                try:
                    # Check if user is a member of the organization
                    membership = OrganizationMember.objects.get(
                        organization=organization,
                        user=request.user,
                        is_active=True
                    )
                    
                    # Define allowed roles for creating feedback
                    allowed_roles = ['owner', 'admin', 'manager', 'analyst', 'viewer']
                    if membership.role not in allowed_roles:
                        messages.error(
                            request,
                            _("You don't have permission to create feedback in this organization.")
                        )
                        # CORRECTED: Use organization_pk instead of org_slug
                        return redirect('feedback:feedback-list', organization_pk=organization.pk)
                        
                except OrganizationMember.DoesNotExist:
                    messages.error(
                        request,
                        _("You are not a member of this organization.")
                    )
                    return redirect('accounts:org-detail')
        except (ImportError, AttributeError):
            # If OrganizationMember model doesn't exist, skip membership check
            pass
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_invalid(self, form):
        """Handle invalid form submission with better error display"""
        # Log form errors for debugging
        if form.errors:
            logger.warning(f'Form errors: {form.errors}')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(self.request, f"{field}: {error}")
        
        return super().form_invalid(form)
    
logger = logging.getLogger(__name__)

class FeedbackUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update existing feedback with proper organization handling
    """
    model = Feedback
    form_class = FeedbackForm
    template_name = 'feedback/feedback-form.html'
    
    def get_organization(self):
        """
        Get organization from the feedback object itself
        """
        try:
            # Get feedback object
            feedback = self.get_object()
            return feedback.organization
        except (AttributeError, KeyError):
            logger.error("Could not get organization from feedback object")
            return None
    
    def get_form_kwargs(self):
        """Pass organization and instance to form"""
        kwargs = super().get_form_kwargs()
        
        # Get organization from feedback
        organization = self.get_organization()
        if organization:
            kwargs['organization'] = organization
        
        # Pass initial customer data if exists
        if self.object and self.object.customer:
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            
            kwargs['initial'].update({
                'customer': self.object.customer,
                'customer_email': self.object.customer.email if self.object.customer.email else '',
                'customer_first_name': self.object.customer.first_name if self.object.customer.first_name else '',
                'customer_last_name': self.object.customer.last_name if self.object.customer.last_name else '',
            })
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add organization context to template"""
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        if organization:
            context.update({
                'organization': organization,
                'page_title': _('Edit Feedback - %(id)s') % {'id': self.object.feedback_id},
                'submit_text': _('Update Feedback'),
                'organization_pk': organization.pk,
                'editing': True,
            })
            
            # Add customer statistics for context
            try:
                total_customers = Customer.objects.filter(organization=organization).count()
                recent_feedback = Feedback.objects.filter(
                    organization=organization
                ).exclude(pk=self.object.pk).order_by('-created_at')[:5]
                
                context.update({
                    'total_customers': total_customers,
                    'recent_feedback': recent_feedback,
                })
            except Exception as e:
                logger.warning(f'Error getting statistics: {str(e)}')
                context.update({
                    'total_customers': 0,
                    'recent_feedback': [],
                })
        else:
            # Set default values if no organization
            context.update({
                'organization': None,
                'page_title': _('Edit Feedback'),
                'submit_text': _('Update Feedback'),
                'total_customers': 0,
                'recent_feedback': [],
                'editing': True,
            })
        
        # Add form field help texts and choices
        context.update({
            'feedback_type_choices': Feedback._meta.get_field('feedback_type').choices,
            'priority_choices': Feedback._meta.get_field('priority').choices,
            'status_choices': Feedback._meta.get_field('status').choices,
        })
        
        return context
    
    def form_valid(self, form):
        """
        Handle successful form submission with transaction safety
        """
        try:
            with transaction.atomic():
                # Get organization from existing feedback
                organization = self.get_organization()
                if not organization:
                    messages.error(
                        self.request,
                        _("Organization not found for this feedback.")
                    )
                    return self.form_invalid(form)
                
                # Get the existing feedback object before saving
                original_feedback = self.get_object()
                
                # Save the form but don't commit yet
                feedback = form.save(commit=False)
                
                # Ensure organization stays the same
                feedback.organization = organization
                
                # Handle customer updates
                customer_email = form.cleaned_data.get('customer_email', '').strip().lower()
                customer_first_name = form.cleaned_data.get('customer_first_name', '').strip()
                customer_last_name = form.cleaned_data.get('customer_last_name', '').strip()
                
                if customer_email:
                    # Create or find customer with email
                    customer, created = Customer.objects.get_or_create(
                        organization=organization,
                        email=customer_email,
                        defaults={
                            'first_name': customer_first_name,
                            'last_name': customer_last_name,
                            'customer_id': f"CUST-{uuid.uuid4().hex[:8].upper()}",
                            'customer_type': 'identified',
                        }
                    )
                    
                    # Update customer details if they exist
                    if not created and customer_email:
                        if customer_first_name:
                            customer.first_name = customer_first_name
                        if customer_last_name:
                            customer.last_name = customer_last_name
                        customer.save()
                    
                    feedback.customer = customer
                    
                    if created:
                        logger.info(f'Created new customer during update: {customer.customer_id}')
                    else:
                        logger.info(f'Using existing customer: {customer.customer_id}')
                        
                elif form.cleaned_data.get('customer'):
                    # Use selected existing customer
                    feedback.customer = form.cleaned_data['customer']
                    logger.info(f'Using selected customer: {feedback.customer.customer_id}')
                    
                elif not feedback.customer:
                    # If no customer selected and none exists, create anonymous
                    customer = Customer.objects.create(
                        organization=organization,
                        customer_type='anonymous',
                        customer_id=f"ANON-{uuid.uuid4().hex[:12].upper()}",
                        email='',
                    )
                    feedback.customer = customer
                    logger.info(f'Created anonymous customer during update: {customer.customer_id}')
                
                # Save the feedback
                feedback.save()
                
                # Save many-to-many relationships (tags)
                form.save_m2m()
                
                # Log the update
                logger.info(
                    f'Feedback updated: {feedback.feedback_id} | '
                    f'Organization: {organization.name} | '
                    f'User: {self.request.user.email} | '
                    f'Changes: Content updated'
                )
                
                # Success message
                messages.success(
                    self.request,
                    _('Feedback "%(id)s" has been updated successfully!') % {
                        'id': feedback.feedback_id
                    }
                )
                
                # Store the updated object
                self.object = feedback
                
                return redirect(self.get_success_url())
                
        except ValidationError as e:
            messages.error(self.request, str(e))
            logger.error(f'Validation error updating feedback: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f'Error updating feedback: {str(e)}', exc_info=True)
            messages.error(
                self.request,
                _('An error occurred while updating the feedback. Please try again.')
            )
            return self.form_invalid(form)
    
    def get_success_url(self):
        """
        Determine where to redirect after successful update
        """
        try:
            # Get organization from the updated feedback
            if hasattr(self, 'object') and self.object and hasattr(self.object, 'organization'):
                organization = self.object.organization
                
                # CORRECTED: Use organization_pk (UUID)
                return reverse_lazy('feedback:feedback-list', kwargs={
                    'organization_pk': organization.pk
                })
        
        except Exception as e:
            logger.error(f'Error determining success URL: {str(e)}')
        
        # Fallback to home or dashboard
        return reverse_lazy('dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        """Check permissions before processing view"""
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Get the feedback object
        feedback = self.get_object()
        if not feedback:
            messages.error(request, _('Feedback not found.'))
            return redirect('dashboard')
        
        # Get organization from feedback
        organization = feedback.organization
        if not organization:
            messages.error(request, _('Organization not found for this feedback.'))
            return redirect('dashboard')
        
        # Check membership if OrganizationMember model exists
        try:
            from django.apps import apps
            if apps.is_installed('accounts') and hasattr(apps.get_app_config('accounts'), 'models'):
                try:
                    # Check if user is a member of the organization
                    membership = OrganizationMember.objects.get(
                        organization=organization,
                        user=request.user,
                        is_active=True
                    )
                    
                    # Define allowed roles for updating feedback
                    allowed_roles = ['owner', 'admin', 'manager', 'analyst']
                    if membership.role not in allowed_roles:
                        messages.error(
                            request,
                            _("You don't have permission to update feedback in this organization.")
                        )
                        return redirect('feedback:feedback-list', organization_pk=organization.pk)
                        
                except OrganizationMember.DoesNotExist:
                    messages.error(
                        request,
                        _("You are not a member of this organization.")
                    )
                    return redirect('accounts:org-detail')
        except (ImportError, AttributeError):
            # If OrganizationMember model doesn't exist, skip membership check
            pass
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_invalid(self, form):
        """Handle invalid form submission with better error display"""
        # Log form errors for debugging
        if form.errors:
            logger.warning(f'Form errors during update: {form.errors}')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(self.request, f"{field}: {error}")
        
        return super().form_invalid(form)
    

class FeedbackDetailView1(FeedbackMixin, DetailView):
    """
    View feedback details
    """
    model = Feedback
    template_name = 'feedback/feedback-detail.html'
    context_object_name = 'feedback'

    def get_queryset(self):
        organization = self.get_organization()
        return Feedback.objects.filter(organization=organization).select_related(
            'customer', 'channel', 'product', 'assigned_to'
        ).prefetch_related('tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Feedback {self.object.feedback_id}"
        
        # Check if sentiment analysis exists
        context['has_sentiment_analysis'] = hasattr(self.object, 'sentiment_analysis')
        
        # Get sentiment analysis if it exists
        if context['has_sentiment_analysis'] and self.object.sentiment_analysis:
            context['sentiment_analysis'] = self.object.sentiment_analysis
            context['sentiment_analysis_pk'] = self.object.sentiment_analysis.pk
        
        return context

    def dispatch(self, request, *args, **kwargs):
        """
        Handle sentiment-detail redirection
        """
        response = super().dispatch(request, *args, **kwargs)
        
        # Check if this is a request for sentiment analysis
        if request.GET.get('action') == 'analyze' or 'analyze' in request.path:
            return self.redirect_to_sentiment_analysis()
        
        return response
    
    def redirect_to_sentiment_analysis(self):
        """
        Redirect to sentiment analysis detail, creating it if necessary
        """
        feedback = self.get_object()
        
        try:
            # Try to get existing sentiment analysis
            if hasattr(feedback, 'sentiment_analysis') and feedback.sentiment_analysis:
                sentiment_analysis = feedback.sentiment_analysis
            else:
                # Check if SentimentAnalysis model exists and create one
                from django.apps import apps
                
                try:
                    SentimentAnalysis = apps.get_model('cx_analytics', 'SentimentAnalysis')
                    
                    # Create a new sentiment analysis
                    sentiment_analysis = SentimentAnalysis.objects.create(
                        feedback=feedback,
                        organization=feedback.organization,
                        status='pending'
                    )
                    
                    # Update the feedback to mark as analyzed
                    feedback.ai_analyzed = True
                    feedback.save(update_fields=['ai_analyzed'])
                    
                    messages.info(
                        self.request,
                        _("Sentiment analysis created. Running analysis...")
                    )
                    
                except LookupError:
                    # SentimentAnalysis model doesn't exist
                    messages.error(
                        self.request,
                        _("Sentiment analysis feature is not available.")
                    )
                    return redirect('feedback:feedback-detail', 
                                   organization_pk=feedback.organization.pk,
                                   pk=feedback.pk)
            
            # Redirect to sentiment analysis detail page
            return redirect('cx_analytics:sentiment-detail',
                          organization_pk=feedback.organization.pk,
                          pk=sentiment_analysis.pk)
            
        except Exception as e:
            logger.error(f"Error redirecting to sentiment analysis: {str(e)}")
            messages.error(
                self.request,
                _("Could not create sentiment analysis. Please try again.")
            )
            return redirect('feedback:feedback-detail',
                          organization_pk=feedback.organization.pk,
                          pk=feedback.pk)
              
class FeedbackDetailView(FeedbackMixin, DetailView):
    """
    View feedback details
    """
    model = Feedback
    template_name = 'feedback/feedback-detail.html'
    context_object_name = 'feedback'

    def get_queryset(self):
        organization = self.get_organization()
        return Feedback.objects.filter(organization=organization).select_related(
            'customer', 'channel', 'product', 'assigned_to'
        ).prefetch_related('tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Feedback {self.object.feedback_id}"
        return context

class FeedbackDeleteView(FeedbackMixin, DeleteView):
    """
    Delete feedback
    """
    model = Feedback
    template_name = 'feedback/feedback-confirm-delete.html'

    def get_queryset(self):
        organization = self.get_organization()
        return Feedback.objects.filter(organization=organization)

    def form_valid(self, request, *args, **kwargs):
        feedback = self.get_object()
        feedback_id = feedback.feedback_id
        
        try:
            with transaction.atomic():
                response = super().form_valid(request, *args, **kwargs)
                
                messages.success(
                    self.request,
                    _('Feedback "%(id)s" was deleted successfully.') % {
                        'id': feedback_id
                    }
                )
                
                logger.info(
                    f'Feedback deleted: {feedback_id} by {self.request.user.email}'
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error deleting feedback: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while deleting the feedback. Please try again.')
            )
            return redirect('feedback:feedback-list', organization_pk=self.get_organization().pk)

    def get_success_url(self):
        return reverse_lazy('feedback:feedback-list', kwargs={
            'organization_pk': self.get_organization().pk
        })

class BulkFeedbackAnalysisView(FeedbackMixin, FormView):
    """
    Handle bulk feedback analysis
    """
    template_name = 'feedback/bulk-analysis.html'
    form_class = BulkFeedbackAnalysisForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        feedback_ids = self.request.GET.get('ids', '').split(',')
        
        # Get selected feedback items
        selected_feedbacks = Feedback.objects.filter(
            organization=self.get_organization(),
            id__in=[uid for uid in feedback_ids if uid]
        )[:100]  # Limit to 100 items
        
        context['selected_feedbacks'] = selected_feedbacks
        context['page_title'] = _('Bulk Feedback Analysis')
        context['total_selected'] = selected_feedbacks.count()
        
        return context

    def form_valid(self, form):
        try:
            feedback_ids = form.cleaned_data['feedback_ids']
            analysis_type = form.cleaned_data['analysis_type']
            overwrite_existing = form.cleaned_data['overwrite_existing']
            
            # Get feedback items
            feedbacks = Feedback.objects.filter(
                organization=self.get_organization(),
                id__in=feedback_ids
            )
            
            # Filter based on overwrite setting
            if not overwrite_existing:
                feedbacks = feedbacks.filter(ai_analyzed=False)
            
            total_to_analyze = feedbacks.count()
            
            if total_to_analyze == 0:
                messages.warning(
                    self.request,
                    _('No feedback items selected for analysis.')
                )
                return redirect('feedback:feedback-list', organization_pk=self.get_organization().pk)
            
            # Start analysis process (in background task for production)
            self.start_bulk_analysis(feedbacks, analysis_type)
            
            messages.success(
                self.request,
                _('Bulk analysis started for %(count)s feedback items.') % {
                    'count': total_to_analyze
                }
            )
            
            logger.info(
                f'Bulk analysis started for {total_to_analyze} feedback items '
                f'by {self.request.user.email}'
            )
            
        except Exception as e:
            logger.error(f'Error starting bulk analysis: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while starting bulk analysis. Please try again.')
            )
        
        return redirect('feedback:feedback-list', organization_pk=self.get_organization().pk)

    def start_bulk_analysis(self, feedbacks, analysis_type):
        """
        Start bulk analysis process
        In production, this would use Celery or similar task queue
        """
        # For now, just mark as scheduled
        from django.utils import timezone
        feedbacks.update(
            ai_analysis_date=timezone.now(),
            requires_human_review=True  # Mark for review after analysis
        )
        
        # TODO: Integrate with actual AI analysis service
        # This would typically be a Celery task
        # analyze_feedbacks.delay([f.id for f in feedbacks], analysis_type)

class FeedbackImportView(FeedbackMixin, FormView):
    """
    Import feedback from CSV file
    """
    template_name = 'feedback/feedback-import.html'
    form_class = FeedbackImportForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.get_organization()
        return kwargs

    def form_valid(self, form):
        try:
            file = form.cleaned_data['file']
            channel = form.cleaned_data['channel']
            
            # Read CSV file with BOM handling
            content = file.read().decode('utf-8-sig')  # FIXED: Use utf-8-sig
            decoded_file = content.splitlines()
            reader = csv.DictReader(decoded_file)
            
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, 2):  # Start from 2 (header is 1)
                try:
                    with transaction.atomic():
                        # Find or create customer
                        customer_email = row.get('customer_email', '').strip().lower()
                        if not customer_email:
                            errors.append(f"Row {row_num}: Missing customer email")
                            continue
                        
                        customer, created = Customer.objects.get_or_create(
                            organization=self.get_organization(),
                            email=customer_email,
                            defaults={
                                'customer_id': f"CUST-{uuid.uuid4().hex[:8].upper()}",
                                'first_name': row.get('first_name', ''),
                                'last_name': row.get('last_name', ''),
                            }
                        )
                        
                        # Create feedback
                        feedback = Feedback(
                            organization=self.get_organization(),
                            customer=customer,
                            channel=channel,
                            subject=row.get('subject', '')[:500],
                            content=row.get('content', ''),
                            feedback_type=row.get('feedback_type', 'general'),
                            priority=row.get('priority', 'medium'),
                            status=row.get('status', 'new'),
                            original_language=row.get('language', 'en'),
                        )
                        feedback.save()
                        
                        imported_count += 1
                        
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    continue
            
            if imported_count > 0:
                messages.success(
                    self.request,
                    _('Successfully imported %(count)s feedback items.') % {
                        'count': imported_count
                    }
                )
            
            if errors:
                messages.warning(
                    self.request,
                    _('Completed with %(error_count)s errors.') % {
                        'error_count': len(errors)
                    }
                )
                # Store errors in session for display
                self.request.session['import_errors'] = errors[:10]  # Limit to 10 errors
            
            logger.info(
                f'Feedback import completed: {imported_count} imported, '
                f'{len(errors)} errors by {self.request.user.email}'
            )
            
        except Exception as e:
            logger.error(f'Error importing feedback: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred during import. Please check your file format.')
            )
            return self.form_invalid(form)
        
        return redirect('feedback:feedback-list', organization_pk=self.get_organization().pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Import Feedback')
        return context

class FeedbackAnalysisDashboardView(FeedbackMixin, TemplateView):
    """
    Dashboard for feedback analysis insights
    """
    template_name = 'feedback/analysis-dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        # Get analysis statistics
        total_feedbacks = Feedback.objects.filter(organization=organization).count()
        analyzed_feedbacks = Feedback.objects.filter(
            organization=organization, ai_analyzed=True
        ).count()
        
        # Sentiment distribution
        sentiment_data = Feedback.objects.filter(
            organization=organization,
            sentiment_label__isnull=False
        ).values('sentiment_label').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / total_feedbacks
        )
        
        # Feedback type distribution
        type_data = Feedback.objects.filter(
            organization=organization
        ).values('feedback_type').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / total_feedbacks
        )
        
        # Priority distribution
        priority_data = Feedback.objects.filter(
            organization=organization
        ).values('priority').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / total_feedbacks
        )
        
        context.update({
            'page_title': _('Feedback Analysis Dashboard'),
            'total_feedbacks': total_feedbacks,
            'analyzed_feedbacks': analyzed_feedbacks,
            'analysis_percentage': (analyzed_feedbacks / total_feedbacks * 100) if total_feedbacks > 0 else 0,
            'sentiment_data': sentiment_data,
            'type_data': type_data,
            'priority_data': priority_data,
            'needs_review': Feedback.objects.filter(
                organization=organization,
                requires_human_review=True
            ).count(),
        })
        
        return context

# API Views for AJAX operations
class AnalyzeSingleFeedbackView(FeedbackMixin, DetailView):
    """
    Analyze single feedback via AJAX
    """
    model = Feedback
    http_method_names = ['post']

    def get_queryset(self):
        organization = self.get_organization()
        return Feedback.objects.filter(organization=organization)

    def post(self, request, *args, **kwargs):
        feedback = self.get_object()
        
        try:
            # TODO: Integrate with AI analysis service
            # For now, simulate analysis
            feedback.ai_analyzed = True
            feedback.ai_analysis_date = timezone.now()
            feedback.requires_human_review = True
            feedback.save()
            
            return JsonResponse({
                'success': True,
                'message': _('Analysis completed successfully.'),
                'feedback_id': feedback.feedback_id
            })
            
        except Exception as e:
            logger.error(f'Error analyzing feedback {feedback.feedback_id}: {str(e)}')
            return JsonResponse({
                'success': False,
                'message': _('Analysis failed. Please try again.')
            }, status=500)