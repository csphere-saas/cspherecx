# ALTERNATIVE 4: Using Custom FormMixin
# Automatically inject organization_id into all forms
# Most robust and DRY approach

import logging
from threading import local
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, FormView
from core.models import Organization, Customer, OrganizationMember
from .forms import CustomerForm, CustomerFilterForm
from django.contrib.messages.views import SuccessMessageMixin
logger = logging.getLogger(__name__)
from django.db import transaction
import logging
import uuid

_thread_locals = local()

def get_current_organization_id():
    """Get organization ID from thread-local context"""
    return getattr(_thread_locals, 'organization_id', None)

def set_organization_id(org_id):
    """Set organization ID in thread-local context"""
    _thread_locals.organization_id = org_id
    
class CustomerMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin for customer views to handle organization permissions
    """
    def get_organization(self):
        organization_pk = self.kwargs.get('organization_pk')
        return get_object_or_404(Organization, pk=organization_pk)

    def get_organization_id(self):
        """Get just the organization ID"""
        return self.kwargs.get('organization_pk')

    def test_func(self):
        organization = self.get_organization()
        return organization.members.filter(
            user=self.request.user,
            is_active=True
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        return context

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
    
    
class OrganizationMixin1:
    """Mixin to handle organization context"""
    
    def get_organization(self):
        organization_id = self.kwargs.get('organization_id')
        return get_object_or_404(Organization, id=organization_id)
    
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
 
class CustomerCreateView(OrganizationMixin, CreateView):
    """
    View to create a customer manually.
    Explicitly assigns organization before saving.
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass organization to form __init__ for validation/filtering if needed
        kwargs['organization'] = self.get_organization()
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # CRITICAL FIX: Assign organization manually before saving
                customer = form.save(commit=False)
                customer.organization = self.get_organization()
                customer.save()
                
                messages.success(self.request, f"Customer {customer.get_full_name()} created successfully.")
                logger.info(f"Customer {customer.id} created by {self.request.user}")
                return redirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            messages.error(self.request, "Error creating customer.")
            return self.form_invalid(form)

    def get_success_url(self):
        # Update with your actual URL name
        return reverse_lazy('customer-list', kwargs={'organization_pk': self.get_organization().pk})   
    
