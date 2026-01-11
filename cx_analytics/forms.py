# forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from core.models import *

class SentimentAnalysisDisplayForm(forms.ModelForm):
    """
    Form for displaying sentiment analysis results (read-only for display)
    """
    class Meta:
        model = SentimentAnalysis
        fields = [
            'overall_score', 'overall_label', 'confidence_score',
            'aspects', 'emotions', 'intent', 'intent_confidence',
            'urgency_level', 'urgency_indicators', 'key_phrases',
            'entities', 'model_used', 'model_version'
        ]
        widgets = {
            'overall_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': True,
                'step': '0.001'
            }),
            'overall_label': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'confidence_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': True,
                'step': '0.001'
            }),
            'aspects': forms.Textarea(attrs={
                'class': 'form-control',
                'readonly': True,
                'rows': 4
            }),
            'emotions': forms.Textarea(attrs={
                'class': 'form-control',
                'readonly': True,
                'rows': 4
            }),
            'intent': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'intent_confidence': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': True,
                'step': '0.001'
            }),
            'urgency_level': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'urgency_indicators': forms.Textarea(attrs={
                'class': 'form-control',
                'readonly': True,
                'rows': 3
            }),
            'key_phrases': forms.Textarea(attrs={
                'class': 'form-control',
                'readonly': True,
                'rows': 3
            }),
            'entities': forms.Textarea(attrs={
                'class': 'form-control',
                'readonly': True,
                'rows': 4
            }),
            'model_used': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'model_version': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields disabled for display
        for field in self.fields:
            self.fields[field].disabled = True


