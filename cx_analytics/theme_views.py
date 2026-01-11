# views.py
import os
import csv
import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from core.models import *
from .forms import *

logger = logging.getLogger(__name__)

class GeminiThemeAnalyzer:
    """Gemini AI integration for theme analysis"""
    
    def __init__(self):
        import google.generativeai as genai
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def analyze_feedback_batch(self, feedback_contents, language='en'):
        """Analyze batch of feedback contents and extract themes"""
        try:
            prompt = self._build_theme_analysis_prompt(feedback_contents, language)
            response = self.model.generate_content(prompt)
            return self._parse_theme_response(response.text)
        except Exception as e:
            logger.error(f"Gemini analysis failed: {str(e)}")
            raise
    
    def _build_theme_analysis_prompt(self, feedback_contents, language):
        """Build prompt for theme analysis"""
        feedback_text = "\n\n".join([
            f"Feedback {i+1}:\n{content}" 
            for i, content in enumerate(feedback_contents)
        ])
        
        return f"""
        Analyze the following customer feedback and extract key themes, pain points, and topics.
        Focus ONLY on the actual content provided. Do not invent or assume anything not present.
        
        Language: {language}
        Feedback Contents:
        {feedback_text}
        
        Provide analysis in this exact JSON format:
        {{
            "themes": [
                {{
                    "name": "theme_name",
                    "description": "clear_description_based_only_on_feedback_content",
                    "category": "choose_from: product_quality, customer_service, pricing, delivery, usability, features, performance, documentation, other",
                    "keywords": ["keyword1", "keyword2", "keyword3"],
                    "representative_snippets": ["snippet1", "snippet2"],
                    "sentiment_analysis": {{
                        "positive_count": 0,
                        "negative_count": 0,
                        "neutral_count": 0
                    }}
                }}
            ],
            "feedback_assignments": [
                {{
                    "feedback_index": 0,
                    "themes": [
                        {{
                            "theme_name": "theme_name",
                            "relevance_score": 0.95,
                            "matching_keywords": ["keyword1", "keyword2"],
                            "content_snippet": "relevant_snippet_from_feedback"
                        }}
                    ]
                }}
            ]
        }}
        
        Rules:
        1. Base themes ONLY on the actual feedback content provided
        2. Do not create generic themes - be specific to the content
        3. Ensure relevance scores accurately reflect content relevance
        4. Include specific content snippets that support each theme
        5. Categorize themes appropriately based on actual content
        """
    
    def _parse_theme_response(self, response_text):
        """Parse Gemini response into structured data"""
        try:
            # Extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Gemini response: {str(e)}")
            raise ValueError("Invalid response format from AI service")

class FeedbackCreateView(CreateView):
    model = Feedback
    form_class = FeedbackForm
    template_name = 'feedback/feedback_create.html'
    success_url = reverse_lazy('feedback_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Trigger async theme analysis
        self.analyze_feedback_themes([self.object])
        messages.success(self.request, _('Feedback submitted successfully and sent for analysis.'))
        return response
    
    def analyze_feedback_themes(self, feedback_objects):
        """Trigger async theme analysis for feedback objects"""
        from .tasks import analyze_feedback_themes_task
        feedback_ids = [fb.id for fb in feedback_objects]
        analyze_feedback_themes_task.delay(feedback_ids)

class BulkFeedbackUploadView(FormView):
    form_class = BulkFeedbackUploadForm
    template_name = 'feedback/bulk_upload.html'
    success_url = reverse_lazy('feedback_list')
    
    def form_valid(self, form):
        try:
            csv_file = form.cleaned_data['csv_file']
            organization = form.cleaned_data['organization']
            language = form.cleaned_data['language']
            generate_themes = form.cleaned_data['generate_themes']
            
            feedback_objects = self.process_csv_file(csv_file, organization, language)
            
            if generate_themes:
                self.analyze_feedback_themes(feedback_objects)
            
            messages.success(
                self.request, 
                _(f'Successfully uploaded {len(feedback_objects)} feedback entries.')
            )
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, _(f'Error processing CSV file: {str(e)}'))
            return self.form_invalid(form)
    
    def process_csv_file(self, csv_file, organization, language):
        """Process CSV file and create feedback objects"""
        feedback_objects = []
        
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        
        required_columns = ['customer_email', 'content']
        
        for row_num, row in enumerate(reader, start=2):
            # Validate required columns
            if not all(col in row for col in required_columns):
                raise ValidationError(_(f'Missing required columns in row {row_num}'))
            
            try:
                customer, created = Customer.objects.get_or_create(
                    email=row['customer_email'],
                    organization=organization,
                    defaults={'name': row.get('customer_name', '')}
                )
                
                feedback = Feedback(
                    organization=organization,
                    customer=customer,
                    channel_id=row.get('channel'),
                    product_id=row.get('product'),
                    subject=row.get('subject', ''),
                    content=row['content'],
                    feedback_type=row.get('feedback_type', 'general'),
                    priority=row.get('priority', 'medium'),
                    original_language=language
                )
                feedback.save()
                feedback_objects.append(feedback)
                
            except Exception as e:
                logger.error(f"Error processing row {row_num}: {str(e)}")
                continue
        
        return feedback_objects

