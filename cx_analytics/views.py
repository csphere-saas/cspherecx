from django.shortcuts import render
# views.py
import logging
import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, TemplateView, View
from django.http import JsonResponse
from core.models import *
from .utils import *
from .forms import *
from .services.gemini_analyzer import GeminiSentimentAnalyzer
from .services.translation_service import TranslationService
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger 

logger = logging.getLogger(__name__)

class SentimentAnalysisMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin for sentiment analysis views
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
        return user_membership is not None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        return context

class SentimentAnalysisListView(SentimentAnalysisMixin, TemplateView):
    """
    List view for sentiment analysis with bulk actions
    """
    template_name = 'sentiment_analysis/sentiment-list.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        # Get filter parameters
        sentiment_filter = self.request.GET.get('sentiment', '')
        analyzed_filter = self.request.GET.get('analyzed', '')
        search_query = self.request.GET.get('q', '')
        
        # Base queryset with prefetch for sentiment analysis
        feedbacks = Feedback.objects.filter(organization=organization).prefetch_related('sentiment_analysis')
        
        # Apply filters
        if sentiment_filter:
            feedbacks = feedbacks.filter(sentiment_label=sentiment_filter)
        
        if analyzed_filter == 'analyzed':
            feedbacks = feedbacks.filter(ai_analyzed=True)
        elif analyzed_filter == 'not_analyzed':
            feedbacks = feedbacks.filter(ai_analyzed=False)
        elif analyzed_filter == 'needs_review':
            feedbacks = feedbacks.filter(requires_human_review=True)
        
        if search_query:
            feedbacks = feedbacks.filter(
                Q(content__icontains=search_query) |
                Q(customer__name__icontains=search_query) |
                Q(feedback_id__icontains=search_query)
            )
        
        # Get pagination parameters
        page = self.request.GET.get('page', 1)
        paginator = Paginator(feedbacks.select_related('customer'), self.paginate_by)
        
        try:
            feedbacks_page = paginator.page(page)
        except PageNotAnInteger:
            feedbacks_page = paginator.page(1)
        except EmptyPage:
            feedbacks_page = paginator.page(paginator.num_pages)
        
        # Get quick stats for filters
        total_feedbacks = Feedback.objects.filter(organization=organization).count()
        analyzed_count = Feedback.objects.filter(organization=organization, ai_analyzed=True).count()
        needs_review_count = Feedback.objects.filter(organization=organization, requires_human_review=True).count()
        
        # Calculate sentiment distribution
        sentiment_distribution = self.get_sentiment_distribution(organization)
        
        # Define sentiment choices
        SENTIMENT_CHOICES = [
            ('very_positive', _('Very Positive')),
            ('positive', _('Positive')),
            ('neutral', _('Neutral')),
            ('negative', _('Negative')),
            ('very_negative', _('Very Negative')),
        ]

        # Language choices for analysis
        LANGUAGE_CHOICES = [
            ('en', _('English')),
            ('es', _('Spanish')),
            ('fr', _('French')),
            ('de', _('German')),
            ('it', _('Italian')),
            ('pt', _('Portuguese')),
            ('ja', _('Japanese')),
            ('ko', _('Korean')),
            ('zh', _('Chinese')),
            ('ar', _('Arabic')),
            ('hi', _('Hindi')),
        ]
        
        # Convert sentiment distribution to JSON-serializable format
        sentiment_distribution_json = self.prepare_sentiment_distribution_for_json(sentiment_distribution)
        
        # Debug: Print distribution data
        print("Sentiment Distribution:", sentiment_distribution)
        print("Sentiment Distribution JSON:", sentiment_distribution_json)
        
        context.update({
            'page_title': _('Sentiment Analysis'),
            'feedbacks': feedbacks_page,
            'total_feedbacks': total_feedbacks,
            'analyzed_count': analyzed_count,
            'needs_review_count': needs_review_count,
            'sentiment_filter': sentiment_filter,
            'analyzed_filter': analyzed_filter,
            'search_query': search_query,
            'SENTIMENT_CHOICES': SENTIMENT_CHOICES,
            'LANGUAGE_CHOICES': LANGUAGE_CHOICES,
            'sentiment_distribution': sentiment_distribution,
            'sentiment_distribution_json': json.dumps(sentiment_distribution_json),
        })
        
        return context

    def get_sentiment_distribution(self, organization):
        """
        Calculate sentiment distribution for the organization
        """
        # Get all feedbacks for the organization
        feedbacks = Feedback.objects.filter(organization=organization)
        total_count = feedbacks.count()
        
        distribution = {}
        
        # DEBUG: Check what sentiment labels exist in the database
        unique_sentiments = feedbacks.filter(ai_analyzed=True).exclude(
            sentiment_label__isnull=True
        ).exclude(
            sentiment_label=''
        ).values_list('sentiment_label', flat=True).distinct()
        
        print("Unique sentiment labels in DB:", list(unique_sentiments))
        
        # Count analyzed feedbacks by sentiment with average scores
        sentiment_data = feedbacks.filter(ai_analyzed=True).exclude(
            sentiment_label__isnull=True
        ).exclude(
            sentiment_label=''
        ).values('sentiment_label').annotate(
            count=Count('id'),
            avg_score=Avg('sentiment_score')
        )
        
        print("Raw sentiment data from DB:", list(sentiment_data))
        
        # Initialize all sentiment categories with proper mapping
        sentiment_categories = {
            'very_positive': {'count': 0, 'avg_score': 0, 'label': _('Very Positive')},
            'positive': {'count': 0, 'avg_score': 0, 'label': _('Positive')},
            'neutral': {'count': 0, 'avg_score': 0, 'label': _('Neutral')},
            'negative': {'count': 0, 'avg_score': 0, 'label': _('Negative')},
            'very_negative': {'count': 0, 'avg_score': 0, 'label': _('Very Negative')},
        }
        
        # Map database sentiment labels to our categories
        sentiment_mapping = {
            'very_positive': ['very_positive', 'POSITIVE', 'positive', 'Very Positive'],
            'positive': ['positive', 'POSITIVE', 'Positive'],
            'neutral': ['neutral', 'NEUTRAL', 'Neutral'],
            'negative': ['negative', 'NEGATIVE', 'Negative'],
            'very_negative': ['very_negative', 'NEGATIVE', 'negative', 'Very Negative'],
        }
        
        # Populate with actual data using mapping
        for item in sentiment_data:
            sentiment_label = item['sentiment_label']
            count = item['count']
            avg_score = item['avg_score'] or 0
            
            # Find which category this sentiment belongs to
            matched_category = None
            for category, labels in sentiment_mapping.items():
                if sentiment_label in labels:
                    matched_category = category
                    break
            
            # If no direct match, try case-insensitive matching
            if not matched_category:
                sentiment_lower = sentiment_label.lower()
                for category, labels in sentiment_mapping.items():
                    if any(label.lower() == sentiment_lower for label in labels):
                        matched_category = category
                        break
            
            if matched_category and matched_category in sentiment_categories:
                sentiment_categories[matched_category]['count'] += count
                # For average score, we need to calculate weighted average later
                sentiment_categories[matched_category]['avg_score'] = avg_score
        
        # Calculate weighted average scores
        for sentiment, data in sentiment_categories.items():
            if data['count'] > 0:
                # Recalculate average from individual items for accuracy
                sentiment_feedbacks = feedbacks.filter(ai_analyzed=True, sentiment_label__in=sentiment_mapping[sentiment])
                avg_score = sentiment_feedbacks.aggregate(avg=Avg('sentiment_score'))['avg'] or 0
                sentiment_categories[sentiment]['avg_score'] = avg_score
        
        # Build distribution dictionary
        for sentiment, data in sentiment_categories.items():
            distribution[sentiment] = {
                'count': data['count'],
                'percentage': (data['count'] / total_count * 100) if total_count > 0 else 0,
                'avg_score': data['avg_score'],
                'label': data['label']
            }
        
        # Count not analyzed feedbacks
        not_analyzed_count = feedbacks.filter(ai_analyzed=False).count()
        distribution['not_analyzed'] = {
            'count': not_analyzed_count,
            'percentage': (not_analyzed_count / total_count * 100) if total_count > 0 else 0,
            'avg_score': None,
            'label': _('Not Analyzed')
        }
        
        print("Final distribution:", distribution)
        return distribution

    def prepare_sentiment_distribution_for_json(self, sentiment_distribution):
        """
        Convert sentiment distribution to JSON-serializable format
        by converting any __proxy__ objects to strings
        """
        serializable_distribution = {}
        
        for key, data in sentiment_distribution.items():
            serializable_distribution[key] = {
                'count': data['count'],
                'percentage': float(data['percentage']),  # Ensure it's a float
                'avg_score': float(data['avg_score']) if data['avg_score'] is not None else None,
                'label': str(data['label'])  # Convert __proxy__ to string
            }
        
        return serializable_distribution

    def post(self, request, *args, **kwargs):
        """
        Handle bulk actions
        """
        organization = self.get_organization()
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_feedbacks')
        
        if not selected_ids:
            messages.warning(request, _('No feedback items selected.'))
            return redirect('cx_analytics:sentiment-list', organization_pk=organization.pk)
        
        if action == 'bulk_analyze':
            # Handle bulk analysis
            try:
                # Validate selection limit
                if len(selected_ids) > 50:
                    messages.error(request, _('For performance reasons, please select no more than 50 items for bulk analysis.'))
                    return redirect('cx_analytics:sentiment-list', organization_pk=organization.pk)
                
                # Start bulk analysis (synchronous for now)
                successful_analyses = 0
                failed_analyses = 0
                
                for feedback_id in selected_ids:
                    try:
                        feedback = Feedback.objects.get(id=feedback_id, organization=organization)
                        # Perform analysis (you can integrate your analysis logic here)
                        # For now, we'll just mark it as analyzed for demonstration
                        feedback.ai_analyzed = True
                        feedback.ai_analysis_date = timezone.now()
                        feedback.sentiment_score = 0.5  # Example score
                        feedback.sentiment_label = 'neutral'
                        feedback.save()
                        successful_analyses += 1
                    except Exception as e:
                        logger.error(f"Failed to analyze feedback {feedback_id}: {str(e)}")
                        failed_analyses += 1
                
                if successful_analyses > 0:
                    messages.success(request, _('Successfully analyzed %(count)s items.') % {'count': successful_analyses})
                if failed_analyses > 0:
                    messages.warning(request, _('Failed to analyze %(count)s items.') % {'count': failed_analyses})
                
            except Exception as e:
                messages.error(request, _('Failed to start bulk analysis: %(error)s') % {'error': str(e)})
        
        elif action == 'bulk_mark_reviewed':
            # Mark selected items as reviewed
            updated = Feedback.objects.filter(
                id__in=selected_ids,
                organization=organization
            ).update(requires_human_review=False)
            
            messages.success(request, _('Marked %(count)s items as reviewed.') % {'count': updated})
        
        elif action == 'bulk_delete_analysis':
            # Delete sentiment analysis for selected items
            try:
                with transaction.atomic():
                    # Delete related sentiment analyses
                    SentimentAnalysis.objects.filter(
                        feedback__id__in=selected_ids,
                        feedback__organization=organization
                    ).delete()
                    
                    # Reset feedback analysis flags
                    updated = Feedback.objects.filter(
                        id__in=selected_ids,
                        organization=organization
                    ).update(
                        ai_analyzed=False,
                        ai_analysis_date=None,
                        sentiment_score=None,
                        sentiment_label='',
                        requires_human_review=False
                    )
                
                messages.success(request, _('Removed analysis from %(count)s items.') % {'count': updated})
            
            except Exception as e:
                messages.error(request, _('Failed to delete analysis: %(error)s') % {'error': str(e)})
        
        else:
            messages.warning(request, _('Invalid action selected.'))
        
        return redirect('cx_analytics:sentiment-list', organization_pk=organization.pk)
    

