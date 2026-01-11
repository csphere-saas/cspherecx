# tasks.py
from celery import shared_task
import logging
from django.db import transaction
from core.models import SurveyResponse

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def analyze_survey_response_sentiment(self, response_id):
    """
    Celery task to analyze survey response sentiment
    """
    try:
        with transaction.atomic():
            response = SurveyResponse.objects.select_for_update().get(id=response_id)
            
            # Skip if already analyzed
            if response.ai_analyzed:
                logger.info(f"Survey response {response_id} already analyzed")
                return
            
            # Perform analysis
            success = response.analyze_sentiment_sync()
            
            if success:
                logger.info(f"Successfully analyzed sentiment for response {response_id}")
                
                # Trigger follow-up actions
                response.trigger_followup_actions()
                
            else:
                # Retry if failed
                if response.analysis_retry_count < 3:
                    logger.warning(f"Analysis failed for response {response_id}, retrying...")
                    raise self.retry(countdown=60 * (2 ** response.analysis_retry_count))
                else:
                    logger.error(f"Analysis failed for response {response_id} after 3 retries")
                    
    except SurveyResponse.DoesNotExist:
        logger.error(f"Survey response {response_id} not found")
    except Exception as e:
        logger.error(f"Error in sentiment analysis task: {str(e)}", exc_info=True)
        raise self.retry(countdown=300)  # Retry after 5 minutes
    

# surveys/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import NPSResponse
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def analyze_nps_sentiment(self, nps_response_id):
    """
    Async task to analyze NPS response sentiment
    """
    try:
        nps_response = NPSResponse.objects.get(id=nps_response_id)
        
        # Skip if already analyzed
        if nps_response.ai_analyzed:
            return True
        
        nps_response.analysis_status = 'processing'
        nps_response.save(update_fields=['analysis_status'])
        
        # Extract text for analysis
        text_to_analyze = []
        if nps_response.reason:
            text_to_analyze.append(nps_response.reason)
        
        if nps_response.follow_up_question_responses:
            for response in nps_response.follow_up_question_responses.values():
                if isinstance(response, str) and len(response.strip()) > 5:
                    text_to_analyze.append(response)
        
        if not text_to_analyze:
            nps_response.ai_analyzed = True
            nps_response.analysis_status = 'completed'
            nps_response.sentiment_metadata = {'skipped': 'no_text_content'}
            nps_response.save()
            return True
        
        # Call sentiment analysis service
        from surveys.services.ai_sentiment_service import SurveySentimentAnalyzer
        analyzer = SurveySentimentAnalyzer()
        
        organization_context = {
            'organization_name': nps_response.organization.name,
            'industry': nps_response.organization.industry or 'general',
        }
        
        # Analyze sentiment
        result = analyzer.extract_sentiment_from_response(
            {'nps_feedback': ' '.join(text_to_analyze)},
            organization_context
        )
        
        # Update response
        nps_response.sentiment_score = result.get('overall_sentiment_score', 0.0)
        nps_response.key_themes = result.get('key_themes', [])
        nps_response.ai_analyzed = True
        nps_response.analysis_status = 'completed'
        nps_response.sentiment_metadata = result
        nps_response.save()
        
        logger.info(f"Successfully analyzed NPS response {nps_response_id}")
        return True
        
    except Exception as exc:
        logger.error(f"Error analyzing NPS response {nps_response_id}: {str(exc)}")
        
        # Update response status
        try:
            nps_response = NPSResponse.objects.get(id=nps_response_id)
            nps_response.analysis_status = 'failed'
            nps_response.analysis_retry_count += 1
            nps_response.save()
        except:
            pass
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))