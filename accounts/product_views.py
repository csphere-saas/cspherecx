from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import Http404

from core.models import Product, Organization
from .forms import ProductForm

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


class ProductListView(LoginRequiredMixin, OrganizationMixin, ListView):
    model = Product
    template_name = 'products/product-list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        organization = self.get_organization()
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(category__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Filter by category
        category = self.request.GET.get('category', '')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by service type
        is_service = self.request.GET.get('is_service', '')
        if is_service in ['true', 'false']:
            queryset = queryset.filter(is_service=(is_service == 'true'))
        
        return queryset.select_related('organization').order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        context.update({
            'categories': Product.objects.filter(
                organization=organization
            ).exclude(category='').values_list('category', flat=True).distinct(),
            'search_query': self.request.GET.get('search', ''),
            'selected_category': self.request.GET.get('category', ''),
            'selected_service': self.request.GET.get('is_service', ''),
            'total_products': self.get_queryset().count(),
        })
        return context


class ProductCreateView(LoginRequiredMixin, SuccessMessageMixin, OrganizationMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product-form.html'
    success_message = _('Product "%(name)s" was created successfully!')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.get_organization()
        return kwargs
    
    def form_valid(self, form):
        form.instance.organization = self.get_organization()
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('accounts:product-list', kwargs={'organization_pk': self.get_organization().pk})


class ProductUpdateView(LoginRequiredMixin, SuccessMessageMixin, OrganizationMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product-form.html'
    success_message = _('Product "%(name)s" was updated successfully!')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.get_organization()
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('accounts:product-list', kwargs={'organization_pk': self.get_organization().pk})


class ProductDetailView(LoginRequiredMixin, OrganizationMixin, DetailView):
    model = Product
    template_name = 'products/product-detail.html'
    context_object_name = 'product'


class ProductDeleteView(LoginRequiredMixin, SuccessMessageMixin, OrganizationMixin, DeleteView):
    model = Product
    template_name = 'products/product-confirm-delete.html'
    success_message = _('Product was deleted successfully!')
    
    def get_success_url(self):
        return reverse_lazy('accounts:product-list', kwargs={'organization_pk': self.get_organization().pk})