class SentimentAnalysisDetailView(SentimentAnalysisMixin, DetailView):
    """
    View detailed sentiment analysis results
    """
    model = SentimentAnalysis
    template_name = 'sentiment_analysis/sentiment-analysis-detail.html'
    context_object_name = 'analysis'

    def get_queryset(self):
        organization = self.get_organization()
        return SentimentAnalysis.objects.filter(
            feedback__organization=organization
        ).select_related('feedback', 'feedback__customer')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        analysis = self.object
        
        # Add sentiment display properties
        context.update({
            'page_title': _('Sentiment Analysis Details'),
            'sentiment_color': self.get_sentiment_color(analysis.overall_label),
            'sentiment_icon': self.get_sentiment_icon(analysis.overall_label),
            'urgency_color': self.get_urgency_color(analysis.urgency_level),
            'urgency_text': self.get_urgency_text(analysis.urgency_level),
            'confidence_color': 'success' if analysis.confidence_score > 0.8 else 'warning' if analysis.confidence_score > 0.6 else 'danger',
        })
        return context

    def get_sentiment_color(self, label):
        """Convert sentiment label to Bootstrap color"""
        color_map = {
            'POSITIVE': 'success',
            'NEGATIVE': 'danger',
            'NEUTRAL': 'secondary',
            'MIXED': 'warning',
        }
        return color_map.get(label, 'secondary')

    def get_sentiment_icon(self, label):
        """Convert sentiment label to icon class"""
        icon_map = {
            'POSITIVE': 'fa-smile',
            'NEGATIVE': 'fa-frown',
            'NEUTRAL': 'fa-meh',
            'MIXED': 'fa-comments',
        }
        return icon_map.get(label, 'fa-comment')

    def get_urgency_color(self, level):
        """Convert urgency level to color"""
        color_map = {
            'HIGH': 'danger',
            'MEDIUM': 'warning',
            'LOW': 'success',
            'NONE': 'secondary',
        }
        return color_map.get(level, 'secondary')

    def get_urgency_text(self, level):
        """Convert urgency level to display text"""
        text_map = {
            'HIGH': 'High Urgency',
            'MEDIUM': 'Medium Urgency',
            'LOW': 'Low Urgency',
            'NONE': 'No Urgency',
        }
        return text_map.get(level, 'Unknown')

