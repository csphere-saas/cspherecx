# forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from core.models import *
from django.contrib import messages

class ChannelForm(forms.ModelForm):
    """
    Form for creating and updating feedback channels
    """
    class Meta:
        model = Channel
        fields = [
            'name', 'channel_type', 'description', 'is_enabled', 'configuration'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Customer Support Email')
            }),
            'channel_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Describe this feedback channel...')
            }),
            'is_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'configuration': forms.Textarea(attrs={
                'class': 'form-control font-monospace small',
                'rows': 6,
                'placeholder': '{"api_key": "your_key", "webhook_url": "https://..."}'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field, 'widget') and hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    if isinstance(field, forms.BooleanField):
                        field.widget.attrs['class'] = 'form-check-input'
                    else:
                        field.widget.attrs['class'] = 'form-control'

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and self.organization:
            # Check for uniqueness within organization
            queryset = Channel.objects.filter(
                organization=self.organization,
                name=name
            )
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(
                    _('A channel with this name already exists in your organization.')
                )
        return name

    def clean_configuration(self):
        configuration = self.cleaned_data.get('configuration')
        if configuration:
            if isinstance(configuration, str):
                try:
                    import json
                    return json.loads(configuration)
                except json.JSONDecodeError:
                    raise forms.ValidationError(
                        _('Invalid JSON format. Please check your configuration.')
                    )
        return configuration or {}

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.organization:
            instance.organization = self.organization
        
        if commit:
            instance.save()
        
        return instance

class ChannelFilterForm(forms.Form):
    """
    Form for filtering channels
    """
    channel_type = forms.ChoiceField(
        required=False,
        choices=[('', _('All Types'))] + Channel._meta.get_field('channel_type').choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', _('All Status')),
            ('enabled', _('Enabled Only')),
            ('disabled', _('Disabled Only')),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search channels...')
        })
    )
    
### Tags Forms ###
from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from core.models import Tag
class TagForm(forms.ModelForm):
    """
    Form for creating and updating tags
    """
    class Meta:
        model = Tag
        fields = [
            'name', 'slug', 'category', 'color', 'description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Bug Report')
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('bug-report')
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'style': 'height: 45px;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Describe this tag...')
            }),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field, 'widget') and hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    if isinstance(field, forms.BooleanField):
                        field.widget.attrs['class'] = 'form-check-input'
                    else:
                        field.widget.attrs['class'] = 'form-control'

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and self.organization:
            # Check for uniqueness within organization
            queryset = Tag.objects.filter(
                organization=self.organization,
                name=name
            )
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(
                    _('A tag with this name already exists in your organization.')
                )
        return name

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if slug:
            slug = slugify(slug)
            # Check for uniqueness within organization
            queryset = Tag.objects.filter(
                organization=self.organization,
                slug=slug
            )
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(
                    _('A tag with this slug already exists in your organization.')
                )
        return slug

    def clean_color(self):
        color = self.cleaned_data.get('color')
        if color and not color.startswith('#'):
            raise forms.ValidationError(_('Color must be in hex format (e.g., #FF0000)'))
        return color

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.organization:
            instance.organization = self.organization
        
        # Ensure slug is properly formatted
        if not instance.slug and instance.name:
            instance.slug = slugify(instance.name)
        
        if commit:
            instance.save()
        
        return instance

class TagFilterForm(forms.Form):
    """
    Form for filtering tags
    """
    category = forms.ChoiceField(
        required=False,
        choices=[('', _('All Categories'))] + Tag._meta.get_field('category').choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search tags...')
        })
    )
    