class SingleSentimentAnalysisForm(forms.Form):
    """
    Form for single feedback sentiment analysis with language options
    """
    feedback_id = forms.CharField(
        widget=forms.HiddenInput()
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
        initial='en',
        label=_('Analysis Language'),
        help_text=_('Select the language for the analysis results'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    translate_content = forms.BooleanField(
        required=False,
        initial=False,
        label=_('Translate feedback content before analysis'),
        help_text=_('If checked, the feedback will be translated to the target language before analysis'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )
    
    analysis_config = forms.ChoiceField(
        choices=[
            ('basic', _('Basic Sentiment Only')),
            ('standard', _('Standard Analysis (Sentiment + Emotions)')),
            ('advanced', _('Advanced Analysis (Full Analysis)')),
        ],
        initial='standard',
        label=_('Analysis Depth'),
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        })
    )


class BulkSentimentAnalysisForm(forms.Form):
    """
    Form for bulk sentiment analysis configuration
    """
    feedback_ids = forms.CharField(
        widget=forms.HiddenInput()
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
        initial='en',
        label=_('Analysis Language'),
        help_text=_('Select the language for the analysis results'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    translate_content = forms.BooleanField(
        required=False,
        initial=False,
        label=_('Translate feedback content before analysis'),
        help_text=_('If checked, feedback will be translated to the target language before analysis'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )
    
    analysis_type = forms.ChoiceField(
        choices=[
            ('basic', _('Basic Sentiment Only')),
            ('standard', _('Standard Analysis (Sentiment + Emotions)')),
            ('advanced', _('Advanced Analysis (Full Analysis)')),
            ('custom', _('Custom Configuration')),
        ],
        initial='standard',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label=_('Analysis Depth')
    )
    
    # Custom configuration fields (shown only when analysis_type is 'custom')
    detect_aspects = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Detect aspect-based sentiments'),
        help_text=_('Analyze sentiments for different aspects like product, service, price, etc.'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input custom-config',
            'style': 'display: none;'  # Hidden by default
        })
    )
    
    detect_emotions = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Detect emotions'),
        help_text=_('Identify specific emotions in the feedback'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input custom-config',
            'style': 'display: none;'  # Hidden by default
        })
    )
    
    detect_intent = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Detect customer intent'),
        help_text=_('Classify the primary intent of the feedback'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input custom-config',
            'style': 'display: none;'  # Hidden by default
        })
    )
    
    extract_key_phrases = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Extract key phrases'),
        help_text=_('Identify important phrases and entities mentioned'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input custom-config',
            'style': 'display: none;'  # Hidden by default
        })
    )
    
    overwrite_existing = forms.BooleanField(
        required=False,
        initial=False,
        label=_('Overwrite existing analyses'),
        help_text=_('If checked, will re-analyze feedback that already has sentiment analysis'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

    def __init__(self, *args, **kwargs):
        feedback_ids = kwargs.pop('feedback_ids', '')
        super().__init__(*args, **kwargs)
        
        if feedback_ids:
            self.fields['feedback_ids'].initial = feedback_ids

    def clean(self):
        cleaned_data = super().clean()
        analysis_type = cleaned_data.get('analysis_type')
        
        # Set advanced options based on analysis type
        if analysis_type == 'basic':
            cleaned_data['detect_aspects'] = False
            cleaned_data['detect_emotions'] = False
            cleaned_data['detect_intent'] = False
            cleaned_data['extract_key_phrases'] = False
        elif analysis_type == 'standard':
            cleaned_data['detect_aspects'] = True
            cleaned_data['detect_emotions'] = True
            cleaned_data['detect_intent'] = False
            cleaned_data['extract_key_phrases'] = False
        elif analysis_type == 'advanced':
            cleaned_data['detect_aspects'] = True
            cleaned_data['detect_emotions'] = True
            cleaned_data['detect_intent'] = True
            cleaned_data['extract_key_phrases'] = True
        # For 'custom', use the values from the form
        
        return cleaned_data

    def get_analysis_config(self):
        """
        Convert form data to analysis configuration dictionary
        """
        cleaned_data = self.cleaned_data
        
        return {
            'detect_aspects': cleaned_data.get('detect_aspects', False),
            'detect_emotions': cleaned_data.get('detect_emotions', False),
            'detect_intent': cleaned_data.get('detect_intent', False),
            'extract_key_phrases': cleaned_data.get('extract_key_phrases', False),
            'target_language': cleaned_data.get('target_language', 'en'),
            'translate_content': cleaned_data.get('translate_content', False),
        }


class TranslationForm(forms.Form):
    """
    Form for translating feedback content
    """
    feedback_id = forms.CharField(
        widget=forms.HiddenInput()
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
        initial='en',
        label=_('Target Language'),
        help_text=_('Select the language to translate the feedback to'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    include_analysis = forms.BooleanField(
        required=False,
        initial=False,
        label=_('Perform sentiment analysis after translation'),
        help_text=_('If checked, sentiment analysis will be performed on the translated content'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )
    

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = [
            'organization', 'customer', 'channel', 'product',
            'subject', 'content', 'feedback_type', 'priority'
        ]
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter feedback subject')
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Enter detailed feedback content')
            }),
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'channel': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'feedback_type': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }

class BulkFeedbackUploadForm(forms.Form):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Organization')
    )
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        }),
        label=_('CSV File'),
        help_text=_('Upload CSV file with columns: customer_email, channel, product, subject, content, feedback_type, priority')
    )
    language = forms.ChoiceField(
        choices=[
            ('en', _('English')),
            ('fr', _('French')),
            ('es', _('Spanish')),
            ('de', _('German')),
        ],
        initial='en',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Feedback Language')
    )
    generate_themes = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Generate themes automatically')
    )

class ThemeAnalysisForm(forms.Form):
    feedback_queryset = forms.ModelMultipleChoiceField(
        queryset=Feedback.objects.none(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'size': '10'
        }),
        label=_('Select Feedbacks to Analyze')
    )
    language = forms.ChoiceField(
        choices=[
            ('en', _('English')),
            ('fr', _('French')),
            ('es', _('Spanish')),
            ('de', _('German')),
        ],
        initial='en',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Analysis Language')
    )
    min_relevance_score = forms.FloatField(
        initial=0.7,
        min_value=0.1,
        max_value=1.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1'
        }),
        label=_('Minimum Relevance Score'),
        help_text=_('Only create theme associations with relevance score above this threshold')
    )

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['feedback_queryset'].queryset = Feedback.objects.filter(
                organization=organization,
                ai_analyzed=False
            )