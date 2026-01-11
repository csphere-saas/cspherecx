import logging
import json
import re
import os
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from django.conf import settings
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class GeminiSentimentAnalyzer:
    """
    Service class for analyzing feedback using Google's Gemini AI
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not self.api_key:
            self.api_key = os.getenv('GEMINI_API_KEY')
            
        self.model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')
        self.model = None
        self.configure_client()
    
    def configure_client(self):
        """Configure the Gemini AI client"""
        try:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not found in settings or environment variables")
                
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini AI client configured with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to configure Gemini AI client: {str(e)}")
            raise
    
    def analyze_feedback(self, feedback_content: str, language: str = 'en', 
                        analysis_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze feedback content using Gemini AI
        
        Args:
            feedback_content: The feedback text to analyze
            language: The language of the feedback
            analysis_config: Configuration for analysis depth
        
        Returns:
            Dictionary containing analysis results
        """
        if analysis_config is None:
            analysis_config = {
                'detect_aspects': True,
                'detect_emotions': True,
                'detect_intent': True,
                'extract_key_phrases': True,
                'target_language': 'en'
            }
        
        try:
            # Validate input
            if not feedback_content or not feedback_content.strip():
                raise ValueError("Feedback content cannot be empty")
            
            if self.model is None:
                self.configure_client()
            
            # Construct the analysis prompt
            prompt = self._construct_analysis_prompt(feedback_content, language, analysis_config)
            
            # Generate analysis with safety settings
            generation_config = {
                'temperature': 0.1,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 32768,
            }
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Check if response was blocked
            if not response.text:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    raise ValueError(f"Response blocked due to: {response.prompt_feedback.block_reason}")
                else:
                    raise ValueError("Empty response from Gemini AI")
            
            # Parse the response
            analysis_result = self._parse_analysis_response(response.text, analysis_config)
            
            # Add metadata
            analysis_result['analysis_metadata'] = {
                'model_used': self.model_name,
                'model_version': '1.0',
                'language_detected': language,
                'analysis_config': analysis_config,
                'feedback_length': len(feedback_content),
                'target_language': analysis_config.get('target_language', 'en')
            }
            
            logger.info(f"Successfully analyzed feedback with Gemini AI in language: {language}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing feedback with Gemini AI: {str(e)}")
            raise
    
    def _construct_analysis_prompt(self, content: str, language: str, 
                                 analysis_config: Dict[str, Any]) -> str:
        """Construct the analysis prompt for Gemini AI"""
        
        target_language = analysis_config.get('target_language', 'en')
        
        prompt = f"""You are a sentiment analysis expert. Analyze this customer feedback and return ONLY a valid JSON object.

FEEDBACK (Language: {language}):
{content}

ANALYSIS REQUIREMENTS:
1. Overall sentiment: Provide score (-1.0 to 1.0), label (very_negative, negative, neutral, positive, very_positive), and confidence (0.0 to 1.0)
2. Aspect sentiments: Analyze product, service, price, usability, support with scores and mention counts
3. Emotions: Detect anger, joy, sadness, fear, surprise, trust with scores (0.0 to 1.0)
4. Intent: Classify as complaint, compliment, suggestion, question, or request with confidence
5. Urgency: Level (low, medium, high, critical) with indicators
6. Key phrases: Extract 3-5 most important phrases
7. Entities: Identify products, features, issues mentioned

IMPORTANT: Return ONLY valid JSON with this exact structure:

{{
    "overall_sentiment": {{"score": -0.85, "label": "very_negative", "confidence": 0.92}},
    "aspect_sentiments": {{"product": {{"score": -0.7, "mentions": 2}}, "service": {{"score": -0.9, "mentions": 3}}}},
    "emotions": {{"anger": 0.8, "joy": 0.1, "sadness": 0.6, "fear": 0.2, "surprise": 0.1, "trust": 0.3}},
    "intent": {{"type": "complaint", "confidence": 0.88}},
    "urgency": {{"level": "high", "indicators": ["urgent language", "multiple issues"]}},
    "key_phrases": ["broken feature", "poor service"],
    "entities": {{"products": ["mobile app"], "features": ["login"], "issues": ["crashing"]}}
}}"""
        
        return prompt
    
    def _parse_analysis_response(self, response_text: str, 
                               analysis_config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate the Gemini AI response"""
        
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            
            # Remove markdown code blocks if present
            cleaned_text = re.sub(r'```json\s*', '', cleaned_text)
            cleaned_text = re.sub(r'```\s*', '', cleaned_text)
            cleaned_text = re.sub(r'^json\s*', '', cleaned_text, flags=re.IGNORECASE)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if not json_match:
                logger.error(f"No JSON found in response. Response: {cleaned_text[:200]}")
                raise ValueError("No valid JSON found in AI response")
            
            json_str = json_match.group()
            result = json.loads(json_str)
            
            # Validate required fields
            self._validate_analysis_result(result, analysis_config)
            
            return result
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse Gemini AI response: {str(e)}")
            logger.error(f"Raw response: {response_text[:200]}")
            raise ValueError(f"Invalid analysis response format: {str(e)}")
    
    def _validate_analysis_result(self, result: Dict[str, Any], 
                                analysis_config: Dict[str, Any]):
        """Validate the analysis result structure and values"""
        
        # Validate overall sentiment
        if 'overall_sentiment' not in result:
            raise ValueError("Missing overall_sentiment in analysis result")
        
        sentiment = result['overall_sentiment']
        required_fields = ['score', 'label', 'confidence']
        for field in required_fields:
            if field not in sentiment:
                raise ValueError(f"Missing {field} in overall_sentiment")
        
        if not isinstance(sentiment['score'], (int, float)) or not (-1.0 <= sentiment['score'] <= 1.0):
            raise ValueError("Sentiment score must be a float between -1.0 and 1.0")
        
        valid_labels = ['very_negative', 'negative', 'neutral', 'positive', 'very_positive']
        if sentiment['label'] not in valid_labels:
            raise ValueError(f"Invalid sentiment label: {sentiment['label']}. Must be one of {valid_labels}")
        
        if not isinstance(sentiment['confidence'], (int, float)) or not (0.0 <= sentiment['confidence'] <= 1.0):
            raise ValueError("Confidence score must be a float between 0.0 and 1.0")
        
        # Validate conditional fields
        if analysis_config.get('detect_aspects', True):
            if 'aspect_sentiments' not in result:
                result['aspect_sentiments'] = {}
        
        if analysis_config.get('detect_emotions', True):
            if 'emotions' not in result:
                result['emotions'] = {}
        
        if analysis_config.get('detect_intent', True):
            if 'intent' not in result:
                result['intent'] = {'type': 'unknown', 'confidence': 0.0}
        
        # Ensure all required fields exist
        if 'urgency' not in result:
            result['urgency'] = {'level': 'medium', 'indicators': []}
        
        if 'key_phrases' not in result:
            result['key_phrases'] = []
        
        if 'entities' not in result:
            result['entities'] = {'products': [], 'features': [], 'issues': []}
    
    def batch_analyze_feedbacks(self, feedbacks_data: List[Dict[str, Any]], 
                              analysis_config: Dict[str, bool] = None) -> List[Dict[str, Any]]:
        """
        Analyze multiple feedbacks in batch
        
        Args:
            feedbacks_data: List of dicts with 'id', 'content', and 'language'
            analysis_config: Analysis configuration
        
        Returns:
            List of analysis results with original IDs
        """
        if analysis_config is None:
            analysis_config = {}
        
        results = []
        
        for feedback_data in feedbacks_data:
            try:
                analysis_result = self.analyze_feedback(
                    feedback_data['content'],
                    feedback_data.get('language', 'en'),
                    analysis_config
                )
                analysis_result['feedback_id'] = feedback_data['id']
                analysis_result['success'] = True
                results.append(analysis_result)
                
            except Exception as e:
                logger.error(f"Failed to analyze feedback {feedback_data.get('id')}: {str(e)}")
                results.append({
                    'feedback_id': feedback_data.get('id'),
                    'error': str(e),
                    'success': False
                })
        
        return results

    def health_check(self) -> Dict[str, Any]:
        """
        Check if the Gemini AI service is healthy and accessible
        """
        try:
            if self.model is None:
                self.configure_client()
            
            test_prompt = "Respond with only the word 'healthy' in lowercase"
            response = self.model.generate_content(test_prompt)
            
            return {
                'healthy': response.text.strip().lower() == 'healthy',
                'model': self.model_name,
                'response_time': 'test_not_implemented'
            }
        except Exception as e:
            logger.error(f"Gemini AI health check failed: {str(e)}")
            return {
                'healthy': False,
                'error': str(e),
                'model': self.model_name
            }