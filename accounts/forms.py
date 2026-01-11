
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm, PasswordResetForm,
    SetPasswordForm, PasswordChangeForm
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import validate_email
import re
from core.models import *

User = get_user_model()

class CustomUserRegistrationForm(UserCreationForm):
    """
    Custom user registration form with additional fields
    """
    email = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('your.email@example.com'),
            'autocomplete': 'email'
        }),
        help_text=_('We\'ll never share your email with anyone else.')
    )
    
    first_name = forms.CharField(
        label=_('First Name'),
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('John'),
            'autocomplete': 'given-name'
        })
    )
    
    last_name = forms.CharField(
        label=_('Last Name'),
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Doe'),
            'autocomplete': 'family-name'
        })
    )
    
    username = forms.CharField(
        label=_('Username'),
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('johndoe'),
            'autocomplete': 'username'
        }),
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.')
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        # Remove 'request' from kwargs if it exists to prevent the error
        kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field, 'widget') and hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    if isinstance(field, forms.BooleanField):
                        field.widget.attrs['class'] = 'form-check-input'
                    else:
                        field.widget.attrs['class'] = 'form-control'
            
            # Add aria-describedby for accessibility
            if field.help_text:
                field.widget.attrs['aria-describedby'] = f'{field_name}_help'
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError(
                    _('A user with this email address already exists.')
                )
        return email
    
    def clean_username(self):
        """Validate username uniqueness and format"""
        username = self.cleaned_data.get('username')
        if username:
            username = username.strip()
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError(
                    _('A user with this username already exists.')
                )
            
            # Validate username format
            if not re.match(r'^[\w.@+-]+\Z', username):
                raise forms.ValidationError(
                    _('Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters.')
                )
        return username
    
    def clean_first_name(self):
        """Validate first name"""
        first_name = self.cleaned_data.get('first_name')
        if first_name and len(first_name.strip()) < 2:
            raise forms.ValidationError(
                _('First name must be at least 2 characters long.')
            )
        return first_name.strip()
    
    def clean_last_name(self):
        """Validate last name"""
        last_name = self.cleaned_data.get('last_name')
        if last_name and len(last_name.strip()) < 2:
            raise forms.ValidationError(
                _('Last name must be at least 2 characters long.')
            )
        return last_name.strip()
    
    def save(self, commit=True):
        """Save user with cleaned data"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_active = True  # Ensure user is active
        
        if commit:
            user.save()
        return user
    
class CustomUserRegistrationForm1(UserCreationForm):
    """
    Enhanced user registration form with additional fields
    """
    email = forms.EmailField(
        label=_('Email Address'),
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email address'),
            'autocomplete': 'email',
        })
    )
    
    first_name = forms.CharField(
        label=_('First Name'),
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your first name'),
            'autocomplete': 'given-name',
        })
    )
    
    last_name = forms.CharField(
        label=_('Last Name'),
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your last name'),
            'autocomplete': 'family-name',
        })
    )
    
    phone = forms.CharField(
        label=_('Phone Number'),
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your phone number (optional)'),
            'autocomplete': 'tel',
        })
    )
    
    organization_name = forms.CharField(
        label=_('Organization Name'),
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your organization name (optional)'),
        })
    )
    
    terms_accepted = forms.BooleanField(
        label=_('I accept the Terms of Service and Privacy Policy'),
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 
                  'phone', 'organization_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Choose a username'),
                'autocomplete': 'username',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes and improve help text
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Enter a strong password'),
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Confirm your password'),
            'autocomplete': 'new-password',
        })
        
        # Customize help texts
        self.fields['username'].help_text = _('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.')
        self.fields['password1'].help_text = _(
            'Your password must contain at least 8 characters and cannot be entirely numeric.'
        )
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                _('A user with this email address already exists.'),
                code='duplicate_email'
            )
        return email.lower()
    
    def clean_username(self):
        """Validate username"""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(
                _('This username is already taken.'),
                code='duplicate_username'
            )
        return username.lower()
    
    def clean_phone(self):
        """Clean and validate phone number"""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove common separators
            phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        return phone
    
    def save(self, commit=True):
        """Save user and create associated customer profile"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create or get organization
            org_name = self.cleaned_data.get('organization_name')
            if org_name:
                from django.utils.text import slugify
                org, created = Organization.objects.get_or_create(
                    slug=slugify(org_name),
                    defaults={'name': org_name}
                )
            else:
                # Create a default personal organization
                org, created = Organization.objects.get_or_create(
                    slug=f'user-{user.username}',
                    defaults={'name': f"{user.get_full_name()}'s Organization"}
                )
            
            # Create customer profile
            Customer.objects.create(
                organization=org,
                user=user,
                customer_id=f'CUST-{user.id}',
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=self.cleaned_data.get('phone', ''),
                segment='new'
            )
        
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """
    Enhanced login form with Bootstrap styling
    """
    username = forms.CharField(
        label=_('Username or Email'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your username or email'),
            'autocomplete': 'username',
            'autofocus': True,
        })
    )
    
    password = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password'),
            'autocomplete': 'current-password',
        })
    )
    
    remember_me = forms.BooleanField(
        label=_('Remember Me'),
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )
    
    def clean_username(self):
        """Allow login with email or username"""
        username_or_email = self.cleaned_data.get('username')
        
        # Try to find user by email if @ present
        if '@' in username_or_email:
            try:
                user = User.objects.get(email__iexact=username_or_email)
                return user.username
            except User.DoesNotExist:
                pass
        
        return username_or_email


