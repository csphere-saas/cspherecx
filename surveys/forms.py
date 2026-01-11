from django import forms
from django.utils.translation import gettext_lazy as _
from core.models import *
import json

class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = [
            'title', 'description', 'survey_type', 'questions',
            'language', 'available_languages', 'trigger_event',
            'trigger_delay', 'status', 'response_limit',
            'start_date', 'end_date', 'theme_settings'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter survey title')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Enter survey description')
            }),
            'survey_type': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'trigger_event': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'response_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        # Language choices
        LANGUAGE_CHOICES = [
            ('en', _('English')),
            ('es', _('Spanish')),
            ('fr', _('French')),
            ('de', _('German')),
            ('it', _('Italian')),
            ('pt', _('Portuguese')),
        ]
        
        self.fields['language'].choices = LANGUAGE_CHOICES
        
        # Make questions field more user-friendly
        self.fields['questions'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': _('JSON format: [{"type": "nps", "text": "How likely are you to recommend us?", "required": true}]')
        })
        
        self.fields['available_languages'].widget = forms.SelectMultiple(attrs={
            'class': 'form-select'
        })
        self.fields['available_languages'].choices = LANGUAGE_CHOICES
        
        self.fields['theme_settings'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('JSON format: {"primary_color": "#007bff", "font_family": "Arial"}')
        })

    def clean_questions(self):
        questions = self.cleaned_data.get('questions')
        if questions:
            try:
                if isinstance(questions, str):
                    questions_data = json.loads(questions)
                else:
                    questions_data = questions
                
                # Validate questions structure
                if not isinstance(questions_data, list):
                    raise forms.ValidationError(_('Questions must be a list of question objects'))
                
                for i, question in enumerate(questions_data):
                    if not isinstance(question, dict):
                        raise forms.ValidationError(_(f'Question {i+1} must be an object'))
                    if 'text' not in question or not question['text']:
                        raise forms.ValidationError(_(f'Question {i+1} must have a text field'))
                    if 'type' not in question:
                        raise forms.ValidationError(_(f'Question {i+1} must have a type field'))
                    
                    # Validate question type
                    valid_types = ['nps', 'csat', 'ces', 'text', 'rating', 'multiple_choice', 'yes_no']
                    if question['type'] not in valid_types:
                        raise forms.ValidationError(_(f'Question {i+1} has invalid type. Must be one of: {", ".join(valid_types)}'))
                
                return questions_data
            except json.JSONDecodeError as e:
                raise forms.ValidationError(_('Invalid JSON format for questions: {}').format(str(e)))
        return []

    def clean_theme_settings(self):
        theme_settings = self.cleaned_data.get('theme_settings')
        if theme_settings:
            try:
                if isinstance(theme_settings, str):
                    return json.loads(theme_settings)
                return theme_settings
            except json.JSONDecodeError as e:
                raise forms.ValidationError(_('Invalid JSON format for theme settings: {}').format(str(e)))
        return {}

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError(_('End date must be after start date'))
        
        return cleaned_data
          
from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

class SurveyResponseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.questions = kwargs.pop('questions', [])
        self.survey = kwargs.pop('survey', None)
        self.customer = kwargs.pop('customer', None)
        self.request = kwargs.pop('request', None)
        self.organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        for i, question in enumerate(self.questions):
            field_name = f'q_{i}'
            question_text = question.get('text', '')
            question_type = question.get('type', 'text')
            required = question.get('required', True)
            field_id = question.get('id', f'question_{i}')
            
            if question_type == 'nps':
                self.fields[field_name] = forms.ChoiceField(
                    label=question_text,
                    required=required,
                    choices=[(str(i), str(i)) for i in range(0, 11)],
                    widget=forms.RadioSelect(attrs={
                        'class': 'nps-rating',
                        'data-type': 'nps'
                    })
                )
            elif question_type == 'csat':
                self.fields[field_name] = forms.ChoiceField(
                    label=question_text,
                    required=required,
                    choices=[
                        ('5', _('Very Satisfied')),
                        ('4', _('Satisfied')),
                        ('3', _('Neutral')),
                        ('2', _('Dissatisfied')),
                        ('1', _('Very Dissatisfied')),
                    ],
                    widget=forms.RadioSelect(attrs={
                        'class': 'csat-rating',
                        'data-type': 'csat'
                    })
                )
            elif question_type == 'ces':
                self.fields[field_name] = forms.ChoiceField(
                    label=question_text,
                    required=required,
                    choices=[
                        ('1', _('Very Easy')),
                        ('2', _('Easy')),
                        ('3', _('Neutral')),
                        ('4', _('Difficult')),
                        ('5', _('Very Difficult')),
                    ],
                    widget=forms.RadioSelect(attrs={
                        'class': 'ces-rating',
                        'data-type': 'ces'
                    })
                )
            elif question_type == 'rating':
                options = question.get('options', [])
                if not options:
                    options = [
                        ('1', '1'),
                        ('2', '2'),
                        ('3', '3'),
                        ('4', '4'),
                        ('5', '5'),
                    ]
                self.fields[field_name] = forms.ChoiceField(
                    label=question_text,
                    required=required,
                    choices=options,
                    widget=forms.RadioSelect(attrs={'class': 'rating-options'}),
                    help_text=_('1 = Unsatisfied, 5 = Very Satisfied') if required else _('1 = Unsatisfied, 5 = Very Satisfied')
                )
                
            elif question_type == 'multiple_choice':
                options = question.get('options', [])
                multiple = question.get('multiple', False)  # Add this line to check if multiple selection is allowed
                
                if multiple:
                    # Use MultipleChoiceField with CheckboxSelectMultiple for multiple selections
                    self.fields[field_name] = forms.MultipleChoiceField(
                        label=question_text,
                        required=required,
                        choices=[(opt, opt) for opt in options],
                        widget=forms.CheckboxSelectMultiple(attrs={'class': 'multiple-choice-checkbox'}),
                        help_text=_('Sélectionnez toutes les options applicables') if required else _('Sélectionnez une ou plusieurs options')
                    )
                else:
                    # Keep RadioSelect for single selection
                    self.fields[field_name] = forms.ChoiceField(
                        label=question_text,
                        required=required,
                        choices=[(opt, opt) for opt in options],
                        widget=forms.RadioSelect(attrs={'class': 'multiple-choice-radio'})
                    )
            elif question_type == 'yes_no':
                self.fields[field_name] = forms.ChoiceField(
                    label=question_text,
                    required=required,
                    choices=[
                        ('yes', _('Yes')),
                        ('no', _('No')),
                    ],
                    widget=forms.RadioSelect(attrs={'class': 'yes-no-options'})
                )
            else:  # text field
                self.fields[field_name] = forms.CharField(
                    label=question_text,
                    required=required,
                    widget=forms.Textarea(attrs={
                        'class': 'form-control',
                        'rows': 3,
                        'placeholder': _('Please share your feedback...')
                    })
                )
            
            # Store additional question metadata
            self.fields[field_name].question_id = field_id
            self.fields[field_name].question_type = question_type
    
    def clean(self):
        """Validate the form"""
        cleaned_data = super().clean()
        
        # Validate that survey exists
        if not self.survey:
            raise forms.ValidationError(_("Survey not found."))
        
        # Check if customer is required for this survey
        if hasattr(self.survey, 'require_customer_identification') and self.survey.require_customer_identification:
            if not self.customer:
                raise forms.ValidationError(_("This survey requires customer identification."))
        
        return cleaned_data
    
    def get_response_data(self):
        """Organize response data in a structured format"""
        response_data = {}
        
        for field_name, field in self.fields.items():
            if field_name.startswith('q_'):
                response_data[field_name] = {
                    'question_id': getattr(field, 'question_id', field_name),
                    'question_type': getattr(field, 'question_type', 'text'),
                    'value': self.cleaned_data.get(field_name)
                }
        
        return response_data
    
    def save_response(self):
        """Save the survey response to the database"""
        from core.models import SurveyResponse, Customer
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Ensure we have a customer (create anonymous if needed)
            customer = self.customer
            
            if not customer and self.survey:
                # Create anonymous customer for this organization
                try:
                    customer = Customer.objects.create(
                        organization=self.survey.organization,  # CRITICAL: Set organization
                        customer_id=f"anon_survey_{uuid.uuid4().hex[:12]}",
                        email='',  # Empty for anonymous
                        customer_type='anonymous',
                        segment='new',
                        first_name='',
                        last_name='',
                        metadata={
                            'source': 'survey_response',
                            'survey_id': str(self.survey.id),
                            'created_at': timezone.now().isoformat(),
                            'ip_address': self._get_client_ip(),
                            'user_agent': self._get_user_agent(),
                            'is_temporary': True  # Mark as temporary anonymous user
                        }
                    )
                    logger.info(f"Created anonymous customer for survey: {customer.customer_id}")
                except Exception as e:
                    logger.error(f"Error creating anonymous customer: {str(e)}")
                    raise forms.ValidationError(
                        _("Unable to create anonymous user record. Please try again.")
                    )
            
            # Create the survey response
            response_data = self.get_response_data()
            
            survey_response = SurveyResponse.objects.create(
                organization=self.survey.organization,  # CRITICAL: Set organization
                survey=self.survey,
                customer=customer,
                response_id=f"SR_{uuid.uuid4().hex[:12].upper()}",
                response_data=response_data,
                completion_time=timezone.now(),
                language=self._get_language(),
                device_type=self._get_device_type(),
                ip_address=self._get_client_ip(),
                user_agent=self._get_user_agent(),
                metadata={
                    'form_cleaned_data': {k: str(v) for k, v in self.cleaned_data.items()},
                    'survey_questions': self.questions,
                    'submitted_at': timezone.now().isoformat()
                }
            )
            
            # Update survey statistics
            if self.survey:
                self.survey.total_responses += 1
                if self.survey.total_sent > 0:
                    self.survey.response_rate = (self.survey.total_responses / self.survey.total_sent) * 100
                self.survey.save(update_fields=['total_responses', 'response_rate', 'updated_at'])
            
            # Update customer engagement metrics if customer exists
            if customer:
                customer.total_interactions += 1
                customer.last_interaction_date = timezone.now()
                customer.save(update_fields=['total_interactions', 'last_interaction_date', 'updated_at'])
            
            logger.info(f"Survey response saved: {survey_response.response_id}")
            return survey_response
            
        except Exception as e:
            logger.error(f"Error saving survey response: {str(e)}", exc_info=True)
            raise
    
    def _get_client_ip(self):
        """Get client IP address from request"""
        if not self.request:
            return None
        
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def _get_user_agent(self):
        """Get user agent from request"""
        if not self.request:
            return ''
        
        return self.request.META.get('HTTP_USER_AGENT', '')[:500]
    
    def _get_language(self):
        """Get language from request"""
        if not self.request:
            return 'en'
        
        return self.request.LANGUAGE_CODE
    
    def _get_device_type(self):
        """Detect device type from user agent"""
        if not self.request:
            return 'desktop'
        
        user_agent = self.request.META.get('HTTP_USER_AGENT', '').lower()
        
        if 'mobile' in user_agent:
            return 'mobile'
        elif 'tablet' in user_agent:
            return 'tablet'
        elif 'android' in user_agent or 'ios' in user_agent or 'iphone' in user_agent:
            return 'mobile'
        else:
            return 'desktop'
        

