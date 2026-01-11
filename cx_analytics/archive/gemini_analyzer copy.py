import logging
import json
import re
import os
from typing import Dict, Any, Optional
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
            
            # Construct the analysis prompt
            prompt = self._construct_analysis_prompt(feedback_content, language, analysis_config)
            
            # Generate analysis with safety settings
            generation_config = {
                'temperature': 0.1,  # Low temperature for consistent results
                'top_p': 0.8,
                'top_k': 40,
                #'max_output_tokens': 2048,
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
        
        prompt_parts = []
        
        target_language = analysis_config.get('target_language', 'en')
        
        # System instruction
        system_instruction = f"""You are a highly accurate sentiment analysis AI specialized in customer experience. 
        Analyze the following customer feedback and provide a structured JSON response. 
        Be objective and base your analysis strictly on the content provided. Do not make assumptions.
        
        The feedback is in {language.upper()} language. Provide the analysis results in {target_language.upper()} language.
        
        IMPORTANT: Return ONLY valid JSON. Do not include any other text, explanations, or markdown formatting."""
        
        prompt_parts.append(system_instruction)
        
        # Analysis requirements
        requirements = [f"Provide a comprehensive sentiment analysis in {target_language.upper()} with the following components:"]
        
        # Always include basic sentiment
        requirements.append("1. Overall sentiment score (float between -1.0 to 1.0) and label (very_negative, negative, neutral, positive, very_positive)")
        requirements.append("2. Confidence score (float between 0.0 to 1.0) for the sentiment analysis")
        
        # Conditional requirements based on config
        if analysis_config.get('detect_aspects', True):
            requirements.append("3. Aspect-based sentiment analysis for common aspects like product, service, price, usability, support")
        
        if analysis_config.get('detect_emotions', True):
            requirements.append("4. Emotion detection with scores for key emotions (anger, joy, sadness, fear, surprise, trust)")
        
        if analysis_config.get('detect_intent', True):
            requirements.append("5. Customer intent classification (complaint, compliment, suggestion, question, request)")
        
        if analysis_config.get('extract_key_phrases', True):
            requirements.append("6. Key phrases extraction (most important phrases from the feedback)")
            requirements.append("7. Named entities recognition (products, features, issues mentioned)")
        
        requirements.append("8. Urgency level assessment (low, medium, high, critical) with supporting indicators")
        
        prompt_parts.append("\n".join(requirements))
        
        # Response format with exact structure
        response_format = """
        Return ONLY a valid JSON object with the following exact structure. Do not include any other text or explanations:

        {
            "overall_sentiment": {
                "score": -0.85,
                "label": "very_negative",
                "confidence": 0.92
            },
            "aspect_sentiments": {
                "product": {"score": -0.7, "mentions": 2},
                "service": {"score": -0.9, "mentions": 3},
                "price": {"score": -0.5, "mentions": 1}
            },
            "emotions": {
                "anger": 0.8,
                "disappointment": 0.7,
                "frustration": 0.6
            },
            "intent": {
                "type": "complaint",
                "confidence": 0.88
            },
            "urgency": {
                "level": "high",
                "indicators": ["urgent language", "multiple issues", "emotional tone"]
            },
            "key_phrases": ["broken feature", "poor customer service", "frustrating experience"],
            "entities": {
                "products": ["mobile app"],
                "features": ["login system"],
                "issues": ["crashing", "slow performance"]
            }
        }
        """
        
        prompt_parts.append(response_format)
        
        # Feedback content
        prompt_parts.append(f"Feedback Content (Original Language: {language.upper()}):")
        prompt_parts.append(f'"{content}"')
        
        return "\n\n".join(prompt_parts)
    
    def _parse_analysis_response(self, response_text: str, 
                               analysis_config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate the Gemini AI response"""
        
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            
            # Remove markdown code blocks if present
            cleaned_text = re.sub(r'```json\s*', '', cleaned_text)
            cleaned_text = re.sub(r'```\s*', '', cleaned_text)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if not json_match:
                logger.error(f"No JSON found in response. Response: {cleaned_text}")
                raise ValueError("No valid JSON found in AI response")
            
            json_str = json_match.group()
            result = json.loads(json_str)
            
            # Validate required fields
            self._validate_analysis_result(result, analysis_config)
            
            return result
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse Gemini AI response: {str(e)}")
            logger.error(f"Raw response: {response_text}")
            raise ValueError(f"Invalid analysis response format: {str(e)}")
    
    def _validate_analysis_result(self, result: Dict[str, Any], 
                                analysis_config: Dict[str, Any]):
        """Validate the analysis result structure and values"""
        
        # Validate overall sentiment
        if 'overall_sentiment' not in result:
            raise ValueError("Missing overall_sentiment in analysis result")
        
        sentiment = result['overall_sentiment']
        if 'score' not in sentiment or 'label' not in sentiment or 'confidence' not in sentiment:
            raise ValueError("Missing required fields in overall_sentiment")
        
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
                raise ValueError("Missing aspect_sentiments in analysis result")
        
        if analysis_config.get('detect_emotions', True):
            if 'emotions' not in result:
                raise ValueError("Missing emotions in analysis result")
        
        if analysis_config.get('detect_intent', True):
            if 'intent' not in result:
                raise ValueError("Missing intent in analysis result") 
    def batch_analyze_feedbacks(self, feedbacks_data: list, 
                              analysis_config: Dict[str, bool] = None) -> list:
        """
        Analyze multiple feedbacks in batch
        
        Args:
            feedbacks_data: List of dicts with 'id', 'content', and 'language'
            analysis_config: Analysis configuration
        
        Returns:
            List of analysis results with original IDs
        """
        results = []
        
        for feedback_data in feedbacks_data:
            try:
                analysis_result = self.analyze_feedback(
                    feedback_data['content'],
                    feedback_data.get('language', 'en'),
                    analysis_config
                )
                analysis_result['feedback_id'] = feedback_data['id']
                results.append(analysis_result)
                
            except Exception as e:
                logger.error(f"Failed to analyze feedback {feedback_data.get('id')}: {str(e)}")
                # Add error result to maintain order
                results.append({
                    'feedback_id': feedback_data['id'],
                    'error': str(e),
                    'success': False
                })
        
        return results

    def health_check(self) -> bool:
        """
        Check if the Gemini AI service is healthy and accessible
        """
        try:
            # Try to generate a simple test content
            test_prompt = "Respond with just the word 'healthy'"
            response = self.model.generate_content(test_prompt)
            return response.text.strip().lower() == 'healthy'
        except Exception as e:
            logger.error(f"Gemini AI health check failed: {str(e)}")
            return False