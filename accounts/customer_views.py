# views.py
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from core.models import *
from .forms import CustomerForm, CustomerFilterForm

logger = logging.getLogger(__name__)

class CustomerMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin for customer views to handle organization permissions
    """
    def get_organization(self):
        organization_pk = self.kwargs.get('organization_pk')
        return get_object_or_404(Organization, pk=organization_pk)

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

class CustomerListView(CustomerMixin, ListView):
    """
    List all customers for an organization with filtering and search
    """
    model = Customer
    template_name = 'customers/customer-list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_queryset(self):
        organization = self.get_organization()
        queryset = Customer.objects.filter(organization=organization).select_related('user')
        
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
        
        # Add stats
        organization = self.get_organization()
        context['segment_stats'] = Customer.objects.filter(
            organization=organization
        ).values('segment').annotate(
            count=Count('id'),
            total_value=Sum('lifetime_value')
        )
        
        return context
import uuid
import logging
from django.http import Http404
from django.db import transaction

logger = logging.getLogger(__name__)

class CustomerCreateView(CustomerMixin, CreateView):
    """
    Create a new customer
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer-form.html'

    def get_organization(self):
        """
        Get organization from URL parameter
        """
        # Try organization_id first (from URL pattern)
        organization_id = self.kwargs.get('organization_id')
        
        # If not found, try organization_pk (for compatibility)
        if not organization_id:
            organization_id = self.kwargs.get('organization_pk')
        
        if organization_id:
            return get_object_or_404(Organization, id=organization_id)
        
        # If no organization found, raise 404
        raise Http404(_("Organization not found"))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.get_organization()
        return kwargs

    def form_valid(self, form):
        try:
            # Get organization
            organization = self.get_organization()
            
            # Set organization on customer instance
            customer = form.save(commit=False)
            customer.organization = organization
            
            # Generate customer ID if not provided
            if not customer.customer_id:
                if customer.email:
                    # Use email prefix plus random string
                    email_prefix = customer.email.split('@')[0]
                    random_part = uuid.uuid4().hex[:8]
                    customer.customer_id = f"cust_{email_prefix}_{random_part}"
                else:
                    customer.customer_id = f"anon_{uuid.uuid4().hex[:12]}"
            
            # Save the customer
            customer.save()
            
            # Check if there are any many-to-many fields to save
            if form.cleaned_data.get('tags'):
                customer.tags.set(form.cleaned_data['tags'])
            
            messages.success(
                self.request,
                _('Customer "%(name)s" was created successfully!') % {
                    'name': customer.get_full_name()
                }
            )
            
            logger.info(
                f'Customer created: {customer.customer_id} by {self.request.user.email}'
            )
            
            return redirect(self.get_success_url())
                
        except Exception as e:
            logger.error(f'Error creating customer: {str(e)}', exc_info=True)
            messages.error(
                self.request,
                _('An error occurred while creating the customer. Please try again.')
            )
            # Return the form with errors
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.error(
            self.request,
            _('Please correct the errors below.')
        )
        return super().form_invalid(form)

    def get_success_url(self):
        organization = self.get_organization()
        # Check if the URL pattern expects organization_id or organization_pk
        return reverse_lazy('accounts:customer-list', kwargs={
            'organization_id': organization.pk  # Use organization_id to match URL pattern
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        context.update({
            'organization': organization,
            'page_title': _('Add Customer'),
            'submit_text': _('Create Customer'),
            'cancel_url': reverse_lazy('accounts:customer-list', kwargs={
                'organization_id': organization.pk
            })
        })
        return context
    

class CustomerUpdateView(CustomerMixin, UpdateView):
    """
    Update an existing customer
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer-form.html'

    def get_queryset(self):
        organization = self.get_organization()
        return Customer.objects.filter(organization=organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.get_organization()
        return kwargs

    def form_valid(self, form):
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
            'organization_pk': self.get_organization().pk
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
        organization = self.get_organization()
        return Customer.objects.filter(organization=organization).select_related('user')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.get_full_name()
        return context

class CustomerDeleteView(CustomerMixin, DeleteView):
    """
    Delete a customer
    """
    model = Customer
    template_name = 'customers/customer-confirm-delete.html'

    def get_queryset(self):
        organization = self.get_organization()
        return Customer.objects.filter(organization=organization)

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
            return redirect('accounts:customer-list', organization_pk=self.get_organization().pk)

    def get_success_url(self):
        return reverse_lazy('accounts:customer-list', kwargs={
            'organization_pk': self.get_organization().pk
        })