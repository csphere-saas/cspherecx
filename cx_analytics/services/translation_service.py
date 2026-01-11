import logging
import os
from typing import Optional, Dict, Any
import google.generativeai as genai
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import re 
logger = logging.getLogger(__name__)

class TranslationService:
    """
    Service class for translating text using Google's Gemini AI
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
                logger.warning("GEMINI_API_KEY not found in settings or environment variables")
                self.is_configured_flag = False
                return
            
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            self.is_configured_flag = True
            logger.info(f"Translation service configured with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to configure translation service: {str(e)}")
            self.is_configured_flag = False
            raise
    
    def translate_text(self, text: str, source_language: str = 'auto', 
                      target_language: str = 'en') -> str:
        """
        Translate text to target language using Gemini AI
        
        Args:
            text: The text to translate
            source_language: Source language code or 'auto' for auto-detection
            target_language: Target language code
        
        Returns:
            Translated text
        """
        if not text or not text.strip():
            raise ValueError("Text to translate cannot be empty")
        
        # Check if service is configured
        if not self.is_configured():
            logger.error("Translation service not properly configured")
            raise ValueError("Translation service is not configured. Please check your API key.")
        
        try:
            if self.model is None:
                self.configure_client()
            
            # Construct translation prompt
            if source_language == 'auto':
                prompt = f"""Translate the following text to {target_language}. 
                Detect the source language automatically.
                Return ONLY the translated text without any additional text.
                
                Text: {text}
                
                Translation:"""
            else:
                prompt = f"""Translate the following text from {source_language} to {target_language}. 
                Provide a natural and accurate translation.
                Return ONLY the translated text without any additional text.
                
                Text: {text}
                
                Translation:"""
            
            # Configure generation settings
            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            # Generate translation
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Handle response safely
            if not response or not response.text:
                raise ValueError("Empty response from translation service")
            
            translated_text = response.text.strip()
            
            # Clean up the response
            # Remove quotes and any prefix like "Translation:"
            if translated_text.startswith('"') and translated_text.endswith('"'):
                translated_text = translated_text[1:-1]
            
            # Remove common prefixes
            prefixes = ['translation:', 'translated text:', 'result:']
            for prefix in prefixes:
                if translated_text.lower().startswith(prefix):
                    translated_text = translated_text[len(prefix):].strip()
            
            logger.info(f"Successfully translated text from {source_language} to {target_language}")
            logger.debug(f"Original ({len(text)} chars): {text[:50]}...")
            logger.debug(f"Translated ({len(translated_text)} chars): {translated_text[:50]}...")
            
            return translated_text
            
        except Exception as e:
            logger.error(f"Error translating text: {str(e)}")
            raise
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text
        
        Args:
            text: The text to analyze
        
        Returns:
            Detected language code
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty for language detection")
        
        # Check if service is configured
        if not self.is_configured():
            logger.warning("Translation service not configured - using default 'en'")
            return 'en'
        
        try:
            if self.model is None:
                self.configure_client()
            
            prompt = f"""Detect the language of this text. Return ONLY the ISO 639-1 language code.
            
            Text: {text}
            
            Language code:"""
            
            response = self.model.generate_content(prompt)
            
            if not response.text:
                raise ValueError("Empty response from language detection")
            
            language_code = response.text.strip().lower()[:10]  # Take first 10 chars max
            
            # Clean the response
            language_code = re.sub(r'[^a-z]', '', language_code)
            
            # Validate it's a reasonable language code
            if len(language_code) != 2:
                logger.warning(f"Unexpected language code format: {language_code}, defaulting to 'en'")
                return 'en'
            
            logger.info(f"Detected language: {language_code}")
            return language_code
            
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return 'en'

    def get_supported_languages(self) -> list:
        """
        Get list of supported languages for translation
        
        Returns:
            List of language codes and names
        """
        return [
            ('en', 'English'),
            ('es', 'Spanish'),
            ('fr', 'French'),
            ('de', 'German'),
            ('it', 'Italian'),
            ('pt', 'Portuguese'),
            ('ru', 'Russian'),
            ('ja', 'Japanese'),
            ('ko', 'Korean'),
            ('zh', 'Chinese'),
            ('ar', 'Arabic'),
            ('hi', 'Hindi'),
            ('bn', 'Bengali'),
            ('tr', 'Turkish'),
            ('nl', 'Dutch'),
            ('sv', 'Swedish'),
            ('pl', 'Polish'),
            ('vi', 'Vietnamese'),
            ('th', 'Thai'),
        ]

    def is_configured(self) -> bool:
        """Check if translation service is properly configured"""
        return self.is_configured_flag if hasattr(self, 'is_configured_flag') else bool(self.api_key)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if translation service is healthy
        """
        try:
            if not self.is_configured():
                return {'healthy': False, 'error': 'Service not configured'}
            
            test_prompt = "Translate 'hello' to Spanish. Return only the translation."
            response = self.model.generate_content(test_prompt)
            
            return {
                'healthy': response.text.strip().lower() in ['hola', 'hello'],
                'model': self.model_name,
                'configured': True
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'model': self.model_name
            }