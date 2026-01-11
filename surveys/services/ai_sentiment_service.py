# services/ai_sentiment_service.py
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Try to import Gemini, but handle if not available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("google.generativeai not installed. Sentiment analysis will be disabled.")
    genai = None
    GEMINI_AVAILABLE = False

class SurveySentimentAnalyzer:
    """
    Service for analyzing survey responses using Gemini AI
    """
    
    def __init__(self):
        """Initialize Gemini client"""
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        
        if not GEMINI_AVAILABLE:
            logger.warning("Gemini library not available. Sentiment analysis will be disabled.")
            self.client = None
        elif not self.api_key:
            logger.warning("GEMINI_API_KEY not configured. Sentiment analysis will be disabled.")
            self.client = None
        else:
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {str(e)}")
                self.client = None
    
    def extract_sentiment_from_response(self, survey_response: Dict[str, Any], 
                                      organization_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract sentiment and insights from survey response data
        """
        if not self.client:
            logger.warning("Gemini client not available. Skipping sentiment analysis.")
            return self._get_default_sentiment_data()
        
        try:
            # Prepare the prompt with context
            prompt = self._build_analysis_prompt(survey_response, organization_context)
            
            # Check if we have any text to analyze
            if not self._has_meaningful_text(survey_response):
                logger.info("No meaningful text found for sentiment analysis")
                result = self._get_default_sentiment_data()
                result['analysis_note'] = 'no_meaningful_text'
                return result
            
            # Configure the model
            model = genai.GenerativeModel('gemini-2.5-flash')  # Updated to latest stable version
            
            # Generate response
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.1,
                    'top_p': 0.95,
                    'top_k': 40,
                    #'max_output_tokens': 1024,
                }
            )
            
            # Parse the response
            analysis_result = self._parse_ai_response(response.text)
            
            # Add metadata
            analysis_result.update({
                'analysis_timestamp': timezone.now().isoformat(),
                'model_used': 'gemini-2.5-flash',
                'confidence_score': self._calculate_confidence(analysis_result),
            })
            
            logger.info(f"Successfully analyzed sentiment")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}", exc_info=True)
            result = self._get_default_sentiment_data()
            result['analysis_error'] = True
            result['error_message'] = str(e)
            return result
    
    def _has_meaningful_text(self, survey_response: Dict[str, Any]) -> bool:
        """Check if response contains meaningful text for analysis"""
        if not survey_response:
            return False
        
        total_text_length = 0
        for answer in survey_response.values():
            if isinstance(answer, str) and answer.strip():
                total_text_length += len(answer.strip())
        
        # Require at least 20 characters of meaningful text
        return total_text_length >= 20
    
    def _build_analysis_prompt(self, survey_response: Dict[str, Any], 
                             organization_context: Dict[str, Any]) -> str:
        """
        Build a comprehensive prompt for sentiment analysis
        """
        # Extract textual responses
        text_responses = []
        for question_id, answer in survey_response.items():
            if isinstance(answer, str) and answer.strip():
                # Only include substantial text responses
                if len(answer.strip()) > 5:  # Reduced minimum length
                    # Clean question ID for readability
                    clean_question_id = str(question_id).replace('_', ' ').title()
                    text_responses.append(f"Question: {clean_question_id}\nAnswer: {answer}")
        
        # Combine all text for analysis
        combined_text = "\n\n".join(text_responses) if text_responses else "No textual responses provided."
        
        prompt = f"""
        Analyze the following survey responses and provide a comprehensive sentiment analysis.
        
        ORGANIZATION CONTEXT:
        - Industry: {organization_context.get('industry', 'Not specified')}
        - Organization: {organization_context.get('organization_name', 'Not specified')}
        - Survey Type: {organization_context.get('survey_type', 'General')}
        
        SURVEY RESPONSES:
        {combined_text}
        
        Please analyze and provide the following in JSON format:
        
        1. overall_sentiment_score: A float between -1.0 (very negative) and 1.0 (very positive)
        2. sentiment_label: One of ['very_negative', 'negative', 'neutral', 'positive', 'very_positive']
        3. key_themes: List of main topics mentioned (max 5)
        4. detected_emotions: Object with emotion names and confidence scores (0-1)
        5. urgency_level: One of ['low', 'medium', 'high', 'critical'] based on response content
        6. actionable_feedback: Boolean indicating if feedback contains actionable suggestions
        7. primary_intent: What the respondent is trying to achieve (e.g., complain, suggest, praise)
        8. key_phrases: List of important phrases extracted
        9. sentiment_by_aspect: Object with sentiment scores for different aspects mentioned
        10. summary: Brief summary of the feedback (max 100 words)
        
        Focus on understanding:
        - Overall satisfaction level
        - Specific pain points or praise
        - Areas needing improvement
        - Urgency of issues mentioned
        - Emotional tone of responses
        
        Return ONLY valid JSON, no additional text or markdown formatting.
        
        JSON Response:
        """
        
        return prompt
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into structured data"""
        try:
            # Clean the response - remove markdown code blocks if present
            cleaned_response = ai_response.strip()
            
            # Remove markdown code blocks
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            # Find JSON start and end
            start_idx = cleaned_response.find('{')
            end_idx = cleaned_response.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                logger.error(f"No JSON object found in response: {cleaned_response[:200]}...")
                return self._get_default_sentiment_data()
            
            json_str = cleaned_response[start_idx:end_idx + 1]
            
            # Parse JSON
            result = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['overall_sentiment_score', 'sentiment_label']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"Missing required field in AI response: {field}")
                    result[field] = 0.0 if field == 'overall_sentiment_score' else 'neutral'
            
            # Validate sentiment score range
            score = result.get('overall_sentiment_score', 0)
            if not isinstance(score, (int, float)) or not -1.0 <= score <= 1.0:
                logger.warning(f"Invalid sentiment score: {score}")
                result['overall_sentiment_score'] = 0.0
            
            # Ensure key_themes is a list
            if 'key_themes' in result and not isinstance(result['key_themes'], list):
                result['key_themes'] = []
            
            # Ensure sentiment_by_aspect is a dict
            if 'sentiment_by_aspect' in result and not isinstance(result['sentiment_by_aspect'], dict):
                result['sentiment_by_aspect'] = {}
            
            # Ensure detected_emotions is a dict
            if 'detected_emotions' in result and not isinstance(result['detected_emotions'], dict):
                result['detected_emotions'] = {}
            
            # Ensure key_phrases is a list
            if 'key_phrases' in result and not isinstance(result['key_phrases'], list):
                result['key_phrases'] = []
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            logger.debug(f"Raw AI response: {ai_response[:500]}")
            return self._get_default_sentiment_data()
        except Exception as e:
            logger.error(f"Unexpected error parsing AI response: {str(e)}")
            return self._get_default_sentiment_data()
    
    def _calculate_confidence(self, analysis_result: Dict[str, Any]) -> float:
        """Calculate confidence score based on analysis completeness"""
        confidence = 0.85  # Base confidence
        
        # Adjust based on available data
        if analysis_result.get('key_themes'):
            confidence += 0.05
        
        if analysis_result.get('detected_emotions'):
            confidence += 0.05
        
        if analysis_result.get('sentiment_by_aspect'):
            confidence += 0.05
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _get_default_sentiment_data(self) -> Dict[str, Any]:
        """Return default sentiment data when analysis fails"""
        return {
            'overall_sentiment_score': 0.0,
            'sentiment_label': 'neutral',
            'key_themes': [],
            'detected_emotions': {},
            'urgency_level': 'low',
            'actionable_feedback': False,
            'primary_intent': 'general_feedback',
            'key_phrases': [],
            'sentiment_by_aspect': {},
            'summary': 'Unable to analyze sentiment.',
            'analysis_timestamp': timezone.now().isoformat(),
            'model_used': 'none',
            'confidence_score': 0.0,
            'analysis_error': False,
        }