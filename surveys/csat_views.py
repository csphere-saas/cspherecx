from django.views.generic import ListView, DetailView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from django.db import models
from django.utils.translation import gettext_lazy as _
import json
from datetime import timedelta
from core.models import *
from django.contrib import messages
from django.urls import reverse_lazy


from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg
import uuid

class CSATResponseListView(LoginRequiredMixin, ListView):
    """List view for CSAT responses with filtering and search"""
    model = CSATResponse
    template_name = 'csat_responses/csat-response-list.html'
    context_object_name = 'csat_responses'
    paginate_by = 25
    
    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        # Convert to string if it's a UUID object
        if isinstance(organization_id, uuid.UUID):
            organization_id = str(organization_id)
        
        queryset = CSATResponse.objects.filter(
            organization_id=organization_id
        ).select_related(
            'customer', 'product', 'survey_response'
        ).order_by('-created_at')
        
        # Apply filters
        satisfaction_level = self.request.GET.get('satisfaction_level')
        if satisfaction_level:
            queryset = queryset.filter(satisfaction_level=satisfaction_level)
        
        interaction_type = self.request.GET.get('interaction_type')
        if interaction_type:
            queryset = queryset.filter(interaction_type=interaction_type)
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(customer__email__icontains=search_query) |
                Q(feedback_comment__icontains=search_query) |
                Q(question_text__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.kwargs.get('organization_id')
        
        # Get organization object
        from core.models import Organization  # Import here or at top of file
        context['organization'] = get_object_or_404(Organization, id=organization_id)
        
        context['filter_params'] = self.request.GET.dict()
        
        # Add summary statistics
        queryset = self.get_queryset()
        context['total_responses'] = queryset.count()
        
        # Calculate average score safely
        avg_result = queryset.aggregate(avg_score=Avg('normalized_score'))
        context['avg_score'] = avg_result['avg_score'] or 0
        
        context['positive_count'] = queryset.filter(
            satisfaction_level__in=['satisfied', 'very_satisfied']
        ).count()
        
        return context
    

class CSATResponseDetailView(LoginRequiredMixin, DetailView):
    model = CSATResponse
    template_name = 'csat_responses/csat-response-detail.html'
    context_object_name = 'csat_response'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.kwargs.get('organization_id')
        
        # Convert to string if it's a UUID object
        if isinstance(organization_id, uuid.UUID):
            organization_id = str(organization_id)
        
        # Get the organization object
        from core.models import Organization
        context['organization'] = get_object_or_404(Organization, id=organization_id)
        return context
    
    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        # Convert to string if it's a UUID object
        if isinstance(organization_id, uuid.UUID):
            organization_id = str(organization_id)
        return CSATResponse.objects.filter(organization_id=organization_id)

class CSATResponseDeleteView(LoginRequiredMixin, DeleteView):
    model = CSATResponse
    template_name = 'csat_responses/csat-response-confirm-delete.html'
    context_object_name = 'csat_response'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.kwargs.get('organization_id')
        
        # Convert to string if it's a UUID object
        if isinstance(organization_id, uuid.UUID):
            organization_id = str(organization_id)
        
        # Get the organization object
        from core.models import Organization
        context['organization'] = get_object_or_404(Organization, id=organization_id)
        return context
    
    def get_success_url(self):
        organization_id = self.kwargs.get('organization_id')
        return reverse_lazy('surveys:csat-response-list', kwargs={'organization_id': organization_id})
    
    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        # Convert to string if it's a UUID object
        if isinstance(organization_id, uuid.UUID):
            organization_id = str(organization_id)
        return CSATResponse.objects.filter(organization_id=organization_id)


class CSATDashboardView(LoginRequiredMixin, TemplateView):
    """Comprehensive dashboard view with charts and metrics"""
    template_name = 'csat_responses/csat-dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.kwargs.get('organization_id')
        organization = Organization.objects.get(id=organization_id)
        context['organization'] = organization
        
        # Get date range filter
        days_filter = int(self.request.GET.get('days', 30))
        date_from = timezone.now() - timedelta(days=days_filter)
        
        # Base queryset
        queryset = CSATResponse.objects.filter(
            organization_id=organization_id,
            created_at__gte=date_from
        )
        
        # Overall Metrics
        context['total_responses'] = queryset.count()
        context['avg_score'] = queryset.aggregate(
            avg_score=Avg('normalized_score')
        )['avg_score'] or 0
        
        # Score Distribution
        score_distribution = list(queryset.values('score').annotate(
            count=Count('id')
        ).order_by('score'))
        context['score_distribution'] = json.dumps(score_distribution)
        
        # Satisfaction Level Distribution
        satisfaction_distribution = list(queryset.values('satisfaction_level').annotate(
            count=Count('id')
        ))
        context['satisfaction_distribution'] = json.dumps(satisfaction_distribution)
        
        # Daily Trends
        daily_trends = list(queryset.extra(
            select={'day': "DATE(created_at)"}
        ).values('day').annotate(
            avg_score=Avg('normalized_score'),
            count=Count('id')
        ).order_by('day')[:30])
        context['daily_trends'] = json.dumps(daily_trends)
        
        # Interaction Type Analysis
        interaction_analysis = list(queryset.values('interaction_type').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score')
        ).exclude(interaction_type=''))
        context['interaction_analysis'] = json.dumps(interaction_analysis)
        
        # Sentiment Analysis (if available)
        sentiment_data = list(queryset.filter(
            ai_analyzed=True
        ).values('sentiment_score').annotate(
            count=Count('id')
        ).order_by('sentiment_score'))
        context['sentiment_data'] = json.dumps(sentiment_data)
        
        # Product Performance (if applicable)
        product_performance = list(queryset.filter(
            product__isnull=False
        ).values('product__name').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('-avg_score')[:10])
        context['product_performance'] = json.dumps(product_performance)
        
        # Customer Segmentation
        top_customers = list(queryset.values(
            'customer__email'
        ).annotate(
            response_count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('-response_count')[:5])
        context['top_customers'] = top_customers
        
        # Time-based Metrics
        context['today_count'] = queryset.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        context['yesterday_count'] = queryset.filter(
            created_at__date=timezone.now().date() - timedelta(days=1)
        ).count()
        
        context['weekly_avg'] = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).aggregate(Avg('normalized_score'))['normalized_score__avg'] or 0
        
        # Calculate NPS-like score
        promoter_count = queryset.filter(
            satisfaction_level='very_satisfied'
        ).count()
        detractor_count = queryset.filter(
            satisfaction_level__in=['very_dissatisfied', 'dissatisfied']
        ).count()
        total_count = context['total_responses'] or 1
        
        context['nps_score'] = ((promoter_count - detractor_count) / total_count) * 100
        
        # Response Rate (if you have survey invitation data)
        # This is a placeholder - you'd need to implement based on your data
        context['response_rate'] = 0
        
        # Top Themes from AI Analysis
        if queryset.filter(ai_analyzed=True).exists():
            # Extract common themes from metadata
            themes = {}
            for response in queryset.filter(ai_analyzed=True).only('metadata'):
                if 'themes' in response.metadata:
                    for theme in response.metadata['themes']:
                        themes[theme] = themes.get(theme, 0) + 1
            
            context['common_themes'] = sorted(
                themes.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        
        # Add filter options
        context['days_filter'] = days_filter
        context['available_days'] = [7, 30, 90, 180, 365]
        
        return context