class CustomerCreateView1(OrganizationMixin, CreateView):
    """
    Create a new customer for an organization
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.get_organization()
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                customer = form.save(commit=False)
                customer.organization = self.get_organization()
                
                # Generate customer ID if not provided
                if not customer.customer_id:
                    if customer.email:
                        customer.customer_id = f"cust_{uuid.uuid4().hex[:8]}"
                    else:
                        customer.customer_id = f"anon_{uuid.uuid4().hex[:12]}"
                
                customer.save()
                form.save_m2m()
                
                messages.success(
                    self.request,
                    _('Customer was created successfully!')
                )
                
                logger.info(f'Customer created: {customer.customer_id} in {customer.organization.name}')
                
                return redirect(self.get_success_url())
                
        except Exception as e:
            logger.error(f'Error creating customer: {str(e)}', exc_info=True)
            messages.error(
                self.request,
                _('An error occurred while creating the customer. Please try again.')
            )
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('customer-list', kwargs={
            'organization_id': self.get_organization().id
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Add Customer')
        context['submit_text'] = _('Create Customer')
        return context

class CustomerListView(ListView):
    """
    List all customers for an organization with filtering and search
    """
    model = Customer
    template_name = 'customers/customer-list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_organization_id(self):
        """Get the organization ID from URL parameters"""
        organization_id = self.kwargs.get('organization_id')
        if not organization_id:
            # Try alternative parameter name
            organization_id = self.kwargs.get('organization_pk')
        return organization_id

    def get_organization(self):
        """Get the organization from URL parameters"""
        organization_id = self.get_organization_id()
        if organization_id:
            return get_object_or_404(Organization, id=organization_id)
        return None

    def get_queryset(self):
        """Get filtered queryset for the organization"""
        organization_id = self.get_organization_id()
        
        if not organization_id:
            return Customer.objects.none()
        
        # CORRECTED: Use double underscore notation to filter by organization ID
        queryset = Customer.objects.filter(organization__id=organization_id).select_related('user')
        
        # Apply filters
        self.filter_form = CustomerFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            segment = self.filter_form.cleaned_data.get('segment')
            search = self.filter_form.cleaned_data.get('search')
            sort_by = self.filter_form.cleaned_data.get('sort_by') or '-created_at'
            customer_type = self.filter_form.cleaned_data.get('customer_type')
            
            if segment:
                queryset = queryset.filter(segment=segment)
            
            if customer_type:
                queryset = queryset.filter(customer_type=customer_type)
            
            if search:
                queryset = queryset.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(customer_id__icontains=search) |
                    Q(phone__icontains=search)
                )
            
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.get_organization_id()
        
        if not organization_id:
            messages.error(self.request, _('Organization not found.'))
            return context
        
        # Get organization instance for context
        organization = self.get_organization()
        
        context['filter_form'] = getattr(self, 'filter_form', CustomerFilterForm())
        context['page_title'] = _('Customers')
        context['organization'] = organization
        context['total_customers'] = self.get_queryset().count()
        
        # CORRECTED: Use double underscore notation for statistics
        if organization_id:
            context['segment_stats'] = Customer.objects.filter(
                organization__id=organization_id
            ).values('segment').annotate(
                count=Count('id'),
                total_value=Sum('lifetime_value')
            ).order_by('segment')
        else:
            context['segment_stats'] = []
        
        # CORRECTED: Use double underscore notation for customer type stats
        if organization_id:
            context['customer_type_stats'] = Customer.objects.filter(
                organization__id=organization_id
            ).values('customer_type').annotate(
                count=Count('id')
            ).order_by('customer_type')
        else:
            context['customer_type_stats'] = []
        
        return context
    
class CustomerListView1(ListView):
    """
    List all customers for an organization with filtering and search
    """
    model = Customer
    template_name = 'customers/customer-list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_organization_id(self):
        """Get the organization ID from URL parameters"""
        organization_id = self.kwargs.get('organization_id')
        if not organization_id:
            # Try alternative parameter name
            organization_id = self.kwargs.get('organization_pk')
        return organization_id

    def get_organization(self):
        """Get the organization from URL parameters"""
        organization_id = self.get_organization_id()
        if organization_id:
            return get_object_or_404(Organization, id=organization_id)
        return None

    def get_queryset(self):
        """Get filtered queryset for the organization"""
        organization_id = self.get_organization_id()
        
        if not organization_id:
            return Customer.objects.none()
        
        # Filter by organization using the organization_id
        queryset = Customer.objects.filter(organization_id=organization_id).select_related('user')
        
        # Apply filters
        self.filter_form = CustomerFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            segment = self.filter_form.cleaned_data.get('segment')
            search = self.filter_form.cleaned_data.get('search')
            sort_by = self.filter_form.cleaned_data.get('sort_by') or '-created_at'
            customer_type = self.filter_form.cleaned_data.get('customer_type')
            
            if segment:
                queryset = queryset.filter(segment=segment)
            
            if customer_type:
                queryset = queryset.filter(customer_type=customer_type)
            
            if search:
                queryset = queryset.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(customer_id__icontains=search) |
                    Q(phone__icontains=search)
                )
            
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.get_organization_id()
        
        if not organization_id:
            messages.error(self.request, _('Organization not found.'))
            return context
        
        # Get organization instance for context
        organization = self.get_organization()
        
        context['filter_form'] = getattr(self, 'filter_form', CustomerFilterForm())
        context['page_title'] = _('Customers')
        context['organization'] = organization
        context['total_customers'] = self.get_queryset().count()
        
        # Get segment statistics using organization_id
        if organization_id:
            context['segment_stats'] = Customer.objects.filter(
                organization_id=organization_id
            ).values('segment').annotate(
                count=Count('id'),
                total_value=Sum('lifetime_value')
            ).order_by('segment')
        else:
            context['segment_stats'] = []
        
        # Get customer type distribution
        if organization_id:
            context['customer_type_stats'] = Customer.objects.filter(
                organization_id=organization_id
            ).values('customer_type').annotate(
                count=Count('id')
            ).order_by('customer_type')
        else:
            context['customer_type_stats'] = []
        
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        if not organization:
            messages.error(self.request, _('Organization not found.'))
            return context
        
        context['filter_form'] = getattr(self, 'filter_form', CustomerFilterForm())
        context['page_title'] = _('Customers')
        context['organization'] = organization
        context['total_customers'] = self.get_queryset().count()
        
        # Get segment statistics
        if organization:
            context['segment_stats'] = Customer.objects.filter(
                organization=organization  # Use ForeignKey, not organization_id
            ).values('segment').annotate(
                count=Count('id'),
                total_value=Sum('lifetime_value')
            ).order_by('segment')
        else:
            context['segment_stats'] = []
        
        # Get customer type distribution
        if organization:
            context['customer_type_stats'] = Customer.objects.filter(
                organization=organization
            ).values('customer_type').annotate(
                count=Count('id')
            ).order_by('customer_type')
        else:
            context['customer_type_stats'] = []
        
        return context
     
class CustomerListView1(CustomerMixin, ListView):
    """
    List all customers for an organization with filtering and search
    """
    model = Customer
    template_name = 'customers/customer-list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_queryset(self):
        # ✅ ALTERNATIVE 4: Filter by organization_id
        organization_id = self.get_organization_id()
        queryset = Customer.objects.filter(organization_id=organization_id).select_related('user')
        
        # Apply filters
        self.filter_form = CustomerFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            segment = self.filter_form.cleaned_data.get('segment')
            search = self.filter_form.cleaned_data.get('search')
            sort_by = self.filter_form.cleaned_data.get('sort_by') or '-created_at'
            
            if segment:
                queryset = queryset.filter(segment=segment)
            
            if search:
                queryset = queryset.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(customer_id__icontains=search)
                )
            
            queryset = queryset.order_by(sort_by)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        context['page_title'] = _('Customers')
        context['total_customers'] = self.get_queryset().count()
        
        organization_id = self.get_organization_id()
        context['segment_stats'] = Customer.objects.filter(
            organization_id=organization_id
        ).values('segment').annotate(
            count=Count('id'),
            total_value=Sum('lifetime_value')
        )
        
        return context




class CustomerUpdateView(OrganizationMixin, UpdateView):
    """
    Update an existing customer
    
    Benefits:
    - Organization is automatically injected via mixin
    - Organization is automatically set via mixin
    - Queryset is secured to only org's customers
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer-form.html'

    def get_queryset(self):
        
        organization_id = self.get_organization_id()
        return Customer.objects.filter(organization_id=organization_id)

    def form_valid(self, form):
        """
        Override to add messaging and logging
        Organization is already set by OrganizationFormMixin
        """
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                
                messages.success(
                    self.request,
                    _('Customer "%(name)s" was updated successfully!') % {
                        'name': self.object.get_full_name()
                    }
                )
                
                logger.info(
                    f'Customer updated: {self.object.email} by {self.request.user.email}'
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error updating customer: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while updating the customer. Please try again.')
            )
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('accounts:customer-list', kwargs={
            'organization_pk': self.get_organization_id()
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Edit Customer')
        context['submit_text'] = _('Update Customer')
        context['editing'] = True
        return context


class CustomerDetailView(CustomerMixin, DetailView):
    """
    View customer details
    """
    model = Customer
    template_name = 'customers/customer-detail.html'
    context_object_name = 'customer'

    def get_queryset(self):
        organization_id = self.get_organization_id()
        return Customer.objects.filter(organization_id=organization_id).select_related('user')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.get_full_name()
        return context


class CustomerDeleteView(OrganizationMixin, DeleteView):
    """
    Delete a customer
    
    Uses OrganizationFormMixin for consistent organization handling
    """
    model = Customer
    template_name = 'customers/customer-confirm-delete.html'

    def get_queryset(self):
        organization_id = self.get_organization_id()
        return Customer.objects.filter(organization_id=organization_id)

    def form_valid(self, request, *args, **kwargs):
        customer = self.get_object()
        customer_name = customer.get_full_name()
        
        try:
            with transaction.atomic():
                response = super().form_valid(request, *args, **kwargs)
                
                messages.success(
                    self.request,
                    _('Customer "%(name)s" was deleted successfully.') % {
                        'name': customer_name
                    }
                )
                
                logger.info(
                    f'Customer deleted: {customer_name} by {self.request.user.email}'
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error deleting customer: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while deleting the customer. Please try again.')
            )
            return redirect('accounts:customer-list', organization_pk=self.get_organization_id())

    def get_success_url(self):
        return reverse_lazy('accounts:customer-list', kwargs={
            'organization_pk': self.get_organization_id()
        })

