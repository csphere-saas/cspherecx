from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import *
from . import views
from .views import *
from .channels_views import *
from .tag_views import *

app_name = 'feedback'

urlpatterns = [
    path('organizations/<uuid:organization_pk>/feedback/', FeedbackListView.as_view(), name='feedback-list'),
    path('organizations/<uuid:organization_pk>/feedback/create/', FeedbackCreateView.as_view(), name='feedback-create'),
   
    #path(
    #   'organizations/<uuid:organization_id>/feedback/create/',
    #    views.FeedbackCreateView.as_view(),
    #    name='feedback-create'
    #),
    path('organizations/<uuid:organization_pk>/feedback/<uuid:pk>/', FeedbackDetailView.as_view(), name='feedback-detail'),
    path('organizations/<uuid:organization_pk>/feedback/<uuid:pk>/update/', FeedbackUpdateView.as_view(), name='feedback-update'),
    path('organizations/<uuid:organization_pk>/feedback/<uuid:pk>/delete/', FeedbackDeleteView.as_view(), name='feedback-delete'),
    path('organizations/<uuid:organization_pk>/feedback/bulk-analysis/', BulkFeedbackAnalysisView.as_view(), name='feedback-bulk-analysis'),
    path('organizations/<uuid:organization_pk>/feedback/import/', FeedbackImportView.as_view(), name='feedback-import'),
    path('organizations/<uuid:organization_pk>/feedback/dashboard/', FeedbackAnalysisDashboardView.as_view(), name='feedback-dashboard'),
    path('organizations/<uuid:organization_pk>/feedback/<uuid:pk>/analyze/', AnalyzeSingleFeedbackView.as_view(), name='feedback-analyze-single'),
      
    #####
    path('organizations/<uuid:organization_pk>/channels/', ChannelListView.as_view(), name='channel-list'),
    path('organizations/<uuid:organization_pk>/channels/create/', ChannelCreateView.as_view(), name='channel-create'),
    path('organizations/<uuid:organization_pk>/channels/<uuid:pk>/', ChannelDetailView.as_view(), name='channel-detail'),
    path('organizations/<uuid:organization_pk>/channels/<uuid:pk>/update/', ChannelUpdateView.as_view(), name='channel-update'),
    path('organizations/<uuid:organization_pk>/channels/<uuid:pk>/delete/', ChannelDeleteView.as_view(), name='channel-delete'),
    path('organizations/<uuid:organization_pk>/channels/<uuid:pk>/toggle/', ChannelToggleView.as_view(), name='channel-toggle'),
   
   ##### Tags URLs #####
    path('organizations/<uuid:organization_pk>/tags/', TagListView.as_view(), name='tag-list'),
    path('organizations/<uuid:organization_pk>/tags/create/', TagCreateView.as_view(), name='tag-create'),
    path('organizations/<uuid:organization_pk>/tags/<uuid:pk>/', TagDetailView.as_view(), name='tag-detail'),
    path('organizations/<uuid:organization_pk>/tags/<uuid:pk>/update/', TagUpdateView.as_view(), name='tag-update'),
    path('organizations/<uuid:organization_pk>/tags/<uuid:pk>/delete/', TagDeleteView.as_view(), name='tag-delete'),
   
   ######
   path(
        'ajax/customer-details/',
        CustomerDetailsAjaxView.as_view(),
        name='customer-details-ajax'
    ),
   
   
  
]