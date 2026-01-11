# translation_service.py
import logging
import os
from typing import Optional
import google.generativeai as genai
from django.conf import settings
from django.utils.translation import gettext_lazy as _

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
        self.configure_client()
    
    def configure_client(self):
        """Configure the Gemini AI client"""
        try:
            if not self.api_key:
                logger.warning("GEMINI_API_KEY not found in settings or environment variables")
                return
                
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Translation service configured with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to configure translation service: {str(e)}")
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
        
        # Check if API key is available
        if not self.api_key:
            logger.warning("Translation service not configured - no API key")
            return text  # Return original text if no API key
        
        try:
            # Construct translation prompt
            if source_language == 'auto':
                prompt = f"""Translate the following text to {target_language}. 
                Detect the source language automatically and provide an accurate translation.
                Return ONLY the translated text without any additional explanations, notes, or quotation marks.
                
                Text to translate: {text}"""
            else:
                prompt = f"""Translate the following text from {source_language} to {target_language}. 
                Provide an accurate and natural translation.
                Return ONLY the translated text without any additional explanations, notes, or quotation marks.
                
                Text to translate: {text}"""
            
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
            
            # Clean up the response (remove quotes if present)
            if translated_text.startswith('"') and translated_text.endswith('"'):
                translated_text = translated_text[1:-1]
            
            logger.info(f"Successfully translated text from {source_language} to {target_language}")
            logger.debug(f"Original: {text[:100]}... -> Translated: {translated_text[:100]}...")
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
        
        # Check if API key is available
        if not self.api_key:
            logger.warning("Translation service not configured - no API key")
            return 'en'  # Default to English if no API key
        
        try:
            prompt = f"""Detect the language of the following text. 
            Return ONLY the ISO 639-1 language code (e.g., 'en', 'es', 'fr').
            
            Text: {text}
            
            Language code:"""
            
            response = self.model.generate_content(prompt)
            
            if not response.text:
                raise ValueError("Empty response from language detection")
            
            language_code = response.text.strip().lower()
            
            logger.info(f"Detected language: {language_code}")
            return language_code
            
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            raise

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
        return bool(self.api_key)