class NPSResponseForm(forms.ModelForm):
    """
    Form for collecting NPS responses with enhanced UX
    """
    score = forms.IntegerField(
        label=_('How likely are you to recommend us?'),
        widget=forms.HiddenInput(),
        min_value=0,
        max_value=10,
        required=True
    )
    
    reason = forms.CharField(
        label=_('What is the primary reason for your score?'),
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': _('Please share what influenced your rating...'),
            'class': 'form-control',
            'maxlength': '500'
        }),
        required=False,
        max_length=500
    )
    
    follow_up_questions = forms.JSONField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    class Meta:
        model = NPSResponse
        fields = ['score', 'reason', 'follow_up_question_responses']
    
    def __init__(self, *args, **kwargs):
        self.survey = kwargs.pop('survey', None)
        self.customer = kwargs.pop('customer', None)
        self.channel = kwargs.pop('channel', None)
        super().__init__(*args, **kwargs)
        
        # Add custom follow-up questions based on survey configuration
        if self.survey and self.survey.questions:
            self.add_follow_up_questions()
    
    def add_follow_up_questions(self):
        """Dynamically add follow-up questions based on survey configuration"""
        for question in self.survey.questions:
            if question.get('type') == 'follow_up':
                field_name = f"follow_up_{question.get('id')}"
                
                if question.get('question_type') == 'text':
                    self.fields[field_name] = forms.CharField(
                        label=question.get('text'),
                        widget=forms.Textarea(attrs={
                            'rows': 2,
                            'class': 'form-control',
                            'placeholder': question.get('placeholder', ''),
                            'maxlength': question.get('max_length', '250')
                        }),
                        required=question.get('required', False),
                        max_length=question.get('max_length', 250)
                    )
                elif question.get('question_type') == 'select':
                    self.fields[field_name] = forms.ChoiceField(
                        label=question.get('text'),
                        widget=forms.Select(attrs={
                            'class': 'form-select'
                        }),
                        choices=[(opt['value'], opt['label']) for opt in question.get('options', [])],
                        required=question.get('required', False)
                    )
    
    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get('score')
        
        if score is None:
            raise ValidationError(_('Please provide a score between 0-10'))
        
        # Validate score range
        if not (0 <= score <= 10):
            raise ValidationError(_('Score must be between 0 and 10'))
        
        # Collect follow-up questions
        follow_up_responses = {}
        for field_name, value in cleaned_data.items():
            if field_name.startswith('follow_up_'):
                question_id = field_name.replace('follow_up_', '')
                follow_up_responses[question_id] = value
        
        cleaned_data['follow_up_question_responses'] = follow_up_responses
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set required relationships
        if self.survey:
            instance.organization = self.survey.organization
        if self.customer:
            instance.customer = self.customer
        
        # Create associated SurveyResponse
        if self.survey and commit:
            survey_response = SurveyResponse.objects.create(
                survey=self.survey,
                customer=self.customer,
                response_data=self.construct_response_data(),
                is_complete=True,
                completed_at=timezone.now(),
                channel=self.channel,
                device_type=self.get_device_type()
            )
            instance.survey_response = survey_response
        
        if commit:
            instance.save()
            # Trigger sentiment analysis
            if instance.reason or instance.follow_up_question_responses:
                instance.analyze_sentiment_async()
        
        return instance
    
    def construct_response_data(self):
        """Construct JSON response data for SurveyResponse"""
        response_data = {
            'nps_score': self.cleaned_data.get('score'),
            'reason': self.cleaned_data.get('reason', ''),
            'timestamp': timezone.now().isoformat()
        }
        
        # Add follow-up responses
        follow_up_responses = self.cleaned_data.get('follow_up_question_responses', {})
        if follow_up_responses:
            response_data['follow_up_responses'] = follow_up_responses
        
        return response_data
    
    def get_device_type(self):
        """Detect device type from request"""
        # This would typically be set from middleware
        return 'desktop'