# Feedback forms.py
class FeedbackForm(forms.ModelForm):
    """Form for creating and updating feedback"""
    
    # Add optional fields for new customer creation
    customer_email = forms.EmailField(
        required=False,
        label=_("Customer Email"),
        help_text=_("Leave blank to create anonymous feedback")
    )
    customer_first_name = forms.CharField(
        required=False,
        max_length=100,
        label=_("Customer First Name")
    )
    customer_last_name = forms.CharField(
        required=False,
        max_length=100,
        label=_("Customer Last Name")
    )
    
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Tags')
    )
    
    def __init__(self, *args, **kwargs):
        # Only organization is passed, not request
        self.organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        if self.organization:
            # Filter customers by organization
            self.fields['customer'].queryset = Customer.objects.filter(
                organization=self.organization
            ).order_by('email')
            
            # Filter channels by organization
            self.fields['channel'].queryset = Channel.objects.filter(
                organization=self.organization,
                is_enabled=True
            ).order_by('name')
            
            # Filter products by organization
            self.fields['product'].queryset = Product.objects.filter(
                organization=self.organization
            ).order_by('name')
            
            # Filter tags by organization
            self.fields['tags'].queryset = Tag.objects.filter(
                organization=self.organization
            ).order_by('name')
        
        # Set required fields
        self.fields['customer'].required = False
        self.fields['channel'].required = True
        
        # Add CSS classes for styling
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput) or \
               isinstance(field.widget, forms.EmailInput) or \
               isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 4})
            elif isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({'class': 'form-check-input'})
    
    class Meta:
        model = Feedback
        fields = [
            'customer',
            'customer_email',
            'customer_first_name', 
            'customer_last_name',
            'channel',
            'product',
            'subject',
            'content',
            'origin',
            'feedback_type',
            'priority',
            'status',
            'tags',
            'internal_notes',
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6}),
            'origin': forms.Select(attrs={'class': 'form-select'}),
            'feedback_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'internal_notes': forms.Textarea(attrs={'rows': 3}),
        }

