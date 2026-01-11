from django.views.generic import ListView, DetailView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.db import models
import json
import uuid
from datetime import timedelta
from core.models import *
    

class OrganizationContextMixin:
    """Mixin to add organization to context for views using organization_id"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.kwargs.get('organization_id')
        
        # Convert to string if it's a UUID object
        if isinstance(organization_id, uuid.UUID):
            organization_id = str(organization_id)
        
        context['organization'] = get_object_or_404(Organization, id=organization_id)
        return context


class CESResponseListView(OrganizationContextMixin, LoginRequiredMixin, ListView):
    """List view for CES responses with filtering and search"""
    model = CESResponse
    template_name = 'ces_responses/ces-response-list.html'
    context_object_name = 'ces_responses'
    paginate_by = 25
    
    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        if isinstance(organization_id, uuid.UUID):
            organization_id = str(organization_id)
        
        queryset = CESResponse.objects.filter(
            organization_id=organization_id
        ).select_related(
            'customer', 'survey_response'
        ).order_by('-created_at')
        
        # Apply filters
        effort_level = self.request.GET.get('effort_level')
        if effort_level:
            queryset = queryset.filter(effort_level=effort_level)
        
        effort_area = self.request.GET.get('effort_area')
        if effort_area:
            queryset = queryset.filter(effort_area=effort_area)
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        score_min = self.request.GET.get('score_min')
        if score_min:
            queryset = queryset.filter(score__gte=score_min)
        
        score_max = self.request.GET.get('score_max')
        if score_max:
            queryset = queryset.filter(score__lte=score_max)
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(customer__email__icontains=search_query) |
                Q(feedback_comment__icontains=search_query) |
                Q(question_text__icontains=search_query) |
                Q(task_description__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_params'] = self.request.GET.dict()
        
        # Add summary statistics
        queryset = self.get_queryset()
        context['total_responses'] = queryset.count()
        
        # Calculate average score (higher is better - less effort)
        avg_result = queryset.aggregate(avg_score=Avg('normalized_score'))
        context['avg_score'] = avg_result['avg_score'] or 0
        
        # Count high/low effort responses
        context['low_effort_count'] = queryset.filter(
            effort_level__in=['very_easy', 'easy', 'somewhat_easy']
        ).count()
        
        context['high_effort_count'] = queryset.filter(
            effort_level__in=['very_difficult', 'difficult', 'somewhat_difficult']
        ).count()
        
        # Calculate Effort Score (CES metric)
        total = context['total_responses'] or 1
        context['effort_score'] = (context['low_effort_count'] / total) * 100
        
        return context


class CESResponseDetailView(OrganizationContextMixin, LoginRequiredMixin, DetailView):
    """Detail view for individual CES response"""
    model = CESResponse
    template_name = 'ces_responses/ces-response-detail.html'
    context_object_name = 'ces_response'
    
    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        if isinstance(organization_id, uuid.UUID):
            organization_id = str(organization_id)
        return CESResponse.objects.filter(organization_id=organization_id)


class CESResponseDeleteView(OrganizationContextMixin, LoginRequiredMixin, DeleteView):
    """Delete view for CES response"""
    model = CESResponse
    template_name = 'ces_responses/ces-response-confirm-delete.html'
    context_object_name = 'ces_response'
    
    def get_success_url(self):
        organization_id = self.kwargs.get('organization_id')
        return reverse_lazy('surveys:ces-response-list', kwargs={'organization_id': organization_id})
    
    def get_queryset(self):
        organization_id = self.kwargs.get('organization_id')
        if isinstance(organization_id, uuid.UUID):
            organization_id = str(organization_id)
        return CESResponse.objects.filter(organization_id=organization_id)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('CES response deleted successfully.'))
        return super().delete(request, *args, **kwargs)

class CESDashboardView(OrganizationContextMixin, LoginRequiredMixin, TemplateView):
    """Comprehensive dashboard view with charts and metrics for CES"""
    template_name = 'ces_responses/ces-dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = context['organization']
        
        # Get date range filter
        days_filter = int(self.request.GET.get('days', 30))
        date_from = timezone.now() - timedelta(days=days_filter)
        
        # Base queryset
        queryset = CESResponse.objects.filter(
            organization=organization,
            created_at__gte=date_from
        )
        
        # Initialize default values
        total = queryset.count()
        
        # Overall Metrics
        context['total_responses'] = total
        context['avg_ces_score'] = queryset.aggregate(
            avg_score=Avg('normalized_score')
        )['avg_score'] or 0
        
        # Effort Level Distribution
        effort_distribution = list(queryset.values('effort_level').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('effort_level'))
        context['effort_distribution'] = json.dumps(effort_distribution)
        
        # Score Distribution
        score_distribution = list(queryset.values('score').annotate(
            count=Count('id')
        ).order_by('score'))
        context['score_distribution'] = json.dumps(score_distribution)
        
        # Daily Trends - FIXED: Use slicing after converting to list
        daily_trends_query = queryset.extra(
            select={'day': "DATE(created_at)"}
        ).values('day').annotate(
            avg_score=Avg('normalized_score'),
            count=Count('id')
        ).order_by('day')
        
        # Convert to list first, then slice
        daily_trends = list(daily_trends_query)
        # Take last 30 days if available
        daily_trends = daily_trends[-30:] if len(daily_trends) > 30 else daily_trends
        context['daily_trends'] = json.dumps(daily_trends)
        
        # Effort Area Analysis
        effort_area_analysis = list(queryset.values('effort_area').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score'),
            avg_raw_score=Avg('score')
        ).exclude(effort_area='').order_by('-avg_score'))
        context['effort_area_analysis'] = json.dumps(effort_area_analysis)
        
        # Friction Points Analysis (if AI analyzed)
        context['common_friction_points'] = []
        if queryset.filter(ai_analyzed=True).exists():
            friction_points = {}
            for response in queryset.filter(ai_analyzed=True):
                if response.friction_points:
                    for point in response.friction_points:
                        friction_points[point] = friction_points.get(point, 0) + 1
            
            context['common_friction_points'] = sorted(
                friction_points.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        
        # Customer Segmentation by Effort
        high_effort_customers = list(queryset.filter(
            effort_level__in=['very_difficult', 'difficult', 'somewhat_difficult']
        ).values('customer__email').annotate(
            response_count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('avg_score')[:5])
        context['high_effort_customers'] = high_effort_customers
        
        low_effort_customers = list(queryset.filter(
            effort_level__in=['very_easy', 'easy', 'somewhat_easy']
        ).values('customer__email').annotate(
            response_count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('-avg_score')[:5])
        context['low_effort_customers'] = low_effort_customers
        
        # Time-based Metrics
        context['today_count'] = queryset.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        context['week_count'] = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        context['month_count'] = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # CES Metric Calculation (Percentage of low-effort experiences)
        low_effort_count = queryset.filter(
            effort_level__in=['very_easy', 'easy', 'somewhat_easy']
        ).count()
        high_effort_count = queryset.filter(
            effort_level__in=['very_difficult', 'difficult', 'somewhat_difficult']
        ).count()
        
        total_for_calc = total or 1  # Avoid division by zero
        context['ces_metric'] = (low_effort_count / total_for_calc) * 100
        context['detractor_rate'] = (high_effort_count / total_for_calc) * 100
        
        # Response Frequency Analysis - FIXED
        if queryset.exists():
            # Method 1: Using Django's Extract function (database agnostic)
            try:
                from django.db.models.functions import ExtractHour
                response_frequency = list(
                    queryset.annotate(
                        hour=ExtractHour('created_at')
                    ).values('hour').annotate(
                        count=Count('id')
                    ).order_by('hour')
                )
            except:
                # Method 2: Fallback using database-specific SQL
                try:
                    response_frequency = list(queryset.extra(
                        select={'hour': 'strftime("%H", created_at)'}  # SQLite
                    ).values('hour').annotate(
                        count=Count('id')
                    ).order_by('hour'))
                except:
                    # Method 3: Another fallback for MySQL
                    try:
                        response_frequency = list(queryset.extra(
                            select={'hour': 'HOUR(created_at)'}  # MySQL
                        ).values('hour').annotate(
                            count=Count('id')
                        ).order_by('hour'))
                    except:
                        # Method 4: Fallback for PostgreSQL
                        try:
                            response_frequency = list(queryset.extra(
                                select={'hour': 'EXTRACT(HOUR FROM created_at)'}  # PostgreSQL
                            ).values('hour').annotate(
                                count=Count('id')
                            ).order_by('hour'))
                        except:
                            # If all else fails, return empty list
                            response_frequency = []
        else:
            response_frequency = []
        context['response_frequency'] = json.dumps(response_frequency)
        
        # Sentiment Analysis (if available)
        sentiment_data = []
        if queryset.filter(ai_analyzed=True).exists():
            sentiment_data = list(queryset.filter(
                ai_analyzed=True
            ).extra({
                'sentiment_bucket': "CASE \
                    WHEN sentiment_score < -0.5 THEN 'negative' \
                    WHEN sentiment_score < 0.5 THEN 'neutral' \
                    ELSE 'positive' \
            END"
            }).values('sentiment_bucket').annotate(
                count=Count('id')
            ))
        context['sentiment_data'] = json.dumps(sentiment_data)
        
        # Task Performance Analysis
        task_performance = list(queryset.exclude(
            task_description=''
        ).values('task_description').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('-avg_score')[:10])
        context['task_performance'] = json.dumps(task_performance)
        
        # Add filter options
        context['days_filter'] = days_filter
        context['available_days'] = [7, 30, 90, 180, 365]
        
        # Scale information - with fallback
        if queryset.exists():
            context['scale_max'] = queryset.first().scale_max
        else:
            context['scale_max'] = 7  # Default value
        
        # Add empty list defaults for missing context
        if 'common_friction_points' not in context:
            context['common_friction_points'] = []
        
        return context
    
class CESDashboardView1(OrganizationContextMixin, LoginRequiredMixin, TemplateView):
    """Comprehensive dashboard view with charts and metrics for CES"""
    template_name = 'ces_responses/ces-dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = context['organization']
        
        # Get date range filter
        days_filter = int(self.request.GET.get('days', 30))
        date_from = timezone.now() - timedelta(days=days_filter)
        
        # Base queryset
        queryset = CESResponse.objects.filter(
            organization=organization,
            created_at__gte=date_from
        )
        
        # Initialize default values
        total = queryset.count()
        
        # Overall Metrics
        context['total_responses'] = total
        context['avg_ces_score'] = queryset.aggregate(
            avg_score=Avg('normalized_score')
        )['avg_score'] or 0
        
        # Effort Level Distribution
        effort_distribution = list(queryset.values('effort_level').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('effort_level'))
        context['effort_distribution'] = json.dumps(effort_distribution)
        
        # Score Distribution
        score_distribution = list(queryset.values('score').annotate(
            count=Count('id')
        ).order_by('score'))
        context['score_distribution'] = json.dumps(score_distribution)
        
        # Daily Trends - FIXED: Use slicing after converting to list
        daily_trends_query = queryset.extra(
            select={'day': "DATE(created_at)"}
        ).values('day').annotate(
            avg_score=Avg('normalized_score'),
            count=Count('id')
        ).order_by('day')
        
        # Convert to list first, then slice
        daily_trends = list(daily_trends_query)
        # Take last 30 days if available
        daily_trends = daily_trends[-30:] if len(daily_trends) > 30 else daily_trends
        context['daily_trends'] = json.dumps(daily_trends)
        
        # Effort Area Analysis
        effort_area_analysis = list(queryset.values('effort_area').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score'),
            avg_raw_score=Avg('score')
        ).exclude(effort_area='').order_by('-avg_score'))
        context['effort_area_analysis'] = json.dumps(effort_area_analysis)
        
        # Friction Points Analysis (if AI analyzed)
        context['common_friction_points'] = []
        if queryset.filter(ai_analyzed=True).exists():
            friction_points = {}
            for response in queryset.filter(ai_analyzed=True):
                if response.friction_points:
                    for point in response.friction_points:
                        friction_points[point] = friction_points.get(point, 0) + 1
            
            context['common_friction_points'] = sorted(
                friction_points.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        
        # Customer Segmentation by Effort
        high_effort_customers = list(queryset.filter(
            effort_level__in=['very_difficult', 'difficult', 'somewhat_difficult']
        ).values('customer__email').annotate(
            response_count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('avg_score')[:5])
        context['high_effort_customers'] = high_effort_customers
        
        low_effort_customers = list(queryset.filter(
            effort_level__in=['very_easy', 'easy', 'somewhat_easy']
        ).values('customer__email').annotate(
            response_count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('-avg_score')[:5])
        context['low_effort_customers'] = low_effort_customers
        
        # Time-based Metrics
        context['today_count'] = queryset.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        context['week_count'] = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        context['month_count'] = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # CES Metric Calculation (Percentage of low-effort experiences)
        low_effort_count = queryset.filter(
            effort_level__in=['very_easy', 'easy', 'somewhat_easy']
        ).count()
        high_effort_count = queryset.filter(
            effort_level__in=['very_difficult', 'difficult', 'somewhat_difficult']
        ).count()
        
        total_for_calc = total or 1  # Avoid division by zero
        context['ces_metric'] = (low_effort_count / total_for_calc) * 100
        context['detractor_rate'] = (high_effort_count / total_for_calc) * 100
        
        # Response Frequency Analysis
        response_frequency = list(queryset.extra({
            'hour': "EXTRACT(HOUR FROM created_at)"
        }).values('hour').annotate(
            count=Count('id')
        ).order_by('hour'))
        context['response_frequency'] = json.dumps(response_frequency)
        
        # Sentiment Analysis (if available)
        sentiment_data = []
        if queryset.filter(ai_analyzed=True).exists():
            sentiment_data = list(queryset.filter(
                ai_analyzed=True
            ).extra({
                'sentiment_bucket': "CASE \
                    WHEN sentiment_score < -0.5 THEN 'negative' \
                    WHEN sentiment_score < 0.5 THEN 'neutral' \
                    ELSE 'positive' \
            END"
            }).values('sentiment_bucket').annotate(
                count=Count('id')
            ))
        context['sentiment_data'] = json.dumps(sentiment_data)
        
        # Task Performance Analysis
        task_performance = list(queryset.exclude(
            task_description=''
        ).values('task_description').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('-avg_score')[:10])
        context['task_performance'] = json.dumps(task_performance)
        
        # Add filter options
        context['days_filter'] = days_filter
        context['available_days'] = [7, 30, 90, 180, 365]
        
        # Scale information - with fallback
        if queryset.exists():
            context['scale_max'] = queryset.first().scale_max
        else:
            context['scale_max'] = 7  # Default value
        
        # Add empty list defaults for missing context
        if 'common_friction_points' not in context:
            context['common_friction_points'] = []
        
        return context
    
class CESDashboardView1(OrganizationContextMixin, LoginRequiredMixin, TemplateView):
    """Comprehensive dashboard view with charts and metrics for CES"""
    template_name = 'ces_responses/ces-dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = context['organization']
        
        # Get date range filter
        days_filter = int(self.request.GET.get('days', 30))
        date_from = timezone.now() - timedelta(days=days_filter)
        
        # Base queryset
        queryset = CESResponse.objects.filter(
            organization=organization,
            created_at__gte=date_from
        )
        
        # Overall Metrics
        context['total_responses'] = total = queryset.count()
        context['avg_ces_score'] = queryset.aggregate(
            avg_score=Avg('normalized_score')
        )['avg_score'] or 0
        
        # Effort Level Distribution
        effort_distribution = list(queryset.values('effort_level').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('effort_level'))
        context['effort_distribution'] = json.dumps(effort_distribution)
        
        # Score Distribution
        score_distribution = list(queryset.values('score').annotate(
            count=Count('id')
        ).order_by('score'))
        context['score_distribution'] = json.dumps(score_distribution)
        
        # Daily Trends
        daily_trends = list(queryset.extra(
            select={'day': "DATE(created_at)"}
        ).values('day').annotate(
            avg_score=Avg('normalized_score'),
            count=Count('id')
        ).order_by('day')[-30:])
        context['daily_trends'] = json.dumps(daily_trends)
        
        # Effort Area Analysis
        effort_area_analysis = list(queryset.values('effort_area').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score'),
            avg_raw_score=Avg('score')
        ).exclude(effort_area='').order_by('-avg_score'))
        context['effort_area_analysis'] = json.dumps(effort_area_analysis)
        
        # Friction Points Analysis (if AI analyzed)
        if queryset.filter(ai_analyzed=True).exists():
            friction_points = {}
            for response in queryset.filter(ai_analyzed=True):
                if response.friction_points:
                    for point in response.friction_points:
                        friction_points[point] = friction_points.get(point, 0) + 1
            
            context['common_friction_points'] = sorted(
                friction_points.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        
        # Customer Segmentation by Effort
        high_effort_customers = list(queryset.filter(
            effort_level__in=['very_difficult', 'difficult', 'somewhat_difficult']
        ).values('customer__email').annotate(
            response_count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('avg_score')[:5])
        context['high_effort_customers'] = high_effort_customers
        
        low_effort_customers = list(queryset.filter(
            effort_level__in=['very_easy', 'easy', 'somewhat_easy']
        ).values('customer__email').annotate(
            response_count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('-avg_score')[:5])
        context['low_effort_customers'] = low_effort_customers
        
        # Time-based Metrics
        context['today_count'] = queryset.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        context['week_count'] = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        context['month_count'] = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # CES Metric Calculation (Percentage of low-effort experiences)
        low_effort_count = queryset.filter(
            effort_level__in=['very_easy', 'easy', 'somewhat_easy']
        ).count()
        high_effort_count = queryset.filter(
            effort_level__in=['very_difficult', 'difficult', 'somewhat_difficult']
        ).count()
        
        total = total or 1  # Avoid division by zero
        context['ces_metric'] = (low_effort_count / total) * 100
        context['detractor_rate'] = (high_effort_count / total) * 100
        
        # Response Frequency Analysis
        response_frequency = list(queryset.extra({
            'hour': "EXTRACT(HOUR FROM created_at)"
        }).values('hour').annotate(
            count=Count('id')
        ).order_by('hour'))
        context['response_frequency'] = json.dumps(response_frequency)
        
        # Sentiment Analysis (if available)
        sentiment_data = list(queryset.filter(
            ai_analyzed=True
        ).extra({
            'sentiment_bucket': "CASE \
                WHEN sentiment_score < -0.5 THEN 'negative' \
                WHEN sentiment_score < 0.5 THEN 'neutral' \
                ELSE 'positive' \
            END"
        }).values('sentiment_bucket').annotate(
            count=Count('id')
        ))
        context['sentiment_data'] = json.dumps(sentiment_data)
        
        # Task Performance Analysis
        task_performance = list(queryset.exclude(
            task_description=''
        ).values('task_description').annotate(
            count=Count('id'),
            avg_score=Avg('normalized_score')
        ).order_by('-avg_score')[:10])
        context['task_performance'] = json.dumps(task_performance)
        
        # Add filter options
        context['days_filter'] = days_filter
        context['available_days'] = [7, 30, 90, 180, 365]
        
        # Scale information
        context['scale_max'] = queryset.first().scale_max if queryset.exists() else 7
        
        return context