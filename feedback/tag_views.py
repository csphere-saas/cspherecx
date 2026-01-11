# views.py
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from core.models import *
from .forms import TagForm, TagFilterForm

logger = logging.getLogger(__name__)

class TagMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin for tag views to handle organization permissions
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
        return user_membership and user_membership.can_manage_organization

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        return context

    def handle_no_permission(self):
        messages.error(
            self.request,
            _('You do not have permission to manage tags for this organization.')
        )
        return redirect('accounts:org-detail', pk=self.get_organization().pk)

class TagListView(TagMixin, ListView):
    """
    List all tags for an organization with filtering
    """
    model = Tag
    template_name = 'tags/tag-list.html'
    context_object_name = 'tags'
    paginate_by = 25

    def get_queryset(self):
        organization = self.get_organization()
        queryset = Tag.objects.filter(organization=organization)
        
        # Apply filters
        self.filter_form = TagFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            category = self.filter_form.cleaned_data.get('category')
            search = self.filter_form.cleaned_data.get('search')
            
            if category:
                queryset = queryset.filter(category=category)
            
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search) |
                    Q(slug__icontains=search)
                )
        
        return queryset.order_by('category', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        context['page_title'] = _('Tags')
        context['total_tags'] = self.get_queryset().count()
        
        # Add category statistics
        organization = self.get_organization()
        context['category_stats'] = Tag.objects.filter(
            organization=organization
        ).values('category').annotate(
            count=Count('id')
        ).order_by('category')
        
        return context

class TagCreateView(TagMixin, CreateView):
    """
    Create a new tag
    """
    model = Tag
    form_class = TagForm
    template_name = 'tags/tag-form.html'

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
                    _('Tag "%(name)s" was created successfully!') % {
                        'name': self.object.name
                    }
                )
                
                logger.info(
                    f'Tag created: {self.object.name} ({self.object.category}) '
                    f'by {self.request.user.email} in {self.object.organization.name}'
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error creating tag: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while creating the tag. Please try again.')
            )
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('feedback:tag-list', kwargs={
            'organization_pk': self.get_organization().pk
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Create Tag')
        context['submit_text'] = _('Create Tag')
        return context

class TagUpdateView(TagMixin, UpdateView):
    """
    Update an existing tag
    """
    model = Tag
    form_class = TagForm
    template_name = 'tags/tag-form.html'

    def get_queryset(self):
        organization = self.get_organization()
        return Tag.objects.filter(organization=organization)

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
                    _('Tag "%(name)s" was updated successfully!') % {
                        'name': self.object.name
                    }
                )
                
                logger.info(
                    f'Tag updated: {self.object.name} by {self.request.user.email}'
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error updating tag: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while updating the tag. Please try again.')
            )
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('feedback:tag-list', kwargs={
            'organization_pk': self.get_organization().pk
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Edit Tag')
        context['submit_text'] = _('Update Tag')
        context['editing'] = True
        return context

class TagDetailView(TagMixin, DetailView):
    """
    View tag details
    """
    model = Tag
    template_name = 'tags/tag-detail.html'
    context_object_name = 'tag'

    def get_queryset(self):
        organization = self.get_organization()
        return Tag.objects.filter(organization=organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        
        # Get usage statistics
        context['customer_count'] = self.object.customers.count()
        context['feedback_count'] = self.object.feedback_set.count() if hasattr(self.object, 'feedback_set') else 0
        
        return context

class TagDeleteView(TagMixin, DeleteView):
    """
    Delete a tag
    """
    model = Tag
    template_name = 'tags/tag-confirm-delete.html'

    def get_queryset(self):
        organization = self.get_organization()
        return Tag.objects.filter(organization=organization)

    def form_valid(self, request, *args, **kwargs):
        tag = self.get_object()
        tag_name = tag.name
        
        try:
            with transaction.atomic():
                response = super().form_valid(request, *args, **kwargs)
                
                messages.success(
                    self.request,
                    _('Tag "%(name)s" was deleted successfully.') % {
                        'name': tag_name
                    }
                )
                
                logger.info(
                    f'Tag deleted: {tag_name} by {self.request.user.email}'
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error deleting tag: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while deleting the tag. Please try again.')
            )
            return redirect('feedback:tag-list', organization_pk=self.get_organization().pk)

    def get_success_url(self):
        return reverse_lazy('feedback:tag-list', kwargs={
            'organization_pk': self.get_organization().pk
        })