from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from core.models import *
from .forms import OrganizationForm, OrganizationMemberForm, OrganizationSettingsForm
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from django.core.exceptions import FieldError
from core.models import Organization, OrganizationMember
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from core.models import Organization, OrganizationMember
from .forms import OrganizationForm, OrganizationMemberForm, OrganizationSettingsForm
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import DetailView
from django.utils.translation import gettext_lazy as _
from django.http import Http404
from django.db.models import Count

logger = logging.getLogger(__name__)

class OrganizationMixin(LoginRequiredMixin):
    
    """
    Mixin to handle organization-based permissions
    """
    def get_queryset(self):
        # Users can only see organizations they are members of
        return Organization.objects.filter(
            members__user=self.request.user,
            members__is_active=True
        ).distinct()

class OrganizationListView(OrganizationMixin, ListView):
    """
    List all organizations the user is a member of
    """
    model = Organization
    template_name = 'organizations/organization-list.html'
    context_object_name = 'organizations'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Check if we want user-specific view (optional)
        view_type = self.request.GET.get('view', 'all')
        
        if view_type == 'user':
            # User-specific logic
            return queryset.annotate(
                member_count=Count('members')
            ).select_related().order_by('-created_at')
        
        # Default logic
        return queryset.annotate(
            member_count=Count('members')
        ).select_related()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('My Organizations')
        return context
    

class OrganizationUserListView(OrganizationMixin, LoginRequiredMixin, ListView):
    """
    List all organizations the user is a member of
    This view lists ORGANIZATIONS, not members of an organization
    """
    model = Organization
    template_name = 'organizations/organization-list.html'  # Template for listing organizations
    context_object_name = 'organizations'
    paginate_by = 10
    
    def get_queryset(self):
        """
        Return organizations based on view type:
        - Default: User's organizations only
        - With ?view=all: All organizations (if user has permission)
        - With ?view=public: Public organizations (if applicable)
        """
        view_type = self.request.GET.get('view', 'user')
        
        # Base queryset
        if view_type == 'all':
            # Check if user has permission to see all organizations
            if self.request.user.is_staff or self.request.user.has_perm('core.view_all_organizations'):
                queryset = Organization.objects.all()
            else:
                # Fallback to user's organizations if no permission
                queryset = Organization.objects.filter(
                    members__user=self.request.user,
                    members__is_active=True
                ).distinct()
        elif view_type == 'public':
            # Return public organizations - check if is_public field exists
            try:
                # Try to filter by is_public if the field exists
                queryset = Organization.objects.filter(is_public=True)
            except FieldError:
                # If is_public field doesn't exist, show organizations with public memberships
                queryset = Organization.objects.filter(
                    members__is_active=True
                ).distinct()
        else:
            # Default: User's organizations only
            queryset = Organization.objects.filter(
                members__user=self.request.user,
                members__is_active=True
            ).distinct()
        
        # Apply annotations and ordering
        queryset = queryset.annotate(
            member_count=Count('members')
        ).select_related('created_by').order_by('-created_at')
        
        # Store view type for context
        self.view_type = view_type
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the current view type (stored in get_queryset)
        view_type = getattr(self, 'view_type', 'user')
        
        # Get user's memberships for permission checking
        user_memberships = OrganizationMember.objects.filter(
            user=self.request.user,
            is_active=True
        ).select_related('organization')
        
        # Create a dict for quick lookup of user's role in each organization
        user_org_roles = {}
        user_org_permissions = {}
        for membership in user_memberships:
            user_org_roles[membership.organization_id] = membership.role
            user_org_permissions[membership.organization_id] = {
                'can_manage_organization': membership.can_manage_organization,
                'can_manage_users': membership.can_manage_users,
            }
        
        # Calculate counts for view type selector
        user_orgs_count = Organization.objects.filter(
            members__user=self.request.user,
            members__is_active=True
        ).distinct().count()
        
        all_orgs_count = Organization.objects.count()
        
        # Try to get public organizations count
        try:
            public_orgs_count = Organization.objects.filter(is_public=True).count()
        except FieldError:
            public_orgs_count = 0
        
        # Set appropriate page title based on view type
        if view_type == 'all':
            context['page_title'] = _('All Organizations')
            context['page_description'] = _('All organizations in the system')
        elif view_type == 'public':
            context['page_title'] = _('Public Organizations')
            context['page_description'] = _('Publicly accessible organizations')
        else:
            context['page_title'] = _('My Organizations')
            context['page_description'] = _('Organizations you are a member of')
        
        # Add view type to context
        context['current_view'] = view_type
        
        # Add organization roles and permissions for template
        context['user_org_roles'] = user_org_roles
        context['user_org_permissions'] = user_org_permissions
        
        # Add counts for the template
        context['user_organization_count'] = user_orgs_count
        context['all_organizations_count'] = all_orgs_count
        context['public_organizations_count'] = public_orgs_count
        
        # Add view type options for template
        context['view_options'] = [
            {
                'value': 'user', 
                'label': _('My Organizations'), 
                'count': user_orgs_count,
                'active': view_type == 'user'
            },
            {
                'value': 'all', 
                'label': _('All Organizations'), 
                'count': all_orgs_count,
                'active': view_type == 'all',
                'disabled': not (self.request.user.is_staff or self.request.user.has_perm('core.view_all_organizations'))
            },
            {
                'value': 'public', 
                'label': _('Public Organizations'), 
                'count': public_orgs_count,
                'active': view_type == 'public'
            }
        ]
        
        # Add permission flags
        context['can_view_all'] = self.request.user.is_staff or self.request.user.has_perm('core.view_all_organizations')
        context['can_create_organization'] = self.request.user.has_perm('core.add_organization')
        context['is_staff'] = self.request.user.is_staff
        
        # Add user object for template
        context['user'] = self.request.user
        
        return context
    

class OrganizationCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Create a new organization
    """
    model = Organization
    form_class = OrganizationForm
    template_name = 'organizations/organization-form.html'
    success_url = reverse_lazy('accounts:org-list')
    success_message = _('Organization created successfully!')

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Add the creator as an owner
        OrganizationMember.objects.create(
            organization=self.object,
            user=self.request.user,
            role='owner',
            is_active=True
        )
        
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Create Organization')
        context['submit_text'] = _('Create Organization')
        return context

class OrganizationDetailView(OrganizationMixin, DetailView):
    """
    View organization details
    """
    model = Organization
    template_name = 'organizations/organization-detail.html'
    context_object_name = 'organization'
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object()
        
        # Get members
        context['members'] = organization.members.select_related('user').all()
        
        # Get user's role in this organization
        user_membership = organization.members.filter(user=self.request.user).first()
        context['user_role'] = user_membership.role if user_membership else None
        context['can_manage'] = user_membership and user_membership.can_manage_organization
        
        context['page_title'] = organization.name
        return context

class OrganizationUpdateView(OrganizationMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    """
    Update organization details
    """
    model = Organization
    form_class = OrganizationForm
    template_name = 'organizations/organization-form.html'
    success_url = reverse_lazy('accounts:org-list')
    success_message = _('Organization updated successfully!')
    slug_url_kwarg = 'slug'

    def test_func(self):
        organization = self.get_object()
        membership = organization.members.filter(
            user=self.request.user,
            role__in=['owner', 'admin']
        ).first()
        return membership is not None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Edit Organization')
        context['submit_text'] = _('Update Organization')
        return context

class OrganizationDeleteView(OrganizationMixin, UserPassesTestMixin, SuccessMessageMixin, DeleteView):
    """
    Delete an organization
    """
    model = Organization
    template_name = 'organizations/organization-confirm-delete.html'
    success_url = reverse_lazy('organizations:list')
    success_message = _('Organization deleted successfully!')
    slug_url_kwarg = 'slug'

    def test_func(self):
        organization = self.get_object()
        membership = organization.members.filter(
            user=self.request.user,
            role='owner'
        ).first()
        return membership is not None


class OrganizationSettingsView(OrganizationMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    """
    Update organization settings
    """
    model = Organization
    form_class = OrganizationSettingsForm
    template_name = 'organizations/organization-settings.html'
    success_url = reverse_lazy('accounts:org-list')
    success_message = _('Organization settings updated successfully!')
    slug_url_kwarg = 'slug'

    def test_func(self):
        organization = self.get_object()
        membership = organization.members.filter(
            user=self.request.user,
            role__in=['owner', 'admin']
        ).first()
        return membership is not None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object()
        
        # Get form instance
        form = kwargs.get('form')
        if not form:
            form = self.get_form()
        
        # Default values for missing methods
        feedback_count = 0
        customer_count = 0
        positive_sentiment_percentage = 0
        feedback_usage_percentage = 0
        
        # Try to get feedback count if Feedback model exists
        try:
            from core.models import Feedback
            feedback_count = Feedback.objects.filter(organization=organization).count()
            
            # Calculate positive sentiment if possible
            positive_count = Feedback.objects.filter(
                organization=organization,
                sentiment_label='positive'
            ).count()
            
            if feedback_count > 0:
                positive_sentiment_percentage = int((positive_count / feedback_count) * 100)
            
            # Calculate feedback usage percentage
            monthly_limit = organization.monthly_feedback_limit
            if monthly_limit and monthly_limit > 0:
                feedback_usage_percentage = min(100, int((feedback_count / monthly_limit) * 100))
                
        except (ImportError, AttributeError, NameError):
            # If Feedback model doesn't exist or query fails, use defaults
            pass
        print("Feedback Count:", feedback_count)
        # Try to get customer count if Customer model exists
        try:
            from core.models import Customer
            customer_count = Customer.objects.filter(organization=organization).count()
        except (ImportError, AttributeError, NameError):
            # If Customer model doesn't exist or query fails, use 0
            customer_count = 0
        
        # Check permissions for dangerous actions
        try:
            can_perform_dangerous_actions = (
                self.request.user == organization.created_by or
                organization.members.filter(
                    user=self.request.user,
                    role='owner'
                ).exists()
            )
        except AttributeError:
            can_perform_dangerous_actions = False
        
        context.update({
            'page_title': _('Organization Settings'),
            'organization': organization,
            'form': form,
            'created_date': organization.created_at.strftime("%B %d, %Y"),
            'total_members': organization.members.count(),
            'active_members_count': organization.members.filter(is_active=True).count(),
            'subscription_tier_display': organization.get_subscription_tier_display(),
            'feedback_count': feedback_count,
            'customer_count': customer_count,
            'feedback_usage_percentage': feedback_usage_percentage,
            'positive_sentiment_percentage': positive_sentiment_percentage,
            'recent_activities': [],  # Empty for now until you implement activity tracking
            'can_perform_dangerous_actions': can_perform_dangerous_actions,
        })
        
        return context

    def get_success_url(self):
        """Redirect to organization settings page after successful update."""
        organization = self.get_object()
        return reverse_lazy('accounts:org-settings', kwargs={'slug': organization.slug})
   

class OrganizationMemberCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Add a member to an organization with proper permission checks and error handling
    """
    model = OrganizationMember
    form_class = OrganizationMemberForm
    template_name = 'organizations/organization-member-form.html'
    
    def get_organization(self):
        """
        Get organization object with proper error handling
        """
        if hasattr(self, '_organization'):
            return self._organization
        
        organization_pk = self.kwargs.get('pk')
        self._organization = get_object_or_404(
            Organization.objects.select_related('created_by'),
            pk=organization_pk
        )
        return self._organization

    def test_func(self):
        """
        Check if user has permission to add members
        """
        try:
            organization = self.get_organization()
            user_membership = organization.members.filter(
                user=self.request.user,
                role__in=['owner', 'admin', 'manager'],
                is_active=True
            ).first()
            return user_membership is not None
        except Organization.DoesNotExist:
            return False

    def get_form_kwargs(self):
        """
        Pass organization to the form
        """
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.get_organization()
        return kwargs

    def form_valid(self, form):
        """
        Handle valid form submission with transaction safety
        """
        try:
            with transaction.atomic():
                # Set the organization and added_by before saving
                form.instance.organization = self.get_organization()
                form.instance.added_by = self.request.user
                form.instance.is_active = True
                
                response = super().form_valid(form)
                
                messages.success(
                    self.request,
                    _('Member "%(email)s" was added successfully!') % {
                        'email': form.instance.user.email
                    }
                )
                
                return response
                
        except Exception as e:
            messages.error(
                self.request,
                _('An error occurred while adding the member. Please try again.')
            )
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Organization member creation error: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        """
        Handle invalid form submission with user-friendly error messages
        """
        messages.error(
            self.request,
            _('Please correct the errors below and try again.')
        )
        return super().form_invalid(form)

    def get_success_url(self):
        """
        Redirect to organization detail page after successful member addition
        """
        return reverse_lazy('accounts:org-detail', kwargs={'pk': self.get_organization().pk})

    def get_context_data(self, **kwargs):
        """
        Add organization and other context to template
        """
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        context.update({
            'organization': organization,
            'page_title': _('Add Team Member'),
            'editing': False,
            'submit_text': _('Add Member'),
            'cancel_url': reverse_lazy('accounts:org-detail', kwargs={'pk': organization.pk})
        })
        return context

    def handle_no_permission(self):
        """
        Custom handling for permission denied
        """
        messages.error(
            self.request,
            _('You do not have permission to add members to this organization.')
        )
        organization_pk = self.kwargs.get('pk')
        return redirect('accounts:org-detail', pk=organization_pk)