class AnalyzeSingleFeedbackView(SentimentAnalysisMixin, View):
    """
    Analyze single feedback using Gemini AI with enhanced error handling
    """
    
    def post(self, request, *args, **kwargs):
        organization = self.get_organization()
        
        # Get feedback ID from URL parameters
        feedback_pk = self.kwargs.get('feedback_pk')
        
        if not feedback_pk:
            return JsonResponse({
                'success': False,
                'message': _('No feedback item specified.')
            }, status=400)
        
        try:
            feedback = get_object_or_404(
                Feedback, 
                id=feedback_pk, 
                organization=organization
            )
            
            # Get analysis parameters
            target_language = request.POST.get('target_language', 'en')
            translate_content = request.POST.get('translate_content', 'false').lower() == 'true'
            
            with transaction.atomic():
                # Initialize services
                analyzer = GeminiSentimentAnalyzer()
                translator = TranslationService()
                
                # Prepare content for analysis
                content_to_analyze = feedback.content
                analysis_language = feedback.original_language
                translated_content = None
                
                # Translate content if requested
                if translate_content and target_language != feedback.original_language:
                    try:
                        if not translator.is_configured():
                            logger.warning(f"Translation service not configured for feedback {feedback_pk}")
                        else:
                            translated_content = translator.translate_text(
                                feedback.content,
                                source_language=feedback.original_language,
                                target_language=target_language
                            )
                            content_to_analyze = translated_content
                            analysis_language = target_language
                    except Exception as e:
                        logger.warning(f"Translation failed for feedback {feedback_pk}: {str(e)}")
                        # Continue with original content if translation fails
                
                # Prepare analysis configuration
                analysis_config = {
                    'detect_aspects': True,
                    'detect_emotions': True,
                    'detect_intent': True,
                    'extract_key_phrases': True,
                    'target_language': target_language
                }
                
                # Analyze feedback with retry logic for JSON parsing issues
                max_retries = 3
                analysis_result = None
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        logger.info(f"Analyzing feedback {feedback_pk}, attempt {attempt + 1}")
                        analysis_result = analyzer.analyze_feedback(
                            content_to_analyze,
                            analysis_language,
                            analysis_config
                        )
                        last_error = None
                        break  # Success, exit retry loop
                    except ValueError as e:
                        last_error = e
                        if "Invalid analysis response format" in str(e) and attempt < max_retries - 1:
                            logger.warning(f"JSON parsing failed on attempt {attempt + 1}, retrying...")
                            # Add a small delay before retry
                            import time
                            time.sleep(0.5 * (attempt + 1))
                            continue
                        else:
                            raise
                    except Exception as e:
                        last_error = e
                        logger.error(f"Analysis failed on attempt {attempt + 1}: {str(e)}")
                        if attempt < max_retries - 1:
                            logger.warning("Retrying...")
                            continue
                        else:
                            raise
                
                if not analysis_result and last_error:
                    raise last_error
                
                # Map sentiment labels to match your model choices
                sentiment_label_map = {
                    'very_negative': 'very_negative',
                    'negative': 'negative',
                    'neutral': 'neutral',
                    'positive': 'positive',
                    'very_positive': 'very_positive'
                }
                
                overall_label = analysis_result['overall_sentiment']['label']
                mapped_label = sentiment_label_map.get(overall_label, 'neutral')
                
                # Get intent data safely with validation
                intent_data = analysis_result.get('intent', {})
                if isinstance(intent_data, dict):
                    intent_type = intent_data.get('type', 'unknown')
                    intent_confidence = intent_data.get('confidence', 0.0)
                    # Validate intent_type
                    valid_intents = ['complaint', 'compliment', 'suggestion', 'question', 'request', 'unknown']
                    if intent_type not in valid_intents:
                        intent_type = 'unknown'
                        intent_confidence = 0.0
                else:
                    intent_type = 'unknown'
                    intent_confidence = 0.0
                
                # Get urgency data safely with validation
                urgency_data = analysis_result.get('urgency', {})
                if isinstance(urgency_data, dict):
                    urgency_level = urgency_data.get('level', 'medium').lower()
                    urgency_indicators = urgency_data.get('indicators', [])
                    # Validate urgency_level
                    valid_urgency_levels = ['low', 'medium', 'high', 'critical']
                    if urgency_level not in valid_urgency_levels:
                        urgency_level = 'medium'
                else:
                    urgency_level = 'medium'
                    urgency_indicators = []
                
                # Create or update sentiment analysis - INCLUDING ORGANIZATION
                sentiment_analysis, created = SentimentAnalysis.objects.update_or_create(
                    feedback=feedback,
                    defaults={
                        'organization': organization,  # CRITICAL: Add this line
                        'overall_score': float(analysis_result['overall_sentiment']['score']),
                        'overall_label': mapped_label,
                        'confidence_score': float(analysis_result['overall_sentiment']['confidence']),
                        'aspects': self._safe_json_field(analysis_result.get('aspect_sentiments', {})),
                        'emotions': self._safe_json_field(analysis_result.get('emotions', {})),
                        'intent': intent_type,
                        'intent_confidence': float(intent_confidence),
                        'urgency_level': urgency_level,
                        'urgency_indicators': self._safe_json_field(urgency_indicators),
                        'key_phrases': self._safe_json_field(analysis_result.get('key_phrases', [])),
                        'entities': self._safe_json_field(analysis_result.get('entities', {})),
                        'model_used': analysis_result.get('analysis_metadata', {}).get('model_used', 'gemini-2.5-flash'),
                        'model_version': analysis_result.get('analysis_metadata', {}).get('model_version', '1.0'),
                        'analysis_metadata': self._safe_json_field(analysis_result.get('analysis_metadata', {})),
                        'analysis_language': target_language,
                        'translated_content': translated_content,
                        'original_language': feedback.original_language
                    }
                )
                
                # Update feedback with quick reference fields
                feedback.ai_analyzed = True
                feedback.ai_analysis_date = timezone.now()
                feedback.sentiment_score = float(analysis_result['overall_sentiment']['score'])
                feedback.sentiment_label = mapped_label
                
                # Determine if human review is needed
                feedback.requires_human_review = self._needs_human_review(analysis_result)
                feedback.save()
                
                logger.info(
                    f"Successfully analyzed feedback {feedback.feedback_id} "
                    f"with sentiment: {feedback.sentiment_label} "
                    f"(score: {feedback.sentiment_score}) "
                    f"in language: {target_language}"
                )
                
                return JsonResponse({
                    'success': True,
                    'message': _('Analysis completed successfully.'),
                    'feedback_id': feedback.feedback_id,
                    'analysis_id': sentiment_analysis.id,
                    'sentiment_label': feedback.sentiment_label,
                    'sentiment_score': feedback.sentiment_score,
                    'confidence': analysis_result['overall_sentiment']['confidence'],
                    'requires_review': feedback.requires_human_review,
                    'analysis_language': target_language,
                    'translated': bool(translated_content),
                    'created': created,
                    'retries_used': min(max_retries - 1, 2)  # For debugging
                })
                
        except ValueError as e:
            logger.error(f"Value error analyzing feedback {feedback_pk}: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': _(f'Analysis failed: {str(e)}'),
                'error': str(e),
                'error_type': 'value_error'
            }, status=400)
        except Exception as e:
            logger.error(f"Error analyzing feedback {feedback_pk}: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': _('Analysis failed. Please try again.'),
                'error': str(e),
                'error_type': 'general_error'
            }, status=500)
    
    def _safe_json_field(self, data):
        """Ensure JSON field data is safe for storage"""
        try:
            # If it's already a dict or list, return as is
            if isinstance(data, (dict, list)):
                return data
            # If it's a string, try to parse it as JSON
            elif isinstance(data, str):
                return json.loads(data)
            # Otherwise, return empty dict
            else:
                return {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def _needs_human_review(self, analysis_result: dict) -> bool:
        """
        Determine if the analysis requires human review
        """
        try:
            # Review needed for low confidence
            confidence = analysis_result['overall_sentiment']['confidence']
            if confidence < 0.5:
                return True
            
            # Review needed for mixed/conflicting signals
            sentiment_score = analysis_result['overall_sentiment']['score']
            if -0.3 <= sentiment_score <= 0.3:  # Neutral range
                return True
            
            # Review needed for critical urgency
            urgency_data = analysis_result.get('urgency', {})
            if isinstance(urgency_data, dict) and urgency_data.get('level') == 'critical':
                return True
            
            # Review needed for very negative sentiment with high emotion scores
            if sentiment_score < -0.8:
                emotions = analysis_result.get('emotions', {})
                if isinstance(emotions, dict):
                    anger_score = emotions.get('anger', 0)
                    if anger_score > 0.8:
                        return True
            
            return False
        except (KeyError, TypeError, AttributeError):
            return True  # If we can't determine, default to review


import logging
from django import forms
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView


logger = logging.getLogger(__name__)

class BulkSentimentAnalysisForm(forms.Form):
    """Form for bulk sentiment analysis configuration"""
    
    ANALYSIS_TYPE_CHOICES = [
        ('basic', _('Basic Analysis')),
        ('standard', _('Standard Analysis')),
        ('advanced', _('Advanced Analysis')),
        ('custom', _('Custom Configuration')),
    ]
    
    analysis_type = forms.ChoiceField(
        choices=ANALYSIS_TYPE_CHOICES,
        widget=forms.RadioSelect,
        label=_('Analysis Type'),
        initial='standard'
    )
    
    # Custom configuration fields (shown when 'custom' is selected)
    detect_aspects = forms.BooleanField(
        required=False,
        label=_('Detect Aspect Sentiments'),
        initial=True
    )
    
    detect_emotions = forms.BooleanField(
        required=False,
        label=_('Detect Emotions'),
        initial=True
    )
    
    detect_intent = forms.BooleanField(
        required=False,
        label=_('Detect Intent'),
        initial=True
    )
    
    extract_key_phrases = forms.BooleanField(
        required=False,
        label=_('Extract Key Phrases'),
        initial=True
    )
    
    target_language = forms.ChoiceField(
        choices=[
            ('en', 'English'),
            ('es', 'Spanish'),
            ('fr', 'French'),
            ('de', 'German'),
            ('it', 'Italian'),
            ('pt', 'Portuguese'),
            ('ja', 'Japanese'),
            ('ko', 'Korean'),
            ('zh', 'Chinese'),
            ('ar', 'Arabic'),
            ('hi', 'Hindi'),
        ],
        label=_('Target Language for Analysis'),
        initial='en'
    )
    
    translate_content = forms.BooleanField(
        required=False,
        label=_('Translate content before analysis'),
        help_text=_('Translate feedback content to target language before analysis')
    )
    
    overwrite_existing = forms.BooleanField(
        required=False,
        label=_('Overwrite existing analysis'),
        help_text=_('Re-analyze feedback items that already have analysis results')
    )
    
    def clean(self):
        cleaned_data = super().clean()
        analysis_type = cleaned_data.get('analysis_type')
        
        # Set defaults based on analysis type
        if analysis_type == 'basic':
            cleaned_data['detect_aspects'] = False
            cleaned_data['detect_emotions'] = False
            cleaned_data['detect_intent'] = False
            cleaned_data['extract_key_phrases'] = False
        elif analysis_type == 'standard':
            cleaned_data['detect_aspects'] = True
            cleaned_data['detect_emotions'] = True
            cleaned_data['detect_intent'] = False
            cleaned_data['extract_key_phrases'] = True
        elif analysis_type == 'advanced':
            cleaned_data['detect_aspects'] = True
            cleaned_data['detect_emotions'] = True
            cleaned_data['detect_intent'] = True
            cleaned_data['extract_key_phrases'] = True
        
        return cleaned_data


class BulkSentimentAnalysisView(SentimentAnalysisMixin, FormView):
    """
    Perform bulk sentiment analysis on multiple feedbacks
    """
    template_name = 'sentiment_analysis/bulk-sentiment-analysis.html'
    form_class = BulkSentimentAnalysisForm
    success_url = None  # We'll override this

    def get_initial(self):
        """Set initial form data"""
        initial = super().get_initial()
        initial['target_language'] = 'en'
        initial['analysis_type'] = 'standard'
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        feedback_ids = self.request.GET.get('ids', '')
        
        if not feedback_ids:
            messages.warning(self.request, _('No feedback items selected for analysis.'))
            return context
        
        feedback_id_list = [fid.strip() for fid in feedback_ids.split(',') if fid.strip()]
        
        # Get selected feedback items
        selected_feedbacks = Feedback.objects.filter(
            organization=self.get_organization(),
            id__in=feedback_id_list
        ).select_related('customer')[:50]  # Limit to 50 items for performance
        
        context.update({
            'selected_feedbacks': selected_feedbacks,
            'page_title': _('Bulk Sentiment Analysis'),
            'total_selected': selected_feedbacks.count(),
            'feedback_ids': feedback_ids,
        })
        
        return context

    def form_valid(self, form):
        try:
            feedback_ids = self.request.GET.get('ids', '')
            if not feedback_ids:
                messages.warning(self.request, _('No feedback items selected for analysis.'))
                return redirect('cx_analytics:sentiment-list', organization_pk=self.get_organization().pk)
            
            feedback_id_list = [fid.strip() for fid in feedback_ids.split(',') if fid.strip()]
            
            # Get form data
            analysis_type = form.cleaned_data['analysis_type']
            target_language = form.cleaned_data['target_language']
            translate_content = form.cleaned_data['translate_content']
            overwrite_existing = form.cleaned_data['overwrite_existing']
            
            # Set analysis configuration based on type
            analysis_config = {
                'detect_aspects': form.cleaned_data['detect_aspects'],
                'detect_emotions': form.cleaned_data['detect_emotions'],
                'detect_intent': form.cleaned_data['detect_intent'],
                'extract_key_phrases': form.cleaned_data['extract_key_phrases'],
                'target_language': target_language
            }
            
            # Get feedback items to analyze
            feedbacks = Feedback.objects.filter(
                organization=self.get_organization(),
                id__in=feedback_id_list
            )
            
            if not overwrite_existing:
                feedbacks = feedbacks.filter(ai_analyzed=False)
            
            total_to_analyze = feedbacks.count()
            
            if total_to_analyze == 0:
                messages.warning(self.request, _('No feedback items to analyze.'))
                return redirect('cx_analytics:sentiment-list', organization_pk=self.get_organization().pk)
            
            # Start bulk analysis
            success_count = self._start_bulk_analysis(
                feedbacks, 
                analysis_config, 
                target_language, 
                translate_content
            )
            
            if success_count > 0:
                messages.success(
                    self.request,
                    _('Bulk analysis completed. Successfully analyzed %(success)s out of %(count)s feedback items.') % {
                        'count': total_to_analyze,
                        'success': success_count
                    }
                )
            else:
                messages.error(
                    self.request,
                    _('Bulk analysis failed for all selected feedback items.')
                )
            
            logger.info(
                f'Bulk sentiment analysis completed for {success_count}/{total_to_analyze} feedback items '
                f'in language: {target_language}'
            )
            
        except Exception as e:
            logger.error(f'Error starting bulk sentiment analysis: {str(e)}', exc_info=True)
            messages.error(
                self.request,
                _('An error occurred while starting bulk analysis. Please try again.')
            )
        
        return redirect('cx_analytics:sentiment-list', organization_pk=self.get_organization().pk)
    
    def _start_bulk_analysis(self, feedbacks, analysis_config, target_language, translate_content):
        """
        Start bulk analysis process
        """
        from django.utils import timezone
        analyzer = GeminiSentimentAnalyzer()
        translator = TranslationService()
        success_count = 0
        
        for feedback in feedbacks:
            try:
                # Prepare content for analysis
                content_to_analyze = feedback.content
                analysis_language = feedback.original_language
                translated_content = None
                
                # Translate content if requested
                if translate_content and target_language != feedback.original_language:
                    try:
                        if translator.is_configured():
                            translated_content = translator.translate_text(
                                feedback.content,
                                source_language=feedback.original_language or 'auto',
                                target_language=target_language
                            )
                            content_to_analyze = translated_content
                            analysis_language = target_language
                    except Exception as e:
                        logger.warning(f"Translation failed for feedback {feedback.feedback_id}: {str(e)}")
                        # Continue with original content if translation fails
                
                # Analyze feedback
                analysis_result = analyzer.analyze_feedback(
                    content_to_analyze,
                    analysis_language,
                    analysis_config
                )
                
                # Map sentiment labels
                sentiment_label_map = {
                    'very_negative': 'very_negative',
                    'negative': 'negative',
                    'neutral': 'neutral',
                    'positive': 'positive',
                    'very_positive': 'very_positive'
                }
                
                overall_label = analysis_result['overall_sentiment']['label']
                mapped_label = sentiment_label_map.get(overall_label, 'neutral')
                
                # Get intent data safely
                intent_data = analysis_result.get('intent', {})
                intent_type = intent_data.get('type') if isinstance(intent_data, dict) else None
                intent_confidence = intent_data.get('confidence') if isinstance(intent_data, dict) else None
                
                # Get urgency data safely
                urgency_data = analysis_result.get('urgency', {})
                urgency_level = urgency_data.get('level', 'medium').lower() if isinstance(urgency_data, dict) else 'medium'
                urgency_indicators = urgency_data.get('indicators', []) if isinstance(urgency_data, dict) else []
                
                # Create or update sentiment analysis - INCLUDING ORGANIZATION
                SentimentAnalysis.objects.update_or_create(
                    feedback=feedback,
                    defaults={
                        'organization': feedback.organization,  # CRITICAL: Add this line
                        'overall_score': analysis_result['overall_sentiment']['score'],
                        'overall_label': mapped_label,
                        'confidence_score': analysis_result['overall_sentiment']['confidence'],
                        'aspects': analysis_result.get('aspect_sentiments', {}),
                        'emotions': analysis_result.get('emotions', {}),
                        'intent': intent_type,
                        'intent_confidence': intent_confidence,
                        'urgency_level': urgency_level,
                        'urgency_indicators': urgency_indicators,
                        'key_phrases': analysis_result.get('key_phrases', []),
                        'entities': analysis_result.get('entities', {}),
                        'model_used': analysis_result.get('analysis_metadata', {}).get('model_used', 'gemini-1.5-flash'),
                        'model_version': analysis_result.get('analysis_metadata', {}).get('model_version', '1.0'),
                        'analysis_metadata': analysis_result.get('analysis_metadata', {}),
                        'analysis_language': target_language,
                        'translated_content': translated_content,
                        'original_language': feedback.original_language
                    }
                )
                
                # Update feedback
                feedback.ai_analyzed = True
                feedback.ai_analysis_date = timezone.now()
                feedback.sentiment_score = analysis_result['overall_sentiment']['score']
                feedback.sentiment_label = mapped_label
                feedback.requires_human_review = self._needs_human_review(analysis_result)
                feedback.save()
                
                success_count += 1
                logger.debug(f"Successfully analyzed feedback {feedback.feedback_id}")
                
            except Exception as e:
                logger.error(f"Failed to analyze feedback {feedback.feedback_id}: {str(e)}")
                continue
        
        return success_count
    
    def _needs_human_review(self, analysis_result):
        """Determine if analysis requires human review"""
        try:
            if analysis_result['overall_sentiment']['confidence'] < 0.5:
                return True
            
            sentiment_score = analysis_result['overall_sentiment']['score']
            if -0.3 <= sentiment_score <= 0.3:
                return True
            
            urgency_data = analysis_result.get('urgency', {})
            if isinstance(urgency_data, dict) and urgency_data.get('level') == 'critical':
                return True
            
            return False
        except (KeyError, TypeError):
            return True
        
class BulkSentimentAnalysisView1(SentimentAnalysisMixin, FormView):
    """
    Perform bulk sentiment analysis on multiple feedbacks
    """
    template_name = 'sentiment_analysis/bulk-sentiment-analysis.html'
    form_class = BulkSentimentAnalysisForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        feedback_ids = self.request.GET.get('ids', '')
        
        if not feedback_ids:
            messages.warning(self.request, _('No feedback items selected for analysis.'))
            return context
        
        feedback_id_list = [fid.strip() for fid in feedback_ids.split(',') if fid.strip()]
        
        # Get selected feedback items
        selected_feedbacks = Feedback.objects.filter(
            organization=self.get_organization(),
            id__in=feedback_id_list
        ).select_related('customer')[:50]  # Limit to 50 items for performance
        
        context.update({
            'selected_feedbacks': selected_feedbacks,
            'page_title': _('Bulk Sentiment Analysis'),
            'total_selected': selected_feedbacks.count(),
            'feedback_ids': feedback_ids,
            'LANGUAGE_CHOICES': [
                ('en', 'English'),
                ('es', 'Spanish'),
                ('fr', 'French'),
                ('de', 'German'),
                ('it', 'Italian'),
                ('pt', 'Portuguese'),
                ('ja', 'Japanese'),
                ('ko', 'Korean'),
                ('zh', 'Chinese'),
                ('ar', 'Arabic'),
                ('hi', 'Hindi'),
            ]
        })
        
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['feedback_ids'] = self.request.GET.get('ids', '')
        return kwargs

    def form_valid(self, form):
        try:
            feedback_ids = form.cleaned_data['feedback_ids']
            target_language = form.cleaned_data['target_language']
            translate_content = form.cleaned_data['translate_content']
            analysis_config = {
                'detect_aspects': form.cleaned_data['detect_aspects'],
                'detect_emotions': form.cleaned_data['detect_emotions'],
                'detect_intent': form.cleaned_data['detect_intent'],
                'extract_key_phrases': form.cleaned_data['extract_key_phrases'],
                'target_language': target_language
            }
            overwrite_existing = form.cleaned_data['overwrite_existing']
            
            if not feedback_ids:
                messages.warning(self.request, _('No feedback items selected for analysis.'))
                return redirect('cx_analysis:sentiment-list', organization_pk=self.get_organization().pk)
            
            feedback_id_list = [fid.strip() for fid in feedback_ids.split(',') if fid.strip()]
            
            # Get feedback items to analyze
            feedbacks = Feedback.objects.filter(
                organization=self.get_organization(),
                id__in=feedback_id_list
            )
            
            if not overwrite_existing:
                feedbacks = feedbacks.filter(ai_analyzed=False)
            
            total_to_analyze = feedbacks.count()
            
            if total_to_analyze == 0:
                messages.warning(self.request, _('No feedback items to analyze.'))
                return redirect('cx_analysis:sentiment-list', organization_pk=self.get_organization().pk)
            
            # Start bulk analysis
            success_count = self._start_bulk_analysis(
                feedbacks, 
                analysis_config, 
                target_language, 
                translate_content
            )
            
            if success_count > 0:
                messages.success(
                    self.request,
                    _('Bulk analysis completed. Successfully analyzed %(success)s out of %(count)s feedback items.') % {
                        'count': total_to_analyze,
                        'success': success_count
                    }
                )
            else:
                messages.error(
                    self.request,
                    _('Bulk analysis failed for all selected feedback items.')
                )
            
            logger.info(
                f'Bulk sentiment analysis completed for {success_count}/{total_to_analyze} feedback items '
                f'in language: {target_language}'
            )
            
        except Exception as e:
            logger.error(f'Error starting bulk sentiment analysis: {str(e)}', exc_info=True)
            messages.error(
                self.request,
                _('An error occurred while starting bulk analysis. Please try again.')
            )
        
        return redirect('cx_analysis:sentiment-list', organization_pk=self.get_organization().pk)
    
    def _start_bulk_analysis(self, feedbacks, analysis_config, target_language, translate_content):
        """
        Start bulk analysis process
        """
        analyzer = GeminiSentimentAnalyzer()
        translator = TranslationService()
        success_count = 0
        
        for feedback in feedbacks:
            try:
                # Prepare content for analysis
                content_to_analyze = feedback.content
                analysis_language = feedback.original_language
                translated_content = None
                
                # Translate content if requested
                if translate_content and target_language != feedback.original_language:
                    try:
                        if translator.is_configured():
                            translated_content = translator.translate_text(
                                feedback.content,
                                source_language=feedback.original_language,
                                target_language=target_language
                            )
                            content_to_analyze = translated_content
                            analysis_language = target_language
                    except Exception as e:
                        logger.warning(f"Translation failed for feedback {feedback.feedback_id}: {str(e)}")
                        # Continue with original content if translation fails
                
                # Analyze feedback
                analysis_result = analyzer.analyze_feedback(
                    content_to_analyze,
                    analysis_language,
                    analysis_config
                )
                
                # Map sentiment labels
                sentiment_label_map = {
                    'very_negative': 'very_negative',
                    'negative': 'negative',
                    'neutral': 'neutral',
                    'positive': 'positive',
                    'very_positive': 'very_positive'
                }
                
                overall_label = analysis_result['overall_sentiment']['label']
                mapped_label = sentiment_label_map.get(overall_label, 'neutral')
                
                # Get intent data safely
                intent_data = analysis_result.get('intent', {})
                intent_type = intent_data.get('type') if isinstance(intent_data, dict) else None
                intent_confidence = intent_data.get('confidence') if isinstance(intent_data, dict) else None
                
                # Get urgency data safely
                urgency_data = analysis_result.get('urgency', {})
                urgency_level = urgency_data.get('level', 'medium').lower() if isinstance(urgency_data, dict) else 'medium'
                urgency_indicators = urgency_data.get('indicators', []) if isinstance(urgency_data, dict) else []
                
                # Create or update sentiment analysis - INCLUDING ORGANIZATION
                SentimentAnalysis.objects.update_or_create(
                    feedback=feedback,
                    defaults={
                        'organization': feedback.organization,  # CRITICAL: Add this line
                        'overall_score': analysis_result['overall_sentiment']['score'],
                        'overall_label': mapped_label,
                        'confidence_score': analysis_result['overall_sentiment']['confidence'],
                        'aspects': analysis_result.get('aspect_sentiments', {}),
                        'emotions': analysis_result.get('emotions', {}),
                        'intent': intent_type,
                        'intent_confidence': intent_confidence,
                        'urgency_level': urgency_level,
                        'urgency_indicators': urgency_indicators,
                        'key_phrases': analysis_result.get('key_phrases', []),
                        'entities': analysis_result.get('entities', {}),
                        'model_used': analysis_result.get('analysis_metadata', {}).get('model_used', 'gemini-1.5-flash'),
                        'model_version': analysis_result.get('analysis_metadata', {}).get('model_version', '1.0'),
                        'analysis_metadata': analysis_result.get('analysis_metadata', {}),
                        'analysis_language': target_language,
                        'translated_content': translated_content,
                        'original_language': feedback.original_language
                    }
                )
                
                # Update feedback
                feedback.ai_analyzed = True
                feedback.ai_analysis_date = timezone.now()
                feedback.sentiment_score = analysis_result['overall_sentiment']['score']
                feedback.sentiment_label = mapped_label
                feedback.requires_human_review = self._needs_human_review(analysis_result)
                feedback.save()
                
                success_count += 1
                logger.debug(f"Successfully analyzed feedback {feedback.feedback_id}")
                
            except Exception as e:
                logger.error(f"Failed to analyze feedback {feedback.feedback_id}: {str(e)}")
                continue
        
        return success_count
    
    def _needs_human_review(self, analysis_result):
        """Determine if analysis requires human review"""
        try:
            if analysis_result['overall_sentiment']['confidence'] < 0.5:
                return True
            
            sentiment_score = analysis_result['overall_sentiment']['score']
            if -0.3 <= sentiment_score <= 0.3:
                return True
            
            urgency_data = analysis_result.get('urgency', {})
            if isinstance(urgency_data, dict) and urgency_data.get('level') == 'critical':
                return True
            
            return False
        except (KeyError, TypeError):
            return True

class BulkActionsView(SentimentAnalysisMixin, View):
    """
    Handle bulk actions from the sentiment list page
    """
    
    def post(self, request, *args, **kwargs):
        organization = self.get_organization()
        action = request.POST.get('action')
        selected_ids = request.POST.get('selected_ids', '')
        
        if not selected_ids:
            messages.warning(request, _('No feedback items selected.'))
            return redirect('cx_analytics:sentiment-list', organization_pk=organization.pk)
        
        feedback_id_list = [fid.strip() for fid in selected_ids.split(',') if fid.strip()]
        
        # Get selected feedbacks
        feedbacks = Feedback.objects.filter(
            organization=organization,
            id__in=feedback_id_list
        )
        
        if action == 'bulk_mark_reviewed':
            # Mark feedbacks as reviewed
            updated_count = feedbacks.update(requires_human_review=False)
            messages.success(
                request, 
                _('Marked %(count)s feedback items as reviewed.') % {'count': updated_count}
            )
            
        elif action == 'bulk_delete_analysis':
            # Delete sentiment analysis for selected feedbacks
            deleted_count = 0
            for feedback in feedbacks:
                try:
                    # Delete related sentiment analysis if exists
                    SentimentAnalysis.objects.filter(feedback=feedback).delete()
                    # Reset feedback analysis fields
                    feedback.ai_analyzed = False
                    feedback.ai_analysis_date = None
                    feedback.sentiment_score = None
                    feedback.sentiment_label = None
                    feedback.requires_human_review = False
                    feedback.save()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting analysis for feedback {feedback.id}: {str(e)}")
            
            messages.success(
                request, 
                _('Deleted analysis for %(count)s feedback items.') % {'count': deleted_count}
            )
            
        else:
            messages.warning(request, _('Unknown action selected.'))
        
        return redirect('cx_analytics:sentiment-list', organization_pk=organization.pk)
    
class TranslateFeedbackView(SentimentAnalysisMixin, View):
    """
    Translate feedback content to another language
    """
    def post(self, request, *args, **kwargs):
        organization = self.get_organization()
        feedback_id = kwargs.get('feedback_pk')  # Get from URL parameter
        target_language = request.POST.get('target_language', 'en')
        
        # Use feedback_id from URL parameter instead of POST data
        # You can still keep POST as fallback for compatibility
        if not feedback_id:
            feedback_id = request.POST.get('feedback_id')
        
        if not feedback_id:
            return JsonResponse({
                'success': False,
                'message': _('No feedback item selected.')
            }, status=400)
        
        try:
            # Now we can get feedback using both organization and feedback_id
            feedback = get_object_or_404(
                Feedback, 
                id=feedback_id, 
                organization=organization
            )
            
            translator = TranslationService()
            
            # Check if translation service is configured
            if not translator.is_configured():
                return JsonResponse({
                    'success': False,
                    'message': _('Translation service is not configured. Please check your API key.')
                }, status=503)
            
            # Check if content exists
            if not feedback.content:
                return JsonResponse({
                    'success': False,
                    'message': _('Feedback content is empty.')
                }, status=400)
            
            # Translate content
            translated_content = translator.translate_text(
                feedback.content,
                source_language=feedback.original_language or 'auto',
                target_language=target_language
            )
            
            # Update the feedback with translated content
            feedback.translated_content = translated_content
            feedback.save()
            
            # Also update sentiment analysis if it exists
            try:
                sentiment_analysis = SentimentAnalysis.objects.get(feedback=feedback)
                sentiment_analysis.translated_content = translated_content
                sentiment_analysis.analysis_language = target_language
                sentiment_analysis.save()
            except SentimentAnalysis.DoesNotExist:
                pass  # No sentiment analysis yet, that's fine
            
            # Get language name for display
            language_name = target_language.upper()
            supported_languages = dict(translator.get_supported_languages())
            if target_language in supported_languages:
                language_name = supported_languages[target_language]
            
            return JsonResponse({
                'success': True,
                'message': _('Translation completed successfully.'),
                'translated_content': translated_content,
                'target_language': target_language,
                'language_name': language_name
            })
                
        except ValueError as e:
            logger.error(f"Value error translating feedback {feedback_id}: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': _(f'Translation failed: {str(e)}'),
                'error': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error translating feedback {feedback_id}: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': _('Translation failed. Please try again.'),
                'error': str(e)
            }, status=500)
              
    
