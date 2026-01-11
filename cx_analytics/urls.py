from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import *
from . import views
from .views import *


app_name = 'cx_analytics'

urlpatterns = [
    path('organizations/<uuid:organization_pk>/sentiment/', SentimentAnalysisListView.as_view(), name='sentiment-list'),
    path('organizations/<uuid:organization_pk>/sentiment/<uuid:pk>/', SentimentAnalysisDetailView.as_view(), name='sentiment-detail'),
    path('organizations/<uuid:organization_pk>/feedback/<uuid:feedback_pk>/analyze-sentiment/', AnalyzeSingleFeedbackView.as_view(), name='sentiment-analyze-single'),
    path('organizations/<uuid:organization_pk>/sentiment/bulk-analysis/', BulkSentimentAnalysisView.as_view(), name='sentiment-bulk-analysis'),
    path('organizations/<uuid:organization_pk>/sentiment/bulk-actions/', BulkActionsView.as_view(), name='sentiment-bulk-actions'),
    path('organizations/<uuid:organization_pk>/sentiment/dashboard/', SentimentAnalysisDashboardView.as_view(), name='sentiment-dashboard'),
    path('organizations/<uuid:organization_pk>/feedback/<uuid:feedback_pk>/translate/', TranslateFeedbackView.as_view(), name='feedback-translate'), 
    
]