from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

class OrganizationMemberUpdateView(UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    """
    Update organization member role
    """
    model = OrganizationMember
    form_class = OrganizationMemberForm
    template_name = 'organizations/organization-member-form.html'
    success_message = _('Member updated successfully!')
    pk_url_kwarg = 'member_pk'  # Tell Django to look for 'member_pk' in URL
    
    def setup(self, request, *args, **kwargs):
        """Initialize the view and get the organization"""
        super().setup(request, *args, **kwargs)
        # Get organization from URL parameter (org_pk)
        self.organization = get_object_or_404(
            Organization, 
            pk=self.kwargs.get('org_pk')
        )
    
    def get_queryset(self):
        """Filter members by the current organization for security"""
        queryset = super().get_queryset()
        return queryset.filter(organization=self.organization)
    
    def get_object(self, queryset=None):
        """Get the specific member to update"""
        if queryset is None:
            queryset = self.get_queryset()
        
        # Get member_pk from URL
        member_pk = self.kwargs.get(self.pk_url_kwarg)
        if not member_pk:
            raise AttributeError(
                "OrganizationMemberUpdateView must be called with 'member_pk' "
                "in the URLconf."
            )
        
        # Get the member
        return get_object_or_404(queryset, pk=member_pk)
    
    def test_func(self):
        """Check if user has permission to edit this member"""
        # Get organization
        if not hasattr(self, 'organization'):
            return False
        
        # Get user membership
        user_membership = self.organization.members.filter(
            user=self.request.user,
            is_active=True
        ).first()
        
        if not user_membership:
            return False
        
        # Get member being edited
        try:
            member = self.get_object()
        except Http404:
            return False
        
        # CANNOT edit yourself through this view
        if member.user == self.request.user:
            return False
        
        # Only users with can_manage_users permission can edit
        if not user_membership.can_manage_users:
            return False
        
        # Additional: Only owners can edit other owners
        if member.role == 'owner' and user_membership.role != 'owner':
            return False
        
        return True
    
    def get_form(self, form_class=None):
        """Customize the form based on user's permissions"""
        form = super().get_form(form_class)
        
        # Get current user's membership
        user_membership = self.organization.members.filter(
            user=self.request.user
        ).first()
        
        # Get the member being edited
        member = self.get_object()
        
        # Limit role choices based on user's permissions
        if user_membership:
            if user_membership.role == 'manager':
                # Managers can only assign analyst or viewer roles
                form.fields['role'].choices = [
                    ('analyst', _('Analyst')),
                    ('viewer', _('Viewer'))
                ]
            elif user_membership.role == 'admin':
                # Admins can assign admin, manager, analyst, or viewer
                # But not owner (owner transfer should be a separate process)
                form.fields['role'].choices = [
                    ('admin', _('Administrator')),
                    ('manager', _('Manager')),
                    ('analyst', _('Analyst')),
                    ('viewer', _('Viewer'))
                ]
            # Owners can assign any role including other owners
        
        return form
    
    def form_valid(self, form):
        """Add additional validation before saving"""
        member = form.instance
        user_membership = self.organization.members.filter(
            user=self.request.user
        ).first()
        
        # Additional validation
        if member.role == 'owner':
            # Check if user can assign owner role
            if user_membership.role != 'owner':
                form.add_error('role', _('Only owners can assign owner role.'))
                return self.form_invalid(form)
            
            # Warn about transferring ownership (you might want to handle this differently)
            if self.get_object().role != 'owner':
                # This is an ownership transfer - add warning message
                from django.contrib import messages
                messages.warning(
                    self.request,
                    _('You are assigning ownership to this member. '
                      'This will give them full control over the organization.')
                )
        
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to member detail page"""
        # Check what parameters your member detail URL expects
        return reverse_lazy('accounts:org-member-detail', kwargs={
            'org_pk': self.organization.pk,
            'member_pk': self.object.pk
        })
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.get_object()
        
        context.update({
            'organization': self.organization,
            'page_title': _('Edit Member - %(name)s') % {
                'name': member.user.get_full_name() or member.user.email
            },
            'editing': True,
            'member': member,  # Add member to context for template
        })
        
        return context
   

from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _ 

class OrganizationMemberUpdateView1(OrganizationMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    """
    Update organization member role
    """
    model = OrganizationMember
    form_class = OrganizationMemberForm
    template_name = 'organizations/organization-member-form.html'
    success_message = _('Member updated successfully!')
    pk_url_kwarg = 'member_pk'

    def test_func(self):
        member = self.get_object()
        user_membership = member.organization.members.filter(
            user=self.request.user,
            role__in=['owner', 'admin', 'manager']
        ).first()
        
        # Cannot modify owners unless you are an owner
        if member.role == 'owner' and user_membership.role != 'owner':
            return False
            
        return user_membership is not None

    def get_success_url(self):
        return reverse_lazy('accounts:org-member-detail', kwargs={'pk': self.object.organization.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.object.organization
        context['page_title'] = _('Edit Member')
        context['editing'] = True
        return context

class OrganizationMemberDeleteView(OrganizationMixin, UserPassesTestMixin, SuccessMessageMixin, DeleteView):
    """
    Remove a member from an organization
    """
    model = OrganizationMember
    template_name = 'organizations/organization-member-confirm-delete.html'
    success_message = _('Member removed successfully!')

    def test_func(self):
        member = self.get_object()
        user_membership = member.organization.members.filter(
            user=self.request.user,
            role__in=['owner', 'admin', 'manager']
        ).first()
        
        # Cannot remove owners unless you are an owner
        if member.role == 'owner' and user_membership.role != 'owner':
            return False
            
        # Cannot remove yourself
        if member.user == self.request.user:
            return False
            
        return user_membership is not None

    def get_success_url(self):
        return reverse_lazy('accounts:member-detail', kwargs={'slug': self.object.organization.slug})


    
class OrganizationMemberListView(OrganizationMixin, UserPassesTestMixin, ListView):
    """
    List all members of an organization with filtering and search
    """
    model = OrganizationMember
    template_name = 'organizations/organization-member-list.html'
    context_object_name = 'members'
    paginate_by = 20
    
    def get_organization(self):
        """Get organization from URL parameters"""
        organization_pk = self.kwargs.get('pk')
        return get_object_or_404(Organization, pk=organization_pk)
    
    def test_func(self):
        """Check if user has permission to view members"""
        organization = self.get_organization()
        user_membership = organization.members.filter(
            user=self.request.user,
            is_active=True
        ).first()
        return user_membership is not None
    
    def get_queryset(self):
        """Get filtered queryset for organization members"""
        organization = self.get_organization()
        queryset = OrganizationMember.objects.filter(
            organization=organization,
            is_active=True
        ).select_related('user').order_by('-role', 'user__email')
        
        # Apply search filter
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(user__email__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(role__icontains=search_query)
            )
        
        # Apply role filter
        role_filter = self.request.GET.get('role', '')
        if role_filter:
            queryset = queryset.filter(role=role_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        # Get current user's membership for permission checks
        user_membership = organization.members.filter(
            user=self.request.user,
            is_active=True
        ).first()
        
        context.update({
            'organization': organization,
            'page_title': _('Team Members - %(org)s') % {'org': organization.name},
            'user_membership': user_membership,
            'can_manage_members': user_membership and user_membership.can_manage_users,
            'can_manage_organization': user_membership and user_membership.can_manage_organization,
            'role_choices': OrganizationMember.ORGANIZATION_ROLES,
            'search_query': self.request.GET.get('search', ''),
            'role_filter': self.request.GET.get('role', ''),
        })
        
        # Add member statistics
        total_members = self.get_queryset().count()
        context['total_members'] = total_members
        context['owners_count'] = self.get_queryset().filter(role='owner').count()
        context['admins_count'] = self.get_queryset().filter(role='admin').count()
        context['managers_count'] = self.get_queryset().filter(role='manager').count()
        context['viewers_count'] = self.get_queryset().filter(role='viewer').count()
        context['analysts_count'] = self.get_queryset().filter(role='analyst').count()
        context['owner_managers_count'] = self.get_queryset().filter(role__in=['admin', 'manager']).count()
        context['viewers_analysts_count'] = self.get_queryset().filter(role__in=['viewer', 'analyst']).count()
        
        return context

# Assuming you have these models
# from .models import Organization, OrganizationMember

class OrganizationMemberDetailView(UserPassesTestMixin, DetailView):
    """
    View organization member details
    """
    model = OrganizationMember
    template_name = 'organizations/organization-member-detail.html'
    context_object_name = 'member'
    pk_url_kwarg = 'member_pk'  # This tells Django to use 'member_pk' instead of 'pk'
    
    def setup(self, request, *args, **kwargs):
        """Initialize view and set organization based on URL parameter"""
        super().setup(request, *args, **kwargs)
        
        # Try to get organization by slug first, then by pk
        org_slug = self.kwargs.get('org_slug')
        org_pk = self.kwargs.get('org_pk')
        
        try:
            if org_slug:
                self.organization = get_object_or_404(
                    Organization, 
                    slug=org_slug
                )
            elif org_pk:
                self.organization = get_object_or_404(
                    Organization, 
                    pk=org_pk
                )
            else:
                raise Http404(_("Organization not specified"))
        except (Organization.DoesNotExist, Http404):
            raise Http404(_("Organization not found"))
    
    def get_queryset(self):
        """Filter members by organization for security"""
        queryset = super().get_queryset()
        return queryset.filter(organization=self.organization)
    
    def get_object(self, queryset=None):
        """Get the specific member with organization validation"""
        if queryset is None:
            queryset = self.get_queryset()
        
        # Get member_pk from URL
        member_pk = self.kwargs.get(self.pk_url_kwarg)
        if not member_pk:
            raise AttributeError(
                "OrganizationMemberDetailView must be called with 'member_pk' "
                "in the URLconf."
            )
        
        # Get the member
        obj = get_object_or_404(queryset, pk=member_pk)
        return obj
    
    def test_func(self):
        """Check if user has permission to view member details"""
        # Get current user's membership in this organization
        user_membership = self.organization.members.filter(
            user=self.request.user,
            is_active=True
        ).first()
        
        if not user_membership:
            return False  # User is not a member of this organization
        
        try:
            # Get the member being viewed
            member = self.get_object()
        except Http404:
            return False
        
        # Users can view their own membership or if they can manage users
        return (
            member.user == self.request.user or 
            user_membership.can_manage_users
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.get_object()
        
        # Get current user's membership for permission checks
        user_membership = self.organization.members.filter(
            user=self.request.user,
            is_active=True
        ).first()
        
        # Get role distribution for the sidebar
        role_distribution = self.organization.members.filter(
            is_active=True
        ).values('role').annotate(
            count=Count('role')
        ).order_by('-count')
        
        context.update({
            'organization': self.organization,
            'page_title': _('Member Details - %(name)s') % {
                'name': member.user.get_full_name() or member.user.email
            },
            'user_membership': user_membership,
            'can_edit_member': (
                user_membership and 
                user_membership.can_manage_users and
                user_membership != member  # Can't edit your own role via this view
            ),
            'can_remove_member': (
                user_membership and 
                user_membership.can_manage_users and
                member.user != self.request.user and  # Cannot remove self
                (user_membership.role == 'owner' or member.role != 'owner')  # Only owners can remove other owners
            ),
            'role_distribution': role_distribution,  # For the sidebar stats
        })
        
        return context


from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import timedelta

class OrganizationMemberInviteView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Invite a new user to join the organization
    """
    model = OrganizationMember
    template_name = 'organizations/organization-member-invite.html'
    fields = []  # Empty because we'll use a custom form
    
    def get_organization(self):
        """Get organization from URL parameters"""
        organization_pk = self.kwargs.get('pk')
        return get_object_or_404(Organization, pk=organization_pk)
    
    def test_func(self):
        """Check if user can invite members"""
        organization = self.get_organization()
        user_membership = organization.members.filter(
            user=self.request.user,
            role__in=['owner', 'admin', 'manager'],
            is_active=True
        ).first()
        return user_membership is not None
    
    def get_form_class(self):
        """Return the form class to use"""
        from django import forms
        
        class OrganizationMemberInviteForm(forms.Form):
            email = forms.EmailField(
                label=_('Email Address'),
                required=True,
                widget=forms.EmailInput(attrs={
                    'class': 'form-control',
                    'placeholder': _('user@example.com')
                }),
                help_text=_("Enter the email address of the person you want to invite")
            )
            role = forms.ChoiceField(
                label=_('Role'),
                choices=OrganizationMember.ORGANIZATION_ROLES,
                initial='viewer',
                widget=forms.Select(attrs={'class': 'form-control'}),
                help_text=_("Select the role for this member")
            )
            
            def clean_email(self):
                """Validate email address"""
                email = self.cleaned_data['email']
                
                # Check if email belongs to requesting user
                if self.request and email == self.request.user.email:
                    raise forms.ValidationError(
                        _("You cannot invite yourself.")
                    )
                
                return email.lower()  # Normalize to lowercase
        
        return OrganizationMemberInviteForm
    
    def get_form(self, form_class=None):
        """Create form instance"""
        if form_class is None:
            form_class = self.get_form_class()
        
        form_kwargs = self.get_form_kwargs()
        form_kwargs.pop('instance', None)
        form = form_class(**form_kwargs)
        
        # Pass request to form for custom validation
        form.request = self.request
        return form
    
    def send_invitation_email(self, invitation):
        """Send invitation email"""
        try:
            # Prepare email content
            context = {
                'invitation': invitation,
                'organization': invitation.organization,
                'invited_by': invitation.invited_by,
                'invitation_link': invitation.get_invitation_link(self.request),
                'expiration_days': 7,  # Default expiration
            }
            
            # Render email templates
            subject = _('Invitation to join %(org)s') % {'org': invitation.organization.name}
            html_message = render_to_string('emails/organization_invitation.html', context)
            plain_message = strip_tags(html_message)
            
            # Send email
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [invitation.email]
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            
            # Mark invitation as sent
            invitation.mark_as_sent()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending invitation email to {invitation.email}: {str(e)}", exc_info=True)
            return False
    
    def form_valid(self, form):
        """Handle invitation submission"""
        try:
            with transaction.atomic():
                organization = self.get_organization()
                email = form.cleaned_data['email']
                role = form.cleaned_data['role']
                
                # Check if user exists
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                try:
                    user = User.objects.get(email=email)
                    user_exists = True
                except User.DoesNotExist:
                    user_exists = False
                
                # Check if user is already a member
                existing_member = organization.members.filter(user__email=email).first()
                if existing_member:
                    if existing_member.is_active:
                        messages.error(
                            self.request,
                            _('User %(email)s is already a member of this organization.') % {'email': email}
                        )
                        return self.form_invalid(form)
                    else:
                        # Reactivate inactive member
                        existing_member.is_active = True
                        existing_member.role = role
                        existing_member.save()
                        
                        messages.success(
                            self.request,
                            _('User %(email)s has been reactivated.') % {'email': email}
                        )
                        return redirect(self.get_success_url())
                
                # Check for existing pending invitation
                existing_invitation = Invitation.objects.filter(
                    organization=organization,
                    email=email,
                    status__in=['pending', 'sent']
                ).first()
                
                if existing_invitation:
                    if existing_invitation.is_expired:
                        # Resend expired invitation
                        existing_invitation.resend()
                        invitation = existing_invitation
                        messages.info(
                            self.request,
                            _('Existing invitation was expired. A new invitation has been sent to %(email)s.') % {'email': email}
                        )
                    else:
                        # Update existing invitation
                        existing_invitation.role = role
                        existing_invitation.save()
                        invitation = existing_invitation
                        messages.info(
                            self.request,
                            _('Invitation already sent to %(email)s. Role has been updated.') % {'email': email}
                        )
                else:
                    if user_exists:
                        # For existing users, add them directly
                        OrganizationMember.objects.create(
                            organization=organization,
                            user=user,
                            role=role,
                            is_active=True,
                        )
                        
                        messages.success(
                            self.request,
                            _('User %(email)s has been added to the organization.') % {'email': email}
                        )
                        return redirect(self.get_success_url())
                    else:
                        # Create invitation for non-existing user
                        invitation = Invitation.objects.create(
                            organization=organization,
                            email=email,
                            role=role,
                            invited_by=self.request.user,
                            # Token and expires_at are set automatically in save()
                        )
                        
                        messages.success(
                            self.request,
                            _('Invitation created for %(email)s.') % {'email': email}
                        )
                
                # Send invitation email
                email_sent = self.send_invitation_email(invitation)
                
                if email_sent:
                    messages.success(
                        self.request,
                        _('Invitation email sent to %(email)s.') % {'email': email}
                    )
                else:
                    messages.warning(
                        self.request,
                        _('Invitation created but email could not be sent. You can resend it later.')
                    )
                
                return redirect(self.get_success_url())
                
        except Exception as e:
            logger.error(f"Error inviting member: {str(e)}", exc_info=True)
            messages.error(
                self.request,
                _('An error occurred while sending the invitation. Please try again.')
            )
            return self.form_invalid(form)
    
    def get_success_url(self):
        """Redirect to member list after invitation"""
        organization = self.get_organization()
        return reverse_lazy('accounts:org-member-list', kwargs={'pk': organization.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        # Get pending invitations for this organization
        pending_invitations = Invitation.objects.filter(
            organization=organization,
            status__in=['pending', 'sent']
        ).count()
        
        context.update({
            'organization': organization,
            'page_title': _('Invite Team Member'),
            'submit_text': _('Send Invitation'),
            'cancel_url': reverse_lazy('accounts:org-member-list', kwargs={'pk': organization.pk}),
            'current_members_count': organization.members.count(),
            'pending_invitations_count': pending_invitations,
        })
        return context

class AcceptInvitationView(LoginRequiredMixin, View):
    """
    Handle invitation acceptance
    """
    template_name = 'organizations/accept-invitation.html'
    
    def get(self, request, token):
        """Display invitation details"""
        try:
            invitation = get_object_or_404(Invitation, token=token)
            
            # Check if invitation is valid
            if not invitation.is_valid:
                messages.error(
                    request,
                    _('This invitation is no longer valid.')
                )
                return render(request, 'organizations/invitation_invalid.html')
            
            # Check if user is already logged in with same email
            if request.user.email.lower() != invitation.email.lower():
                messages.warning(
                    request,
                    _('This invitation is for %(email)s, but you are logged in as %(current_email)s.') % {
                        'email': invitation.email,
                        'current_email': request.user.email
                    }
                )
            
            return render(request, self.template_name, {
                'invitation': invitation,
                'organization': invitation.organization,
            })
            
        except Invitation.DoesNotExist:
            messages.error(
                request,
                _('Invalid invitation token.')
            )
            return redirect('home')
    
    def post(self, request, token):
        """Accept the invitation"""
        try:
            invitation = get_object_or_404(Invitation, token=token)
            
            # Validate invitation
            if not invitation.is_valid:
                messages.error(
                    request,
                    _('This invitation is no longer valid.')
                )
                return redirect('home')
            
            # Check if user email matches
            if request.user.email.lower() != invitation.email.lower():
                messages.error(
                    request,
                    _('This invitation is for a different email address.')
                )
                return render(request, self.template_name, {
                    'invitation': invitation,
                    'organization': invitation.organization,
                })
            
            # Check if user is already a member
            existing_member = invitation.organization.members.filter(
                user=request.user
            ).first()
            
            if existing_member:
                if existing_member.is_active:
                    messages.info(
                        request,
                        _('You are already a member of %(org)s.') % {'org': invitation.organization.name}
                    )
                else:
                    # Reactivate membership
                    existing_member.is_active = True
                    existing_member.save()
                    messages.success(
                        request,
                        _('Your membership to %(org)s has been reactivated.') % {'org': invitation.organization.name}
                    )
            else:
                # Accept invitation
                success = invitation.accept(request.user)
                if success:
                    messages.success(
                        request,
                        _('You have successfully joined %(org)s!') % {'org': invitation.organization.name}
                    )
                else:
                    messages.error(
                        request,
                        _('Failed to accept invitation. Please try again.')
                    )
                    return redirect('accounts:home-page')
            
            # Redirect to organization dashboard
            return redirect('dashboard:organization-dashboard', slug=invitation.organization.slug)
            
        except Exception as e:
            logger.error(f"Error accepting invitation: {str(e)}", exc_info=True)
            messages.error(
                request,
                _('An error occurred while accepting the invitation.')
            )
            return redirect('accounts:home-page')    

class OrganizationMemberDeactivateView(OrganizationMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    """
    Deactivate a member (soft delete)
    """
    model = OrganizationMember
    template_name = 'organizations/organization-member-confirm-deactivate.html'
    success_message = _('Member deactivated successfully!')
    
    def test_func(self):
        """Check if user can deactivate members"""
        member = self.get_object()
        organization = member.organization
        
        user_membership = organization.members.filter(
            user=self.request.user,
            role__in=['owner', 'admin', 'manager'],
            is_active=True
        ).first()
        
        # Cannot deactivate yourself
        if member.user == self.request.user:
            return False
        
        # Only owners can deactivate other owners
        if member.role == 'owner' and user_membership.role != 'owner':
            return False
        
        return user_membership is not None
    
    def form_valid(self, form):
        """Deactivate the member"""
        member = self.get_object()
        member.is_active = False
        member.save()
        
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to member list after deactivation"""
        member = self.get_object()
        return reverse_lazy('accounts:org-member-list', kwargs={'pk': member.organization.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.get_object()
        
        context.update({
            'organization': member.organization,
            'page_title': _('Deactivate Member'),
            'member': member,
        })
        return context

class OrganizationMemberReactivateView(OrganizationMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    """
    Reactivate a deactivated member
    """
    model = OrganizationMember
    template_name = 'organizations/organization-member-confirm-reactivate.html'
    success_message = _('Member reactivated successfully!')
    
    def test_func(self):
        """Check if user can reactivate members"""
        member = self.get_object()
        organization = member.organization
        
        user_membership = organization.members.filter(
            user=self.request.user,
            role__in=['owner', 'admin', 'manager'],
            is_active=True
        ).first()
        
        return user_membership is not None and not member.is_active
    
    def form_valid(self, form):
        """Reactivate the member"""
        member = self.get_object()
        member.is_active = True
        member.save()
        
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to member list after reactivation"""
        member = self.get_object()
        return reverse_lazy('accounts:org-member-list', kwargs={'pk': member.organization.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.get_object()
        
        context.update({
            'organization': member.organization,
            'page_title': _('Reactivate Member'),
            'member': member,
        })
        return context
    
from django.views.generic.edit import FormView

class OrganizationTransferOwnershipView(OrganizationMixin, UserPassesTestMixin, SuccessMessageMixin, FormView):
    """
    Transfer organization ownership to another member
    """
    template_name = 'organizations/organization-transfer-ownership.html'
    success_message = _('Ownership transferred successfully!')
    
    def test_func(self):
        """Check if user is the current owner"""
        organization = self.get_organization()
        user_membership = organization.members.filter(
            user=self.request.user,
            role='owner',
            is_active=True
        ).first()
        return user_membership is not None
    
    def get_organization(self):
        """Get organization from URL - using UUID"""
        from core.models import Organization
        from django.shortcuts import get_object_or_404
        
        # Try to get organization by UUID (from URL pattern)
        organization_id = self.kwargs.get('organization_pk') or self.kwargs.get('pk') or self.kwargs.get('slug')
        
        try:
            # First try to get by UUID if it looks like one
            import uuid
            try:
                uuid_obj = uuid.UUID(str(organization_id))
                return Organization.objects.get(id=uuid_obj)
            except (ValueError, AttributeError):
                # If not a valid UUID, try to get by slug
                return Organization.objects.get(slug=organization_id)
        except Organization.DoesNotExist:
            # Return 404 if organization doesn't exist
            raise Http404(_("Organization does not exist"))
    
    def get_form(self, form_class=None):
        """Create form for selecting new owner"""
        from django import forms
        from core.models import OrganizationMember
        
        organization = self.get_organization()
        
        class TransferOwnershipForm(forms.Form):
            new_owner = forms.ModelChoiceField(
                label=_('Select New Owner'),
                queryset=OrganizationMember.objects.filter(
                    organization=organization,
                    is_active=True
                ).exclude(user=self.request.user).select_related('user'),
                widget=forms.Select(attrs={'class': 'form-control'}),
                empty_label=_('Select a member'),
                required=True
            )
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['new_owner'].label_from_instance = lambda obj: f"{obj.user.get_full_name() or obj.user.email} ({obj.get_role_display()})"
        
        return TransferOwnershipForm(**self.get_form_kwargs())
    
    def form_valid(self, form):
        """Transfer ownership"""
        from core.models import OrganizationMember
        
        try:
            organization = self.get_organization()
            new_owner_member = form.cleaned_data['new_owner']
            
            # Check if new owner is the same as current owner
            if new_owner_member.user == self.request.user:
                form.add_error('new_owner', _('You cannot transfer ownership to yourself.'))
                return self.form_invalid(form)
            
            # Check if organization has at least 2 members
            active_members = organization.members.filter(is_active=True).count()
            if active_members < 2:
                messages.error(
                    self.request,
                    _('Cannot transfer ownership. Organization must have at least 2 members.')
                )
                return redirect(self.get_success_url())
            
            with transaction.atomic():
                # Update current owner's role to admin
                current_owner = organization.members.get(
                    user=self.request.user,
                    role='owner'
                )
                current_owner.role = 'admin'
                current_owner.save()
                
                # Update new owner's role to owner
                new_owner_member.role = 'owner'
                new_owner_member.save()
                
                # Update organization created_by field
                organization.created_by = new_owner_member.user
                organization.save()
                
                # Log the ownership transfer
                logger.info(
                    f"Ownership transferred: {self.request.user.email} -> {new_owner_member.user.email} "
                    f"for organization: {organization.name}"
                )
                
                messages.success(
                    self.request,
                    _('Ownership transferred to %(email)s.') % {'email': new_owner_member.user.email}
                )
                
                return redirect(self.get_success_url())
                
        except OrganizationMember.DoesNotExist:
            logger.error(f"Current owner not found: {self.request.user.email}")
            messages.error(
                self.request,
                _('You are not the owner of this organization.')
            )
            return redirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Error transferring ownership: {str(e)}", exc_info=True)
            messages.error(
                self.request,
                _('An error occurred while transferring ownership. Please try again.')
            )
            return self.form_invalid(form)
    
    def get_success_url(self):
        """Redirect to organization settings"""
        organization = self.get_organization()
        # Check what URL pattern your org-settings uses
        # If it uses UUID:
        return reverse_lazy('accounts:org-settings', kwargs={'pk': organization.pk})
        # OR if it uses slug:
        # return reverse_lazy('accounts:org-settings', kwargs={'slug': organization.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        # Check what URL pattern your org-settings uses
        cancel_url = reverse_lazy('accounts:org-settings', kwargs={'pk': organization.pk})
        
        context.update({
            'organization': organization,
            'page_title': _('Transfer Ownership'),
            'submit_text': _('Transfer Ownership'),
            'cancel_url': cancel_url,
        })
        return context