class QuickNPSForm(forms.Form):
    """
    Simplified NPS form for embedded/widget use
    """
    score = forms.IntegerField(
        widget=forms.HiddenInput(),
        min_value=0,
        max_value=10,
        required=True
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'placeholder': _('Your email (optional)'),
            'class': 'form-control'
        })
    )
    
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': _('Additional comments (optional)'),
            'class': 'form-control'
        }),
        max_length=250
    )
    
    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get('score')
        
        if score is None:
            raise ValidationError(_('Please select a score'))
        
        if not (0 <= score <= 10):
            raise ValidationError(_('Invalid score selected'))
        
        return cleaned_data
    

class NPSShareForm(forms.Form):
    """
    Form for promoters to share testimonials and referrals
    """
    testimonial = forms.CharField(
        label=_('Share your experience (optional)'),
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': _('What do you love about our service? Your testimonial could be featured on our website...'),
            'class': 'form-control',
            'maxlength': '500'
        }),
        required=False,
        max_length=500
    )
    
    allow_testimonial_use = forms.BooleanField(
        label=_('I allow my testimonial to be used on marketing materials'),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    friend_emails = forms.CharField(
        label=_('Invite friends (optional)'),
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': _('Enter email addresses separated by commas'),
            'class': 'form-control'
        }),
        required=False,
        help_text=_('We\'ll send them an invitation to provide feedback')
    )
    
    personal_message = forms.CharField(
        label=_('Personal message (optional)'),
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': _('Add a personal note to your invitation...'),
            'class': 'form-control',
            'maxlength': '200'
        }),
        required=False,
        max_length=200
    )
    
    def __init__(self, *args, **kwargs):
        self.survey = kwargs.pop('survey', None)
        self.customer = kwargs.pop('customer', None)
        self.nps_response = kwargs.pop('nps_response', None)
        super().__init__(*args, **kwargs)
    
    def clean_friend_emails(self):
        emails = self.cleaned_data.get('friend_emails', '')
        if emails:
            email_list = [email.strip() for email in emails.split(',')]
            valid_emails = []
            
            for email in email_list:
                if email:  # Skip empty strings
                    try:
                        validate_email(email)
                        valid_emails.append(email)
                    except ValidationError:
                        raise ValidationError(_('Enter valid email addresses separated by commas.'))
            
            # Limit number of emails
            if len(valid_emails) > 10:
                raise ValidationError(_('You can invite up to 10 friends at once.'))
            
            return valid_emails
        return []
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate testimonial usage permission
        testimonial = cleaned_data.get('testimonial')
        allow_use = cleaned_data.get('allow_testimonial_use')
        
        if testimonial and not allow_use:
            self.add_error(
                'allow_testimonial_use',
                _('Please allow us to use your testimonial if you want to share it.')
            )
        
        return cleaned_data

