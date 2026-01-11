from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import *
from . import views
from .response_views import *
from .nps_views import *
from .csat_views import *
from .ces_views import *


app_name = 'surveys'

urlpatterns = [
      # Organization-scoped survey management
    path('organizations/<uuid:organization_pk>/surveys/', SurveyListView.as_view(), name='survey-list'),
    path('organizations/<uuid:organization_pk>/surveys/create/', SurveyCreateView.as_view(), name='survey-create'),
    path('organizations/<uuid:organization_pk>/surveys/<uuid:pk>/', SurveyDetailView.as_view(), name='survey-detail'),
    path('organizations/<uuid:organization_pk>/surveys/<uuid:pk>/update/', SurveyUpdateView.as_view(), name='survey-update'),
    path('organizations/<uuid:organization_pk>/surveys/<uuid:pk>/delete/', SurveyDeleteView.as_view(), name='survey-delete'),
    path('organizations/<uuid:organization_pk>/surveys/<uuid:pk>/analytics/', SurveyAnalyticsView.as_view(), name='survey-analytics'),
    
    # Public survey URLs
    
    #path('organizations/public/<uuid:survey_uuid>/', SurveyPublicView.as_view(), name='survey-public-alt'),
    
    # Add alternative patterns for flexibility
    path('organizations/public/survey/<uuid:survey_uuid>/', SurveyPublicView.as_view(), name='survey-public'),
  
    path('s/<uuid:survey_uuid>/', SurveyPublicView.as_view(), name='survey-public-short'),

    #path('organizations/public/<uuid:survey_uuid>/', SurveyPublicView.as_view(), name='survey-public'),
    #path('organizations/public/<str:survey_uuid>/surveys/', SurveyPublicView.as_view(), name='survey-public'),
    path('organizations/embed/<uuid:survey_uuid>/', SurveyEmbedView.as_view(), name='survey-embed'),
    
    # API endpoints
    #path('api/<uuid:organization_pk>/surveys/', SurveyListAPIView.as_view(), name='api-list'),
    #path('api/survey-responses/<uuid:pk>/analyze/', views.analyze_sentiment_api, name='analyze-sentiment-api'),
    
    ###### Survey Responses ######
    path('organizations/<uuid:organization_pk>/surveys/<uuid:survey_id>/response/new', SurveyResponseCreateView.as_view(), name='survey-response-create'),
    path('surveys/response/<uuid:pk>/thank-you/', SurveyResponseThankYouView.as_view(), name='survey-response-thank-you'),
    
    # Authenticated user URLs (organization members)
    path('organizations/<uuid:organization_pk>/surveys/<uuid:survey_id>/responses/', SurveyResponseListView.as_view(), name='survey-response-list'),
    path('organizations/<uuid:organization_pk>/surveys/<uuid:survey_id>/responses/<uuid:pk>/', SurveyResponseDetailView.as_view(), name='survey-response-detail'),
    
    path('organizations/<uuid:organization_pk>/surveys/<uuid:pk>/export/csv/', ExportSurveyResponsesCSVView.as_view(), name='export-survey-csv'),
    path('organizations/<uuid:organization_pk>/surveys/<uuid:pk>/export/report/', ExportSurveyAnalyticsReportView.as_view(), name='export-survey-report'),
   
   
   # NPS Response Collection
    path('organizations/<uuid:organization_id>/nps-dashboard/', NPSDashboardView.as_view(), name='nps-response-dashboard'),
    path('organizations/<uuid:organization_id>/nps-responses/', NPSResponseListView.as_view(), name='nps-response-list'),
    path('organizations/<uuid:organization_id>/nps-responses/<uuid:pk>/', NPSResponseDetailView.as_view(), name='nps-response-detail'),
    path('organizations/<uuid:organization_id>/nps-responses/<uuid:pk>/delete/', NPSResponseDeleteView.as_view(), name='nps-response-delete'),
    path('organizations/<uuid:organization_id>/nps-dashboard/api/', NPSDashboardAPIView.as_view(), name='nps-dashboard-api'),
   
   # CSAT Responses Collection
   path('organizations/<uuid:organization_id>/csat-dashboard/', CSATDashboardView.as_view(), name='csat-response-dashboard'),
    
    # List view
    path('organizations/<uuid:organization_id>/csat-responses/', CSATResponseListView.as_view(), name='csat-response-list'),
    
    # Detail view
    path('organizations/<uuid:organization_id>/csat-responses/<uuid:pk>/detail/', CSATResponseDetailView.as_view(), name='csat-response-detail'),
    
    # Delete view
    path('organizations/<uuid:organization_id>/csat-responses/<uuid:pk>/delete/', CSATResponseDeleteView.as_view(), name='csat-response-delete'),
    
    ##### CES Responses Collection #####
    path('organizations/<uuid:organization_id>/ces-dashboard/', CESDashboardView.as_view(), name='ces-response-dashboard'),
    # List view
    path('organizations/<uuid:organization_id>/ces-responses/', CESResponseListView.as_view(), name='ces-response-list'),
    path('organizations/<uuid:organization_id>/ces-responses/<uuid:pk>/detail/', CESResponseDetailView.as_view(), name='ces-response-detail'),
    path('organizations/<uuid:organization_id>/ces-responses/<uuid:pk>/delete/', CESResponseDeleteView.as_view(), name='ces-response-delete'),
]