class SentimentAnalysisDashboardView(SentimentAnalysisMixin, TemplateView):
    """
    Dashboard for sentiment analysis insights
    """
    template_name = 'sentiment_analysis/sentiment-dashboard.html'

    def get_sentiment_color(self, label):
        """Convert sentiment label to Bootstrap color"""
        color_map = {
            'POSITIVE': 'success',
            'NEGATIVE': 'danger',
            'NEUTRAL': 'secondary',
            'MIXED': 'warning',
        }
        return color_map.get(label, 'secondary')

    def get_sentiment_icon(self, label):
        """Convert sentiment label to icon class"""
        icon_map = {
            'POSITIVE': 'fa-smile',
            'NEGATIVE': 'fa-frown',
            'NEUTRAL': 'fa-meh',
            'MIXED': 'fa-comments',
        }
        return icon_map.get(label, 'fa-comment')

    def get_urgency_color(self, level):
        """Convert urgency level to color"""
        color_map = {
            'HIGH': 'danger',
            'MEDIUM': 'warning',
            'LOW': 'success',
            'NONE': 'secondary',
        }
        return color_map.get(level, 'secondary')

    def get_urgency_text(self, level):
        """Convert urgency level to display text"""
        text_map = {
            'HIGH': 'High Urgency',
            'MEDIUM': 'Medium Urgency',
            'LOW': 'Low Urgency',
            'NONE': 'No Urgency',
        }
        return text_map.get(level, 'Unknown')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        
        # Get sentiment statistics
        sentiment_stats_raw = SentimentAnalysis.objects.filter(
            feedback__organization=organization
        ).values('overall_label').annotate(
            count=Count('id'),
            avg_confidence=Avg('confidence_score'),
            avg_score=Avg('overall_score')
        ).order_by('overall_label')
        
        # Process sentiment stats with display properties
        sentiment_stats = []
        total_sentiment_count = 0
        
        for stat in sentiment_stats_raw:
            processed_stat = {
                'label': stat['overall_label'],
                'count': stat['count'],
                'avg_confidence': stat['avg_confidence'] or 0,
                'avg_score': stat['avg_score'] or 0,
                'color': self.get_sentiment_color(stat['overall_label']),
                'icon': self.get_sentiment_icon(stat['overall_label']),
                'percentage': 0  # Will calculate below
            }
            sentiment_stats.append(processed_stat)
            total_sentiment_count += stat['count']
        
        # Calculate percentages
        for stat in sentiment_stats:
            if total_sentiment_count > 0:
                stat['percentage'] = (stat['count'] / total_sentiment_count) * 100
        
        # Get analysis coverage
        total_feedbacks = Feedback.objects.filter(organization=organization).count()
        analyzed_feedbacks = Feedback.objects.filter(
            organization=organization, ai_analyzed=True
        ).count()
        
        # Calculate coverage percentage and color
        coverage_percentage = (analyzed_feedbacks / total_feedbacks * 100) if total_feedbacks > 0 else 0
        coverage_color = 'success' if coverage_percentage >= 80 else 'warning' if coverage_percentage >= 50 else 'danger'
        
        # Get urgency distribution with processed data
        urgency_stats_raw = SentimentAnalysis.objects.filter(
            feedback__organization=organization
        ).values('urgency_level').annotate(count=Count('id'))
        
        urgency_stats = []
        for stat in urgency_stats_raw:
            urgency_stats.append({
                'level': stat['urgency_level'],
                'count': stat['count'],
                'color': self.get_urgency_color(stat['urgency_level']),
                'text': self.get_urgency_text(stat['urgency_level'])
            })
        
        # Get intent distribution
        intent_stats = SentimentAnalysis.objects.filter(
            feedback__organization=organization
        ).exclude(intent__isnull=True).values('intent').annotate(count=Count('id')).order_by('-count')[:10]  # Top 10 intents
        
        # Get recent analyses for detailed display
        recent_analyses = SentimentAnalysis.objects.filter(
            feedback__organization=organization
        ).select_related('feedback').order_by('-created_at')[:10]
        
        # Process recent analyses with display properties
        processed_recent_analyses = []
        for analysis in recent_analyses:
            processed_recent_analyses.append({
                'analysis': analysis,
                'sentiment_color': self.get_sentiment_color(analysis.overall_label),
                'sentiment_icon': self.get_sentiment_icon(analysis.overall_label),
                'urgency_color': self.get_urgency_color(analysis.urgency_level),
                'urgency_text': self.get_urgency_text(analysis.urgency_level),
                'confidence_color': 'success' if analysis.confidence_score > 0.8 else 'warning' if analysis.confidence_score > 0.6 else 'danger'
            })
        
        # Calculate overall sentiment summary
        overall_sentiment = 'NEUTRAL'
        if sentiment_stats:
            positive_stat = next((s for s in sentiment_stats if s['label'] == 'POSITIVE'), None)
            negative_stat = next((s for s in sentiment_stats if s['label'] == 'NEGATIVE'), None)
            
            if positive_stat and negative_stat:
                if positive_stat['count'] > negative_stat['count']:
                    overall_sentiment = 'POSITIVE'
                elif negative_stat['count'] > positive_stat['count']:
                    overall_sentiment = 'NEGATIVE'
        
        context.update({
            'page_title': _('Sentiment Analysis Dashboard'),
            'sentiment_stats': sentiment_stats,
            'urgency_stats': urgency_stats,
            'intent_stats': intent_stats,
            'total_feedbacks': total_feedbacks,
            'analyzed_feedbacks': analyzed_feedbacks,
            'analysis_coverage': coverage_percentage,
            'coverage_color': coverage_color,
            'needs_review': Feedback.objects.filter(
                organization=organization,
                requires_human_review=True
            ).count(),
            'recent_analyses': processed_recent_analyses,
            'overall_sentiment': overall_sentiment,
            'overall_sentiment_color': self.get_sentiment_color(overall_sentiment),
            'overall_sentiment_icon': self.get_sentiment_icon(overall_sentiment),
            'total_sentiment_analyses': total_sentiment_count,
        })
        
        return context
    


# Create your views here.