''' 
class NPSSupportRequestForm(forms.ModelForm):
    """
    Form for detractors to request support
    """
    class Meta:
        from .models import SupportRequest  # Assuming this model exists
        model = SupportRequest
        fields = ['request_type', 'subject', 'description', 'contact_method', 'preferred_contact']
        widgets = {
            'request_type': forms.Select(attrs={
                'class': 'form-select',
                'aria-label': 'Select request type'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Brief summary of your issue')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Please describe the issue in detail...')
            }),
            'contact_method': forms.Select(attrs={
                'class': 'form-select',
                'aria-label': 'Select contact method'
            }),
            'preferred_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Phone number or specific time')
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.survey = kwargs.pop('survey', None)
        self.customer = kwargs.pop('customer', None)
        self.nps_response = kwargs.pop('nps_response', None)
        super().__init__(*args, **kwargs)
        
        # Customize choices based on available support channels
        self.customize_field_choices()
        
        # Pre-fill data from NPS response
        if self.nps_response and self.nps_response.reason:
            self.initial['description'] = self.nps_response.reason
            self.initial['subject'] = _('Follow-up on NPS feedback')
    
    def customize_field_choices(self):
        """Customize form field choices based on available support"""
        # Request type choices
        self.fields['request_type'].choices = [
            ('technical', _('Technical Issue')),
            ('billing', _('Billing Question')),
            ('feature', _('Feature Request')),
            ('account', _('Account Issue')),
            ('general', _('General Inquiry')),
            ('escalation', _('Escalation Request')),
        ]
        
        # Contact method choices
        contact_choices = [('email', _('Email'))]
        
        if self.customer and not self.customer.is_anonymous and self.customer.phone:
            contact_choices.append(('phone', _('Phone Call')))
        
        # Check if chat is available
        if hasattr(self, 'survey') and self.survey:
            # You would implement actual chat availability check
            contact_choices.append(('chat', _('Live Chat')))
        
        self.fields['contact_method'].choices = contact_choices


class ReferralInviteForm(forms.Form):
    """
    Simple form for referral invitations
    """
    email = forms.EmailField(
        label=_("Friend's Email"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('friend@example.com')
        })
    )
    
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': _('Add a personal message (optional)')
        }),
        max_length=200
    ) 
    '''