class CustomPasswordResetForm(PasswordResetForm):
    """
    Enhanced password reset form
    """
    email = forms.EmailField(
        label=_('Email Address'),
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your registered email address'),
            'autocomplete': 'email',
            'autofocus': True,
        })
    )
    
    def clean_email(self):
        """Validate that email exists (but don't reveal if it doesn't for security)"""
        email = self.cleaned_data.get('email')
        return email.lower()


class CustomSetPasswordForm(SetPasswordForm):
    """
    Enhanced set password form (used in password reset)
    """
    new_password1 = forms.CharField(
        label=_('New Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter new password'),
            'autocomplete': 'new-password',
            'autofocus': True,
        }),
        help_text=_('Your password must contain at least 8 characters and cannot be entirely numeric.')
    )
    
    new_password2 = forms.CharField(
        label=_('Confirm New Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm new password'),
            'autocomplete': 'new-password',
        })
    )


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Enhanced password change form for logged-in users
    """
    old_password = forms.CharField(
        label=_('Current Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your current password'),
            'autocomplete': 'current-password',
            'autofocus': True,
        })
    )
    
    new_password1 = forms.CharField(
        label=_('New Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter new password'),
            'autocomplete': 'new-password',
        }),
        help_text=_('Your password must contain at least 8 characters and cannot be entirely numeric.')
    )
    
    new_password2 = forms.CharField(
        label=_('Confirm New Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm new password'),
            'autocomplete': 'new-password',
        })
    )


class UserProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile information
    """
    email = forms.EmailField(
        label=_('Email Address'),
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',  # Prevent email changes
        })
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('First Name'),
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Last Name'),
            }),
        }
    
    def clean_first_name(self):
        """Validate first name"""
        first_name = self.cleaned_data.get('first_name')
        if not first_name or not first_name.strip():
            raise ValidationError(_('First name is required.'))
        return first_name.strip()
    
    def clean_last_name(self):
        """Validate last name"""
        last_name = self.cleaned_data.get('last_name')
        if not last_name or not last_name.strip():
            raise ValidationError(_('Last name is required.'))
        return last_name.strip()