class ThemeAnalysisView(FormView):
    form_class = ThemeAnalysisForm
    template_name = 'feedback/theme_analysis.html'
    success_url = reverse_lazy('theme_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        organization_id = self.kwargs.get('organization_id')
        if organization_id:
            kwargs['organization'] = Organization.objects.get(id=organization_id)
        return kwargs
    
    def form_valid(self, form):
        try:
            feedback_queryset = form.cleaned_data['feedback_queryset']
            language = form.cleaned_data['language']
            min_relevance_score = form.cleaned_data['min_relevance_score']
            
            # Perform theme analysis
            analyzer = GeminiThemeAnalyzer()
            feedback_contents = [fb.content for fb in feedback_queryset]
            
            analysis_result = analyzer.analyze_feedback_batch(feedback_contents, language)
            
            # Process themes and assignments
            self.process_theme_analysis(analysis_result, feedback_queryset, min_relevance_score)
            
            messages.success(
                self.request, 
                _(f'Successfully analyzed {len(feedback_queryset)} feedback entries and generated themes.')
            )
            
        except Exception as e:
            messages.error(self.request, _(f'Themes analysis failed: {str(e)}'))
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    @transaction.atomic
    def process_theme_analysis(self, analysis_result, feedback_queryset, min_relevance_score):
        """Process AI analysis results and create theme relationships"""
        organization = feedback_queryset.first().organization
        
        # Create or update themes
        theme_map = {}
        for theme_data in analysis_result.get('themes', []):
            theme, created = Theme.objects.get_or_create(
                organization=organization,
                name=theme_data['name'],
                defaults={
                    'description': theme_data['description'],
                    'category': theme_data['category'],
                    'keywords': theme_data['keywords'],
                    'content_snippets': theme_data['representative_snippets'],
                    'occurrence_count': 0,
                    'sentiment_distribution': theme_data['sentiment_analysis'],
                    'auto_generated': True,
                    'last_analysis_date': timezone.now()
                }
            )
            theme_map[theme_data['name']] = theme
        
        # Create feedback-theme relationships
        for assignment in analysis_result.get('feedback_assignments', []):
            feedback_index = assignment['feedback_index']
            if feedback_index >= len(feedback_queryset):
                continue
                
            feedback = feedback_queryset[feedback_index]
            
            for theme_assignment in assignment['themes']:
                theme_name = theme_assignment['theme_name']
                relevance_score = theme_assignment['relevance_score']
                
                if (theme_name in theme_map and 
                    relevance_score >= min_relevance_score):
                    
                    FeedbackTheme.objects.update_or_create(
                        feedback=feedback,
                        theme=theme_map[theme_name],
                        defaults={
                            'relevance_score': relevance_score,
                            'matching_keywords': theme_assignment['matching_keywords'],
                            'content_snippet': theme_assignment['content_snippet'],
                            'is_primary': relevance_score > 0.8
                        }
                    )
        
        # Update theme occurrence counts
        for theme in theme_map.values():
            theme.occurrence_count = theme.feedback_themes.count()
            theme.save()
        
        # Mark feedback as analyzed
        feedback_queryset.update(
            ai_analyzed=True,
            ai_analysis_date=timezone.now()
        )

class FeedbackListView(ListView):
    model = Feedback
    template_name = 'feedback/feedback_list.html'
    paginate_by = 20
    context_object_name = 'feedbacks'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        organization_id = self.request.GET.get('organization')
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        return queryset.select_related('customer', 'organization', 'product')

class ThemeListView(ListView):
    model = Theme
    template_name = 'feedback/theme_list.html'
    paginate_by = 15
    context_object_name = 'themes'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        organization_id = self.request.GET.get('organization')
        category = self.request.GET.get('category')
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if category:
            queryset = queryset.filter(category=category)
            
        return queryset.prefetch_related('products')

class ThemeDetailView(DetailView):
    model = Theme
    template_name = 'feedback/theme_detail.html'
    context_object_name = 'theme'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_feedbacks'] = self.object.feedback_themes.select_related(
            'feedback', 'feedback__customer'
        ).order_by('-relevance_score')[:10]
        return context

class DashboardView(TemplateView):
    template_name = 'feedback/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.request.GET.get('organization')
        
        if organization_id:
            feedbacks = Feedback.objects.filter(organization_id=organization_id)
            themes = Theme.objects.filter(organization_id=organization_id)
        else:
            feedbacks = Feedback.objects.all()
            themes = Theme.objects.all()
        
        context.update({
            'total_feedbacks': feedbacks.count(),
            'analyzed_feedbacks': feedbacks.filter(ai_analyzed=True).count(),
            'total_themes': themes.count(),
            'recent_feedbacks': feedbacks.order_by('-created_at')[:5],
            'top_themes': themes.order_by('-occurrence_count')[:5],
        })
        return context