# forms.py or wherever your FeedbackFilterForm is defined
from datetime import datetime, timedelta
from django import forms
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class FeedbackFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        label=_('Search'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search feedback...')
        })
    )
    origin = forms.ChoiceField(
        required=False,
        label=_('Origin'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    feedback_type = forms.ChoiceField(
        required=False,
        label=_('Type'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    priority = forms.ChoiceField(
        required=False,
        label=_('Priority'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        required=False,
        label=_('Status'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_range = forms.ChoiceField(
        required=False,
        label=_('Date Range'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        choices=[
            ('', _('All Time')),
            ('today', _('Today')),
            ('yesterday', _('Yesterday')),
            ('last_7_days', _('Last 7 Days')),
            ('last_30_days', _('Last 30 Days')),
            ('last_90_days', _('Last 90 Days')),
            ('this_month', _('This Month')),
            ('last_month', _('Last Month')),
            ('this_year', _('This Year')),
            ('custom', _('Custom Range')),
        ]
    )
    start_date = forms.DateField(
        required=False,
        label=_('Start Date'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    end_date = forms.DateField(
        required=False,
        label=_('End Date'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    sentiment = forms.ChoiceField(
        required=False,
        label=_('Sentiment'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    ai_analyzed = forms.ChoiceField(
        required=False,
        label=_('AI Analysis'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        choices=[
            ('', _('All')),
            ('true', _('Analyzed')),
            ('false', _('Not Analyzed')),
        ]
    )
    assigned_to = forms.ChoiceField(
        required=False,
        label=_('Assigned To'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        # Set choices for fields
        self.fields['origin'].choices = [
            ('', _('All Origins')),
            ('customer', _('Customer')),
            ('employee', _('Employee')),
            ('system', _('System Generated')),
            ('third_party', _('Third Party')),
        ]
        
        self.fields['feedback_type'].choices = [
            ('', _('All Types')),
            ('complaint', _('Complaint')),
            ('suggestion', _('Suggestion')),
            ('compliment', _('Compliment')),
            ('question', _('Question')),
            ('bug_report', _('Bug Report')),
            ('feature_request', _('Feature Request')),
            ('general', _('General')),
        ]
        
        self.fields['priority'].choices = [
            ('', _('All Priorities')),
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('critical', _('Critical')),
        ]
        
        self.fields['status'].choices = [
            ('', _('All Statuses')),
            ('new', _('New')),
            ('in_progress', _('In Progress')),
            ('pending', _('Pending')),
            ('resolved', _('Resolved')),
            ('closed', _('Closed')),
            ('reopened', _('Reopened')),
        ]
        
        self.fields['sentiment'].choices = [
            ('', _('All Sentiments')),
            ('very_negative', _('Very Negative')),
            ('negative', _('Negative')),
            ('neutral', _('Neutral')),
            ('positive', _('Positive')),
            ('very_positive', _('Very Positive')),
        ]
        
        # Set assigned_to choices based on organization members
        if organization:
            try:
                # Try to get organization members
                try:
                    OrganizationMember = apps.get_model('accounts', 'OrganizationMember')
                    members = OrganizationMember.objects.filter(
                        organization=organization,
                        is_active=True
                    ).select_related('user')
                    user_choices = [(member.user.id, member.user.get_full_name() or member.user.email) 
                                   for member in members]
                except LookupError:
                    # Try alternative app names
                    try:
                        OrganizationMember = apps.get_model('organizations', 'OrganizationMember')
                        members = OrganizationMember.objects.filter(
                            organization=organization,
                            is_active=True
                        ).select_related('user')
                        user_choices = [(member.user.id, member.user.get_full_name() or member.user.email) 
                                       for member in members]
                    except LookupError:
                        # Fallback: get all users in the system (or implement your own logic)
                        user_choices = [(user.id, user.get_full_name() or user.email) 
                                       for user in User.objects.filter(is_active=True)]
                
                self.fields['assigned_to'].choices = [
                    ('', _('All Users')),
                ] + user_choices
            except Exception as e:
                self.fields['assigned_to'].choices = [('', _('All Users'))]
        else:
            self.fields['assigned_to'].choices = [('', _('All Users'))]

    def get_date_range_filter(self):
        """
        Returns a dictionary of filter parameters for the selected date range
        """
        date_range = self.cleaned_data.get('date_range')
        
        if not date_range or date_range == 'custom':
            return {}
        
        now = datetime.now()
        
        if date_range == 'today':
            return {
                'created_at__date': now.date()
            }
        elif date_range == 'yesterday':
            yesterday = now.date() - timedelta(days=1)
            return {
                'created_at__date': yesterday
            }
        elif date_range == 'last_7_days':
            seven_days_ago = now - timedelta(days=7)
            return {
                'created_at__gte': seven_days_ago
            }
        elif date_range == 'last_30_days':
            thirty_days_ago = now - timedelta(days=30)
            return {
                'created_at__gte': thirty_days_ago
            }
        elif date_range == 'last_90_days':
            ninety_days_ago = now - timedelta(days=90)
            return {
                'created_at__gte': ninety_days_ago
            }
        elif date_range == 'this_month':
            return {
                'created_at__year': now.year,
                'created_at__month': now.month
            }
        elif date_range == 'last_month':
            last_month = now.month - 1 if now.month > 1 else 12
            last_month_year = now.year if now.month > 1 else now.year - 1
            return {
                'created_at__year': last_month_year,
                'created_at__month': last_month
            }
        elif date_range == 'this_year':
            return {
                'created_at__year': now.year
            }
        
        return {}
    
class FeedbackFilterForm1(forms.Form):
    search = forms.CharField(required=False, label=_('Search'))
    origin = forms.ChoiceField(required=False, label=_('Origin'))
    feedback_type = forms.ChoiceField(required=False, label=_('Type'))
    priority = forms.ChoiceField(required=False, label=_('Priority'))
    status = forms.ChoiceField(required=False, label=_('Status'))
    date_range = forms.ChoiceField(
        required=False,
        label=_('Date Range'),
        choices=[
            ('', _('All Time')),
            ('today', _('Today')),
            ('yesterday', _('Yesterday')),
            ('last_7_days', _('Last 7 Days')),
            ('last_30_days', _('Last 30 Days')),
            ('last_90_days', _('Last 90 Days')),
            ('this_month', _('This Month')),
            ('last_month', _('Last Month')),
            ('this_year', _('This Year')),
            ('custom', _('Custom Range')),
        ]
    )
    start_date = forms.DateField(
        required=False,
        label=_('Start Date'),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        label=_('End Date'),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    sentiment = forms.ChoiceField(required=False, label=_('Sentiment'))
    ai_analyzed = forms.ChoiceField(
        required=False,
        label=_('AI Analysis'),
        choices=[
            ('', _('All')),
            ('true', _('Analyzed')),
            ('false', _('Not Analyzed')),
        ]
    )
    assigned_to = forms.ChoiceField(required=False, label=_('Assigned To'))

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        # Set choices for fields
        self.fields['origin'].choices = [
            ('', _('All Origins')),
            ('customer', _('Customer')),
            ('employee', _('Employee')),
            ('system', _('System Generated')),
            ('third_party', _('Third Party')),
        ]
        
        self.fields['feedback_type'].choices = [
            ('', _('All Types')),
            ('complaint', _('Complaint')),
            ('suggestion', _('Suggestion')),
            ('compliment', _('Compliment')),
            ('question', _('Question')),
            ('bug_report', _('Bug Report')),
            ('feature_request', _('Feature Request')),
            ('general', _('General')),
        ]
        
        self.fields['priority'].choices = [
            ('', _('All Priorities')),
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('critical', _('Critical')),
        ]
        
        self.fields['status'].choices = [
            ('', _('All Statuses')),
            ('new', _('New')),
            ('in_progress', _('In Progress')),
            ('pending', _('Pending')),
            ('resolved', _('Resolved')),
            ('closed', _('Closed')),
            ('reopened', _('Reopened')),
        ]
        
        self.fields['sentiment'].choices = [
            ('', _('All Sentiments')),
            ('very_negative', _('Very Negative')),
            ('negative', _('Negative')),
            ('neutral', _('Neutral')),
            ('positive', _('Positive')),
            ('very_positive', _('Very Positive')),
        ]
        
        # Set assigned_to choices based on organization members
        if organization:
            try:
                from django.apps import apps
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                # Try to get organization members
                try:
                    OrganizationMember = apps.get_model('accounts', 'OrganizationMember')
                    members = OrganizationMember.objects.filter(
                        organization=organization,
                        is_active=True
                    ).select_related('user')
                    user_choices = [(member.user.id, member.user.get_full_name() or member.user.email) 
                                   for member in members]
                except LookupError:
                    # Fallback: get all users (or implement your own logic)
                    user_choices = [(user.id, user.get_full_name() or user.email) 
                                   for user in User.objects.all()]
                    
                self.fields['assigned_to'].choices = [
                    ('', _('All Users')),
                ] + user_choices
            except Exception as e:
                self.fields['assigned_to'].choices = [('', _('All Users'))]

    def get_date_range_filter(self):
        """
        Returns a dictionary of filter parameters for the selected date range
        """
        date_range = self.cleaned_data.get('date_range')
        
        if not date_range or date_range == 'custom':
            return {}
        
        now = datetime.now()
        
        if date_range == 'today':
            return {
                'created_at__date': now.date()
            }
        elif date_range == 'yesterday':
            yesterday = now.date() - timedelta(days=1)
            return {
                'created_at__date': yesterday
            }
        elif date_range == 'last_7_days':
            seven_days_ago = now - timedelta(days=7)
            return {
                'created_at__gte': seven_days_ago
            }
        elif date_range == 'last_30_days':
            thirty_days_ago = now - timedelta(days=30)
            return {
                'created_at__gte': thirty_days_ago
            }
        elif date_range == 'last_90_days':
            ninety_days_ago = now - timedelta(days=90)
            return {
                'created_at__gte': ninety_days_ago
            }
        elif date_range == 'this_month':
            return {
                'created_at__year': now.year,
                'created_at__month': now.month
            }
        elif date_range == 'last_month':
            last_month = now.month - 1 if now.month > 1 else 12
            last_month_year = now.year if now.month > 1 else now.year - 1
            return {
                'created_at__year': last_month_year,
                'created_at__month': last_month
            }
        elif date_range == 'this_year':
            return {
                'created_at__year': now.year
            }
        
        return {}
 
     
class BulkFeedbackAnalysisForm(forms.Form):
    """
    Form for bulk feedback analysis
    """
    feedback_ids = forms.CharField(
        widget=forms.HiddenInput()
    )
    analysis_type = forms.ChoiceField(
        choices=[
            ('sentiment', _('Sentiment Analysis')),
            ('themes', _('Theme Detection')),
            ('summary', _('Summary Generation')),
            ('full', _('Full Analysis')),
        ],
        initial='sentiment',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    overwrite_existing = forms.BooleanField(
        required=False,
        initial=False,
        label=_('Overwrite existing analysis'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_feedback_ids(self):
        feedback_ids = self.cleaned_data.get('feedback_ids')
        if feedback_ids:
            try:
                ids = [uuid.UUID(id.strip()) for id in feedback_ids.split(',')]
                return ids
            except ValueError:
                raise forms.ValidationError(_('Invalid feedback IDs provided.'))
        return []

class FeedbackImportForm(forms.Form):
    """
    Form for importing feedback from file
    """
    file = forms.FileField(
        label=_('CSV File'),
        help_text=_('Upload a CSV file with feedback data'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        })
    )
    channel = forms.ModelChoiceField(
        queryset=Channel.objects.none(),
        required=True,
        label=_('Channel'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        if self.organization:
            self.fields['channel'].queryset = Channel.objects.filter(
                organization=self.organization,
                is_enabled=True
            ).order_by('name')