class CustomerProfileUpdateForm(forms.ModelForm):
    """
    Form for updating customer-specific profile information
    """
    class Meta:
        model = Customer
        fields = ('phone', 'language_preference', 'country', 'timezone')
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Phone Number'),
            }),
            'language_preference': forms.Select(attrs={
                'class': 'form-control',
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Country'),
            }),
            'timezone': forms.Select(attrs={
                'class': 'form-control',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add language choices
        self.fields['language_preference'].widget.choices = [
            ('en', _('English')),
            ('es', _('Spanish')),
            ('fr', _('French')),
            ('de', _('German')),
            ('zh', _('Chinese')),
            ('ja', _('Japanese')),
            ('ar', _('Arabic')),
        ]
        
        # Add timezone choices (common ones)
        self.fields['timezone'].widget.choices = [
            ('UTC', 'UTC'),
            ('America/New_York', 'Eastern Time'),
            ('America/Chicago', 'Central Time'),
            ('America/Denver', 'Mountain Time'),
            ('America/Los_Angeles', 'Pacific Time'),
            ('Europe/London', 'London'),
            ('Europe/Paris', 'Paris'),
            ('Asia/Tokyo', 'Tokyo'),
            ('Asia/Shanghai', 'Shanghai'),
            ('Australia/Sydney', 'Sydney'),
        ]


class EmailChangeForm(forms.Form):
    """
    Form for changing user email with confirmation
    """
    new_email = forms.EmailField(
        label=_('New Email Address'),
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter new email address'),
            'autofocus': True,
        })
    )
    
    confirm_email = forms.EmailField(
        label=_('Confirm Email Address'),
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm new email address'),
        })
    )
    
    password = forms.CharField(
        label=_('Current Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your current password to confirm'),
        }),
        help_text=_('For security, please enter your current password.')
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_new_email(self):
        """Validate new email"""
        new_email = self.cleaned_data.get('new_email')
        
        if User.objects.filter(email=new_email).exclude(pk=self.user.pk).exists():
            raise ValidationError(
                _('This email address is already in use.'),
                code='duplicate_email'
            )
        
        if new_email == self.user.email:
            raise ValidationError(
                _('This is already your current email address.'),
                code='same_email'
            )
        
        return new_email.lower()
    
    def clean_password(self):
        """Verify current password"""
        password = self.cleaned_data.get('password')
        
        if not self.user.check_password(password):
            raise ValidationError(
                _('The password you entered is incorrect.'),
                code='incorrect_password'
            )
        
        return password
    
    def clean(self):
        """Validate that emails match"""
        cleaned_data = super().clean()
        new_email = cleaned_data.get('new_email')
        confirm_email = cleaned_data.get('confirm_email')
        
        if new_email and confirm_email and new_email != confirm_email:
            raise ValidationError(
                _('The email addresses do not match.'),
                code='email_mismatch'
            )
        
        return cleaned_data


