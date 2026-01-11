from django.views.generic import ListView, DetailView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, FloatField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.core.paginator import Paginator
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
from django.urls import reverse_lazy, reverse
from core.models import NPSResponse, SurveyResponse, Customer, Organization, Survey

logger = logging.getLogger(__name__)


class NPSResponseListView(LoginRequiredMixin, ListView):
    """List all NPS responses with filtering and pagination"""
    model = NPSResponse
    template_name = 'nps_responses/nps-response-list.html'
    context_object_name = 'responses'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = NPSResponse.objects.select_related(
            'organization', 'customer', 'survey_response', 'product'
        ).order_by('-created_at')
        
        # FIRST, try to get organization_id from URL kwargs
        organization_id = self.kwargs.get('organization_id')
        
        # If not in URL kwargs, try from GET parameters
        if not organization_id:
            organization_id = self.request.GET.get('organization')
        
        # If we have an organization_id, filter by it
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
            # Store it in view for later use
            self.organization_id = organization_id
        
        # Filter by category
        category = self.request.GET.get('category')
        if category in ['detractor', 'passive', 'promoter']:
            queryset = queryset.filter(category=category)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        # Filter by score range
        min_score = self.request.GET.get('min_score')
        max_score = self.request.GET.get('max_score')
        if min_score:
            queryset = queryset.filter(score__gte=min_score)
        if max_score:
            queryset = queryset.filter(score__lte=max_score)
        
        # Search by customer email or reason
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(customer__email__icontains=search) |
                Q(reason__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter counts
        queryset = self.get_queryset()
        context['total_responses'] = queryset.count()
        context['promoter_count'] = queryset.filter(category='promoter').count()
        context['passive_count'] = queryset.filter(category='passive').count()
        context['detractor_count'] = queryset.filter(category='detractor').count()
        
        # Add filter options
        context['organizations'] = Organization.objects.all()
        context['categories'] = ['detractor', 'passive', 'promoter']
        
        # Add current filters for form preservation
        context['current_filters'] = {
            'organization': self.request.GET.get('organization', ''),
            'category': self.request.GET.get('category', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'min_score': self.request.GET.get('min_score', ''),
            'max_score': self.request.GET.get('max_score', ''),
            'search': self.request.GET.get('search', ''),
        }
        
        # CRITICAL: Add organization_id to context if available
        # Try multiple sources in order of priority
        organization_id = None
        
        # 1. First check if we stored it in get_queryset
        if hasattr(self, 'organization_id'):
            organization_id = self.organization_id
        # 2. Check URL kwargs
        elif 'organization_id' in self.kwargs:
            organization_id = self.kwargs['organization_id']
        # 3. Check GET parameters
        elif self.request.GET.get('organization'):
            organization_id = self.request.GET.get('organization')
        
        context['organization_id'] = organization_id
        
        return context
    
class NPSResponseDetailView(LoginRequiredMixin, DetailView):
    """View detailed information about a specific NPS response"""
    model = NPSResponse
    template_name = 'nps_responses/nps-response-detail.html'
    context_object_name = 'response'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add organization_id to context
        context['organization_id'] = self.kwargs.get('organization_id')
        
        # Get related survey response if available
        if self.object.survey_response:
            context['survey_response'] = self.object.survey_response
        
        # Get customer information
        if self.object.customer:
            context['customer'] = self.object.customer
            context['customer_responses'] = NPSResponse.objects.filter(
                customer=self.object.customer
            ).order_by('-created_at')[:10]
        
        # Get similar responses (same category, same organization)
        context['similar_responses'] = NPSResponse.objects.filter(
            organization=self.object.organization,
            category=self.object.category
        ).exclude(id=self.object.id).order_by('-created_at')[:5]
        
        # Get sentiment insights if available
        if self.object.ai_analyzed and self.object.sentiment_metadata:
            context['sentiment_insights'] = self.object.survey_response.get_sentiment_insights() \
                if self.object.survey_response else None
        
        # Parse JSON fields for display
        try:
            import json
            if self.object.follow_up_question_responses:
                context['follow_up_responses_parsed'] = json.dumps(
                    self.object.follow_up_question_responses, 
                    indent=2
                )
            if self.object.sentiment_metadata:
                context['sentiment_metadata_parsed'] = json.dumps(
                    self.object.sentiment_metadata,
                    indent=2
                )
        except:
            pass
        
        return context


class NPSResponseDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an NPS response"""
    model = NPSResponse
    template_name = 'nps_responses/nps-response-confirm-delete.html'
    
    def get_object(self, queryset=None):
        """Get the object and store organization_id from URL"""
        obj = super().get_object(queryset)
        self.organization_id = self.kwargs.get('organization_id')
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['back_url'] = self.request.META.get(
            'HTTP_REFERER', 
            reverse('surveys:nps-response-list', kwargs={'organization_id': self.kwargs.get('organization_id')})
        )
        context['organization_id'] = self.kwargs.get('organization_id')
        return context
    
    def get_success_url(self):
        """Return to the list view with organization_id"""
        return reverse('surveys:nps-response-list', kwargs={
            'organization_id': self.kwargs.get('organization_id')
        })

import json
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from datetime import timedelta


class NPSDashboardView(LoginRequiredMixin, TemplateView):
    """Comprehensive NPS Dashboard with charts and metrics"""
    template_name = 'nps_responses/nps-dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get organization_id from URL kwargs
        organization_id = self.kwargs.get('organization_id')
        
        # Get date range from request or default to last 30 days
        days_filter = int(self.request.GET.get('days', 30))
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_filter)
        
        # Base queryset filtered by organization
        organization = get_object_or_404(Organization, id=organization_id)
        queryset = NPSResponse.objects.filter(
            organization=organization,
            created_at__range=[start_date, end_date]
        )
        
        # Calculate NPS metrics
        total_responses = queryset.count()
        
        if total_responses > 0:
            promoters = queryset.filter(category='promoter').count()
            passives = queryset.filter(category='passive').count()
            detractors = queryset.filter(category='detractor').count()
            
            promoter_percent = (promoters / total_responses) * 100
            detractor_percent = (detractors / total_responses) * 100
            nps_score = promoter_percent - detractor_percent
            
            avg_score = queryset.aggregate(avg_score=Avg('score'))['avg_score']
        else:
            promoters = passives = detractors = 0
            promoter_percent = detractor_percent = nps_score = avg_score = 0
        
        # Get time series data
        time_series_data = self._get_time_series_data(queryset, days_filter)
        
        # Get category distribution
        category_data = self._get_category_data(queryset)
        
        # Get score distribution
        score_data = self._get_score_distribution(queryset)
        
        # Get sentiment analysis data
        sentiment_data = self._get_sentiment_data(queryset)
        
        # Get top themes
        themes_data = self._get_top_themes(queryset)
        
        # Get recent responses
        recent_responses = queryset.select_related('customer', 'product').order_by('-created_at')[:10]
        
        # Get product performance
        product_performance = queryset.filter(
            product__isnull=False
        ).values(
            'product__name'
        ).annotate(
            avg_score=Avg('score'),
            response_count=Count('id'),
            nps_score=(
                (Count('id', filter=Q(category='promoter')) * 100.0 / Count('id')) -
                (Count('id', filter=Q(category='detractor')) * 100.0 / Count('id'))
            )
        ).order_by('-avg_score')[:10]
        
        # Calculate trend data
        trend_30_days = self._get_trend_data(queryset, organization_id, 30)
        
        context.update({
            'organization': organization,
            'organization_id': organization_id,
            'days_filter': days_filter,
            'start_date': start_date,
            'end_date': end_date,
            'total_responses': total_responses,
            'promoter_count': promoters,
            'passive_count': passives,
            'detractor_count': detractors,
            'nps_score': round(nps_score, 1),
            'avg_score': round(avg_score, 1) if avg_score else 0,
            'promoter_percentage': round(promoter_percent, 1),
            'detractor_percentage': round(detractor_percent, 1),
            'time_series_data': json.dumps(time_series_data) if time_series_data else '[]',
            'category_data': json.dumps(category_data) if category_data else '[]',
            'score_data': json.dumps(score_data) if score_data else '{}',
            'sentiment_data': json.dumps(sentiment_data) if sentiment_data else '{}',
            'themes_data': json.dumps(themes_data) if themes_data else '[]',
            'recent_responses': recent_responses,
            'product_performance': list(product_performance),
            'trend_30_days': trend_30_days,
        })
        
        return context
    
    def _get_time_series_data(self, queryset, days_filter):
        """Get time series data for charts"""
        if days_filter <= 30:
            trunc_func = TruncDate('created_at')
        elif days_filter <= 90:
            trunc_func = TruncWeek('created_at')
        else:
            trunc_func = TruncMonth('created_at')
        
        time_series = queryset.annotate(
            period=trunc_func
        ).values('period').annotate(
            total=Count('id'),
            promoters=Count('id', filter=Q(category='promoter')),
            detractors=Count('id', filter=Q(category='detractor')),
            avg_score=Avg('score')
        ).order_by('period')
        
        data = []
        for item in time_series:
            if item['period']:
                total = item['total']
                if total > 0:
                    nps = (item['promoters'] / total * 100) - (item['detractors'] / total * 100)
                else:
                    nps = 0
                
                data.append({
                    'date': item['period'].strftime('%Y-%m-%d'),
                    'count': total,
                    'nps': round(nps, 1),
                    'avg_score': round(item['avg_score'] or 0, 1),
                })
        
        return data
    
    def _get_category_data(self, queryset):
        """Get category distribution data"""
        categories = ['detractor', 'passive', 'promoter']
        category_data = []
        
        total = queryset.count()
        for category in categories:
            count = queryset.filter(category=category).count()
            percentage = (count / total * 100) if total > 0 else 0
            category_data.append({
                'category': category,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        return category_data
    
    def _get_score_distribution(self, queryset):
        """Get score distribution (0-10)"""
        score_dist = {}
        for score in range(11):  # 0 to 10
            count = queryset.filter(score=score).count()
            score_dist[score] = count
        
        return score_dist
    
    def _get_sentiment_data(self, queryset):
        """Get sentiment analysis data"""
        analyzed_responses = queryset.filter(ai_analyzed=True)
        total_analyzed = analyzed_responses.count()
        total_responses = queryset.count()
        
        if total_analyzed > 0:
            # Overall sentiment
            overall_sentiment = analyzed_responses.aggregate(
                avg_sentiment=Avg('sentiment_score')
            )['avg_sentiment'] or 0
            
            # Sentiment counts
            positive = analyzed_responses.filter(sentiment_score__gte=0.1).count()
            negative = analyzed_responses.filter(sentiment_score__lte=-0.1).count()
            neutral = total_analyzed - positive - negative
            
            analysis_rate = (total_analyzed / total_responses * 100) if total_responses > 0 else 0
        else:
            overall_sentiment = 0
            positive = negative = neutral = 0
            analysis_rate = 0
        
        return {
            'overall': round(overall_sentiment, 2),
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'analysis_rate': round(analysis_rate, 1)
        }
    
    def _get_top_themes(self, queryset, limit=10):
        """Get top key themes from analyzed responses"""
        themes_counter = {}
        analyzed_responses = queryset.filter(
            ai_analyzed=True,
            key_themes__isnull=False
        )
        
        for response in analyzed_responses:
            if response.key_themes and isinstance(response.key_themes, list):
                for theme in response.key_themes:
                    if isinstance(theme, str):
                        themes_counter[theme] = themes_counter.get(theme, 0) + 1
        
        # Sort by count and get top themes
        sorted_themes = sorted(themes_counter.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [{'theme': theme, 'count': count} for theme, count in sorted_themes]
    
    def _get_trend_data(self, queryset, organization_id, days):
        """Calculate trend data for specified days"""
        end_date = timezone.now()
        start_date_prev = end_date - timedelta(days=days * 2)
        start_date_current = end_date - timedelta(days=days)
        
        # Get responses for previous period
        previous_period = NPSResponse.objects.filter(
            organization_id=organization_id,
            created_at__gte=start_date_prev,
            created_at__lt=start_date_current
        )
        
        # Get responses for current period
        current_period = queryset.filter(
            created_at__gte=start_date_current
        )
        
        # Calculate NPS for both periods
        prev_nps = self._calculate_nps(previous_period)
        curr_nps = self._calculate_nps(current_period)
        
        # Calculate trend percentage
        trend = 0
        if prev_nps != 0:
            trend = ((curr_nps - prev_nps) / abs(prev_nps)) * 100
        
        return {
            'previous': prev_nps,
            'current': curr_nps,
            'trend': round(trend, 1),
            'direction': 'up' if trend > 0 else 'down' if trend < 0 else 'stable'
        }
    
    def _calculate_nps(self, queryset):
        """Calculate NPS for a given queryset"""
        total = queryset.count()
        if total == 0:
            return 0
        
        promoters = queryset.filter(category='promoter').count()
        detractors = queryset.filter(category='detractor').count()
        
        return round(((promoters / total) * 100) - ((detractors / total) * 100), 1)


class NPSDashboardAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for AJAX dashboard updates"""
    
    def get(self, request, *args, **kwargs):
        organization_id = kwargs.get('organization_id')
        days_filter = int(request.GET.get('days', 30))
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_filter)
        
        # Get organization and filter responses
        organization = get_object_or_404(Organization, id=organization_id)
        queryset = NPSResponse.objects.filter(
            organization=organization,
            created_at__range=[start_date, end_date]
        )
        
        # Calculate metrics
        total_responses = queryset.count()
        
        if total_responses > 0:
            promoters = queryset.filter(category='promoter').count()
            passives = queryset.filter(category='passive').count()
            detractors = queryset.filter(category='detractor').count()
            
            promoter_percent = (promoters / total_responses) * 100
            detractor_percent = (detractors / total_responses) * 100
            nps_score = promoter_percent - detractor_percent
            
            avg_score = queryset.aggregate(avg_score=Avg('score'))['avg_score']
        else:
            promoters = passives = detractors = 0
            promoter_percent = detractor_percent = nps_score = avg_score = 0
        
        # Get simplified time series data
        time_series_data = self._get_time_series_data(queryset, days_filter)
        
        response_data = {
            'success': True,
            'metrics': {
                'total_responses': total_responses,
                'promoters': promoters,
                'passives': passives,
                'detractors': detractors,
                'promoter_percent': round(promoter_percent, 1),
                'detractor_percent': round(detractor_percent, 1),
                'nps_score': round(nps_score, 1),
                'avg_score': round(avg_score, 1) if avg_score else 0,
            },
            'time_series': time_series_data,
            'time_period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
            },
        }
        
        return JsonResponse(response_data)
    
    def _get_time_series_data(self, queryset, days_filter):
        """Helper method to get time series data"""
        if days_filter <= 30:
            trunc_func = TruncDate('created_at')
        elif days_filter <= 90:
            trunc_func = TruncWeek('created_at')
        else:
            trunc_func = TruncMonth('created_at')
        
        time_series = queryset.annotate(
            period=trunc_func
        ).values('period').annotate(
            total=Count('id'),
            promoters=Count('id', filter=Q(category='promoter')),
            detractors=Count('id', filter=Q(category='detractor')),
        ).order_by('period')
        
        dates = []
        nps_scores = []
        
        for item in time_series:
            if item['period']:
                dates.append(item['period'].strftime('%Y-%m-%d'))
                total = item['total']
                if total > 0:
                    nps = (item['promoters'] / total * 100) - (item['detractors'] / total * 100)
                else:
                    nps = 0
                nps_scores.append(round(nps, 1))
        
        return {
            'dates': dates,
            'nps_scores': nps_scores,
        }