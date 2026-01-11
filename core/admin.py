from django.contrib import admin
from core.models import *
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.db import models
from parler.admin import TranslatableAdmin
#from networking.urls import *
from django_summernote.admin import SummernoteModelAdmin
from froala_editor.widgets import FroalaEditor

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    #list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    

admin.site.register(Channel)
admin.site.register(Tag)
admin.site.register(OrganizationMember)
admin.site.register(Customer)

admin.site.register(Product)
admin.site.register(Feedback)
admin.site.register(SentimentAnalysis)
admin.site.register(Review)
admin.site.register(Theme)
admin.site.register(FeedbackTheme)
admin.site.register(Survey)
admin.site.register(SurveyResponse)
admin.site.register(NPSResponse)
admin.site.register(CSATResponse)
admin.site.register(CESResponse)

admin.site.register(AIAnalysisJob)
admin.site.register(MetricSnapshot)
admin.site.register(Alert)
admin.site.register(Resolution)
admin.site.register(Escalation)
admin.site.register(Benchmark)
admin.site.register(ActionItem)
admin.site.register(Report)
admin.site.register(ActionPlan)
admin.site.register(StrategicInsight)
admin.site.register(FeedbackCampaign)


# Register your models here.

@admin.action(description='Trigger AI analysis for selected responses')
def trigger_ai_analysis(modeladmin, request, queryset):
    for response in queryset:
        response.trigger_ai_analysis()
    
    modeladmin.message_user(request, f"Triggered AI analysis for {queryset.count()} responses")

class MixedSurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'survey', 'customer', 'completed_at', 'has_nps', 'has_csat', 'has_ces', 'ai_analyzed')
    list_filter = ('survey', 'is_complete', 'ai_analyzed', 'has_nps', 'has_csat', 'has_ces')
    search_fields = ('customer__email', 'survey__title', 'text_feedback_summary')
    actions = [trigger_ai_analysis]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('survey', 'customer', 'organization', 'channel')

admin.site.register(MixedSurveyResponse, MixedSurveyResponseAdmin)