class AccountDeletionForm(forms.Form):
    """
    Form for account deletion with confirmation
    """
    confirmation_text = forms.CharField(
        label=_('Type "DELETE" to confirm'),
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Type DELETE'),
            'autofocus': True,
        }),
        help_text=_('This action cannot be undone. All your data will be permanently deleted.')
    )
    
    password = forms.CharField(
        label=_('Current Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password to confirm'),
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_confirmation_text(self):
        """Validate confirmation text"""
        text = self.cleaned_data.get('confirmation_text')
        
        if text.upper() != 'DELETE':
            raise ValidationError(
                _('Please type "DELETE" to confirm account deletion.'),
                code='invalid_confirmation'
            )
        
        return text
    
    def clean_password(self):
        """Verify password"""
        password = self.cleaned_data.get('password')
        
        if not self.user.check_password(password):
            raise ValidationError(
                _('The password you entered is incorrect.'),
                code='incorrect_password'
            )
        
        return password

from django import forms
from django.utils.translation import gettext_lazy as _
from core.models import Organization, OrganizationMember

class OrganizationForm(forms.ModelForm):
    """
    Form for creating and updating organizations
    """
    class Meta:
        model = Organization
        fields = [
            'name', 'industry', 'country', 'language_code', 
            'timezone', 'logo', 'website', 'subscription_tier',
            'ai_analysis_enabled', 'monthly_feedback_limit'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter organization name')
            }),
            'industry': forms.Select(attrs={'class': 'form-select'}),
            'country': forms.Select(attrs={'class': 'form-select'}),
            'language_code': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.Select(attrs={'class': 'form-select'}),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
            'subscription_tier': forms.Select(attrs={'class': 'form-select'}),
            'monthly_feedback_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in self.Meta.widgets:
                if isinstance(field, forms.BooleanField):
                    field.widget.attrs['class'] = 'form-check-input'
                else:
                    field.widget.attrs['class'] = 'form-control'

        

        # Country choices (you can use django-countries in production)
        self.fields['country'].choices = [
            ('', _('Select Country')),
            ('US', _('United States')),
            ('CA', _('Canada')),
            ('GB', _('United Kingdom')),
            ('AU', _('Australia')),
            ('DE', _('Germany')),
            ('FR', _('France')),
            ('JP', _('Japan')),
            ('SG', _('Singapore')),
            ('TG', _('Togo')),
            ('BN', _('Benin')),
            ('BF', _('Burkina Faso')),
        ]

        # Language choices
        self.fields['language_code'].choices = [
            ('en', _('English')),
            ('es', _('Spanish')),
            ('fr', _('French')),
            ('de', _('German')),
            ('zh-hans', _('Chinese (Simplified)')),
        ]

        # Timezone choices (simplified)
        self.fields['timezone'].choices = [
            ('UTC', 'UTC'),
            ('US/Eastern', 'US/Eastern'),
            ('US/Central', 'US/Central'),
            ('US/Pacific', 'US/Pacific'),
            ('Europe/London', 'Europe/London'),
            ('Europe/Paris', 'Europe/Paris'),
            ('Asia/Tokyo', 'Asia/Tokyo'),
            ('Asia/Singapore', 'Asia/Singapore'),
        ]

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Organization.objects.filter(name=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_('An organization with this name already exists.'))
        return name

    def clean_monthly_feedback_limit(self):
        limit = self.cleaned_data.get('monthly_feedback_limit')
        if limit < 0:
            raise forms.ValidationError(_('Feedback limit cannot be negative.'))
        return limit

class OrganizationMemberForm(forms.ModelForm):
    """
    Form for adding/editing organization members
    """
    email = forms.EmailField(
        label=_('User Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter user email address')
        })
    )

    class Meta:
        model = OrganizationMember
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'})
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        from django.contrib.auth.models import User
        email = self.cleaned_data.get('email')
        
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError(_('No user found with this email address.'))
        
        user = User.objects.get(email=email)
        
        # Check if user is already a member
        if self.organization and OrganizationMember.objects.filter(
            organization=self.organization, user=user
        ).exists():
            raise forms.ValidationError(_('This user is already a member of the organization.'))
        
        return email

    def save(self, commit=True):
        from django.contrib.auth.models import User
        
        instance = super().save(commit=False)
        if self.organization:
            instance.organization = self.organization
        
        email = self.cleaned_data.get('email')
        user = User.objects.get(email=email)
        instance.user = user
        
        if commit:
            instance.save()
        
        return instance

class OrganizationSettingsForm(forms.ModelForm):
    """
    Form for organization settings
    """
    class Meta:
        model = Organization
        fields = ['settings']
        widgets = {
            'settings': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': '{"key": "value"}'
            })
        }

    def clean_settings(self):
        import json
        settings = self.cleaned_data.get('settings')
        
        if isinstance(settings, str):
            try:
                return json.loads(settings)
            except json.JSONDecodeError:
                raise forms.ValidationError(_('Invalid JSON format.'))
        
        return settings
    
