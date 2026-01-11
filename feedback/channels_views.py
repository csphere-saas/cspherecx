# views.py
import logging
import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from core.models import *
from .forms import *

logger = logging.getLogger(__name__)

class ChannelMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin for channel views to handle organization permissions
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
            _('You do not have permission to manage channels for this organization.')
        )
        return redirect('accounts:org-detail', pk=self.get_organization().pk)

class ChannelListView(ChannelMixin, ListView):
    """
    List all channels for an organization with filtering
    """
    model = Channel
    template_name = 'channels/channel-list.html'
    context_object_name = 'channels'
    paginate_by = 20

    def get_queryset(self):
        organization = self.get_organization()
        queryset = Channel.objects.filter(organization=organization)
        
        # Apply filters
        self.filter_form = ChannelFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            channel_type = self.filter_form.cleaned_data.get('channel_type')
            status = self.filter_form.cleaned_data.get('status')
            search = self.filter_form.cleaned_data.get('search')
            
            if channel_type:
                queryset = queryset.filter(channel_type=channel_type)
            
            if status == 'enabled':
                queryset = queryset.filter(is_enabled=True)
            elif status == 'disabled':
                queryset = queryset.filter(is_enabled=False)
            
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search)
                )
        
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        context['page_title'] = _('Feedback Channels')
        context['total_channels'] = self.get_queryset().count()
        context['enabled_channels'] = self.get_queryset().filter(is_enabled=True).count()
        
        # Add channel type statistics
        organization = self.get_organization()
        context['type_stats'] = Channel.objects.filter(
            organization=organization
        ).values('channel_type').annotate(
            count=Count('id'),
            enabled_count=Count('id', filter=Q(is_enabled=True))
        )
        
        return context

class ChannelCreateView(ChannelMixin, CreateView):
    """
    Create a new feedback channel
    """
    model = Channel
    form_class = ChannelForm
    template_name = 'channels/channel-form.html'

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
                    _('Channel "%(name)s" was created successfully!') % {
                        'name': self.object.name
                    }
                )
                
                logger.info(
                    f'Channel created: {self.object.name} ({self.object.channel_type}) '
                    f'by {self.request.user.email} in {self.object.organization.name}'
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error creating channel: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while creating the channel. Please try again.')
            )
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('feedback:channel-list', kwargs={
            'organization_pk': self.get_organization().pk
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Add Channel')
        context['submit_text'] = _('Create Channel')
        return context

class ChannelUpdateView(ChannelMixin, UpdateView):
    """
    Update an existing feedback channel
    """
    model = Channel
    form_class = ChannelForm
    template_name = 'channels/channel-form.html'

    def get_queryset(self):
        organization = self.get_organization()
        return Channel.objects.filter(organization=organization)

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
                    _('Channel "%(name)s" was updated successfully!') % {
                        'name': self.object.name
                    }
                )
                
                logger.info(
                    f'Channel updated: {self.object.name} by {self.request.user.email}'
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error updating channel: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while updating the channel. Please try again.')
            )
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('feedback:channel-list', kwargs={
            'organization_pk': self.get_organization().pk
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Edit Channel')
        context['submit_text'] = _('Update Channel')
        context['editing'] = True
        return context

class ChannelDetailView(ChannelMixin, DetailView):
    """
    View channel details
    """
    model = Channel
    template_name = 'channels/channel-detail.html'
    context_object_name = 'channel'

    def get_queryset(self):
        organization = self.get_organization()
        return Channel.objects.filter(organization=organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        
        # Format configuration for display
        if self.object.configuration:
            context['configuration_formatted'] = json.dumps(
                self.object.configuration, indent=2, ensure_ascii=False
            )
        
        return context

class ChannelDeleteView(ChannelMixin, DeleteView):
    """
    Delete a channel
    """
    model = Channel
    template_name = 'channels/channel-confirm-delete.html'

    def get_queryset(self):
        organization = self.get_organization()
        return Channel.objects.filter(organization=organization)

    def form_valid(self, request, *args, **kwargs):
        channel = self.get_object()
        channel_name = channel.name
        
        try:
            with transaction.atomic():
                response = super().form_valid(request, *args, **kwargs)
                
                messages.success(
                    self.request,
                    _('Channel "%(name)s" was deleted successfully.') % {
                        'name': channel_name
                    }
                )
                
                logger.info(
                    f'Channel deleted: {channel_name} by {self.request.user.email}'
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error deleting channel: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while deleting the channel. Please try again.')
            )
            return redirect('feedback:channels-list', organization_pk=self.get_organization().pk)

    def get_success_url(self):
        return reverse_lazy('feedback:channel-list', kwargs={
            'organization_pk': self.get_organization().pk
        })

class ChannelToggleView(ChannelMixin, UpdateView):
    """
    Toggle channel enabled/disabled status
    """
    model = Channel
    fields = ['is_enabled']
    http_method_names = ['post']

    def get_queryset(self):
        organization = self.get_organization()
        return Channel.objects.filter(organization=organization)

    def form_valid(self, form):
        channel = self.get_object()
        new_status = not channel.is_enabled
        form.instance.is_enabled = new_status
        
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                
                status_text = _('enabled') if new_status else _('disabled')
                messages.success(
                    self.request,
                    _('Channel "%(name)s" has been %(status)s.') % {
                        'name': channel.name,
                        'status': status_text
                    }
                )
                
                logger.info(
                    f'Channel {status_text}: {channel.name} by {self.request.user.email}'
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error toggling channel status: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while updating the channel status.')
            )
        
        return redirect('feedback:channel-list', organization_pk=self.get_organization().pk)

    def get_success_url(self):
        return reverse_lazy('feedback:channel-list', kwargs={
            'organization_pk': self.get_organization().pk
        })