#### Customer Forms
class CustomerForm(forms.ModelForm):
    """
    Form for creating/editing customers manually.
    Does NOT include organization field (set by view).
    """
    class Meta:
        model = Customer
        fields = [
            'customer_id',
            'email',
            'first_name',
            'last_name',
            'phone',
            'customer_type',
            'device_type',
            'country',
            'city',
            'segment',
        ]
        widgets = {
            'customer_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Leave blank to auto-generate')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('customer@example.com')
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('First Name')
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Last Name')
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('+1234567890')
            }),
            'customer_type': forms.Select(attrs={'class': 'form-control'}),
            'device_type': forms.Select(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Country')
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('City')
            }),
            'segment': forms.Select(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'customer_id': _('Leave blank to auto-generate a unique customer ID'),
            'email': _('Primary email address for the customer'),
            'segment': _('Customer segmentation category'),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        
        # Make fields optional based on your business rules
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['phone'].required = False
        self.fields['device_type'].required = False
        self.fields['country'].required = False
        self.fields['city'].required = False
        
        # If editing, make customer_id read-only
        if self.instance and self.instance.pk:
            self.fields['customer_id'].widget.attrs['readonly'] = True
            self.fields['customer_id'].help_text = _('Customer ID cannot be changed')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and self.organization:
            # Check for duplicate email within the same organization
            existing = Customer.objects.filter(
                organization=self.organization,
                email=email
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError(
                    _('A customer with this email already exists in this organization.')
                )
        return email

    def clean_customer_id(self):
        customer_id = self.cleaned_data.get('customer_id')
        if customer_id and self.organization:
            # Check for duplicate customer_id within the same organization
            existing = Customer.objects.filter(
                organization=self.organization,
                customer_id=customer_id
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError(
                    _('A customer with this ID already exists in this organization.')
                )
        return customer_id


class CustomerFilterForm(forms.Form):
    """
    Form for filtering and searching customers
    """
    SORT_CHOICES = [
        ('-created_at', _('Newest First')),
        ('created_at', _('Oldest First')),
        ('first_name', _('First Name (A-Z)')),
        ('-first_name', _('First Name (Z-A)')),
        ('email', _('Email (A-Z)')),
        ('-email', _('Email (Z-A)')),
    ]
    
    search = forms.CharField(
        label=_('Search'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by name, email, or customer ID...'),
        })
    )
    
    segment = forms.ChoiceField(
        label=_('Segment'),
        required=False,
        initial='',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort_by = forms.ChoiceField(
        label=_('Sort By'),
        required=False,
        initial='-created_at',
        choices=SORT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['segment'].choices = [('', _('All Segments'))]
        
class CustomerFilterForm1(forms.Form):
    """Form for filtering customers - unchanged"""
    SORT_CHOICES = [
        ('-created_at', _('Newest First')),
        ('created_at', _('Oldest First')),
        ('first_name', _('First Name (A-Z)')),
        ('-first_name', _('First Name (Z-A)')),
        ('email', _('Email (A-Z)')),
        ('-email', _('Email (Z-A)')),
    ]
    
    search = forms.CharField(
        label=_('Search'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by name, email, or customer ID...'),
            'autocomplete': 'off'
        })
    )
    
    segment = forms.ChoiceField(
        label=_('Segment'),
        required=False,
        initial='',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort_by = forms.ChoiceField(
        label=_('Sort By'),
        required=False,
        initial='-created_at',
        choices=SORT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        segment_choices = [('', _('All Segments'))]
        self.fields['segment'].choices = segment_choices
 
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 
            'sku', 
            'category', 
            'description', 
            'image', 
            'is_service', 
            'metadata'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter product name')
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter SKU (optional)')
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter category (optional)')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Enter product description (optional)')
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'is_service': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        # Add JSON field for metadata with better styling
        self.fields['metadata'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Enter additional metadata as JSON (optional)')
        })
        
        if self.instance and self.instance.metadata:
            import json
            self.initial['metadata'] = json.dumps(self.instance.metadata, indent=2)

    def clean_metadata(self):
        metadata = self.cleaned_data.get('metadata')
        if metadata:
            try:
                import json
                if isinstance(metadata, str):
                    return json.loads(metadata)
                return metadata
            except json.JSONDecodeError:
                raise forms.ValidationError(_('Invalid JSON format for metadata'))
        return {}

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        if sku and self.organization:
            queryset = Product.objects.filter(organization=self.organization, sku=sku)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError(
                    _('A product with this SKU already exists in your organization.')
                )
        return sku