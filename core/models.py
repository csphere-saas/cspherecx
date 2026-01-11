import os
import uuid
import json
import logging
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from django.contrib.postgres.fields import ArrayField
# Third-party Libraries
from django.db import models
from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, AbstractUser
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.validators import (
    MinValueValidator, MaxValueValidator, FileExtensionValidator,
    URLValidator, EmailValidator, RegexValidator, MinLengthValidator
)
from django.core.exceptions import ValidationError
from django_countries.fields import CountryField
from timezone_field import TimeZoneField
import pandas as pd
from common.utils import *
from django_random_id_model import RandomIDModel
from django.utils.text import slugify
import secrets
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from typing import Dict, Any, Optional, List, Union
import json
import logging
from datetime import datetime, date
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import uuid
import hashlib
from surveys.services.ai_sentiment_service import SurveySentimentAnalyzer            
 
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import uuid
import hashlib

# Make sure these imports are available in your project

from common.utils import TIME_ZONES
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import logging
from uuid import UUID
import json
import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save



# Make sure these imports are available in your project

from common.utils import *

# Configure logger
logger = logging.getLogger(__name__)

class TimeStampedModel(models.Model):
    """Abstract base model for timestamp tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True, db_index=True)

    class Meta:
        abstract = True

class Organization(TimeStampedModel):
    """
    Multi-tenant organization model for companies using the CX platform
    """
    name = models.CharField(_('Organization Name'), max_length=255, unique=True)
    slug = models.SlugField(_('Slug'), max_length=255, unique=True, db_index=True)
    industry = models.CharField(_('Industry'), max_length=100, choices=DOMAIN_EXPERTISE, blank=True)
    country = models.CharField(_('Country'), max_length=100, choices=COUNTRIES, blank=True)
    language_code = models.CharField(_('Primary Language'), max_length=10, choices=LANGUAGES, default='en')
    timezone = models.CharField(_('Timezone'), max_length=50, choices=TIME_ZONES, default='UTC')
    logo = models.ImageField(_('Logo'), upload_to='organizations/logos/', null=True, blank=True)
    website = models.URLField(_('Website'), blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_organizations'
    ) 
    
    subscription_tier = models.CharField(
        _('Subscription Tier'),
        max_length=50,
        choices=[
            ('free', _('Free')),
            ('basic', _('Basic')),
            ('professional', _('Professional')),
            ('enterprise', _('Enterprise')),
        ],
        default='free'
    )
    ai_analysis_enabled = models.BooleanField(_('AI Analysis Enabled'), default=True)
    monthly_feedback_limit = models.IntegerField(_('Monthly Feedback Limit'), default=1000)
    
    settings = models.JSONField(_('Organization Settings'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Organization')
        verbose_name_plural = _('Organizations')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

def pre_save_organization(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)    
        
class OrganizationMember(TimeStampedModel):
    """
    Model for organization members with roles
    """
    ORGANIZATION_ROLES = [
        ('owner', _('Owner')),
        ('admin', _('Administrator')),
        ('manager', _('Manager')),
        ('analyst', _('Analyst')),
        ('viewer', _('Viewer')),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name=_('Organization'),
        null=True,  # ← CRITICAL: Make nullable to bypass form validation
        blank=True  # ← Allow form to not require it  
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
        verbose_name=_('User')
    )
    role = models.CharField(
        _('Role'),
        max_length=20,
        choices=ORGANIZATION_ROLES,
        default='viewer'
    )
    is_active = models.BooleanField(_('Is Active'), default=True)

    class Meta:
        verbose_name = _('Organization Member')
        verbose_name_plural = _('Organization Members')
        unique_together = ['organization', 'user']
        ordering = ['organization', 'role']

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.get_role_display()})"

    @property
    def can_manage_organization(self):
        return self.role in ['owner', 'admin']

    @property
    def can_manage_users(self):
        return self.role in ['owner', 'admin', 'manager']

class Invitation(TimeStampedModel):
    ORGANIZATION_ROLES = [
        ('owner', _('Owner')),
        ('admin', _('Administrator')),
        ('manager', _('Manager')),
        ('analyst', _('Analyst')),
        ('viewer', _('Viewer')),
    ]
     
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=OrganizationMember.ORGANIZATION_ROLES)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('sent', _('Sent')),
            ('accepted', _('Accepted')),
            ('expired', _('Expired')),
            ('cancelled', _('Cancelled')),
        ],
        default='pending',
        db_index=True
    )
    accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_invitations',
        verbose_name=_('Accepted By')
    )
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    # Track invitation attempts
    sent_count = models.IntegerField(_('Sent Count'), default=0)
    last_sent_at = models.DateTimeField(_('Last Sent At'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Invitation')
        verbose_name_plural = _('Invitations')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'status']),
            models.Index(fields=['token', 'status']),
            models.Index(fields=['expires_at', 'status']),
        ]

    def __str__(self):
        return f"Invitation to {self.email} for {self.organization.name}"

    def save(self, *args, **kwargs):
        # Generate token if not set
        if not self.token:
            self.token = self.generate_token()
        
        # Set expiration date if not set (default 7 days)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        
        super().save(*args, **kwargs)

    def generate_token(self):
        """Generate a secure invitation token"""
        # Use Django's get_random_string for cryptographically secure tokens
        return get_random_string(length=64)

    @property
    def is_expired(self):
        """Check if invitation is expired"""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if invitation is valid (not expired or cancelled)"""
        return (
            self.status in ['pending', 'sent'] and 
            not self.is_expired
        )

    def mark_as_sent(self):
        """Mark invitation as sent"""
        self.status = 'sent'
        self.sent_count += 1
        self.last_sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_count', 'last_sent_at', 'updated_at'])

    def accept(self, user):
        """Accept invitation for a user"""
        if not self.is_valid:
            return False
        
        # Create organization membership
        OrganizationMember.objects.create(
            organization=self.organization,
            user=user,
            role=self.role,
            is_active=True
        )
        
        # Update invitation status
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.accepted_by = user
        self.save(update_fields=['status', 'accepted_at', 'accepted_by', 'updated_at'])
        
        return True

    def cancel(self):
        """Cancel the invitation"""
        self.status = 'cancelled'
        self.save(update_fields=['status', 'updated_at'])
        
    def resend(self):
        """Reset invitation for resending"""
        if self.status in ['cancelled', 'expired']:
            # Generate new token for security
            self.token = self.generate_token()
            self.expires_at = timezone.now() + timedelta(days=7)
        
        self.status = 'pending'
        self.save(update_fields=['token', 'expires_at', 'status', 'updated_at'])

    def get_absolute_url(self):
        """Get absolute URL for invitation acceptance"""
        from django.urls import reverse
        return reverse('accounts:accept-invitation', kwargs={'token': self.token})

    def get_invitation_link(self, request=None):
        """Get full invitation link"""
        if request:
            return request.build_absolute_uri(self.get_absolute_url())
        # Fallback to relative URL
        return self.get_absolute_url()
    
   

class Customer(TimeStampedModel):
    """
    Customer model with comprehensive profile information
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='customers',
        verbose_name=_('Organization')
    )
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_profile',
        verbose_name=_('User Account')
    )
    
    # Basic Information
    customer_id = models.CharField(_('Customer ID'), max_length=100, db_index=True)
    email = models.EmailField(_('Email'), db_index=True)
    first_name = models.CharField(_('First Name'), max_length=100, blank=True)
    last_name = models.CharField(_('Last Name'), max_length=100, blank=True)
    phone = models.CharField(_('Phone Number'), max_length=50, blank=True)
    
    # Demographics
    language_preference = models.CharField(
        _('Language Preference'), 
        max_length=10, 
        default='en'
    )
    country = models.CharField(_('Country'), max_length=100, blank=True)
    city = models.CharField(_('City'), max_length=100, blank=True)
    timezone = models.CharField(
        _('Timezone'), 
        max_length=50, 
        choices=TIME_ZONES, 
        default='UTC'
    )
    
    # Customer Type
    CUSTOMER_TYPES = [
        ('authenticated', _('Authenticated User')),
        ('identified', _('Identified (Email/Phone)')),
        ('anonymous', _('Anonymous')),
        ('bot', _('Bot/Suspicious')),
    ]
    customer_type = models.CharField(
        _('Customer Type'),
        max_length=20,
        choices=CUSTOMER_TYPES,
        default='anonymous',
        db_index=True
    )
    
    # Customer Segmentation
    segment = models.CharField(
        _('Customer Segment'),
        max_length=50,
        choices=[
            ('vip', _('VIP')),
            ('loyal', _('Loyal')),
            ('regular', _('Regular')),
            ('new', _('New')),
            ('at_risk', _('At Risk')),
            ('churned', _('Churned')),
            ('anonymous', _('Anonymous')),
        ],
        default='new',
        db_index=True
    )
    
    lifetime_value = models.DecimalField(
        _('Lifetime Value'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Engagement Metrics
    total_interactions = models.IntegerField(_('Total Interactions'), default=0)
    total_purchases = models.IntegerField(_('Total Purchases'), default=0)
    last_interaction_date = models.DateTimeField(_('Last Interaction'), null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    tags = models.ManyToManyField('Tag', related_name='customers', blank=True, verbose_name=_('Tags'))
    
    # Device and Technical Information
    device_type = models.CharField(
        _('Device Type'),
        max_length=50,
        choices=[
            ('desktop', _('Desktop')),
            ('mobile', _('Mobile')),
            ('tablet', _('Tablet')),
            ('other', _('Other')),
        ],
        null=True,
        blank=True
    )
    
    device_fingerprint = models.CharField(
        _('Device Fingerprint'),
        max_length=255,
        blank=True,
        help_text=_('Hash of device characteristics for anonymous identification')
    )
    
    user_agent = models.TextField(
        _('User Agent'),
        blank=True,
        help_text=_('Raw user agent string from the browser')
    )
    
    # Location Information
    ip_address = models.GenericIPAddressField(
        _('IP Address'),
        null=True,
        blank=True,
        help_text=_('Customer IP address')
    )
    
    latitude = models.DecimalField(
        _('Latitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('Geographical latitude')
    )
    
    longitude = models.DecimalField(
        _('Longitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('Geographical longitude')
    )
    
    region = models.CharField(_('Region/State'), max_length=100, blank=True)
    country_code = models.CharField(_('Country Code'), max_length=2, blank=True)
    
    # Network Information
    isp = models.CharField(
        _('Internet Service Provider'),
        max_length=200,
        blank=True,
        help_text=_('Detected ISP from IP address')
    )
    
    connection_type = models.CharField(
        _('Connection Type'),
        max_length=50,
        choices=[
            ('broadband', _('Broadband')),
            ('cellular', _('Cellular')),
            ('wifi', _('WiFi')),
            ('corporate', _('Corporate')),
            ('unknown', _('Unknown')),
        ],
        default='unknown'
    )
    
    # Session and Tracking
    session_id = models.CharField(
        _('Session ID'),
        max_length=100,
        blank=True,
        help_text=_('Browser session identifier')
    )
    
    browser_family = models.CharField(_('Browser Family'), max_length=100, blank=True)
    browser_version = models.CharField(_('Browser Version'), max_length=50, blank=True)
    os_family = models.CharField(_('Operating System'), max_length=100, blank=True)
    os_version = models.CharField(_('OS Version'), max_length=50, blank=True)
    
    # Screen Information
    screen_resolution = models.CharField(
        _('Screen Resolution'),
        max_length=20,
        blank=True,
        help_text=_('Format: widthxheight, e.g., 1920x1080')
    )
    
    color_depth = models.IntegerField(
        _('Color Depth'),
        null=True,
        blank=True,
        help_text=_('Screen color depth in bits')
    )
    
    timezone_offset = models.IntegerField(
        _('Timezone Offset'),
        null=True,
        blank=True,
        help_text=_('Timezone offset from UTC in minutes')
    )
    
    # Trust score (for fraud detection)
    trust_score = models.FloatField(
        _('Trust Score'),
        default=1.0,
        help_text=_('Score from 0.0 (untrusted) to 1.0 (fully trusted)')
    )

    class Meta:
        verbose_name = _('Customer')
        verbose_name_plural = _('Customers')
        ordering = ['-created_at']
        unique_together = [['organization', 'customer_id'], ['organization', 'email']]
        indexes = [
            models.Index(fields=['organization', 'email']),
            models.Index(fields=['organization', 'customer_id']),
            models.Index(fields=['segment']),
            models.Index(fields=['last_interaction_date']),
            models.Index(fields=['customer_type']),
            models.Index(fields=['trust_score']),
        ]

    def __str__(self):
        if self.customer_type == 'anonymous':
            return f"Anonymous Customer - {self.customer_id} - {self.organization.name}"
        return f"{self.email} - {self.organization.name}"

    def get_full_name(self):
        """Return full name or email if no name provided"""
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email
    
    @property
    def location_string(self):
        """Return formatted location string"""
        parts = []
        if self.city:
            parts.append(self.city)
        if self.region:
            parts.append(self.region)
        if self.country:
            parts.append(self.country)
        return ', '.join(parts) if parts else 'Unknown'

    @property
    def device_string(self):
        """Return formatted device information"""
        parts = []
        if self.device_type:
            parts.append(self.device_type.title())
        if self.browser_family:
            parts.append(self.browser_family)
        if self.os_family:
            parts.append(f"({self.os_family})")
        return ' '.join(parts) if parts else 'Unknown'

    def update_trust_score(self):
        """Update trust score based on available data"""
        score = 1.0  # Start with perfect trust
        
        # Deduct points for suspicious indicators
        if not self.email or '@anonymous.com' in self.email:
            score -= 0.1  # Anonymous email
        
        if not self.ip_address:
            score -= 0.1  # No IP
        
        if self.customer_type == 'bot':
            score = 0.0  # Bots are not trusted
        
        # Add points for positive indicators
        if self.customer_type == 'authenticated':
            score += 0.2  # Authenticated users are more trusted
        
        if self.total_interactions > 0:
            # More interactions = more trust
            bonus = min(0.3, self.total_interactions * 0.01)
            score += bonus
        
        if self.lifetime_value and self.lifetime_value > Decimal('100.00'):
            score += 0.1  # Higher value customers are more trusted
        
        # Ensure score stays within bounds
        self.trust_score = max(0.0, min(1.0, score))
        self.save(update_fields=['trust_score', 'updated_at'])
        
        return self.trust_score

    def create_device_fingerprint(self, request=None, user_agent=None):
        """Create a device fingerprint from available data"""
        fingerprint_data = []
        
        # Use provided user agent or get from request
        if request and not user_agent:
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        if user_agent:
            fingerprint_data.append(user_agent)
            
            # Accept headers from request
            if request:
                accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
                accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
                fingerprint_data.extend([accept_language, accept_encoding])
        
        # Add device-specific data
        if self.screen_resolution:
            fingerprint_data.append(self.screen_resolution)
        if self.color_depth:
            fingerprint_data.append(str(self.color_depth))
        if self.timezone_offset:
            fingerprint_data.append(str(self.timezone_offset))
        if self.browser_family and self.browser_version:
            fingerprint_data.append(f"{self.browser_family}/{self.browser_version}")
        if self.os_family and self.os_version:
            fingerprint_data.append(f"{self.os_family}/{self.os_version}")
        
        # Create hash
        fingerprint_string = '|'.join(filter(None, fingerprint_data))
        if fingerprint_string:
            self.device_fingerprint = hashlib.sha256(fingerprint_string.encode()).hexdigest()
            self.save(update_fields=['device_fingerprint', 'updated_at'])
        
        return self.device_fingerprint
    
    def _parse_user_agent(self, user_agent=None):
        """Parse user agent string to extract browser and OS info"""
        if not user_agent:
            user_agent = self.user_agent
        
        if not user_agent:
            return
        
        ua = user_agent.lower()
        
        # Browser detection
        if 'chrome' in ua and 'edg' not in ua:
            self.browser_family = 'Chrome'
            # Try to extract version
            import re
            version_match = re.search(r'chrome/(\d+\.\d+)', ua)
            if version_match:
                self.browser_version = version_match.group(1)
        elif 'firefox' in ua:
            self.browser_family = 'Firefox'
            version_match = re.search(r'firefox/(\d+\.\d+)', ua)
            if version_match:
                self.browser_version = version_match.group(1)
        elif 'safari' in ua and 'chrome' not in ua:
            self.browser_family = 'Safari'
            version_match = re.search(r'version/(\d+\.\d+)', ua)
            if version_match:
                self.browser_version = version_match.group(1)
        elif 'edg' in ua:
            self.browser_family = 'Edge'
            version_match = re.search(r'edg/(\d+\.\d+)', ua)
            if version_match:
                self.browser_version = version_match.group(1)
        
        # OS detection
        if 'windows' in ua:
            self.os_family = 'Windows'
            if 'windows nt 10.0' in ua:
                self.os_version = '10'
            elif 'windows nt 6.3' in ua:
                self.os_version = '8.1'
            elif 'windows nt 6.2' in ua:
                self.os_version = '8'
            elif 'windows nt 6.1' in ua:
                self.os_version = '7'
        elif 'mac' in ua:
            self.os_family = 'macOS'
            version_match = re.search(r'mac os x (\d+[._]\d+)', ua)
            if version_match:
                self.os_version = version_match.group(1).replace('_', '.')
        elif 'linux' in ua:
            self.os_family = 'Linux'
        elif 'android' in ua:
            self.os_family = 'Android'
            version_match = re.search(r'android (\d+\.\d+)', ua)
            if version_match:
                self.os_version = version_match.group(1)
        elif 'ios' in ua or 'iphone' in ua:
            self.os_family = 'iOS'
            version_match = re.search(r'os (\d+[._]\d+)', ua)
            if version_match:
                self.os_version = version_match.group(1).replace('_', '.')
        
        # Save parsed data
        if self.browser_family or self.os_family:
            update_fields = ['updated_at']
            if self.browser_family:
                update_fields.append('browser_family')
            if self.browser_version:
                update_fields.append('browser_version')
            if self.os_family:
                update_fields.append('os_family')
            if self.os_version:
                update_fields.append('os_version')
            
            self.save(update_fields=update_fields)
    
    def increment_interactions(self, interaction_type='general'):
        """Increment interaction count and update last interaction date"""
        self.total_interactions += 1
        self.last_interaction_date = timezone.now()
        
        # Update metadata with interaction history
        metadata = self.metadata.copy()
        interactions = metadata.get('interactions', [])
        interactions.append({
            'type': interaction_type,
            'timestamp': timezone.now().isoformat(),
            'count': self.total_interactions
        })
        metadata['interactions'] = interactions[-100:]  # Keep last 100 interactions
        
        self.metadata = metadata
        self.save(update_fields=[
            'total_interactions', 
            'last_interaction_date', 
            'metadata', 
            'updated_at'
        ])
    
    def update_location_from_ip(self):
        """Update location information from IP address (requires geoip service)"""
        if not self.ip_address:
            return False
        
        try:
            # This would typically use a geoip service like ipinfo.io or maxmind
            # For now, this is a placeholder implementation
            # In production, you would:
            # 1. Call a geoip API service
            # 2. Parse the response
            # 3. Update location fields
            
            # Example with ipinfo.io (requires requests library and API key)
            # import requests
            # response = requests.get(f'https://ipinfo.io/{self.ip_address}/json?token=YOUR_TOKEN')
            # data = response.json()
            # self.city = data.get('city', '')
            # self.region = data.get('region', '')
            # self.country = data.get('country', '')
            # self.country_code = data.get('country', '')
            # self.latitude, self.longitude = data.get('loc', ',').split(',')
            
            # For now, just mark as attempted
            metadata = self.metadata.copy()
            metadata['location_update_attempted'] = timezone.now().isoformat()
            self.metadata = metadata
            
            self.save(update_fields=['metadata', 'updated_at'])
            return True
            
        except Exception as e:
            logger.error(f"Failed to update location for customer {self.id}: {str(e)}")
            return False
    
    @classmethod
    def get_or_create_anonymous(cls, organization, request=None, **kwargs):
        """Convenience method to get or create an anonymous customer"""
        try:
            # Try to find existing anonymous customer by device fingerprint
            if request and hasattr(request, 'session'):
                session_id = request.session.session_key
                if session_id:
                    customer = cls.objects.filter(
                        organization=organization,
                        customer_type='anonymous',
                        session_id=session_id
                    ).first()
                    if customer:
                        return customer, False
            
            # Create new anonymous customer
            customer = cls.anonymous_customers.create_anonymous(
                organization=organization,
                request=request,
                **kwargs
            )
            return customer, True
            
        except Exception as e:
            logger.error(f"Error in get_or_create_anonymous: {str(e)}")
            # Fallback: create without request
            customer = cls.objects.create(
                organization=organization,
                customer_id=f"anon_emergency_{uuid.uuid4().hex[:8]}",
                email=f"anon_emergency_{uuid.uuid4().hex[:8]}@anonymous.com",
                customer_type='anonymous',
                segment='anonymous',
                **kwargs
            )
            return customer, True
    
    def convert_to_identified(self, email, **kwargs):
        """Convert anonymous customer to identified customer"""
        if self.customer_type != 'anonymous':
            raise ValueError("Only anonymous customers can be converted to identified")
        
        # Check if email already exists in this organization
        existing = Customer.objects.filter(
            organization=self.organization,
            email=email
        ).exclude(id=self.id).first()
        
        if existing:
            # Merge data into existing customer
            existing.total_interactions += self.total_interactions
            existing.metadata.update(self.metadata)
            existing.save()
            self.delete()
            return existing
        
        # Convert this customer
        self.email = email
        self.customer_type = 'identified'
        self.customer_id = f"id_{uuid.uuid4().hex[:8]}"  # New ID for identified user
        
        # Update other fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.save()
        return self


class Channel(TimeStampedModel):
    """
    Feedback collection channels (email, chat, phone, social media, etc.)
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='channels',
        verbose_name=_('Organization')
    )
    name = models.CharField(_('Channel Name'), max_length=100)
    channel_type = models.CharField(
        _('Channel Type'),
        max_length=50,
        choices=[
            ('email', _('Email')),
            ('phone', _('Phone')),
            ('chat', _('Live Chat')),
            ('social_media', _('Social Media')),
            ('web_form', _('Web Form')),
            ('in_app', _('In-App')),
            ('sms', _('SMS')),
            ('survey', _('Survey')),
            ('review_site', _('Review Site')),
            ('other', _('Other')),
        ],
        db_index=True
    )
    description = models.TextField(_('Description'), blank=True)
    is_enabled = models.BooleanField(_('Enabled'), default=True)
    configuration = models.JSONField(_('Channel Configuration'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Channel')
        verbose_name_plural = _('Channels')
        ordering = ['name']
        unique_together = [['organization', 'name']]

    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"

class Product(TimeStampedModel):
    """
    Products or services that feedback can be associated with
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name=_('Organization')
    )
    name = models.CharField(_('Product Name'), max_length=255)
    sku = models.CharField(_('SKU'), max_length=100, blank=True, db_index=True)
    category = models.CharField(_('Category'), max_length=100, blank=True, db_index=True)
    description = models.TextField(_('Description'), blank=True)
    image = models.ImageField(_('Product Image'), upload_to='products/', null=True, blank=True)
    is_service = models.BooleanField(_('Is Service'), default=False)
    
    # Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['name']
        unique_together = [['organization', 'sku']]
        indexes = [
            models.Index(fields=['organization', 'category']),
        ]

    def __str__(self):
        return self.name
    
class Tag(TimeStampedModel):
    """
    Flexible tagging system for categorization
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='tags',
        verbose_name=_('Organization')
    )
    name = models.CharField(_('Tag Name'), max_length=100)
    slug = models.SlugField(_('Slug'), max_length=100)
    category = models.CharField(
        _('Tag Category'),
        max_length=50,
        choices=[
            ('issue', _('Issue Type')),
            ('priority', _('Priority')),
            ('department', _('Department')),
            ('feature', _('Feature')),
            ('custom', _('Custom')),
        ],
        default='custom'
    )
    color = models.CharField(_('Color Code'), max_length=7, default='#000000')
    description = models.TextField(_('Description'), blank=True)
    
    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        ordering = ['name']
        unique_together = [['organization', 'slug']]

    def __str__(self):
        return self.name

class Feedback(TimeStampedModel):
    """
    Core feedback/complaint model for capturing customer input
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='feedbacks',
        verbose_name=_('Organization'),
        
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='feedbacks',
        verbose_name=_('Customer')
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.SET_NULL,
        null=True,
        related_name='feedbacks',
        verbose_name=_('Channel')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedbacks',
        verbose_name=_('Product')
    )
    
    # Feedback Content
    feedback_id = models.CharField(_('Feedback ID'), max_length=100, unique=True, db_index=True)
    subject = models.CharField(_('Subject'), max_length=500, blank=True)
    content = models.TextField(_('Feedback Content'))
    original_language = models.CharField(_('Original Language'), max_length=10, default='en')
    translated_content = models.TextField(_('Translated Content'), blank=True)
    origin = models.CharField(
        _('Feedback Origin'),
        max_length=20,
        choices=[
            ('customer', _('Customer')),
            ('employee', _('Employee')),
            ('system', _('System Generated')),
            ('third_party', _('Third Party')),
        ],
        default='customer'
    ) 
    # Classification
    feedback_type = models.CharField(
        _('Feedback Type'),
        max_length=50,
        choices=[
            ('complaint', _('Complaint')),
            ('suggestion', _('Suggestion')),
            ('compliment', _('Compliment')),
            ('question', _('Question')),
            ('bug_report', _('Bug Report')),
            ('feature_request', _('Feature Request')),
            ('general', _('General')),
        ],
        default='general',
        db_index=True
    )
    priority = models.CharField(
        _('Priority'),
        max_length=20,
        choices=[
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('critical', _('Critical')),
        ],
        default='medium',
        db_index=True
    )
    status = models.CharField(
        _('Status'),
        max_length=50,
        choices=[
            ('new', _('New')),
            ('in_progress', _('In Progress')),
            ('pending', _('Pending')),
            ('resolved', _('Resolved')),
            ('closed', _('Closed')),
            ('reopened', _('Reopened')),
        ],
        default='new',
        db_index=True
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_feedbacks',
        verbose_name=_('Assigned To')
    )
    assigned_at = models.DateTimeField(_('Assigned At'), null=True, blank=True)
    
    # AI Analysis Flags
    ai_analyzed = models.BooleanField(_('AI Analyzed'), default=False, db_index=True)
    ai_analysis_date = models.DateTimeField(_('AI Analysis Date'), null=True, blank=True)
    requires_human_review = models.BooleanField(_('Requires Human Review'), default=False)
    
    # Sentiment (quick reference, detailed in SentimentAnalysis model)
    sentiment_score = models.FloatField(
        _('Sentiment Score'),
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        db_index=True
    )
    sentiment_label = models.CharField(
        _('Sentiment Label'),
        max_length=20,
        choices=[
            ('very_negative', _('Very Negative')),
            ('negative', _('Negative')),
            ('neutral', _('Neutral')),
            ('positive', _('Positive')),
            ('very_positive', _('Very Positive')),
        ],
        null=True,
        blank=True,
        db_index=True
    )
    
    # Resolution
    resolution_time = models.DurationField(_('Resolution Time'), null=True, blank=True)
    resolved_at = models.DateTimeField(_('Resolved At'), null=True, blank=True)
    closed_at = models.DateTimeField(_('Closed At'), null=True, blank=True)
    
    # Attachments and Metadata
    attachments = models.JSONField(_('Attachments'), default=list, blank=True)
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    tags = models.ManyToManyField(Tag, related_name='feedbacks', blank=True, verbose_name=_('Tags'))
    
    # Internal Notes
    internal_notes = models.TextField(_('Internal Notes'), blank=True)
    
    class Meta:
        verbose_name = _('Feedback')
        verbose_name_plural = _('Feedbacks')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'feedback_type']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['ai_analyzed', 'created_at']),
            models.Index(fields=['sentiment_label']),
            models.Index(fields=['priority', 'status']),
        ]

    def __str__(self):
        return f"{self.feedback_id}"

    def save(self, *args, **kwargs):
        if not self.feedback_id:
            # Generate unique feedback ID
            self.feedback_id = f"FB-{self.organization.slug.upper()}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def sentiment_analysis_obj(self):
        """Safely get the related sentiment analysis object"""
        try:
            # Use the related_name from OneToOneField
            return self.sentiment_analysis
        except SentimentAnalysis.DoesNotExist:
            return None
    
    @property
    def has_sentiment_analysis(self):
        """Check if feedback has sentiment analysis"""
        return hasattr(self, 'sentiment_analysis') and self.sentiment_analysis is not None
    
    @property
    def sentiment_analysis_pk(self):
        """Safely get sentiment analysis PK"""
        if self.has_sentiment_analysis:
            return self.sentiment_analysis.pk
        return None
    
    def get_sentiment_analyses(self):
        """Get all sentiment analyses for this feedback (for ForeignKey relationship)"""
        return self.sentiment_analyses.all()

class SentimentAnalysis(TimeStampedModel):
    """
    Detailed sentiment analysis results for feedback
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='sentiment_analyses',
        verbose_name=_('Organization')
    )
    
    feedback = models.OneToOneField(
        Feedback,
        on_delete=models.CASCADE,
        related_name='sentiment_analysis',
        verbose_name=_('Feedback')
    )
    
    # Overall Sentiment
    overall_score = models.FloatField(
        _('Overall Sentiment Score'),
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text=_('Sentiment score from -1.0 (negative) to 1.0 (positive)')
    )
    overall_label = models.CharField(
        _('Overall Sentiment Label'),
        max_length=20,
        choices=[
            ('very_negative', _('Very Negative')),
            ('negative', _('Negative')),
            ('neutral', _('Neutral')),
            ('positive', _('Positive')),
            ('very_positive', _('Very Positive')),
        ]
    )
    confidence_score = models.FloatField(
        _('Confidence Score'),
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('AI model confidence in the analysis (0.0 to 1.0)')
    )
    
    # Detailed Analysis
    aspects = models.JSONField(
        _('Aspect Sentiments'),
        default=dict,
        help_text=_('Sentiment analysis for different aspects (product, service, etc.)')
    )
    emotions = models.JSONField(
        _('Emotion Analysis'),
        default=dict,
        help_text=_('Detected emotions with confidence scores')
    )
    intent = models.CharField(
        _('Customer Intent'),
        max_length=100,
        null=True,
        blank=True,
        help_text=_('Primary intent of the feedback')
    )
    intent_confidence = models.FloatField(
        _('Intent Confidence'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    # Urgency and Importance
    urgency_level = models.CharField(
        _('Urgency Level'),
        max_length=20,
        choices=[
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('critical', _('Critical')),
        ],
        default='medium'
    )
    urgency_indicators = models.JSONField(
        _('Urgency Indicators'),
        default=list,
        help_text=_('Factors contributing to urgency assessment')
    )
    
    # Content Analysis
    key_phrases = models.JSONField(
        _('Key Phrases'),
        default=list,
        help_text=_('Important phrases extracted from the feedback')
    )
    entities = models.JSONField(
        _('Named Entities'),
        default=dict,
        help_text=_('Recognized entities (products, features, issues)')
    )
    
    # Language and Translation
    analysis_language = models.CharField(
        _('Analysis Language'),
        max_length=10,
        default='en',
        help_text=_('Language used for analysis')
    )
    translated_content = models.TextField(
        _('Translated Content'),
        blank=True,
        null=True,   # Allow NULL in database
        help_text=_('Content translated for analysis (if applicable)')
    )
    original_language = models.CharField(
        _('Original Language'),
        max_length=10,
        default='en',
        help_text=_('Original language of the feedback')
    )
    
    # Model Information
    model_used = models.CharField(
        _('AI Model Used'),
        max_length=100,
        default='gemini-2.5-flash'
    )
    model_version = models.CharField(
        _('Model Version'),
        max_length=50,
        default='1.0'
    )
    analysis_metadata = models.JSONField(
        _('Analysis Metadata'),
        default=dict,
        help_text=_('Additional metadata about the analysis process')
    )
    
    class Meta:
        verbose_name = _('Sentiment Analysis')
        verbose_name_plural = _('Sentiment Analyses')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['feedback']),
            models.Index(fields=['overall_label']),
            models.Index(fields=['urgency_level']),
            models.Index(fields=['confidence_score']),
        ]

    def __str__(self):
        return f"Sentiment Analysis for {self.feedback.feedback_id}"


    @property
    def is_high_confidence(self):
        return self.confidence_score >= 0.7

    @property
    def needs_human_review(self):
        return self.confidence_score < 0.65 or self.urgency_level == 'CRITICAL'
    
    @property
    def sentiment_color(self):
        """Get Bootstrap color for sentiment label"""
        color_map = {
            'very_positive': 'success',
            'positive': 'success',
            'neutral': 'secondary',
            'negative': 'warning',
            'very_negative': 'danger',
        }
        return color_map.get(self.overall_label, 'secondary')

    @property
    def sentiment_icon(self):
        """Get FontAwesome icon for sentiment label"""
        icon_map = {
            'very_positive': 'fa-smile-beam',
            'positive': 'fa-smile',
            'neutral': 'fa-meh',
            'negative': 'fa-frown',
            'very_negative': 'fa-angry',
        }
        return icon_map.get(self.overall_label, 'fa-comment')
 

class Review(TimeStampedModel):
    """
    Review model for customer reviews with sentiment tracking
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Organization')
    )
    
    # Basic review info
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name=_('Customer')
    )
    
    # Review content
    title = models.CharField(_('Review Title'), max_length=255, blank=True)
    content = models.TextField(_('Review Content'))
    
    # Rating (if applicable)
    rating = models.IntegerField(
        _('Rating'),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('Rating from 1 to 5 stars')
    )
    
    # Sentiment analysis
    sentiment_score = models.FloatField(
        _('Sentiment Score'),
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text=_('Sentiment score from -1.0 (negative) to 1.0 (positive)')
    )
    
    # Source information
    source = models.CharField(
        _('Source'),
        max_length=100,
        choices=[
            ('app_store', _('App Store')),
            ('play_store', _('Google Play Store')),
            ('website', _('Website')),
            ('social_media', _('Social Media')),
            ('third_party', _('Third Party Review Site')),
            ('other', _('Other')),
        ],
        default='website'
    )
    
    # Metadata
    source_id = models.CharField(_('Source ID'), max_length=255, blank=True)
    source_url = models.URLField(_('Source URL'), blank=True)
    is_verified = models.BooleanField(_('Verified Review'), default=False)
    is_public = models.BooleanField(_('Public Review'), default=True)
    
    # Response tracking
    has_response = models.BooleanField(_('Has Response'), default=False)
    response_content = models.TextField(_('Response Content'), blank=True)
    responded_at = models.DateTimeField(_('Responded At'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Review')
        verbose_name_plural = _('Reviews')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'sentiment_score']),
            models.Index(fields=['organization', 'rating']),
            models.Index(fields=['source', 'created_at']),
        ]

    def __str__(self):
        if self.customer:
            return f"Review by {self.customer.email}"
        return f"Review {self.id}"

    @property
    def sentiment_color(self):
        if self.sentiment_score > 0.1:
            return "success"
        elif self.sentiment_score < -0.1:
            return "danger"
        else:
            return "secondary"
    
    @property
    def sentiment_text(self):
        if self.sentiment_score > 0.1:
            return "Positive"
        elif self.sentiment_score < -0.1:
            return "Negative"
        else:
            return "Neutral"
    
    @property
    def sentiment_icon(self):
        if self.sentiment_score > 0.1:
            return "fa-smile"
        elif self.sentiment_score < -0.1:
            return "fa-frown"
        else:
            return "fa-meh"
    
    @property
    def rating_stars(self):
        """Return rating as stars string"""
        if not self.rating:
            return ""
        return "★" * self.rating + "☆" * (5 - self.rating)
        
class Theme(TimeStampedModel):
    """
    AI-generated themes/topics from customer feedback
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='themes',
        verbose_name=_('Organization')
    )
    
    # Theme Information
    name = models.CharField(_('Theme Name'), max_length=255)
    description = models.TextField(_('Description'))
    category = models.CharField(
        _('Category'),
        max_length=100,
        choices=[
            ('product_quality', _('Product Quality')),
            ('customer_service', _('Customer Service')),
            ('pricing', _('Pricing')),
            ('delivery', _('Delivery')),
            ('usability', _('Usability')),
            ('features', _('Features')),
            ('performance', _('Performance')),
            ('documentation', _('Documentation')),
            ('other', _('Other')),
        ],
        db_index=True
    )
    
    # Theme Metrics
    occurrence_count = models.IntegerField(_('Occurrence Count'), default=0)
    sentiment_distribution = models.JSONField(
        _('Sentiment Distribution'),
        default=dict,
        blank=True,
        help_text=_('Distribution of sentiments for this theme')
    )
    average_sentiment = models.FloatField(
        _('Average Sentiment'),
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)]
    )
    
    # Trend Information
    trend = models.CharField(
        _('Trend'),
        max_length=20,
        choices=[
            ('increasing', _('Increasing')),
            ('stable', _('Stable')),
            ('decreasing', _('Decreasing')),
        ],
        default='stable'
    )
    trend_percentage = models.FloatField(_('Trend Percentage'), null=True, blank=True)
    
    # FIXED: Replaced ArrayField with JSONField for database compatibility
    keywords = models.JSONField(
        _('Related Keywords'),
        default=list,
        blank=True
    )
    
    # Priority and Status
    priority = models.CharField(
        _('Priority'),
        max_length=20,
        choices=[
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('critical', _('Critical')),
        ],
        default='medium'
    )
    status = models.CharField(
        _('Status'),
        max_length=50,
        choices=[
            ('new', _('New')),
            ('acknowledged', _('Acknowledged')),
            ('in_progress', _('In Progress')),
            ('resolved', _('Resolved')),
            ('archived', _('Archived')),
        ],
        default='new'
    )
    
    # AI Generation Info
    auto_generated = models.BooleanField(_('Auto Generated'), default=True)
    generation_date = models.DateTimeField(_('Generation Date'), auto_now_add=True)
    last_analysis_date = models.DateTimeField(_('Last Analysis Date'), null=True, blank=True)
    
    # Related Products
    products = models.ManyToManyField(
        'Product',
        related_name='themes',
        blank=True,
        verbose_name=_('Related Products')
    )
    
    # Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Theme')
        verbose_name_plural = _('Themes')
        ordering = ['-occurrence_count', '-created_at']
        unique_together = [['organization', 'name']]
        indexes = [
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['-occurrence_count']),
        ]

    def __str__(self):
        return f"{self.name} ({self.occurrence_count} occurrences)"


class FeedbackTheme(TimeStampedModel):
    """
    Many-to-many relationship between Feedback and Themes with relevance score
    """
    feedback = models.ForeignKey(
        Feedback,
        on_delete=models.CASCADE,
        related_name='feedback_themes',
        verbose_name=_('Feedback')
    )
    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name='feedback_themes',
        verbose_name=_('Theme')
    )
    relevance_score = models.FloatField(
        _('Relevance Score'),
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('AI-calculated relevance of this theme to the feedback')
    )
    is_primary = models.BooleanField(_('Primary Theme'), default=False)
    
    class Meta:
        verbose_name = _('Feedback Theme')
        verbose_name_plural = _('Feedback Themes')
        ordering = ['-relevance_score']
        unique_together = [['feedback', 'theme']]
        indexes = [
            models.Index(fields=['feedback', '-relevance_score']),
        ]

    def __str__(self):
        return f"{self.theme.name} - {self.feedback.feedback_id} ({self.relevance_score:.2f})"



class Survey(TimeStampedModel):
    """
    Survey templates for structured feedback collection
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='surveys',
        verbose_name=_('Organization')
    )
    
    # Survey Information
    title = models.CharField(_('Survey Title'), max_length=255)
    description = models.TextField(_('Description'), blank=True)
    survey_type = models.CharField(
        _('Survey Type'),
        max_length=50,
        choices=[
            ('nps', _('Net Promoter Score')),
            ('csat', _('Customer Satisfaction')),
            ('ces', _('Customer Effort Score')),
            ('mixed', _('Mixed Survey')), 
            ('custom', _('Custom Survey')),
            ('transactional', _('Transactional')),
            ('relationship', _('Relationship')),
        ],
        db_index=True
    )
    
    # Survey Configuration
    questions = models.JSONField(
        _('Survey Questions'),
        default=list,
        help_text=_('List of question objects with type, text, options, etc.')
    )
    language = models.CharField(_('Survey Language'), max_length=10, choices=LANGUAGES, default='en')
    # FIXED: Replaced ArrayField with JSONField for database compatibility
    available_languages = models.JSONField(
        _('Available Languages'),
        default=list,
        blank=True,
        null=True
    )
    
    # Distribution Settings
    trigger_event = models.CharField(
        _('Trigger Event'),
        max_length=50,
        choices=[
            ('post_purchase', _('Post Purchase')),
            ('post_support', _('Post Support Interaction')),
            ('periodic', _('Periodic')),
            ('manual', _('Manual')),
            ('milestone', _('Customer Milestone')),
        ],
        null=True,
        blank=True
    )
    trigger_delay = models.DurationField(_('Trigger Delay'), null=True, blank=True)
    
    # Status and Settings
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('draft', _('Draft')),
            ('active', _('Active')),
            ('paused', _('Paused')),
            ('archived', _('Archived')),
        ],
        default='draft'
    )
    response_limit = models.IntegerField(_('Response Limit'), null=True, blank=True)
    start_date = models.DateTimeField(_('Start Date'), null=True, blank=True)
    end_date = models.DateTimeField(_('End Date'), null=True, blank=True)
    
    # Design and Branding
    theme_settings = models.JSONField(_('Theme Settings'), default=dict, blank=True)
    
    # Statistics
    total_sent = models.IntegerField(_('Total Sent'), default=0)
    total_responses = models.IntegerField(_('Total Responses'), default=0)
    response_rate = models.FloatField(_('Response Rate'), default=0.0)
    
    # Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Survey')
        verbose_name_plural = _('Surveys')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'survey_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_survey_type_display()})"
    
    @property
    def is_mixed_survey(self):
        return self.survey_type == 'mixed'


logger = logging.getLogger(__name__)

# Helper functions for JSON serialization
def convert_to_json_serializable(data):
    """Convert any data to JSON-serializable format"""
    if isinstance(data, dict):
        return {k: convert_to_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_json_serializable(item) for item in data]
    elif isinstance(data, UUID):
        return str(data)
    elif isinstance(data, (datetime.datetime, datetime.date, datetime.time)):
        return data.isoformat()
    elif isinstance(data, Decimal):
        return float(data)
    elif hasattr(data, '__dict__'):
        return str(data)
    else:
        return data


def safe_metadata_dict(instance):
    """Get metadata as a safe JSON-serializable dictionary"""
    if not hasattr(instance, 'metadata') or not instance.metadata:
        return {}
    
    metadata_copy = instance.metadata.copy() if instance.metadata else {}
    return convert_to_json_serializable(metadata_copy)

class SurveyResponse(TimeStampedModel):
    """
    Individual responses to surveys
    """
    
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name=_('Survey')
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='survey_responses',
        verbose_name=_('Customer')
    )
    survey_type = models.CharField(
        _('Survey Type'),
        max_length=50,
        choices=[
            ('nps', _('Net Promoter Score')),
            ('csat', _('Customer Satisfaction')),
            ('ces', _('Customer Effort Score')),
            ('custom', _('Custom Survey')),
            ('transactional', _('Transactional')),
            ('relationship', _('Relationship')),
            
        ],
        db_index=True,
        help_text=_('Type of survey this response belongs to')
    )

    # Response Data
    response_data = models.JSONField(
        _('Response Data'),
        help_text=_('Complete survey response with question IDs and answers')
    )
    language = models.CharField(_('Response Language'), max_length=10, default='en')
    
    # Completion Status
    is_complete = models.BooleanField(_('Complete'), default=False)
    completion_time = models.DurationField(_('Completion Time'), null=True, blank=True)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)
    started_at = models.DateTimeField(_('Started At'), null=True, blank=True)
    # Source Information
    channel = models.ForeignKey(
        Channel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='survey_responses',
        verbose_name=_('Channel')
    )
    device_type = models.CharField(
        _('Device Type'),
        max_length=50,
        choices=[
            ('desktop', _('Desktop')),
            ('mobile', _('Mobile')),
            ('tablet', _('Tablet')),
            ('other', _('Other')),
        ],
        null=True,
        blank=True
    )
    
    # AI Analysis
    ai_analyzed = models.BooleanField(_('AI Analyzed'), default=False)
    sentiment_score = models.FloatField(
        _('Overall Sentiment'),
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)]
    )
    
    # Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    sentiment_metadata = models.JSONField(
        _('Sentiment Analysis Metadata'),
        default=dict,
        blank=True,
        help_text=_('Detailed sentiment analysis results')
    )
    
    analysis_status = models.CharField(
        _('Analysis Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending Analysis')),
            ('processing', _('Processing')),
            ('completed', _('Completed')),
            ('failed', _('Failed')),
        ],
        default='pending',
        db_index=True
    )
    
    analysis_retry_count = models.IntegerField(
        _('Analysis Retry Count'),
        default=0,
        help_text=_('Number of times analysis has been retried')
    )
    

    class Meta:
        verbose_name = _('Survey Response')
        verbose_name_plural = _('Survey Responses')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['survey', 'customer']),
            models.Index(fields=['survey', 'is_complete']),
            models.Index(fields=['completed_at']),
            models.Index(fields=['analysis_status', 'created_at']),
            models.Index(fields=['sentiment_score']),
            models.Index(fields=['ai_analyzed', 'created_at']),
        ]

    def __str__(self):
        if self.customer:
            return f"{self.survey.title} - {self.customer.email} ({self.get_survey_type_display()})"
        return f"{self.survey.title} - Anonymous Response ({self.get_survey_type_display()})"

    def save(self, *args, **kwargs):
        """Ensure organization and survey_type are always set from survey before saving"""
        if self.survey:
            if not hasattr(self, 'organization'):
                self.organization = self.survey.organization
            
            # Always copy survey_type from the survey
            self.survey_type = self.survey.survey_type
        
        super().save(*args, **kwargs)
        
    @property
    def organization(self):
        """Get organization through survey"""
        if hasattr(self, '_organization'):
            return self._organization
        elif self.survey and hasattr(self.survey, 'organization'):
            return self.survey.organization
        return None
    
    
    @organization.setter
    def organization(self, value):
        """Allow setting organization directly"""
        self._organization = value
    
    def get_nps_score(self) -> Optional[int]:
        """Extract NPS score from response data for NPS surveys"""
        if self.survey_type != 'nps':
            logger.debug(f"Not an NPS survey: {self.survey_type}")
            return None
        
        try:
            response_data = self.response_data
            if not response_data:
                logger.debug(f"No response data for survey response {self.id}")
                return None
            
            # Log the structure for debugging
            logger.debug(f"NPS Response data for {self.id}: {response_data}")
            
            # Handle different response data structures
            score = self._extract_score_from_data(response_data, score_range=(0, 10))
            
            if score is not None:
                logger.debug(f"Extracted NPS score {score} for response {self.id}")
                return score
            
            # Check for nested structure (common in survey platforms)
            if isinstance(response_data, dict):
                # Look in common nested structures
                for key in ['answers', 'responses', 'data', 'questions']:
                    if key in response_data and isinstance(response_data[key], dict):
                        nested_score = self._extract_score_from_data(response_data[key], score_range=(0, 10))
                        if nested_score is not None:
                            logger.debug(f"Found NPS score {nested_score} in nested key '{key}'")
                            return nested_score
                
                # Check if it's an array of question responses
                for key, value in response_data.items():
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                item_score = self._extract_score_from_data(item, score_range=(0, 10))
                                if item_score is not None:
                                    logger.debug(f"Found NPS score {item_score} in list item")
                                    return item_score
            
            logger.warning(f"No NPS score found in response data for {self.id}, using default 5")
            return 5  # Default fallback
            
        except Exception as e:
            logger.error(f"Error extracting NPS score for response {self.id}: {str(e)}")
            return 5
    
    def get_csat_score(self) -> Optional[int]:
        """Extract CSAT score from response data for CSAT surveys"""
        if self.survey_type != 'csat':
            logger.debug(f"Not a CSAT survey: {self.survey_type}")
            return None
        
        try:
            response_data = self.response_data
            if not response_data:
                logger.debug(f"No response data for CSAT survey {self.id}")
                return None
            
            # Log the structure for debugging
            logger.debug(f"CSAT Response data for {self.id}: {response_data}")
            
            # Handle different response data structures
            score = self._extract_score_from_data(response_data, score_range=(1, 10))
            
            if score is not None:
                logger.debug(f"Extracted CSAT score {score} for response {self.id}")
                return score
            
            # Check for nested structure
            if isinstance(response_data, dict):
                for key in ['answers', 'responses', 'data', 'questions']:
                    if key in response_data and isinstance(response_data[key], dict):
                        nested_score = self._extract_score_from_data(response_data[key], score_range=(1, 10))
                        if nested_score is not None:
                            logger.debug(f"Found CSAT score {nested_score} in nested key '{key}'")
                            return nested_score
                
                # Check survey configuration for default scale
                if hasattr(self.survey, 'metadata') and self.survey.metadata:
                    if 'default_score' in self.survey.metadata:
                        default_score = self.survey.metadata['default_score']
                        if isinstance(default_score, (int, float)):
                            logger.debug(f"Using default CSAT score from survey metadata: {default_score}")
                            return int(default_score)
            
            logger.warning(f"No CSAT score found in response data for {self.id}, using default 3")
            return 3  # Neutral score
            
        except Exception as e:
            logger.error(f"Error extracting CSAT score for response {self.id}: {str(e)}")
            return 3
    def get_csat_scale_max(self) -> int:
        """Determine the scale maximum for CSAT survey"""
        if self.survey_type != 'csat':
            return 5  # Default
        
        try:
            # Check survey configuration for scale
            if hasattr(self.survey, 'questions') and isinstance(self.survey.questions, list):
                for question in self.survey.questions:
                    if question.get('type') == 'rating' and 'scale_max' in question:
                        return int(question['scale_max'])
            
            # Check response metadata
            if self.metadata and 'csat_scale' in self.metadata:
                return int(self.metadata['csat_scale'])
            
        except (KeyError, ValueError, TypeError):
            pass
        
        return 5  # Default 5-point scale
    
    def get_csat_question_text(self) -> str:
        """Extract the CSAT question text"""
        if self.survey_type != 'csat':
            return ""
        
        try:
            # Try to get from survey questions
            if hasattr(self.survey, 'questions') and isinstance(self.survey.questions, list):
                for question in self.survey.questions:
                    if question.get('type') == 'rating' and 'text' in question:
                        return question['text']
            
            # Check response data for question
            if isinstance(self.response_data, dict):
                for key, value in self.response_data.items():
                    if isinstance(key, str) and ('question' in key.lower() or 'csat' in key.lower()):
                        # Try to extract question from key
                        if isinstance(value, str) and len(value) < 200:  # Not too long
                            return value
            
        except (KeyError, ValueError, TypeError):
            pass
        
        return "How satisfied were you with our service?"
    
    def get_csat_feedback(self) -> str:
        """Extract feedback comment from CSAT response"""
        if self.survey_type != 'csat':
            return ""
        
        feedback_text = ""
        
        try:
            if isinstance(self.response_data, dict):
                # Look for feedback in common field names
                feedback_keys = ['feedback', 'comment', 'additional_comments', 
                                'suggestion', 'improvement', 'other_feedback']
                
                for key in feedback_keys:
                    if key in self.response_data:
                        value = self.response_data[key]
                        if isinstance(value, str) and value.strip():
                            feedback_text = value.strip()
                            break
                
                # If not found, look for any text response
                if not feedback_text:
                    for key, value in self.response_data.items():
                        if isinstance(value, str) and len(value.strip()) > 20:  # Substantial text
                            if 'score' not in key.lower() and 'rating' not in key.lower():
                                feedback_text = value.strip()
                                break
                
        except (KeyError, ValueError, TypeError):
            pass
        
        return feedback_text
    
    def get_ces_score(self) -> Optional[int]:
        """Extract CES score from response data for CES surveys"""
        if self.survey_type != 'ces':
            logger.debug(f"Not a CES survey: {self.survey_type}")
            return None
        
        try:
            response_data = self.response_data
            if not response_data:
                logger.debug(f"No response data for CES survey {self.id}")
                return None
            
            # Log the structure for debugging
            logger.debug(f"CES Response data for {self.id}: {response_data}")
            
            # Handle different response data structures
            score = self._extract_score_from_data(response_data, score_range=(1, 10))
            
            if score is not None:
                logger.debug(f"Extracted CES score {score} for response {self.id}")
                return score
            
            # Check for nested structure
            if isinstance(response_data, dict):
                for key in ['answers', 'responses', 'data', 'questions']:
                    if key in response_data and isinstance(response_data[key], dict):
                        nested_score = self._extract_score_from_data(response_data[key], score_range=(1, 10))
                        if nested_score is not None:
                            logger.debug(f"Found CES score {nested_score} in nested key '{key}'")
                            return nested_score
                
                # Check for effort-related scores
                for key, value in response_data.items():
                    if isinstance(key, str) and 'effort' in key.lower():
                        if isinstance(value, (int, float)) and 1 <= value <= 10:
                            logger.debug(f"Found effort score {value} in key '{key}'")
                            return int(value)
            
            logger.warning(f"No CES score found in response data for {self.id}, using default 4")
            return 4  # Neutral score on 7-point scale
            
        except Exception as e:
            logger.error(f"Error extracting CES score for response {self.id}: {str(e)}")
            return 4
    
    def get_ces_scale_max(self) -> int:
        """Determine the scale maximum for CES survey"""
        if self.survey_type != 'ces':
            return 7  # Default for CES
        
        try:
            # Check survey configuration for scale
            if hasattr(self.survey, 'questions') and isinstance(self.survey.questions, list):
                for question in self.survey.questions:
                    if question.get('type') == 'rating' and 'scale_max' in question:
                        return int(question['scale_max'])
            
            # Check response metadata
            if self.metadata and 'ces_scale' in self.metadata:
                return int(self.metadata['ces_scale'])
            
        except (KeyError, ValueError, TypeError):
            pass
        
        return 7  # Default 7-point scale for CES
    
    def get_ces_question_text(self) -> str:
        """Extract the CES question text"""
        if self.survey_type != 'ces':
            return ""
        
        try:
            # Try to get from survey questions
            if hasattr(self.survey, 'questions') and isinstance(self.survey.questions, list):
                for question in self.survey.questions:
                    if question.get('type') == 'rating' and 'text' in question:
                        return question['text']
            
            # Check response data for question
            if isinstance(self.response_data, dict):
                for key, value in self.response_data.items():
                    if isinstance(key, str) and ('question' in key.lower() or 'ces' in key.lower() or 'effort' in key.lower()):
                        # Try to extract question from key
                        if isinstance(value, str) and len(value) < 200:  # Not too long
                            return value
            
        except (KeyError, ValueError, TypeError):
            pass
        
        return "How easy was it to accomplish your goal?"
    
    def get_ces_task_description(self) -> str:
        """Extract task description from CES response"""
        if self.survey_type != 'ces':
            return ""
        
        try:
            if isinstance(self.response_data, dict):
                # Look for task description in common field names
                task_keys = ['task', 'task_description', 'goal', 'purpose', 
                            'what_were_you_trying_to_do', 'objective']
                
                for key in task_keys:
                    if key in self.response_data:
                        value = self.response_data[key]
                        if isinstance(value, str) and value.strip():
                            return value.strip()
                
        except (KeyError, ValueError, TypeError):
            pass
        
        return ""
    
    def get_ces_feedback(self) -> str:
        """Extract feedback comment from CES response"""
        if self.survey_type != 'ces':
            return ""
        
        feedback_text = ""
        
        try:
            if isinstance(self.response_data, dict):
                # Look for feedback in common field names
                feedback_keys = ['feedback', 'comment', 'additional_comments', 
                                'suggestion', 'improvement', 'other_feedback',
                                'why_difficult', 'why_easy']
                
                for key in feedback_keys:
                    if key in self.response_data:
                        value = self.response_data[key]
                        if isinstance(value, str) and value.strip():
                            feedback_text = value.strip()
                            break
                
                # If not found, look for any text response
                if not feedback_text:
                    for key, value in self.response_data.items():
                        if isinstance(value, str) and len(value.strip()) > 20:  # Substantial text
                            if 'score' not in key.lower() and 'rating' not in key.lower() and 'task' not in key.lower():
                                feedback_text = value.strip()
                                break
                
        except (KeyError, ValueError, TypeError):
            pass
        
        return feedback_text
    
    def get_effort_area(self) -> str:
        """Determine the effort area for CES"""
        if self.survey_type != 'ces':
            return ""
        
        try:
            # Check survey metadata
            if self.survey.metadata and 'effort_area' in self.survey.metadata:
                return self.survey.metadata['effort_area']
            
            # Check trigger event
            if self.survey.trigger_event:
                event_mapping = {
                    'post_purchase': 'purchase',
                    'post_support': 'support',
                    'milestone': 'account_management',
                }
                return event_mapping.get(self.survey.trigger_event, 'other')
            
            # Try to infer from question text
            question_text = self.get_ces_question_text().lower()
            if 'support' in question_text:
                return 'support'
            elif 'purchase' in question_text or 'buy' in question_text:
                return 'purchase'
            elif 'problem' in question_text or 'issue' in question_text:
                return 'problem_resolution'
            elif 'navigate' in question_text or 'find' in question_text:
                return 'information_finding'
            elif 'account' in question_text:
                return 'account_management'
            
        except (KeyError, ValueError, TypeError):
            pass
        
        return 'other'
    
    def extract_friction_points(self) -> list:
        """Extract friction points from CES feedback"""
        if self.survey_type != 'ces':
            return []
        
        friction_points = []
        
        try:
            # Get feedback text
            feedback = self.get_ces_feedback()
            if not feedback:
                return []
            
            # Common CES friction points to look for
            common_frictions = [
                'complicated', 'confusing', 'slow', 'long wait', 'difficult',
                'hard to find', 'too many steps', 'technical issue', 'error',
                'broken', 'not working', 'frustrating', 'annoying', 'unclear',
                'ambiguous', 'requires help', 'need assistance', 'cumbersome'
            ]
            
            # Check for these friction points in feedback
            feedback_lower = feedback.lower()
            for friction in common_frictions:
                if friction in feedback_lower:
                    friction_points.append(friction)
            
            # Also check sentiment metadata if AI analyzed
            if self.ai_analyzed and self.sentiment_metadata:
                if 'friction_points' in self.sentiment_metadata:
                    friction_points.extend(self.sentiment_metadata['friction_points'])
                
        except (KeyError, ValueError, TypeError):
            pass
        
        # Return unique friction points
        return list(set(friction_points))[:10]  # Limit to 10 
    def get_interaction_type(self) -> str:
        """Determine the interaction type for CSAT"""
        if self.survey_type != 'csat':
            return ""
        
        try:
            # Check survey metadata
            if self.survey.metadata and 'interaction_type' in self.survey.metadata:
                return self.survey.metadata['interaction_type']
            
            # Check trigger event
            if self.survey.trigger_event:
                event_mapping = {
                    'post_purchase': 'purchase',
                    'post_support': 'support',
                    'milestone': 'product_use',
                }
                return event_mapping.get(self.survey.trigger_event, 'overall')
            
        except (KeyError, ValueError, TypeError):
            pass
        
        return 'overall'

    def get_follow_up_responses(self) -> Dict:
        """Extract follow-up question responses from response data"""
        if not self.response_data or not isinstance(self.response_data, dict):
            return {}
        
        follow_up_responses = {}
        
        # Get follow-up questions (questions that are not the main score question)
        for key, value in self.response_data.items():
            # Skip the main score field (usually numeric)
            if isinstance(value, (int, float)) and 0 <= value <= 10:
                continue
            
            # Include text responses and other follow-up data
            if key not in ['nps_score', 'score', 'rating', 'overall_score', 'nps']:
                follow_up_responses[key] = value
        
        return follow_up_responses
    
    def extract_key_themes(self) -> list:
        """Extract key themes from text responses"""
        if not self.ai_analyzed or not self.sentiment_metadata:
            return []
        
        # Get themes from sentiment metadata if available
        themes = self.sentiment_metadata.get('key_themes', [])
        
        # If no themes from AI analysis, extract from text
        if not themes and self.has_text_responses:
            # Simple keyword extraction (could be enhanced)
            text_content = ""
            for value in self.response_data.values():
                if isinstance(value, str):
                    text_content += " " + value.lower()
            
            # Common NPS themes
            common_themes = ['customer service', 'product quality', 'pricing', 
                            'ease of use', 'features', 'support', 'reliability']
            
            themes = [theme for theme in common_themes if theme in text_content]
        
        return themes[:5]  # Return top 5 themes
    
    def _extract_score_from_data(self, data: Any, score_range: tuple) -> Optional[int]:
        """
        Extract a score from response data with flexible handling
        
        Args:
            data: Response data (dict, list, or scalar)
            score_range: Tuple of (min_score, max_score)
            
        Returns:
            Extracted score as integer, or None if not found
        """
        min_score, max_score = score_range
        
        try:
            if isinstance(data, dict):
                # Look for score in common field names
                score_keys = ['score', 'rating', 'value', 'answer', 'selected']
                
                for key in score_keys:
                    if key in data:
                        value = data[key]
                        score = self._parse_score_value(value, min_score, max_score)
                        if score is not None:
                            return score
                
                # Check all values in dict
                for key, value in data.items():
                    if isinstance(key, str) and ('score' in key.lower() or 'rating' in key.lower() or 'nps' in key.lower()):
                        score = self._parse_score_value(value, min_score, max_score)
                        if score is not None:
                            return score
                
                # Try to find any numeric value within range
                for value in data.values():
                    score = self._parse_score_value(value, min_score, max_score)
                    if score is not None:
                        return score
            
            elif isinstance(data, (int, float)):
                # Data is directly a number
                score = self._parse_score_value(data, min_score, max_score)
                if score is not None:
                    return score
            
            elif isinstance(data, str):
                # Try to parse string as number
                try:
                    parsed_value = float(data)
                    score = self._parse_score_value(parsed_value, min_score, max_score)
                    if score is not None:
                        return score
                except (ValueError, TypeError):
                    pass
            
            elif isinstance(data, list):
                # Check each item in the list
                for item in data:
                    score = self._extract_score_from_data(item, score_range)
                    if score is not None:
                        return score
            
            return None
            
        except Exception as e:
            logger.error(f"Error in _extract_score_from_data: {str(e)}")
            return None
    
    def _parse_score_value(self, value: Any, min_score: int, max_score: int) -> Optional[int]:
        """Parse a value to see if it's a valid score within range"""
        try:
            if isinstance(value, (int, float)):
                if min_score <= value <= max_score:
                    return int(value)
            
            elif isinstance(value, str):
                # Try to extract number from string
                import re
                numbers = re.findall(r'[-+]?\d*\.\d+|\d+', value)
                if numbers:
                    parsed_value = float(numbers[0])
                    if min_score <= parsed_value <= max_score:
                        return int(parsed_value)
            
            return None
            
        except (ValueError, TypeError):
            return None
    
    def copy_to_nps_response(self) -> 'NPSResponse':
        """Copy data to NPSResponse model"""
        from .models import NPSResponse
        
        try:
            nps_response = NPSResponse()
            nps_response.copy_from_survey_response(self)
            
            # Get NPS score
            score = self.get_nps_score()
            if score is not None:
                nps_response.score = score
            else:
                logger.error(f"Could not extract NPS score for survey response {self.id}")
                raise ValidationError("Could not extract NPS score")
            
            # Save the response
            nps_response.save()
            logger.info(f"Successfully created NPS response from survey response {self.id}")
            
            return nps_response
            
        except Exception as e:
            logger.error(f"Error copying to NPS response for survey {self.id}: {str(e)}")
            raise
    
    def copy_to_csat_response(self) -> 'CSATResponse':
        """Copy data to CSATResponse model"""
        from .models import CSATResponse
        
        try:
            csat_response = CSATResponse()
            
            # Copy basic information
            csat_response.survey_response = self
            csat_response.organization = self.organization
            csat_response.customer = self.customer
            
            # Get CSAT score
            score = self.get_csat_score()
            if score is not None:
                csat_response.score = score
            else:
                logger.error(f"Could not extract CSAT score for survey response {self.id}")
                raise ValidationError("Could not extract CSAT score")
            
            # Get scale maximum
            csat_response.scale_max = self.get_csat_scale_max()
            
            # Extract additional data
            csat_response.question_text = self.get_csat_question_text()
            csat_response.feedback = self.get_csat_feedback()
            csat_response.interaction_type = self.get_interaction_type()
            
            # Copy follow-up responses
            csat_response.follow_up_responses = self.get_follow_up_responses()
            
            # Copy sentiment analysis if available
            if self.ai_analyzed:
                csat_response.ai_analyzed = True
                csat_response.sentiment_score = self.sentiment_score
                csat_response.sentiment_metadata = self.sentiment_metadata
                csat_response.analysis_status = self.analysis_status
                
                # Extract key themes
                csat_response.key_themes = self.extract_key_themes()
            
            # Copy metadata
            if self.metadata:
                csat_response.metadata = self.metadata.copy()
            
            # Copy channel if available
            if self.channel:
                csat_response.metadata['channel'] = self.channel.name
            
            # Save the response
            csat_response.save()
            logger.info(f"Successfully created CSAT response from survey response {self.id}")
            
            return csat_response
            
        except Exception as e:
            logger.error(f"Error copying to CSAT response for survey {self.id}: {str(e)}")
            raise
    
    def copy_to_ces_response(self) -> 'CESResponse':
        """Copy data to CESResponse model"""
        from .models import CESResponse
        
        try:
            ces_response = CESResponse()
            
            # Copy basic information
            ces_response.survey_response = self
            ces_response.organization = self.organization
            ces_response.customer = self.customer
            
            # Get CES score
            score = self.get_ces_score()
            if score is not None:
                ces_response.score = score
            else:
                logger.error(f"Could not extract CES score for survey response {self.id}")
                raise ValidationError("Could not extract CES score")
            
            # Get scale maximum
            ces_response.scale_max = self.get_ces_scale_max()
            
            # Extract additional data
            ces_response.question_text = self.get_ces_question_text()
            ces_response.task_description = self.get_ces_task_description()
            ces_response.feedback = self.get_ces_feedback()
            ces_response.effort_area = self.get_effort_area()
            ces_response.friction_points = self.extract_friction_points()
            
            # Copy follow-up responses
            ces_response.follow_up_responses = self.get_follow_up_responses()
            
            # Copy sentiment analysis if available
            if self.ai_analyzed:
                ces_response.ai_analyzed = True
                ces_response.sentiment_score = self.sentiment_score
                ces_response.sentiment_metadata = self.sentiment_metadata
                ces_response.analysis_status = self.analysis_status
                
                # Extract key themes
                ces_response.key_themes = self.extract_key_themes()
            
            # Copy metadata
            if self.metadata:
                ces_response.metadata = self.metadata.copy()
            
            # Copy channel if available
            if self.channel:
                ces_response.metadata['channel'] = self.channel.name
            
            # Save the response
            ces_response.save()
            logger.info(f"Successfully created CES response from survey response {self.id}")
            
            return ces_response
            
        except Exception as e:
            logger.error(f"Error copying to CES response for survey {self.id}: {str(e)}")
            raise
    
    def copy_to_specific_response(self):
        """Copy survey response to specific response model based on survey type"""
        if self.survey_type == 'nps':
            return self.copy_to_nps_response()
        elif self.survey_type == 'csat':
            return self.copy_to_csat_response()
        elif self.survey_type == 'ces':
            return self.copy_to_ces_response()
        else:
            logger.warning(f"No specific response model for survey type: {self.survey_type}")
            return None
    @property
    def has_text_responses(self) -> bool:
        """Check if response contains textual feedback for analysis"""
        if not self.response_data:
            return False
        
        for answer in self.response_data.values():
            if isinstance(answer, str) and len(answer.strip()) > 10:
                return True
        return False
    
    def analyze_sentiment_async(self):
        """Trigger async sentiment analysis"""
        try:
            # Create analysis task
            from surveys.tasks import analyze_survey_response_sentiment
            analyze_survey_response_sentiment.delay(self.id)
            logger.info(f"Queued sentiment analysis for survey response {self.id}")
        except Exception as e:
            logger.error(f"Failed to queue sentiment analysis: {str(e)}")
    
    def analyze_sentiment_sync(self) -> bool:
        """Perform synchronous sentiment analysis (for immediate feedback)"""
        if not self.has_text_responses:
            logger.info(f"Survey response {self.id} has no text responses for analysis")
            self.sentiment_score = 0.0
            self.ai_analyzed = True
            self.analysis_status = 'completed'
            self.sentiment_metadata = {'analysis_skipped': 'no_text_responses'}
            self.save(update_fields=[
                'sentiment_score', 'ai_analyzed', 'analysis_status', 
                'sentiment_metadata', 'updated_at'
            ])
            return True
        
        try:
            self.analysis_status = 'processing'
            self.save(update_fields=['analysis_status', 'updated_at'])
            
            # Get organization context
            organization = self.organization
            organization_context = {
                'industry': organization.industry or 'Not specified',
                'organization_name': organization.name,
                'survey_type': self.survey.survey_type,
            }
            
            # Initialize analyzer
            analyzer = SurveySentimentAnalyzer()
            
            # Extract text from response data
            survey_response_data = {}
            for question_id, answer in self.response_data.items():
                if isinstance(answer, str):
                    survey_response_data[question_id] = answer
            
            # Analyze sentiment
            analysis_result = analyzer.extract_sentiment_from_response(
                survey_response_data, 
                organization_context
            )
            
            # Update model fields
            self.sentiment_score = analysis_result.get('overall_sentiment_score', 0.0)
            self.ai_analyzed = True
            self.analysis_status = 'completed'
            
            # Update metadata with analysis results
            self.metadata.update({
                'sentiment_analysis': {
                    'timestamp': analysis_result.get('analysis_timestamp'),
                    'model_used': analysis_result.get('model_used'),
                    'confidence': analysis_result.get('confidence_score', 0.0),
                }
            })
            
            # Store detailed sentiment metadata
            self.sentiment_metadata = analysis_result
            
            # Save all changes
            self.save(update_fields=[
                'sentiment_score', 'ai_analyzed', 'analysis_status',
                'metadata', 'sentiment_metadata', 'updated_at'
            ])
            
            logger.info(f"Successfully analyzed sentiment for survey response {self.id}: score={self.sentiment_score}")
            return True
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis for response {self.id}: {str(e)}", exc_info=True)
            self.analysis_status = 'failed'
            self.analysis_retry_count += 1
            self.save(update_fields=['analysis_status', 'analysis_retry_count', 'updated_at'])
            return False
    
    def get_sentiment_insights(self) -> Dict[str, Any]:
        """Get formatted sentiment insights for display"""
        if not self.ai_analyzed or not self.sentiment_metadata:
            return {
                'status': 'not_analyzed',
                'score': self.sentiment_score or 0.0,
                'label': 'neutral',
                'summary': 'No analysis available.',
            }
        
        metadata = self.sentiment_metadata
        
        # Determine sentiment color and icon based on score
        score = self.sentiment_score or 0.0
        if score >= 0.5:
            color = 'success'
            icon = 'fa-smile-beam'
            label = 'Very Positive'
        elif score >= 0.1:
            color = 'info'
            icon = 'fa-smile'
            label = 'Positive'
        elif score <= -0.5:
            color = 'danger'
            icon = 'fa-angry'
            label = 'Very Negative'
        elif score <= -0.1:
            color = 'warning'
            icon = 'fa-frown'
            label = 'Negative'
        else:
            color = 'secondary'
            icon = 'fa-meh'
            label = 'Neutral'
        
        return {
            'status': 'analyzed',
            'score': score,
            'label': label,
            'color': color,
            'icon': icon,
            'summary': metadata.get('summary', 'No summary available.'),
            'key_themes': metadata.get('key_themes', []),
            'urgency_level': metadata.get('urgency_level', 'low'),
            'actionable_feedback': metadata.get('actionable_feedback', False),
            'detected_emotions': metadata.get('detected_emotions', {}),
            'sentiment_by_aspect': metadata.get('sentiment_by_aspect', {}),
            'analysis_timestamp': metadata.get('analysis_timestamp'),
            'confidence_score': metadata.get('confidence_score', 0.0),
        }
    
    def trigger_followup_actions(self):
        """Trigger follow-up actions based on sentiment analysis"""
        if not self.ai_analyzed:
            return
        
        score = self.sentiment_score or 0.0
        
        # Check for negative sentiment that needs attention
        if score < -0.3:  # Negative sentiment threshold
            logger.info(f"Negative sentiment detected (score: {score}) for response {self.id}")
            
            # Could trigger:
            # 1. Alert to customer support team
            # 2. Email to account manager
            # 3. Create follow-up task in CRM
            # 4. Schedule customer check-in
            
            # For now, just log it
            self.metadata.setdefault('followup_actions', []).append({
                'trigger': 'negative_sentiment',
                'sentiment_score': score,
                'timestamp': timezone.now().isoformat(),
                'action': 'logged_for_review',
            })
            self.save(update_fields=['metadata', 'updated_at'])
        
        # Check for positive sentiment for advocacy
        elif score > 0.7:  # Highly positive threshold
            logger.info(f"Highly positive sentiment detected (score: {score}) for response {self.id}")
            
            # Could trigger:
            # 1. Add to advocacy program
            # 2. Request for testimonial
            # 3. Send thank you gift
            # 4. Feature in case studies
            
            self.metadata.setdefault('followup_actions', []).append({
                'trigger': 'highly_positive_sentiment',
                'sentiment_score': score,
                'timestamp': timezone.now().isoformat(),
                'action': 'potential_advocate',
            })
            self.save(update_fields=['metadata', 'updated_at'])
            
    def get_serializable_metadata(self):
        """Get metadata as JSON-serializable dict"""
        return safe_metadata_dict(self)


class NPSResponse(TimeStampedModel):
    """
    Net Promoter Score specific tracking
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='nps_responses',
        verbose_name=_('Organization')
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='nps_responses',
        verbose_name=_('Customer')
    )
    survey_response = models.OneToOneField(
        'SurveyResponse',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='nps_data',
        verbose_name=_('Survey Response')
    )
    
    # NPS Score (0-10)
    score = models.IntegerField(
        _('NPS Score'),
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        db_index=True
    )
    category = models.CharField(
        _('NPS Category'),
        max_length=20,
        choices=[
            ('detractor', _('Detractor (0-6)')),
            ('passive', _('Passive (7-8)')),
            ('promoter', _('Promoter (9-10)')),
        ],
        db_index=True
    )
    
    # Additional Context
    reason = models.TextField(_('Reason'), blank=True)
    follow_up_question_responses = models.JSONField(
        _('Follow-up Responses'),
        default=dict,
        blank=True
    )
    
    # Contextual Information
    product = models.ForeignKey(
        'Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='nps_responses',
        verbose_name=_('Product')
    )
    touchpoint = models.CharField(
        _('Touchpoint'),
        max_length=100,
        blank=True,
        help_text=_('Where in customer journey this was collected')
    )
    
    # AI Analysis
    ai_analyzed = models.BooleanField(_('AI Analyzed'), default=False)
    sentiment_score = models.FloatField(
        _('Sentiment Score'),
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)]
    )
    # FIXED: Replaced ArrayField with JSONField for database compatibility
    key_themes = models.JSONField(
        _('Key Themes'),
        default=list,
        blank=True
    )
    
    # Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    sentiment_metadata = models.JSONField(
        _('Sentiment Analysis Metadata'),
        default=dict,
        blank=True,
        help_text=_('Detailed sentiment analysis results')
    )
    
    analysis_status = models.CharField(
        _('Analysis Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending Analysis')),
            ('processing', _('Processing')),
            ('completed', _('Completed')),
            ('failed', _('Failed')),
        ],
        default='pending',
        db_index=True
    )
    
    analysis_retry_count = models.IntegerField(
        _('Analysis Retry Count'),
        default=0,
        help_text=_('Number of times analysis has been retried')
    )
    
    class Meta:
        verbose_name = _('NPS Response')
        verbose_name_plural = _('NPS Responses')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['score']),
        ]

    def __str__(self):
        return f"NPS {self.score} ({self.category}) - {self.customer.email}"

    def save(self, *args, **kwargs):
        # Auto-categorize based on score
        if self.score <= 6:
            self.category = 'detractor'
        elif self.score <= 8:
            self.category = 'passive'
        else:
            self.category = 'promoter'
        super().save(*args, **kwargs)
    
    def copy_from_survey_response(self, survey_response):
        """Copy data from SurveyResponse to NPSResponse"""
        try:
            self.survey_response = survey_response
            self.organization = survey_response.organization
            self.customer = survey_response.customer
            
            # Extract NPS score using the improved method
            score = survey_response.get_nps_score()
            if score is not None:
                self.score = score
                logger.debug(f"Set NPS score to {score} for response {survey_response.id}")
            else:
                logger.error(f"Could not extract NPS score from survey response {survey_response.id}")
                self.score = 5  # Default fallback
            
            # Extract follow-up responses
            self.follow_up_question_responses = survey_response.get_follow_up_responses()
            
            # Extract reason from text responses
            self.reason = self._extract_reason_from_survey(survey_response)
            
            # Copy sentiment analysis if available
            if survey_response.ai_analyzed:
                self.ai_analyzed = True
                self.sentiment_score = survey_response.sentiment_score
                self.sentiment_metadata = survey_response.sentiment_metadata
                self.analysis_status = survey_response.analysis_status
                self.key_themes = survey_response.extract_key_themes()
            
            # Copy metadata
            if survey_response.metadata:
                self.metadata = survey_response.metadata.copy()
            
            # Copy channel if available
            if survey_response.channel:
                self.metadata['channel'] = survey_response.channel.name
            
            logger.info(f"Successfully copied data from survey response {survey_response.id}")
            
        except Exception as e:
            logger.error(f"Error copying from survey response {survey_response.id}: {str(e)}")
            raise
    
    def _extract_reason_from_survey(self, survey_response):
        """Extract reason text from survey response"""
        reason = ""
        
        try:
            if survey_response.response_data:
                response_data = survey_response.response_data
                
                # First, look for specific reason/question fields
                reason_fields = ['reason', 'feedback', 'comment', 'why', 'explanation', 
                                'additional_comments', 'suggestion', 'improvement']
                
                for field in reason_fields:
                    if field in response_data:
                        value = response_data[field]
                        if isinstance(value, str) and value.strip():
                            reason = value.strip()
                            break
                
                # If no specific reason field found, look for any substantial text
                if not reason:
                    for key, value in response_data.items():
                        if isinstance(value, str) and len(value.strip()) > 10:
                            # Skip if it looks like a question or label
                            if not key.lower().startswith(('question', 'q_', 'label', 'l_')):
                                reason = value.strip()
                                break
            
            return reason
            
        except Exception as e:
            logger.error(f"Error extracting reason from survey response: {str(e)}")
            return ""
    def copy_from_survey_response1(self, survey_response):
        """Copy data from SurveyResponse to NPSResponse"""
        self.survey_response = survey_response
        self.organization = survey_response.organization
        self.customer = survey_response.customer
        
        # Extract NPS score
        self.score = survey_response.get_nps_score() or 0
        
        # Extract follow-up responses
        self.follow_up_question_responses = survey_response.get_follow_up_responses()
        
        # Extract reason from text responses
        if survey_response.response_data:
            for key, value in survey_response.response_data.items():
                if isinstance(value, str) and len(value.strip()) > 10:
                    if not self.reason:  # Use first substantial text as reason
                        self.reason = value
                    break
        
        # Copy sentiment analysis if available
        if survey_response.ai_analyzed:
            self.ai_analyzed = True
            self.sentiment_score = survey_response.sentiment_score
            self.sentiment_metadata = survey_response.sentiment_metadata
            self.analysis_status = survey_response.analysis_status
            self.key_themes = survey_response.extract_key_themes()
        
        # Copy metadata
        if survey_response.metadata:
            self.metadata = survey_response.metadata.copy()
        
        # Copy channel if available
        if survey_response.channel:
            # You might want to create a Channel field in NPSResponse too
            self.metadata['channel'] = survey_response.channel.name


# Signal handler for creating NPSResponse from SurveyResponse
@receiver(post_save, sender=SurveyResponse)
def create_nps_response_from_survey_response(sender, instance, created, **kwargs):
    """
    Create NPSResponse when a SurveyResponse is created for an NPS survey
    """
    # Only process if it's an NPS survey and is complete
    if not created or not instance.is_complete or instance.survey_type != 'nps':
        return
    
    # Don't create if customer is not available
    if not instance.customer:
        logger.warning(f"Cannot create NPSResponse for SurveyResponse {instance.id}: No customer")
        return
    
    try:
        # Check if NPSResponse already exists
        if hasattr(instance, 'nps_data') and instance.nps_data:
            logger.info(f"NPSResponse already exists for SurveyResponse {instance.id}")
            return
        
        # Extract NPS score
        nps_score = instance.get_nps_score()
        if nps_score is None:
            logger.warning(f"Cannot extract NPS score from SurveyResponse {instance.id}")
            return
        
        # Create NPSResponse
        nps_response = NPSResponse(
            survey_response=instance,
            organization=instance.organization,
            customer=instance.customer,
            score=nps_score
        )
        
        # Copy additional data
        nps_response.copy_from_survey_response(instance)
        
        # Save the NPSResponse
        nps_response.save()
        
        logger.info(f"Created NPSResponse {nps_response.id} from SurveyResponse {instance.id}")
        
        # Update survey statistics
        instance.survey.total_responses += 1
        instance.survey.save(update_fields=['total_responses', 'updated_at'])
        
    except Exception as e:
        logger.error(f"Error creating NPSResponse from SurveyResponse {instance.id}: {str(e)}", exc_info=True)


# Signal handler for auto-analysis
@receiver(post_save, sender=SurveyResponse)
def trigger_sentiment_analysis(sender, instance, created, **kwargs):
    """
    Trigger sentiment analysis when a survey response is created
    """
    if created and instance.is_complete:
        # For immediate feedback, run sync analysis
        # For production, use async with Celery
        if settings.DEBUG:
            # Sync for development
            instance.analyze_sentiment_sync()
        else:
            # Async for production
            instance.analyze_sentiment_async()


# Signal handler for updating NPSResponse when SurveyResponse sentiment is analyzed
@receiver(post_save, sender=SurveyResponse)
def update_nps_response_from_analysis(sender, instance, created, **kwargs):
    """
    Update NPSResponse with sentiment analysis results
    """
    # Only process if it's an NPS survey and has been analyzed
    if created or instance.survey_type != 'nps' or not instance.ai_analyzed:
        return
    
    try:
        # Find and update the associated NPSResponse
        if hasattr(instance, 'nps_data') and instance.nps_data:
            nps_response = instance.nps_data
            
            # Update sentiment analysis data
            nps_response.ai_analyzed = True
            nps_response.sentiment_score = instance.sentiment_score
            nps_response.sentiment_metadata = instance.sentiment_metadata
            nps_response.analysis_status = instance.analysis_status
            nps_response.key_themes = instance.extract_key_themes()
            
            nps_response.save(update_fields=[
                'ai_analyzed', 'sentiment_score', 'sentiment_metadata',
                'analysis_status', 'key_themes', 'updated_at'
            ])
            
            logger.info(f"Updated NPSResponse {nps_response.id} with sentiment analysis results")
            
    except Exception as e:
        logger.error(f"Error updating NPSResponse for SurveyResponse {instance.id}: {str(e)}", exc_info=True)
        


class CSATResponse(TimeStampedModel):
    """
    Customer Satisfaction Score tracking
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='csat_responses',
        verbose_name=_('Organization')
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='csat_responses',
        verbose_name=_('Customer')
    )
    survey_response = models.OneToOneField(
        SurveyResponse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='csat_data',
        verbose_name=_('Survey Response')
    )
    
    # CSAT Score (typically 1-5 or 1-7)
    score = models.IntegerField(
        _('CSAT Score'),
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        db_index=True
    )
    scale_max = models.IntegerField(
        _('Scale Maximum'),
        default=5,
        validators=[MinValueValidator(2), MaxValueValidator(10)]
    )
    normalized_score = models.FloatField(
        _('Normalized Score (0-100)'),
        null=True,
        blank=True,
        db_index=True
    )
    
    # Satisfaction Level
    satisfaction_level = models.CharField(
        _('Satisfaction Level'),
        max_length=50,
        choices=[
            ('very_dissatisfied', _('Very Dissatisfied')),
            ('dissatisfied', _('Dissatisfied')),
            ('neutral', _('Neutral')),
            ('satisfied', _('Satisfied')),
            ('very_satisfied', _('Very Satisfied')),
        ],
        db_index=True
    )
    
    # Context
    question_text = models.TextField(_('Question Text'))
    feedback_comment = models.TextField(_('Feedback Comment'), blank=True)
    
    # What was rated
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='csat_responses',
        verbose_name=_('Product')
    )
    interaction_type = models.CharField(
        _('Interaction Type'),
        max_length=50,
        choices=[
            ('purchase', _('Purchase')),
            ('support', _('Support')),
            ('delivery', _('Delivery')),
            ('product_use', _('Product Use')),
            ('overall', _('Overall Experience')),
            ('other', _('Other')),
        ],
        blank=True
    )
    
    # AI Analysis
    ai_analyzed = models.BooleanField(_('AI Analyzed'), default=False)
    sentiment_score = models.FloatField(
        _('Sentiment Score'),
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)]
    )
    
    # Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('CSAT Response')
        verbose_name_plural = _('CSAT Responses')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'satisfaction_level']),
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['customer', '-created_at']),
        ]

    def __str__(self):
        return f"CSAT {self.score}/{self.scale_max} - {self.customer.email}"

    def save(self, *args, **kwargs):
        # Calculate normalized score (0-100)
        self.normalized_score = ((self.score - 1) / (self.scale_max - 1)) * 100
        
        # Auto-categorize satisfaction level
        self.satisfaction_level = self.calculate_satisfaction_level()
        
        super().save(*args, **kwargs)
    
    def calculate_satisfaction_level(self) -> str:
        """Calculate satisfaction level based on score and scale"""
        if self.scale_max == 5:
            # 5-point scale
            if self.score == 1:
                return 'very_dissatisfied'
            elif self.score == 2:
                return 'dissatisfied'
            elif self.score == 3:
                return 'neutral'
            elif self.score == 4:
                return 'satisfied'
            else:  # score == 5
                return 'very_satisfied'
        
        elif self.scale_max == 7:
            # 7-point scale mapping
            if self.score <= 2:
                return 'very_dissatisfied'
            elif self.score <= 3:
                return 'dissatisfied'
            elif self.score == 4:
                return 'neutral'
            elif self.score <= 5:
                return 'satisfied'
            else:  # score >= 6
                return 'very_satisfied'
        
        else:
            # Generic scale - calculate percentages
            percentage = (self.score - 1) / (self.scale_max - 1)
            if percentage < 0.2:
                return 'very_dissatisfied'
            elif percentage < 0.4:
                return 'dissatisfied'
            elif percentage < 0.6:
                return 'neutral'
            elif percentage < 0.8:
                return 'satisfied'
            else:
                return 'very_satisfied'
    
    def copy_from_survey_response(self, survey_response):
        """Copy data from SurveyResponse to CSATResponse"""
        try:
            self.survey_response = survey_response
            self.organization = survey_response.organization
            self.customer = survey_response.customer
            
            # Extract CSAT score
            score = survey_response.get_csat_score()
            if score is not None:
                self.score = score
            else:
                self.score = 3  # Default neutral
            
            # Extract additional CSAT-specific data
            self.scale_max = survey_response.get_csat_scale_max()
            self.question_text = survey_response.get_csat_question_text()
            self.feedback = survey_response.get_csat_feedback()
            self.interaction_type = survey_response.get_interaction_type()
            
            # Copy follow-up responses
            self.follow_up_responses = survey_response.get_follow_up_responses()
            
            # Copy sentiment analysis if available
            if survey_response.ai_analyzed:
                self.ai_analyzed = True
                self.sentiment_score = survey_response.sentiment_score
                self.sentiment_metadata = survey_response.sentiment_metadata
                self.analysis_status = survey_response.analysis_status
                self.key_themes = survey_response.extract_key_themes()
            
            # Copy metadata
            if survey_response.metadata:
                self.metadata = survey_response.metadata.copy()
            
            logger.info(f"Successfully copied data to CSAT response from survey {survey_response.id}")
            
        except Exception as e:
            logger.error(f"Error copying to CSAT response: {str(e)}")
            raise
    
    def _extract_reason_from_survey(self, survey_response):
        """Extract reason text from survey response"""
        reason = ""
        
        try:
            if survey_response.response_data:
                response_data = survey_response.response_data
                
                # First, look for specific reason/question fields
                reason_fields = ['reason', 'feedback', 'comment', 'why', 'explanation', 
                                'additional_comments', 'suggestion', 'improvement']
                
                for field in reason_fields:
                    if field in response_data:
                        value = response_data[field]
                        if isinstance(value, str) and value.strip():
                            reason = value.strip()
                            break
                
                # If no specific reason field found, look for any substantial text
                if not reason:
                    for key, value in response_data.items():
                        if isinstance(value, str) and len(value.strip()) > 10:
                            # Skip if it looks like a question or label
                            if not key.lower().startswith(('question', 'q_', 'label', 'l_')):
                                reason = value.strip()
                                break
            
            return reason
            
        except Exception as e:
            logger.error(f"Error extracting reason from survey response: {str(e)}")
            return ""     
    
    @property
    def is_positive(self) -> bool:
        """Check if this is a positive CSAT response"""
        return self.satisfaction_level in ['satisfied', 'very_satisfied']
    
    @property
    def is_negative(self) -> bool:
        """Check if this is a negative CSAT response"""
        return self.satisfaction_level in ['very_dissatisfied', 'dissatisfied']
    
    @property
    def is_neutral(self) -> bool:
        """Check if this is a neutral CSAT response"""
        return self.satisfaction_level == 'neutral'
    
    def get_score_percentage(self) -> float:
        """Get score as percentage (0-100)"""
        return self.normalized_score or ((self.score - 1) / (self.scale_max - 1)) * 100


# Signal handler for creating CSATResponse from SurveyResponse
@receiver(post_save, sender=SurveyResponse)
def create_csat_response_from_survey_response(sender, instance, created, **kwargs):
    """
    Create CSATResponse when a SurveyResponse is created for a CSAT survey
    """
    # Only process if it's a CSAT survey and is complete
    if not created or not instance.is_complete or instance.survey_type != 'csat':
        return
    
    # Don't create if customer is not available
    if not instance.customer:
        logger.warning(f"Cannot create CSATResponse for SurveyResponse {instance.id}: No customer")
        return
    
    try:
        # Check if CSATResponse already exists
        if hasattr(instance, 'csat_data') and instance.csat_data:
            logger.info(f"CSATResponse already exists for SurveyResponse {instance.id}")
            return
        
        # Extract CSAT score
        csat_score = instance.get_csat_score()
        if csat_score is None:
            logger.warning(f"Cannot extract CSAT score from SurveyResponse {instance.id}")
            return
        
        # Ensure organization is available
        if not instance.organization:
            logger.warning(f"Cannot create CSATResponse: No organization for SurveyResponse {instance.id}")
            return
        
        # Create CSATResponse
        csat_response = CSATResponse(
            survey_response=instance,
            organization=instance.organization,
            customer=instance.customer,
            score=csat_score,
            scale_max=instance.get_csat_scale_max(),
            question_text=instance.get_csat_question_text(),
            feedback_comment=instance.get_csat_feedback(),
            interaction_type=instance.get_interaction_type()
        )
        
        # Copy additional data
        csat_response.copy_from_survey_response(instance)
        
        # Save the CSATResponse
        csat_response.save()
        
        logger.info(f"Created CSATResponse {csat_response.id} from SurveyResponse {instance.id}")
        
        # Update survey statistics
        try:
            instance.survey.total_responses += 1
            instance.survey.save(update_fields=['total_responses', 'updated_at'])
        except Exception as e:
            logger.error(f"Failed to update survey statistics: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error creating CSATResponse from SurveyResponse {instance.id}: {str(e)}", exc_info=True)

# Signal handler for updating CSATResponse when SurveyResponse sentiment is analyzed
@receiver(post_save, sender=SurveyResponse)
def update_csat_response_from_analysis(sender, instance, created, **kwargs):
    """
    Update CSATResponse with sentiment analysis results
    """
    # Only process if it's a CSAT survey and has been analyzed
    if created or instance.survey_type != 'csat' or not instance.ai_analyzed:
        return
    
    try:
        # Find and update the associated CSATResponse
        if hasattr(instance, 'csat_data') and instance.csat_data:
            csat_response = instance.csat_data
            
            # Update sentiment analysis data
            csat_response.ai_analyzed = True
            csat_response.sentiment_score = instance.sentiment_score
            
            # Add sentiment metadata
            if instance.sentiment_metadata:
                csat_response.metadata['sentiment_analysis'] = {
                    'timestamp': instance.sentiment_metadata.get('analysis_timestamp'),
                    'confidence': instance.sentiment_metadata.get('confidence_score'),
                    'key_themes': instance.sentiment_metadata.get('key_themes', []),
                }
            
            csat_response.save(update_fields=[
                'ai_analyzed', 'sentiment_score', 'metadata', 'updated_at'
            ])
            
            logger.info(f"Updated CSATResponse {csat_response.id} with sentiment analysis results")
            
    except Exception as e:
        logger.error(f"Error updating CSATResponse for SurveyResponse {instance.id}: {str(e)}", exc_info=True)

@receiver(post_save, sender=CSATResponse)
def calculate_csat_metrics(sender, instance, created, **kwargs):
    """
    Recalculate organization CSAT metrics when a response is saved
    """
    if created:
        # Update organization metrics
        organization = instance.organization
        organization.update_csat_metrics()

class CESResponse(TimeStampedModel):
    """
    Customer Effort Score tracking
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='ces_responses',
        verbose_name=_('Organization')
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='ces_responses',
        verbose_name=_('Customer')
    )
    survey_response = models.OneToOneField(
        'SurveyResponse',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ces_data',
        verbose_name=_('Survey Response')
    )
    
    # CES Score (typically 1-7, where 1 is very difficult, 7 is very easy)
    score = models.IntegerField(
        _('CES Score'),
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        db_index=True
    )
    scale_max = models.IntegerField(
        _('Scale Maximum'),
        default=7,
        validators=[MinValueValidator(2), MaxValueValidator(10)]
    )
    normalized_score = models.FloatField(
        _('Normalized Score (0-100)'),
        null=True,
        blank=True
    )
    
    # Effort Level
    effort_level = models.CharField(
        _('Effort Level'),
        max_length=50,
        choices=[
            ('very_difficult', _('Very Difficult')),
            ('difficult', _('Difficult')),
            ('somewhat_difficult', _('Somewhat Difficult')),
            ('neutral', _('Neutral')),
            ('somewhat_easy', _('Somewhat Easy')),
            ('easy', _('Easy')),
            ('very_easy', _('Very Easy')),
        ],
        db_index=True
    )
    
    # Context
    question_text = models.TextField(_('Question Text'))
    task_description = models.CharField(_('Task Description'), max_length=255, blank=True)
    feedback_comment = models.TextField(_('Feedback Comment'), blank=True)
    
    # What effort was measured
    effort_area = models.CharField(
        _('Effort Area'),
        max_length=50,
        choices=[
            ('purchase', _('Purchase Process')),
            ('support', _('Getting Support')),
            ('problem_resolution', _('Problem Resolution')),
            ('navigation', _('Website/App Navigation')),
            ('information_finding', _('Finding Information')),
            ('account_management', _('Account Management')),
            ('other', _('Other')),
        ],
        blank=True
    )
    
    # AI Analysis
    ai_analyzed = models.BooleanField(_('AI Analyzed'), default=False)
    # FIXED: Replaced ArrayField with JSONField for database compatibility
    friction_points = models.JSONField(
        _('Identified Friction Points'),
        default=list,
        blank=True
    )
    sentiment_score = models.FloatField(
        _('Sentiment Score'),
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)]
    )
     
    # Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('CES Response')
        verbose_name_plural = _('CES Responses')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'effort_level']),
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['customer', '-created_at']),
        ]

    def __str__(self):
        return f"CES {self.score}/{self.scale_max} - {self.customer.email}"

    def save(self, *args, **kwargs):
        # Calculate normalized score (0-100, higher is better - less effort)
        self.normalized_score = ((self.score - 1) / (self.scale_max - 1)) * 100
        
        # Auto-categorize effort level based on scale
        self.effort_level = self.calculate_effort_level()
        
        super().save(*args, **kwargs)
    
    def calculate_effort_level(self) -> str:
        """Calculate effort level based on score and scale"""
        if self.scale_max == 7:
            # Standard 7-point CES scale
            if self.score == 1:
                return 'very_difficult'
            elif self.score == 2:
                return 'difficult'
            elif self.score == 3:
                return 'somewhat_difficult'
            elif self.score == 4:
                return 'neutral'
            elif self.score == 5:
                return 'somewhat_easy'
            elif self.score == 6:
                return 'easy'
            else:  # score == 7
                return 'very_easy'
        
        elif self.scale_max == 5:
            # 5-point scale mapping
            if self.score == 1:
                return 'very_difficult'
            elif self.score == 2:
                return 'difficult'
            elif self.score == 3:
                return 'neutral'
            elif self.score == 4:
                return 'easy'
            else:  # score == 5
                return 'very_easy'
        
        else:
            # Generic scale - calculate percentages
            percentage = (self.score - 1) / (self.scale_max - 1)
            if percentage < 0.2:
                return 'very_difficult'
            elif percentage < 0.35:
                return 'difficult'
            elif percentage < 0.5:
                return 'somewhat_difficult'
            elif percentage < 0.65:
                return 'neutral'
            elif percentage < 0.8:
                return 'somewhat_easy'
            elif percentage < 0.95:
                return 'easy'
            else:
                return 'very_easy'
    
    def copy_from_survey_response(self, survey_response):
        """Copy data from SurveyResponse to CESResponse"""
        try:
            self.survey_response = survey_response
            self.organization = survey_response.organization
            self.customer = survey_response.customer
            
            # Extract CES score
            score = survey_response.get_ces_score()
            if score is not None:
                self.score = score
            else:
                self.score = 4  # Default neutral
            
            # Extract additional CES-specific data
            self.scale_max = survey_response.get_ces_scale_max()
            self.question_text = survey_response.get_ces_question_text()
            self.task_description = survey_response.get_ces_task_description()
            self.feedback = survey_response.get_ces_feedback()
            self.effort_area = survey_response.get_effort_area()
            self.friction_points = survey_response.extract_friction_points()
            
            # Copy follow-up responses
            self.follow_up_responses = survey_response.get_follow_up_responses()
            
            # Copy sentiment analysis if available
            if survey_response.ai_analyzed:
                self.ai_analyzed = True
                self.sentiment_score = survey_response.sentiment_score
                self.sentiment_metadata = survey_response.sentiment_metadata
                self.analysis_status = survey_response.analysis_status
                self.key_themes = survey_response.extract_key_themes()
            
            # Copy metadata
            if survey_response.metadata:
                self.metadata = survey_response.metadata.copy()
            
            logger.info(f"Successfully copied data to CES response from survey {survey_response.id}")
            
        except Exception as e:
            logger.error(f"Error copying to CES response: {str(e)}")
            raise
    
    def copy_from_survey_response1(self, survey_response: SurveyResponse):
        """Copy data from SurveyResponse to CESResponse"""
        self.survey_response = survey_response
        self.organization = survey_response.organization
        self.customer = survey_response.customer
        
        # Extract CES score
        self.score = survey_response.get_ces_score() or 4
        self.scale_max = survey_response.get_ces_scale_max()
        
        # Extract question text, task description, and feedback
        self.question_text = survey_response.get_ces_question_text()
        self.task_description = survey_response.get_ces_task_description()
        self.feedback_comment = survey_response.get_ces_feedback()
        
        # Extract effort area
        self.effort_area = survey_response.get_effort_area()
        
        # Extract friction points
        self.friction_points = survey_response.extract_friction_points()
        
        # Copy AI analysis if available
        if survey_response.ai_analyzed:
            self.ai_analyzed = True
            self.sentiment_score = survey_response.sentiment_score
        
        # Copy metadata using serializable version
        try:
            self.metadata = survey_response.get_serializable_metadata()
        except Exception as e:
            logger.warning(f"Could not get serializable metadata: {str(e)}")
            self.metadata = {}
        
        # Add CES-specific metadata
        if survey_response.id:
            self.metadata.update({
                'survey_response_id': str(survey_response.id),
                'survey_id': str(survey_response.survey_id) if survey_response.survey_id else None,
                'customer_id': str(survey_response.customer_id) if survey_response.customer_id else None,
                'created_at': survey_response.created_at.isoformat() if survey_response.created_at else None,
                'is_complete': survey_response.is_complete,
                'channel': survey_response.channel.name if survey_response.channel else None,
                'device_type': survey_response.device_type,
                'survey_type': survey_response.survey_type,
                'language': survey_response.language,
            })
    
    @property
    def is_high_effort(self) -> bool:
        """Check if this is a high effort response (difficult)"""
        return self.effort_level in ['very_difficult', 'difficult', 'somewhat_difficult']
    
    @property
    def is_low_effort(self) -> bool:
        """Check if this is a low effort response (easy)"""
        return self.effort_level in ['very_easy', 'easy', 'somewhat_easy']
    
    @property
    def is_neutral_effort(self) -> bool:
        """Check if this is a neutral effort response"""
        return self.effort_level == 'neutral'
    
    def get_effort_percentage(self) -> float:
        """Get effort as percentage (0-100, higher is better - less effort)"""
        return self.normalized_score or ((self.score - 1) / (self.scale_max - 1)) * 100
    
    def get_ces_category(self) -> str:
        """Get CES category (High Effort, Low Effort, or Neutral)"""
        if self.is_high_effort:
            return 'high_effort'
        elif self.is_low_effort:
            return 'low_effort'
        else:
            return 'neutral'


# Signal handler for creating CESResponse from SurveyResponse
@receiver(post_save, sender=SurveyResponse)
def create_ces_response_from_survey_response(sender, instance, created, **kwargs):
    """
    Create CESResponse when a SurveyResponse is created for a CES survey
    """
    # Only process if it's a CES survey and is complete
    if not created or not instance.is_complete or instance.survey_type != 'ces':
        return
    
    # Don't create if customer is not available
    if not instance.customer:
        logger.warning(f"Cannot create CESResponse for SurveyResponse {instance.id}: No customer")
        return
    
    try:
        # Check if CESResponse already exists
        if hasattr(instance, 'ces_data') and instance.ces_data:
            logger.info(f"CESResponse already exists for SurveyResponse {instance.id}")
            return
        
        # Extract CES score
        ces_score = instance.get_ces_score()
        if ces_score is None:
            logger.warning(f"Cannot extract CES score from SurveyResponse {instance.id}")
            return
        
        # Ensure organization is available
        if not instance.organization:
            logger.warning(f"Cannot create CESResponse: No organization for SurveyResponse {instance.id}")
            return
        
        # Create CESResponse with minimal required fields first
        ces_response = CESResponse.objects.create(
            survey_response=instance,
            organization=instance.organization,
            customer=instance.customer,
            score=ces_score,
            scale_max=instance.get_ces_scale_max(),
            question_text=instance.get_ces_question_text(),
            task_description=instance.get_ces_task_description(),
            feedback_comment=instance.get_ces_feedback(),
            effort_area=instance.get_effort_area(),
            friction_points=instance.extract_friction_points()
        )
        
        # Now update with additional data (after save)
        ces_response.copy_from_survey_response(instance)
        ces_response.save()  # Save again with updated data
        
        logger.info(f"Created CESResponse {ces_response.id} from SurveyResponse {instance.id}")
        
        # Update survey statistics
        try:
            instance.survey.total_responses += 1
            instance.survey.save(update_fields=['total_responses', 'updated_at'])
        except Exception as e:
            logger.error(f"Failed to update survey statistics: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error creating CESResponse from SurveyResponse {instance.id}: {str(e)}", exc_info=True)


# Signal handler for updating CESResponse when SurveyResponse sentiment is analyzed
@receiver(post_save, sender=SurveyResponse)
def update_ces_response_from_analysis(sender, instance, created, **kwargs):
    """
    Update CESResponse with sentiment analysis results
    """
    # Only process if it's a CES survey and has been analyzed
    if created or instance.survey_type != 'ces' or not instance.ai_analyzed:
        return
    
    try:
        # Find and update the associated CESResponse
        if hasattr(instance, 'ces_data') and instance.ces_data:
            ces_response = instance.ces_data
            
            # Update sentiment analysis data
            ces_response.ai_analyzed = True
            ces_response.sentiment_score = instance.sentiment_score
            
            # Update friction points from AI analysis
            friction_points = instance.extract_friction_points()
            if friction_points:
                # Merge with existing friction points
                existing_points = list(ces_response.friction_points) if ces_response.friction_points else []
                merged_points = list(set(existing_points + friction_points))
                ces_response.friction_points = merged_points[:10]  # Limit to 10
            
            # Add sentiment metadata
            if instance.sentiment_metadata:
                ces_response.metadata['sentiment_analysis'] = {
                    'timestamp': instance.sentiment_metadata.get('analysis_timestamp'),
                    'confidence': instance.sentiment_metadata.get('confidence_score'),
                    'key_themes': instance.sentiment_metadata.get('key_themes', []),
                }
            
            ces_response.save(update_fields=[
                'ai_analyzed', 'sentiment_score', 'friction_points', 
                'metadata', 'updated_at'
            ])
            
            logger.info(f"Updated CESResponse {ces_response.id} with sentiment analysis results")
            
    except Exception as e:
        logger.error(f"Error updating CESResponse for SurveyResponse {instance.id}: {str(e)}", exc_info=True)

import logging
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)

import logging
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class MixedSurveyResponse(TimeStampedModel):

    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name='mixed_responses',
        verbose_name=_('Survey')
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mixed_survey_responses',
        verbose_name=_('Customer')
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='mixed_survey_responses',
        verbose_name=_('Organization'),
        null=True,
        blank=True
    )
    
    # Link to original SurveyResponse
    original_response = models.OneToOneField(
        'SurveyResponse',  # Same app
        on_delete=models.CASCADE,
        related_name='mixed_survey_response',
        null=True,
        blank=True,
        verbose_name=_('Original Survey Response')
    )
    
    # Response Data with enhanced structure for mixed metrics
    response_data = models.JSONField(
        _('Response Data'),
        help_text=_('Structured response data with question types and metric scores'),
        default=dict
    )
    
    # Extracted Metrics (calculated from response_data)
    extracted_metrics = models.JSONField(
        _('Extracted Metrics'),
        help_text=_('Automatically extracted metric scores (NPS, CSAT, CES, etc.)'),
        default=dict,
        blank=True
    )
    
    # Completion Status
    is_complete = models.BooleanField(_('Complete'), default=False)
    completion_time = models.DurationField(_('Completion Time'), null=True, blank=True)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)
    started_at = models.DateTimeField(_('Started At'), null=True, blank=True)
    
    # Source Information
    channel = models.ForeignKey(
        Channel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mixed_survey_responses',
        verbose_name=_('Channel')
    )
    device_type = models.CharField(
        _('Device Type'),
        max_length=50,
        choices=[
            ('desktop', _('Desktop')),
            ('mobile', _('Mobile')),
            ('tablet', _('Tablet')),
            ('other', _('Other')),
        ],
        null=True,
        blank=True
    )
    language = models.CharField(_('Response Language'), max_length=10, default='en')
    
    # AI Analysis
    ai_analyzed = models.BooleanField(_('AI Analyzed'), default=False)
    overall_sentiment_score = models.FloatField(
        _('Overall Sentiment Score'),
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)]
    )
    
    # Enhanced Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    sentiment_metadata = models.JSONField(
        _('Sentiment Analysis Metadata'),
        default=dict,
        blank=True,
        help_text=_('Detailed sentiment analysis results')
    )
    
    # Metric-specific data for quick querying
    has_nps = models.BooleanField(_('Contains NPS'), default=False, db_index=True)
    has_csat = models.BooleanField(_('Contains CSAT'), default=False, db_index=True)
    has_ces = models.BooleanField(_('Contains CES'), default=False, db_index=True)
    has_rating = models.BooleanField(_('Contains Rating'), default=False, db_index=True)
    
    # Calculated scores for easy querying (can be null if not present in survey)
    nps_score = models.IntegerField(
        _('NPS Score'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        db_index=True
    )
    nps_category = models.CharField(
        _('NPS Category'),
        max_length=20,
        choices=[
            ('detractor', _('Detractor (0-6)')),
            ('passive', _('Passive (7-8)')),
            ('promoter', _('Promoter (9-10)')),
        ],
        null=True,
        blank=True,
        db_index=True
    )
    
    csat_score = models.IntegerField(
        _('CSAT Score'),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        db_index=True
    )
    csat_satisfaction_level = models.CharField(
        _('Satisfaction Level'),
        max_length=50,
        choices=[
            ('very_dissatisfied', _('Very Dissatisfied')),
            ('dissatisfied', _('Dissatisfied')),
            ('neutral', _('Neutral')),
            ('satisfied', _('Satisfied')),
            ('very_satisfied', _('Very Satisfied')),
        ],
        null=True,
        blank=True,
        db_index=True
    )
    csat_normalized_score = models.FloatField(
        _('CSAT Normalized Score'),
        null=True,
        blank=True,
        db_index=True
    )
    
    ces_score = models.IntegerField(
        _('CES Score'),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        db_index=True
    )
    ces_effort_level = models.CharField(
        _('Effort Level'),
        max_length=50,
        choices=[
            ('very_difficult', _('Very Difficult')),
            ('difficult', _('Difficult')),
            ('somewhat_difficult', _('Somewhat Difficult')),
            ('neutral', _('Neutral')),
            ('somewhat_easy', _('Somewhat Easy')),
            ('easy', _('Easy')),
            ('very_easy', _('Very Easy')),
        ],
        null=True,
        blank=True,
        db_index=True
    )
    ces_normalized_score = models.FloatField(
        _('CES Normalized Score'),
        null=True,
        blank=True,
        db_index=True
    )
    
    # Overall rating (if multiple ratings, calculate average)
    overall_rating = models.FloatField(
        _('Overall Rating'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        db_index=True
    )
    
    # Text analysis summary
    text_feedback_summary = models.TextField(_('Feedback Summary'), blank=True)
    
    # Friction points for CES
    friction_points = models.JSONField(
        _('Friction Points'),
        default=list,
        blank=True
    )
    
    # Key themes from AI analysis
    key_themes = models.JSONField(
        _('Key Themes'),
        default=list,
        blank=True
    )
    
    # Analysis status
    analysis_status = models.CharField(
        _('Analysis Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending Analysis')),
            ('processing', _('Processing')),
            ('completed', _('Completed')),
            ('failed', _('Failed')),
        ],
        default='pending',
        db_index=True
    )
    
    analysis_retry_count = models.IntegerField(
        _('Analysis Retry Count'),
        default=0,
        help_text=_('Number of times analysis has been retried')
    )
    
    class Meta:
        verbose_name = _('Mixed Survey Response')
        verbose_name_plural = _('Mixed Survey Responses')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['survey', 'customer']),
            models.Index(fields=['survey', 'is_complete']),
            models.Index(fields=['completed_at']),
            models.Index(fields=['analysis_status', 'created_at']),
            models.Index(fields=['overall_sentiment_score']),
            models.Index(fields=['ai_analyzed', 'created_at']),
            models.Index(fields=['has_nps', 'nps_score']),
            models.Index(fields=['has_csat', 'csat_score']),
            models.Index(fields=['has_ces', 'ces_score']),
            models.Index(fields=['nps_category']),
            models.Index(fields=['csat_satisfaction_level']),
            models.Index(fields=['ces_effort_level']),
        ]

    def __str__(self):
        metrics = []
        if self.has_nps and self.nps_score is not None:
            metrics.append(f"NPS:{self.nps_score}")
        if self.has_csat and self.csat_score is not None:
            metrics.append(f"CSAT:{self.csat_score}")
        if self.has_ces and self.ces_score is not None:
            metrics.append(f"CES:{self.ces_score}")
        
        metric_str = " | ".join(metrics) if metrics else "No Metrics"
        
        if self.customer:
            return f"{self.survey.title} - {self.customer.email} [{metric_str}]"
        return f"{self.survey.title} - Anonymous [{metric_str}]"

    def save(self, *args, **kwargs):
        """
        Automatically extract and calculate metrics from response_data before saving
        """
        # Ensure organization is set from survey if not already set
        if not self.organization and self.survey:
            self.organization = self.survey.organization
        
        # Calculate completion time if both started_at and completed_at are available
        if self.started_at and self.completed_at:
            self.completion_time = self.completed_at - self.started_at
        
        # Extract metrics from response_data (always do this)
        if self.response_data:
            # Force extract_and_calculate_metrics to run
            self.extract_and_calculate_metrics()
        
        # Set boolean flags for quick filtering
        self.has_nps = self.nps_score is not None
        self.has_csat = self.csat_score is not None
        self.has_ces = self.ces_score is not None
        self.has_rating = self.overall_rating is not None
        
        super().save(*args, **kwargs)
        
        # Trigger AI analysis after saving (to avoid recursion)
        self._trigger_ai_analysis_after_save()
    
    def _trigger_ai_analysis_after_save(self):
        """Trigger AI analysis after the object is saved"""
        # Only trigger if there's text feedback and not already analyzed
        if (self.text_feedback_summary and not self.ai_analyzed and 
            self.analysis_status == 'pending'):
            try:
                self.trigger_ai_analysis()
            except Exception as e:
                logger.error(f"Error triggering AI analysis for MixedSurveyResponse {self.id}: {str(e)}")
    
    def extract_and_calculate_metrics(self):
        """
        Extract all metrics from response_data and populate the calculated fields
        """
        if not self.response_data:
            logger.warning(f"No response data for MixedSurveyResponse {self.id}")
            return
        
        # Get survey questions for context - handle missing questions
        survey_questions = []
        try:
            if hasattr(self.survey, 'questions'):
                survey_questions = self.survey.questions
                if isinstance(survey_questions, str):
                    import json
                    survey_questions = json.loads(survey_questions)
            else:
                # Try to get from survey metadata
                if hasattr(self.survey, 'metadata') and self.survey.metadata:
                    survey_questions = self.survey.metadata.get('questions', [])
        except Exception as e:
            logger.error(f"Error getting survey questions for MixedSurveyResponse {self.id}: {str(e)}")
            survey_questions = []
        
        # Initialize extracted metrics dictionary
        self.extracted_metrics = {
            'nps_scores': [],
            'csat_scores': [],
            'ces_scores': [],
            'rating_scores': [],
            'yes_no_responses': {},
            'text_responses': [],
            'multiple_choice_responses': {},
            'all_responses': list(self.response_data.items())
        }
        
        # Process each response item
        for question_id, answer in self.response_data.items():
            # Find question definition
            question_def = self._find_question_by_id(question_id, survey_questions)
            
            # If no question definition found, create a basic one
            if not question_def:
                question_def = {
                    'type': self._infer_question_type(question_id, answer),
                    'text': question_id,
                    'id': question_id
                }
            
            question_type = question_def.get('type', 'text')
            question_text = question_def.get('text', question_id)
            
            # Process based on question type
            if question_type == 'nps':
                self._process_nps_response(question_id, answer, question_text)
            elif question_type == 'csat':
                self._process_csat_response(question_id, answer, question_text)
            elif question_type == 'ces':
                self._process_ces_response(question_id, answer, question_text)
            elif question_type == 'rating':
                self._process_rating_response(question_id, answer, question_def)
            elif question_type == 'yes_no':
                self._process_yes_no_response(question_id, answer, question_text)
            elif question_type == 'text':
                self._process_text_response(question_id, answer, question_text)
            elif question_type == 'multiple_choice':
                self._process_multiple_choice_response(question_id, answer, question_def)
            else:
                # Default to text processing for unknown types
                self._process_text_response(question_id, answer, question_text)
        
        # Calculate overall metrics after processing all questions
        self._calculate_overall_metrics()
        
        # Log extracted metrics for debugging
        logger.debug(f"Extracted metrics for MixedSurveyResponse {self.id}: {self.extracted_metrics}")
    
    def _infer_question_type(self, question_id, answer):
        """Infer question type from question ID and answer"""
        question_lower = str(question_id).lower()
        answer_str = str(answer).lower()
        
        # Check question text for clues
        if any(word in question_lower for word in ['nps', 'recommend', 'likely to recommend']):
            return 'nps'
        elif any(word in question_lower for word in ['satisfied', 'satisfaction', 'csat']):
            return 'csat'
        elif any(word in question_lower for word in ['easy', 'difficult', 'effort', 'ces']):
            return 'ces'
        elif any(word in question_lower for word in ['rating', 'rate', 'score']):
            return 'rating'
        elif any(word in answer_str for word in ['yes', 'no', 'true', 'false']):
            return 'yes_no'
        elif isinstance(answer, list) or (',' in answer_str and len(answer_str.split(',')) > 1):
            return 'multiple_choice'
        elif isinstance(answer, (int, float)) or answer_str.isdigit():
            # Check if numeric answer fits common ranges
            try:
                num = float(answer_str)
                if 0 <= num <= 10:
                    # Check if it's NPS (0-10) or CSAT/CES (1-10)
                    if num == 0 or 'nps' in question_lower:
                        return 'nps'
                    elif 'csat' in question_lower:
                        return 'csat'
                    elif 'ces' in question_lower:
                        return 'ces'
                    else:
                        return 'rating'
            except ValueError:
                pass
        
        # Default to text
        return 'text'
    
    def _find_question_by_id(self, question_id, survey_questions):
        """Find question definition by ID or index"""
        if not survey_questions:
            return None
        
        try:
            # Try by ID first
            if isinstance(question_id, str):
                for q in survey_questions:
                    if isinstance(q, dict) and q.get('id') == question_id:
                        return q
            
            # Try by index (q_0, q_1, etc.)
            if isinstance(question_id, str) and question_id.startswith('q_'):
                try:
                    idx = int(question_id[2:])
                    if 0 <= idx < len(survey_questions):
                        return survey_questions[idx]
                except (ValueError, IndexError):
                    pass
            
            # Try by position in list
            try:
                idx = int(question_id)
                if 0 <= idx < len(survey_questions):
                    return survey_questions[idx]
            except (ValueError, TypeError):
                pass
            
            # Return the first question with matching text in key
            for q in survey_questions:
                if isinstance(q, dict):
                    q_text = q.get('text', '').lower()
                    if q_text and isinstance(question_id, str) and any(word in question_id.lower() for word in q_text.split()[:3]):
                        return q
        
        except Exception as e:
            logger.error(f"Error finding question by ID {question_id}: {str(e)}")
        
        return None
    
    def _process_nps_response(self, question_id, answer, question_text):
        """Process NPS question response"""
        try:
            score = self._parse_numeric_score(answer, min_val=0, max_val=10)
            if score is not None:
                self.extracted_metrics['nps_scores'].append({
                    'question_id': question_id,
                    'question_text': question_text,
                    'score': score,
                    'category': self._categorize_nps_score(score)
                })
                
                # Store the NPS score (use first NPS question found or average if multiple)
                if self.nps_score is None:
                    self.nps_score = score
                    self.nps_category = self._categorize_nps_score(score)
                elif len(self.extracted_metrics['nps_scores']) > 1:
                    # Calculate average if multiple NPS questions
                    avg_score = sum(item['score'] for item in self.extracted_metrics['nps_scores']) / len(self.extracted_metrics['nps_scores'])
                    self.nps_score = int(round(avg_score))
                    self.nps_category = self._categorize_nps_score(avg_score)
                    
        except Exception as e:
            logger.error(f"Error processing NPS response {question_id}: {str(e)}")
    
    def _process_csat_response(self, question_id, answer, question_text):
        """Process CSAT question response"""
        try:
            score = self._parse_numeric_score(answer, min_val=1, max_val=10)
            if score is not None:
                # Determine scale from question or default to 5
                scale_max = self._determine_scale_max(question_text) or 5
                
                normalized_score = ((score - 1) / (scale_max - 1)) * 100 if scale_max > 1 else 0
                
                self.extracted_metrics['csat_scores'].append({
                    'question_id': question_id,
                    'question_text': question_text,
                    'score': score,
                    'scale_max': scale_max,
                    'normalized_score': normalized_score,
                    'satisfaction_level': self._categorize_csat_score(score, scale_max)
                })
                
                # Store CSAT score (use average if multiple CSAT questions)
                if self.csat_score is None:
                    self.csat_score = score
                    self.csat_satisfaction_level = self._categorize_csat_score(score, scale_max)
                    self.csat_normalized_score = normalized_score
                elif len(self.extracted_metrics['csat_scores']) > 1:
                    # Calculate average if multiple CSAT questions
                    avg_score = sum(item['score'] for item in self.extracted_metrics['csat_scores']) / len(self.extracted_metrics['csat_scores'])
                    avg_scale_max = self.extracted_metrics['csat_scores'][0]['scale_max']  # Use first question's scale
                    
                    self.csat_score = int(round(avg_score))
                    self.csat_satisfaction_level = self._categorize_csat_score(avg_score, avg_scale_max)
                    self.csat_normalized_score = ((avg_score - 1) / (avg_scale_max - 1)) * 100 if avg_scale_max > 1 else 0
                    
        except Exception as e:
            logger.error(f"Error processing CSAT response {question_id}: {str(e)}")
    
    def _process_ces_response(self, question_id, answer, question_text):
        """Process CES question response"""
        try:
            score = self._parse_numeric_score(answer, min_val=1, max_val=10)
            if score is not None:
                # CES typically uses 7-point scale
                scale_max = self._determine_scale_max(question_text) or 7
                
                normalized_score = ((score - 1) / (scale_max - 1)) * 100 if scale_max > 1 else 0
                
                self.extracted_metrics['ces_scores'].append({
                    'question_id': question_id,
                    'question_text': question_text,
                    'score': score,
                    'scale_max': scale_max,
                    'normalized_score': normalized_score,
                    'effort_level': self._categorize_ces_score(score, scale_max)
                })
                
                # Store CES score (use average if multiple CES questions)
                if self.ces_score is None:
                    self.ces_score = score
                    self.ces_effort_level = self._categorize_ces_score(score, scale_max)
                    self.ces_normalized_score = normalized_score
                elif len(self.extracted_metrics['ces_scores']) > 1:
                    # Calculate average if multiple CES questions
                    avg_score = sum(item['score'] for item in self.extracted_metrics['ces_scores']) / len(self.extracted_metrics['ces_scores'])
                    avg_scale_max = self.extracted_metrics['ces_scores'][0]['scale_max']  # Use first question's scale
                    
                    self.ces_score = int(round(avg_score))
                    self.ces_effort_level = self._categorize_ces_score(avg_score, avg_scale_max)
                    self.ces_normalized_score = ((avg_score - 1) / (avg_scale_max - 1)) * 100 if avg_scale_max > 1 else 0
                    
        except Exception as e:
            logger.error(f"Error processing CES response {question_id}: {str(e)}")
    
    def _process_rating_response(self, question_id, answer, question_def):
        """Process rating question response"""
        try:
            score = self._parse_numeric_score(answer, min_val=0, max_val=10)
            if score is not None:
                scale_max = question_def.get('scale_max', 5)
                
                self.extracted_metrics['rating_scores'].append({
                    'question_id': question_id,
                    'question_text': question_def.get('text', ''),
                    'score': score,
                    'scale_max': scale_max,
                    'normalized_score': (score / scale_max) * 100 if scale_max > 0 else 0
                })
        except Exception as e:
            logger.error(f"Error processing rating response {question_id}: {str(e)}")
    
    def _process_yes_no_response(self, question_id, answer, question_text):
        """Process Yes/No question response"""
        try:
            is_yes = self._parse_yes_no(answer)
            
            self.extracted_metrics['yes_no_responses'][question_id] = {
                'question_text': question_text,
                'answer': answer,
                'is_yes': is_yes,
                'is_no': not is_yes if is_yes is not None else None
            }
        except Exception as e:
            logger.error(f"Error processing Yes/No response {question_id}: {str(e)}")
    
    def _process_text_response(self, question_id, answer, question_text):
        """Process text question response"""
        try:
            if isinstance(answer, str) and answer.strip():
                self.extracted_metrics['text_responses'].append({
                    'question_id': question_id,
                    'question_text': question_text,
                    'answer': answer.strip()
                })
        except Exception as e:
            logger.error(f"Error processing text response {question_id}: {str(e)}")
    
    def _process_multiple_choice_response(self, question_id, answer, question_def):
        """Process multiple choice question response"""
        try:
            options = question_def.get('options', [])
            multiple = question_def.get('multiple', False)
            
            # Handle single or multiple selections
            if multiple and isinstance(answer, list):
                selected_options = [opt for opt in answer if opt in options]
            elif answer in options:
                selected_options = [answer]
            else:
                selected_options = []
            
            self.extracted_metrics['multiple_choice_responses'][question_id] = {
                'question_text': question_def.get('text', ''),
                'options': options,
                'selected_options': selected_options,
                'is_multiple': multiple
            }
        except Exception as e:
            logger.error(f"Error processing multiple choice response {question_id}: {str(e)}")
    
    def _calculate_overall_metrics(self):
        """Calculate overall metrics from extracted data"""
        # Calculate average rating if multiple rating questions
        rating_scores = self.extracted_metrics.get('rating_scores', [])
        if rating_scores:
            total = sum(item['score'] for item in rating_scores)
            count = len(rating_scores)
            self.overall_rating = total / count if count > 0 else None
        
        # Collect all text feedback for analysis
        text_responses = self.extracted_metrics.get('text_responses', [])
        if text_responses:
            # Create a readable summary of text responses
            summaries = []
            for item in text_responses[:3]:  # Limit to 3 responses for summary
                question = item['question_text'][:50] + "..." if len(item['question_text']) > 50 else item['question_text']
                answer = item['answer'][:100] + "..." if len(item['answer']) > 100 else item['answer']
                summaries.append(f"Q: {question}\nA: {answer}")
            
            self.text_feedback_summary = "\n\n".join(summaries)
            
            # Also store all text for AI analysis
            all_text = " ".join([item['answer'] for item in text_responses if item['answer']])
            self.extracted_metrics['all_text_for_analysis'] = all_text
        
        # Log calculated metrics for debugging
        logger.info(f"Calculated metrics for MixedSurveyResponse {self.id}: "
                   f"NPS={self.nps_score}, CSAT={self.csat_score}, CES={self.ces_score}, "
                   f"Overall Rating={self.overall_rating}")
    
    def _parse_numeric_score(self, value, min_val, max_val):
        """Parse numeric score from various input types"""
        try:
            if isinstance(value, (int, float)):
                score = float(value)
            elif isinstance(value, str):
                # Clean the string
                value = value.strip()
                
                # Extract first number from string
                import re
                match = re.search(r'[-+]?\d*\.\d+|\d+', value)
                if match:
                    score = float(match.group())
                else:
                    # Try to parse string values like "very easy", "satisfied", etc.
                    score = self._parse_qualitative_score(value, min_val, max_val)
                    if score is not None:
                        return int(round(score))
                    
                    # Check for common rating strings
                    rating_map = {
                        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
                    }
                    if value.lower() in rating_map:
                        return rating_map[value.lower()]
                    
                    return None
            else:
                return None
            
            if min_val <= score <= max_val:
                return int(round(score))
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing numeric score {value}: {str(e)}")
        return None
    
    def _parse_qualitative_score(self, value, min_val, max_val):
        """Parse qualitative responses like 'very easy', 'satisfied', etc."""
        value_lower = str(value).lower().strip()
        
        # Map qualitative responses to scores
        qualitative_map = {
            # NPS-like (0-10)
            'not at all likely': 0, 'extremely likely': 10,
            'definitely not': 0, 'definitely yes': 10,
            
            # CES-like (1-7)
            'very difficult': 1, 'difficult': 2, 'somewhat difficult': 3,
            'neutral': 4, 'somewhat easy': 5, 'easy': 6, 'very easy': 7,
            
            # CSAT-like (1-5)
            'very dissatisfied': 1, 'dissatisfied': 2, 'neutral': 3,
            'satisfied': 4, 'very satisfied': 5,
            
            # Generic
            'strongly disagree': 1, 'disagree': 2, 'neutral': 3,
            'agree': 4, 'strongly agree': 5,
            
            # Star ratings
            '⭐': 1, '⭐⭐': 2, '⭐⭐⭐': 3, '⭐⭐⭐⭐': 4, '⭐⭐⭐⭐⭐': 5,
            '★': 1, '★★': 2, '★★★': 3, '★★★★': 4, '★★★★★': 5,
        }
        
        return qualitative_map.get(value_lower)
    
    def _parse_yes_no(self, value):
        """Parse Yes/No response"""
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ['yes', 'y', 'true', '1', 'ok', 'agree', 'agree strongly', 'positive']:
                return True
            elif value_lower in ['no', 'n', 'false', '0', 'disagree', 'disagree strongly', 'negative']:
                return False
        elif isinstance(value, bool):
            return value
        elif isinstance(value, int):
            return value == 1
        return None
    
    def _categorize_nps_score(self, score):
        """Categorize NPS score"""
        if score <= 6:
            return 'detractor'
        elif score <= 8:
            return 'passive'
        else:
            return 'promoter'
    
    def _categorize_csat_score(self, score, scale_max=5):
        """Categorize CSAT score"""
        if scale_max == 5:
            if score <= 1:
                return 'very_dissatisfied'
            elif score <= 2:
                return 'dissatisfied'
            elif score <= 3:
                return 'neutral'
            elif score <= 4:
                return 'satisfied'
            else:  # score > 4
                return 'very_satisfied'
        else:
            # Generic categorization for other scales
            percentage = (score - 1) / (scale_max - 1) if scale_max > 1 else 0
            if percentage < 0.2:
                return 'very_dissatisfied'
            elif percentage < 0.4:
                return 'dissatisfied'
            elif percentage < 0.6:
                return 'neutral'
            elif percentage < 0.8:
                return 'satisfied'
            else:
                return 'very_satisfied'
    
    def _categorize_ces_score(self, score, scale_max=7):
        """Categorize CES score"""
        if scale_max == 7:
            if score <= 1:
                return 'very_difficult'
            elif score <= 2:
                return 'difficult'
            elif score <= 3:
                return 'somewhat_difficult'
            elif score <= 4:
                return 'neutral'
            elif score <= 5:
                return 'somewhat_easy'
            elif score <= 6:
                return 'easy'
            else:  # score > 6
                return 'very_easy'
        else:
            # Generic categorization
            percentage = (score - 1) / (scale_max - 1) if scale_max > 1 else 0
            if percentage < 0.2:
                return 'very_difficult'
            elif percentage < 0.35:
                return 'difficult'
            elif percentage < 0.5:
                return 'somewhat_difficult'
            elif percentage < 0.65:
                return 'neutral'
            elif percentage < 0.8:
                return 'somewhat_easy'
            elif percentage < 0.95:
                return 'easy'
            else:
                return 'very_easy'
    
    def _determine_scale_max(self, question_text):
        """Determine scale maximum from question text"""
        if not question_text:
            return None
            
        question_lower = question_text.lower()
        
        # Check for scale indicators in question text
        if '1 to 10' in question_lower or '1-10' in question_lower:
            return 10
        elif '1 to 7' in question_lower or '1-7' in question_lower:
            return 7
        elif '1 to 5' in question_lower or '1-5' in question_lower:
            return 5
        elif '1 to 3' in question_lower or '1-3' in question_lower:
            return 3
        
        # Default based on common patterns
        if 'nps' in question_lower or 'recommend' in question_lower or '0 to 10' in question_lower:
            return 10  # NPS is 0-10
        elif 'effort' in question_lower or 'easy' in question_lower or 'difficult' in question_lower:
            return 7  # CES typically 7-point
        elif 'satisfied' in question_lower or 'satisfaction' in question_lower:
            return 5  # CSAT typically 5-point
        
        return None
    
    def trigger_ai_analysis(self):
        """Trigger AI analysis asynchronously or in background"""
        # Set status to processing
        self.analysis_status = 'processing'
        self.save(update_fields=['analysis_status'])
        
        try:
            # Run analysis synchronously for now
            success = self.analyze_sentiment()
            
            if success:
                logger.info(f"AI analysis completed for MixedSurveyResponse {self.id}")
            else:
                logger.warning(f"AI analysis failed for MixedSurveyResponse {self.id}")
                
        except Exception as e:
            logger.error(f"Error in AI analysis for MixedSurveyResponse {self.id}: {str(e)}")
            self.analysis_status = 'failed'
            self.analysis_retry_count += 1
            self.save(update_fields=['analysis_status', 'analysis_retry_count'])
    
    def analyze_sentiment(self):
        """Perform sentiment analysis on text responses"""
        # Check if we have text to analyze
        if not self.extracted_metrics.get('text_responses'):
            self.analysis_status = 'completed'
            self.ai_analyzed = True
            self.overall_sentiment_score = 0.0
            self.save(update_fields=['analysis_status', 'ai_analyzed', 'overall_sentiment_score'])
            return True
        
        try:
            # Extract all text for analysis
            all_text = " ".join([
                item['answer'] for item in self.extracted_metrics['text_responses']
                if item['answer']
            ])
            
            if not all_text.strip():
                self.analysis_status = 'completed'
                self.ai_analyzed = True
                self.overall_sentiment_score = 0.0
                self.save(update_fields=['analysis_status', 'ai_analyzed', 'overall_sentiment_score'])
                return True
            
            # Try to use TextBlob for sentiment analysis
            try:
                from textblob import TextBlob
                blob = TextBlob(all_text)
                sentiment = blob.sentiment.polarity  # -1 to 1
                
                self.overall_sentiment_score = sentiment
                self.ai_analyzed = True
                
                # Extract key themes (simple keyword extraction)
                import re
                from collections import Counter
                
                # Clean and tokenize text
                words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text.lower())
                
                # Remove common stop words
                stop_words = {'that', 'with', 'this', 'from', 'have', 'what', 'when', 
                            'were', 'your', 'will', 'they', 'their', 'about', 'would',
                            'there', 'which', 'could', 'should', 'them', 'some', 'very'}
                
                filtered_words = [word for word in words if word not in stop_words]
                
                # Count word frequencies
                word_counts = Counter(filtered_words)
                
                # Get top 5 key themes
                self.key_themes = [word for word, count in word_counts.most_common(5)]
                
                # Extract friction points for CES
                if self.has_ces:
                    friction_keywords = ['difficult', 'hard', 'complicated', 'confusing', 
                                        'slow', 'problem', 'issue', 'frustrating', 'annoying',
                                        'challenging', 'trouble', 'struggle', 'hassle']
                    
                    found_frictions = []
                    for keyword in friction_keywords:
                        if keyword in all_text.lower():
                            found_frictions.append(keyword)
                    
                    self.friction_points = found_frictions
                
                # Update sentiment metadata
                self.sentiment_metadata = {
                    'analysis_method': 'textblob',
                    'text_length': len(all_text),
                    'word_count': len(all_text.split()),
                    'key_themes': self.key_themes,
                    'friction_points': self.friction_points,
                    'analysis_timestamp': timezone.now().isoformat()
                }
                
                self.analysis_status = 'completed'
                self.save()
                
                logger.info(f"Sentiment analysis completed for MixedSurveyResponse {self.id}: score={sentiment}")
                return True
                
            except ImportError:
                logger.warning("TextBlob not available for sentiment analysis, using fallback")
                # Fallback: simple sentiment analysis
                positive_words = ['good', 'great', 'excellent', 'awesome', 'love', 'happy', 
                                'satisfied', 'easy', 'wonderful', 'fantastic', 'perfect']
                negative_words = ['bad', 'terrible', 'awful', 'hate', 'unhappy', 'dissatisfied', 
                                'difficult', 'poor', 'horrible', 'worst', 'frustrating']
                
                text_lower = all_text.lower()
                positive_count = sum(1 for word in positive_words if word in text_lower)
                negative_count = sum(1 for word in negative_words if word in text_lower)
                
                total = positive_count + negative_count
                if total > 0:
                    self.overall_sentiment_score = (positive_count - negative_count) / total
                else:
                    self.overall_sentiment_score = 0.0
                
                self.ai_analyzed = True
                
                # Simple keyword extraction for fallback
                words = all_text.lower().split()
                common_words = {'the', 'and', 'for', 'with', 'that', 'this', 'was', 'were', 
                              'are', 'is', 'to', 'of', 'in', 'it', 'you', 'a', 'an'}
                
                word_counts = {}
                for word in words:
                    if len(word) > 3 and word not in common_words and word.isalpha():
                        word_counts[word] = word_counts.get(word, 0) + 1
                
                self.key_themes = [word for word, count in sorted(word_counts.items(), 
                                                                 key=lambda x: x[1], reverse=True)[:3]]
                
                self.analysis_status = 'completed'
                self.save()
                
                return True
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis for MixedSurveyResponse {self.id}: {str(e)}")
            self.analysis_status = 'failed'
            self.analysis_retry_count += 1
            self.save(update_fields=['analysis_status', 'analysis_retry_count'])
            return False
    
    @property
    def contains_metrics(self):
        """Check if response contains any metric scores"""
        return any([
            self.has_nps,
            self.has_csat,
            self.has_ces,
            self.has_rating
        ])
    
    def get_all_metrics(self):
        """Get all metric scores as a dictionary"""
        return {
            'nps': {
                'score': self.nps_score,
                'category': self.nps_category,
                'display': dict(self._meta.get_field('nps_category').choices).get(self.nps_category) if self.nps_category else None
            },
            'csat': {
                'score': self.csat_score,
                'satisfaction_level': self.csat_satisfaction_level,
                'normalized_score': self.csat_normalized_score,
                'display': dict(self._meta.get_field('csat_satisfaction_level').choices).get(self.csat_satisfaction_level) if self.csat_satisfaction_level else None
            },
            'ces': {
                'score': self.ces_score,
                'effort_level': self.ces_effort_level,
                'normalized_score': self.ces_normalized_score,
                'display': dict(self._meta.get_field('ces_effort_level').choices).get(self.ces_effort_level) if self.ces_effort_level else None
            },
            'overall_rating': self.overall_rating,
            'text_feedback_summary': self.text_feedback_summary,
            'friction_points': self.friction_points,
            'key_themes': self.key_themes,
            'has_metrics': self.contains_metrics,
            'sentiment': self.overall_sentiment_score,
            'ai_analyzed': self.ai_analyzed
        }


@receiver(post_save, sender=SurveyResponse)
def create_mixed_response_for_mixed_surveys(sender, instance, created, **kwargs):
    """
    Create MixedSurveyResponse when a SurveyResponse is created for a mixed survey
    """
    # Only process if it's a mixed survey and is complete
    if not instance.is_complete:
        return
    
    # Check if survey is mixed type - check both survey.survey_type and instance.survey_type
    is_mixed_survey = False
    if instance.survey and hasattr(instance.survey, 'survey_type'):
        is_mixed_survey = instance.survey.survey_type == 'mixed'
    elif hasattr(instance, 'survey_type'):
        is_mixed_survey = instance.survey_type == 'mixed'
    
    if not is_mixed_survey:
        return
    
    # Don't create if already linked
    if hasattr(instance, 'mixed_survey_response') and instance.mixed_survey_response:
        logger.debug(f"MixedSurveyResponse already exists for SurveyResponse {instance.id}")
        return
    
    try:
        logger.info(f"Creating MixedSurveyResponse from SurveyResponse {instance.id}")
        
        # Get organization - try multiple sources
        organization = None
        if instance.organization:
            organization = instance.organization
        elif hasattr(instance, '_organization'):
            organization = instance._organization
        elif instance.survey and instance.survey.organization:
            organization = instance.survey.organization
        
        # Create MixedSurveyResponse with all available data
        mixed_response = MixedSurveyResponse(
            survey=instance.survey,
            customer=instance.customer,
            organization=organization,
            original_response=instance,  # Link to original
            response_data=getattr(instance, 'response_data', {}),
            is_complete=True,
            started_at=getattr(instance, 'started_at', None),
            completed_at=getattr(instance, 'completed_at', None),
            channel=getattr(instance, 'channel', None),
            device_type=getattr(instance, 'device_type', None),
            language=getattr(instance, 'language', 'en'),
            metadata=getattr(instance, 'metadata', {}).copy() if hasattr(instance, 'metadata') and instance.metadata else {}
        )
        
        # Copy AI analysis data if available
        if hasattr(instance, 'ai_analyzed') and instance.ai_analyzed:
            mixed_response.ai_analyzed = True
            mixed_response.overall_sentiment_score = getattr(instance, 'sentiment_score', None)
            mixed_response.sentiment_metadata = getattr(instance, 'sentiment_metadata', {}).copy() if hasattr(instance, 'sentiment_metadata') else {}
            mixed_response.analysis_status = getattr(instance, 'analysis_status', 'completed')
            
            # Copy key themes and friction points if available
            if hasattr(instance, 'extract_key_themes'):
                mixed_response.key_themes = instance.extract_key_themes()
            if hasattr(instance, 'extract_friction_points'):
                mixed_response.friction_points = instance.extract_friction_points()
        
        # Save the response - this will trigger metric extraction
        mixed_response.save()
        
        logger.info(f"Created MixedSurveyResponse {mixed_response.id} from SurveyResponse {instance.id}")
        
        # Force metric extraction if not already done
        if not mixed_response.extracted_metrics or mixed_response.extracted_metrics == {}:
            mixed_response.extract_and_calculate_metrics()
            mixed_response.save()
            logger.info(f"Force extracted metrics for MixedSurveyResponse {mixed_response.id}")
        
    except Exception as e:
        logger.error(f"Error creating MixedSurveyResponse from SurveyResponse {instance.id}: {str(e)}", exc_info=True)
        # Log more details for debugging
        logger.error(f"SurveyResponse details: id={instance.id}, survey={instance.survey.id if instance.survey else None}, "
                    f"customer={instance.customer.id if instance.customer else None}, "
                    f"is_complete={instance.is_complete}")
#combined signal handler to include CES
@receiver(post_save, sender=SurveyResponse)
def create_specialized_response(sender, instance, created, **kwargs):
    """
    Create specialized response models (NPSResponse, CSATResponse, CESResponse) based on survey type
    This is a combined handler that calls the specific handlers
    """
    if not created or not instance.is_complete:
        return
    
    # Route to appropriate handler based on survey type
    if instance.survey_type == 'nps':
        create_nps_response_from_survey_response(sender, instance, created, **kwargs)
    elif instance.survey_type == 'csat':
        create_csat_response_from_survey_response(sender, instance, created, **kwargs)
    elif instance.survey_type == 'ces':
        create_ces_response_from_survey_response(sender, instance, created, **kwargs)


class AIAnalysisJob(TimeStampedModel):
    """
    Track AI analysis batch jobs and their status
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='ai_jobs',
        verbose_name=_('Organization')
    )
    
    # Job Information
    job_id = models.CharField(_('Job ID'), max_length=100, unique=True, db_index=True)
    job_type = models.CharField(
        _('Job Type'),
        max_length=50,
        choices=[
            ('sentiment_analysis', _('Sentiment Analysis')),
            ('theme_extraction', _('Theme Extraction')),
            ('bulk_analysis', _('Bulk Analysis')),
            ('trend_analysis', _('Trend Analysis')),
            ('report_generation', _('Report Generation')),
        ],
        db_index=True
    )
    description = models.TextField(_('Description'), blank=True)
    
    # Status Tracking
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('running', _('Running')),
            ('completed', _('Completed')),
            ('failed', _('Failed')),
            ('cancelled', _('Cancelled')),
        ],
        default='pending',
        db_index=True
    )
    progress = models.IntegerField(
        _('Progress Percentage'),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Processing Details
    total_items = models.IntegerField(_('Total Items'), default=0)
    processed_items = models.IntegerField(_('Processed Items'), default=0)
    failed_items = models.IntegerField(_('Failed Items'), default=0)
    
    # Timing
    started_at = models.DateTimeField(_('Started At'), null=True, blank=True)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)
    duration = models.DurationField(_('Duration'), null=True, blank=True)
    
    # Results
    result_data = models.JSONField(_('Result Data'), default=dict, blank=True)
    error_log = models.TextField(_('Error Log'), blank=True)
    
    # AI Model Info
    model_used = models.CharField(_('AI Model'), max_length=100, blank=True)
    api_calls_made = models.IntegerField(_('API Calls Made'), default=0)
    tokens_used = models.IntegerField(_('Tokens Used'), default=0)
    
    # Configuration
    parameters = models.JSONField(_('Job Parameters'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('AI Analysis Job')
        verbose_name_plural = _('AI Analysis Jobs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['job_type', 'status']),
        ]

    def __str__(self):
        return f"{self.job_id} - {self.get_job_type_display()} ({self.status})"


class MetricSnapshot(TimeStampedModel):
    """
    Time-series snapshots of key metrics for trend analysis
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='metric_snapshots',
        verbose_name=_('Organization')
    )
    
    # Time Period
    snapshot_date = models.DateField(_('Snapshot Date'), db_index=True)
    period_type = models.CharField(
        _('Period Type'),
        max_length=20,
        choices=[
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
            ('monthly', _('Monthly')),
            ('quarterly', _('Quarterly')),
            ('yearly', _('Yearly')),
        ],
        db_index=True
    )
    
    # NPS Metrics
    nps_score = models.FloatField(_('NPS Score'), null=True, blank=True)
    nps_promoters_count = models.IntegerField(_('Promoters Count'), default=0)
    nps_passives_count = models.IntegerField(_('Passives Count'), default=0)
    nps_detractors_count = models.IntegerField(_('Detractors Count'), default=0)
    nps_response_count = models.IntegerField(_('NPS Response Count'), default=0)
    
    # CSAT Metrics
    csat_score = models.FloatField(_('Average CSAT Score'), null=True, blank=True)
    csat_response_count = models.IntegerField(_('CSAT Response Count'), default=0)
    csat_distribution = models.JSONField(_('CSAT Distribution'), default=dict, blank=True)
    
    # CES Metrics
    ces_score = models.FloatField(_('Average CES Score'), null=True, blank=True)
    ces_response_count = models.IntegerField(_('CES Response Count'), default=0)
    ces_distribution = models.JSONField(_('CES Distribution'), default=dict, blank=True)
    
    # Sentiment Metrics
    average_sentiment = models.FloatField(_('Average Sentiment'), null=True, blank=True)
    sentiment_distribution = models.JSONField(_('Sentiment Distribution'), default=dict, blank=True)
    
    # Feedback Volume
    total_feedback_count = models.IntegerField(_('Total Feedback'), default=0)
    feedback_by_type = models.JSONField(_('Feedback by Type'), default=dict, blank=True)
    feedback_by_channel = models.JSONField(_('Feedback by Channel'), default=dict, blank=True)
    
    # Resolution Metrics
    average_resolution_time = models.DurationField(_('Avg Resolution Time'), null=True, blank=True)
    resolution_rate = models.FloatField(_('Resolution Rate'), null=True, blank=True)
    
    # Top Themes
    top_themes = models.JSONField(_('Top Themes'), default=list, blank=True)
    
    # Additional Metrics
    custom_metrics = models.JSONField(_('Custom Metrics'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Metric Snapshot')
        verbose_name_plural = _('Metric Snapshots')
        ordering = ['-snapshot_date']
        unique_together = [['organization', 'snapshot_date', 'period_type']]
        indexes = [
            models.Index(fields=['organization', 'snapshot_date']),
            models.Index(fields=['period_type', 'snapshot_date']),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.snapshot_date} ({self.period_type})"

class Alert(TimeStampedModel):
    """
    Real-time alerts for significant events or threshold breaches
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name=_('Organization')
    )
    
    # Alert Configuration
    alert_type = models.CharField(
        _('Alert Type'),
        max_length=50,
        choices=[
            ('negative_sentiment_spike', _('Negative Sentiment Spike')),
            ('nps_drop', _('NPS Score Drop')),
            ('csat_drop', _('CSAT Score Drop')),
            ('ces_increase', _('CES Score Increase')),
            ('high_priority_feedback', _('High Priority Feedback')),
            ('theme_trending', _('Theme Trending')),
            ('response_time_breach', _('Response Time Breach')),
            ('volume_spike', _('Volume Spike')),
            ('custom', _('Custom Alert')),
        ],
        db_index=True
    )
    severity = models.CharField(
        _('Severity'),
        max_length=20,
        choices=[
            ('info', _('Info')),
            ('warning', _('Warning')),
            ('critical', _('Critical')),
        ],
        default='warning',
        db_index=True
    )
    
    # Alert Content
    title = models.CharField(_('Alert Title'), max_length=255)
    message = models.TextField(_('Alert Message'))
    
    # Related Objects
    related_feedback = models.ForeignKey(
        'Feedback',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts',
        verbose_name=_('Related Feedback')
    )
    related_theme = models.ForeignKey(
        'Theme',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts',
        verbose_name=_('Related Theme')
    )
    
    # Alert Data
    metric_value = models.FloatField(_('Metric Value'), null=True, blank=True)
    threshold_value = models.FloatField(_('Threshold Value'), null=True, blank=True)
    additional_data = models.JSONField(_('Additional Data'), default=dict, blank=True)
    
    # Status
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('new', _('New')),
            ('acknowledged', _('Acknowledged')),
            ('resolved', _('Resolved')),
            ('dismissed', _('Dismissed')),
        ],
        default='new',
        db_index=True
    )
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        verbose_name=_('Acknowledged By')
    )
    acknowledged_at = models.DateTimeField(_('Acknowledged At'), null=True, blank=True)
    
    # Notification
    notification_sent = models.BooleanField(_('Notification Sent'), default=False)
    # FIXED: Replaced ArrayField with JSONField for database compatibility
    notification_channels = models.JSONField(
        _('Notification Channels'),
        default=list,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Alert')
        verbose_name_plural = _('Alerts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.title}" 

class Resolution(TimeStampedModel):
    """
    Track resolution details for feedback/complaints
    """
    feedback = models.OneToOneField(
        Feedback,
        on_delete=models.CASCADE,
        related_name='resolution',
        verbose_name=_('Feedback')
    )
    
    # Resolution Details
    resolution_type = models.CharField(
        _('Resolution Type'),
        max_length=50,
        choices=[
            ('resolved', _('Resolved')),
            ('workaround', _('Workaround Provided')),
            ('duplicate', _('Duplicate')),
            ('not_reproducible', _('Not Reproducible')),
            ('wont_fix', _("Won't Fix")),
            ('feature_added', _('Feature Added')),
            ('refund_issued', _('Refund Issued')),
            ('compensation', _('Compensation Provided')),
            ('other', _('Other')),
        ]
    )
    description = models.TextField(_('Resolution Description'))
    
    # Resolution Quality
    customer_satisfied = models.BooleanField(_('Customer Satisfied'), null=True, blank=True)
    satisfaction_score = models.IntegerField(
        _('Satisfaction with Resolution'),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    customer_feedback = models.TextField(_('Customer Feedback on Resolution'), blank=True)
    
    # Ownership
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='resolutions',
        verbose_name=_('Resolved By')
    )
    resolved_at = models.DateTimeField(_('Resolved At'), auto_now_add=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(_('Follow-up Required'), default=False)
    follow_up_date = models.DateTimeField(_('Follow-up Date'), null=True, blank=True)
    follow_up_completed = models.BooleanField(_('Follow-up Completed'), default=False)
    
    # Root Cause Analysis
    root_cause = models.TextField(_('Root Cause'), blank=True)
    corrective_actions = models.TextField(_('Corrective Actions'), blank=True)
    
    # Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Resolution')
        verbose_name_plural = _('Resolutions')
        ordering = ['-resolved_at']

    def __str__(self):
        return f"Resolution for {self.feedback.feedback_id}"


class Escalation(TimeStampedModel):
    """
    Track escalated feedback/complaints
    """
    feedback = models.ForeignKey(
        Feedback,
        on_delete=models.CASCADE,
        related_name='escalations',
        verbose_name=_('Feedback')
    )
    
    # Escalation Details
    escalation_level = models.IntegerField(
        _('Escalation Level'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    escalation_reason = models.CharField(
        _('Escalation Reason'),
        max_length=50,
        choices=[
            ('high_priority', _('High Priority')),
            ('unresolved', _('Unresolved')),
            ('customer_vip', _('VIP Customer')),
            ('legal_concern', _('Legal Concern')),
            ('media_attention', _('Media Attention')),
            ('complex_issue', _('Complex Issue')),
            ('customer_request', _('Customer Request')),
            ('other', _('Other')),
        ]
    )
    description = models.TextField(_('Escalation Description'))
    
    # Ownership
    escalated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='escalations_created',
        verbose_name=_('Escalated By')
    )
    escalated_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='escalations_received',
        verbose_name=_('Escalated To')
    )
    escalated_at = models.DateTimeField(_('Escalated At'), auto_now_add=True)
    
    # Status
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('open', _('Open')),
            ('in_progress', _('In Progress')),
            ('resolved', _('Resolved')),
            ('closed', _('Closed')),
        ],
        default='open'
    )
    resolved_at = models.DateTimeField(_('Resolved At'), null=True, blank=True)
    
    # Notes
    notes = models.TextField(_('Escalation Notes'), blank=True)
    
    class Meta:
        verbose_name = _('Escalation')
        verbose_name_plural = _('Escalations')
        ordering = ['-escalated_at']
        indexes = [
            models.Index(fields=['feedback', 'status']),
            models.Index(fields=['escalation_level', 'status']),
        ]

    def __str__(self):
        return f"Level {self.escalation_level} - {self.feedback.feedback_id}"


class Benchmark(TimeStampedModel):
    """
    Industry benchmarks for comparison
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='benchmarks',
        verbose_name=_('Organization')
    )
    
    # Benchmark Information
    metric_type = models.CharField(
        _('Metric Type'),
        max_length=50,
        choices=[
            ('nps', _('Net Promoter Score')),
            ('csat', _('Customer Satisfaction')),
            ('ces', _('Customer Effort Score')),
            ('resolution_time', _('Resolution Time')),
            ('response_rate', _('Response Rate')),
            ('custom', _('Custom Metric')),
        ],
        db_index=True
    )
    industry = models.CharField(_('Industry'), max_length=100, db_index=True)
    region = models.CharField(_('Region'), max_length=100, blank=True)
    
    # Benchmark Values
    benchmark_value = models.FloatField(_('Benchmark Value'))
    percentile_25 = models.FloatField(_('25th Percentile'), null=True, blank=True)
    percentile_50 = models.FloatField(_('50th Percentile (Median)'), null=True, blank=True)
    percentile_75 = models.FloatField(_('75th Percentile'), null=True, blank=True)
    percentile_90 = models.FloatField(_('90th Percentile'), null=True, blank=True)
    
    # Time Period
    year = models.IntegerField(_('Year'))
    quarter = models.IntegerField(
        _('Quarter'),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    
    # Source
    source = models.CharField(_('Data Source'), max_length=255)
    source_url = models.URLField(_('Source URL'), blank=True)
    sample_size = models.IntegerField(_('Sample Size'), null=True, blank=True)
    
    # Metadata
    notes = models.TextField(_('Notes'), blank=True)
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Benchmark')
        verbose_name_plural = _('Benchmarks')
        ordering = ['-year', '-quarter']
        unique_together = [['organization', 'metric_type', 'industry', 'year', 'quarter']]
        indexes = [
            models.Index(fields=['metric_type', 'industry']),
            models.Index(fields=['year', 'quarter']),
        ]

    def __str__(self):
        return f"{self.get_metric_type_display()} - {self.industry} ({self.year})"


class ActionItem(TimeStampedModel):
    """
    Track action items derived from feedback analysis
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='action_items',
        verbose_name=_('Organization')
    )
    
    # Action Item Details
    title = models.CharField(_('Action Item Title'), max_length=255)
    description = models.TextField(_('Description'))
    action_type = models.CharField(
        _('Action Type'),
        max_length=50,
        choices=[
            ('product_improvement', _('Product Improvement')),
            ('process_change', _('Process Change')),
            ('training', _('Training')),
            ('policy_update', _('Policy Update')),
            ('communication', _('Communication')),
            ('investigation', _('Investigation')),
            ('other', _('Other')),
        ]
    )
    
    # Priority and Status
    priority = models.CharField(
        _('Priority'),
        max_length=20,
        choices=[
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('critical', _('Critical')),
        ],
        default='medium',
        db_index=True
    )
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('planned', _('Planned')),
            ('in_progress', _('In Progress')),
            ('completed', _('Completed')),
            ('on_hold', _('On Hold')),
            ('cancelled', _('Cancelled')),
        ],
        default='planned',
        db_index=True
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='action_items',
        verbose_name=_('Assigned To')
    )
    department = models.CharField(_('Department'), max_length=100, blank=True)
    
    # Timeline
    due_date = models.DateField(_('Due Date'), null=True, blank=True)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)
    
    # Source
    related_theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='action_items',
        verbose_name=_('Related Theme')
    )
    related_feedbacks = models.ManyToManyField(
        Feedback,
        related_name='action_items',
        blank=True,
        verbose_name=_('Related Feedbacks')
    )
    
    # Impact Tracking
    expected_impact = models.TextField(_('Expected Impact'), blank=True)
    actual_impact = models.TextField(_('Actual Impact'), blank=True)
    success_metrics = models.JSONField(_('Success Metrics'), default=dict, blank=True)
    
    # Notes
    notes = models.TextField(_('Notes'), blank=True)
    
    class Meta:
        verbose_name = _('Action Item')
        verbose_name_plural = _('Action Items')
        ordering = ['-priority', 'due_date']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return self.title


class Report(TimeStampedModel):
    """
    Generated reports for insights and analytics
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name=_('Organization')
    )
    
    # Report Details
    title = models.CharField(_('Report Title'), max_length=255)
    report_type = models.CharField(
        _('Report Type'),
        max_length=50,
        choices=[
            ('executive_summary', _('Executive Summary')),
            ('detailed_analysis', _('Detailed Analysis')),
            ('trend_analysis', _('Trend Analysis')),
            ('theme_analysis', _('Theme Analysis')),
            ('nps_report', _('NPS Report')),
            ('csat_report', _('CSAT Report')),
            ('ces_report', _('CES Report')),
            ('sentiment_report', _('Sentiment Report')),
            ('custom', _('Custom Report')),
        ],
        db_index=True
    )
    description = models.TextField(_('Description'), blank=True)
    
    # Time Period
    start_date = models.DateField(_('Start Date'))
    end_date = models.DateField(_('End Date'))
    
    # Report Content
    summary = models.TextField(_('Executive Summary'), blank=True)
    key_findings = models.JSONField(_('Key Findings'), default=list, blank=True)
    visualizations = models.JSONField(_('Visualizations Data'), default=dict, blank=True)
    recommendations = models.JSONField(_('Recommendations'), default=list, blank=True)
    
    # File Storage
    file = models.FileField(
        _('Report File'),
        upload_to='reports/%Y/%m/',
        null=True,
        blank=True
    )
    file_format = models.CharField(
        _('File Format'),
        max_length=20,
        choices=[
            ('pdf', _('PDF')),
            ('xlsx', _('Excel')),
            ('docx', _('Word')),
            ('html', _('HTML')),
            ('json', _('JSON')),
        ],
        null=True,
        blank=True
    )
    
    # Generation Info
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_reports',
        verbose_name=_('Generated By')
    )
    is_automated = models.BooleanField(_('Automated Generation'), default=False)
    generation_status = models.CharField(
        _('Generation Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('generating', _('Generating')),
            ('completed', _('Completed')),
            ('failed', _('Failed')),
        ],
        default='completed'
    )
    
    # Sharing and Access
    is_public = models.BooleanField(_('Public Report'), default=False)
    shared_with = models.ManyToManyField(
        User,
        related_name='shared_reports',
        blank=True,
        verbose_name=_('Shared With')
    )
    
    # Metadata
    metadata = models.JSONField(_('Additional Metadata'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'report_type']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_date} to {self.end_date})"

class ActionPlan(TimeStampedModel):
    """Model for creating and tracking action plans based on feedback themes"""
    
    class PlanStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    class ImpactArea(models.TextChoices):
        PRODUCT = 'PRODUCT', 'Product Development'
        SERVICE = 'SERVICE', 'Customer Service'
        BILLING = 'BILLING', 'Billing & Pricing'
        MARKETING = 'MARKETING', 'Marketing & Communication'
        OPERATIONS = 'OPERATIONS', 'Operations'
        OTHER = 'OTHER', 'Other'
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='action_plans',
        verbose_name=_('Organization')  # Changed from 'action_plans1'
    )
    
    # Basic info
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    
    # Associated themes
    themes = models.ManyToManyField(
        Theme, 
        related_name='action_plans',
        verbose_name=_('Themes')
    )
    
    # Strategic context
    impact_area = models.CharField(
        _('Impact Area'),
        max_length=20, 
        choices=ImpactArea.choices
    )
    strategic_objective = models.TextField(
        _('Strategic Objective'),
        help_text=_("How this aligns with company objectives")
    )
    expected_impact = models.TextField(
        _('Expected Impact'),
        help_text=_("Expected outcome and metrics improvement")
    )
    
    # Execution details
    owner = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='action_plans',
        verbose_name=_('Owner')
    )
    assigned_team = models.CharField(
        _('Assigned Team'),
        max_length=100, 
        help_text=_("Department or team responsible")
    )
    
    # Timeline
    start_date = models.DateField(_('Start Date'), null=True, blank=True)
    target_date = models.DateField(_('Target Date'), null=True, blank=True)
    completed_date = models.DateField(_('Completed Date'), null=True, blank=True)
    
    # Status tracking
    status = models.CharField(
        _('Status'),
        max_length=20, 
        choices=PlanStatus.choices, 
        default=PlanStatus.DRAFT
    )
    progress_percentage = models.IntegerField(
        _('Progress Percentage'),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Metrics
    estimated_cost = models.DecimalField(
        _('Estimated Cost'),
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    priority = models.IntegerField(
        _('Priority'),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Priority level (1-5)")
    )
    
    # Related feedback
    related_feedbacks = models.ManyToManyField(
        Feedback,
        related_name='action_plans',
        blank=True,
        verbose_name=_('Related Feedbacks')
    )
    
    # Notes and tracking
    notes = models.TextField(_('Notes'), blank=True)
    
    class Meta:
        verbose_name = _('Action Plan')
        verbose_name_plural = _('Action Plans')
        indexes = [
            models.Index(fields=['organization', 'status', 'target_date']),
            models.Index(fields=['organization', 'impact_area', 'priority']),
            models.Index(fields=['organization', 'owner', 'status']),
        ]
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.organization.name})"
    
    @property
    def is_overdue(self):
        """Check if action plan is overdue"""
        if self.target_date and self.status not in [self.PlanStatus.COMPLETED, self.PlanStatus.CANCELLED]:
            from django.utils import timezone
            return self.target_date < timezone.now().date()
        return False

class StrategicInsight(TimeStampedModel):
    """Model for storing AI-generated strategic insights from aggregated feedback"""
    
    class InsightType(models.TextChoices):
        TREND = 'TREND', 'Trend Analysis'
        OPPORTUNITY = 'OPPORTUNITY', 'Business Opportunity'
        RISK = 'RISK', 'Potential Risk'
        COMPETITIVE = 'COMPETITIVE', 'Competitive Insight'
        PRODUCT = 'PRODUCT', 'Product Insight'
        CUSTOMER = 'CUSTOMER', 'Customer Behavior Insight'
    
    class ConfidenceLevel(models.TextChoices):
        LOW = 'LOW', 'Low Confidence'
        MEDIUM = 'MEDIUM', 'Medium Confidence'
        HIGH = 'HIGH', 'High Confidence'
        VERY_HIGH = 'VERY_HIGH', 'Very High Confidence'
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='strategic_insights',  # Changed from just 'insights'
        verbose_name=_('Organization')
    )
    
    # Insight content
    title = models.CharField(_('Title'), max_length=300)
    summary = models.TextField(_('Summary'), help_text=_("Executive summary of the insight"))
    detailed_analysis = models.TextField(_('Detailed Analysis'), help_text=_("Comprehensive analysis with data support"))
    
    # Categorization
    insight_type = models.CharField(_('Insight Type'), max_length=20, choices=InsightType.choices)
    impact_area = models.CharField(
        _('Impact Area'),
        max_length=20, 
        choices=[
            ('PRODUCT', _('Product Development')),
            ('SERVICE', _('Customer Service')),
            ('BILLING', _('Billing & Pricing')),
            ('MARKETING', _('Marketing & Communication')),
            ('OPERATIONS', _('Operations')),
            ('OTHER', _('Other')),
        ]
    )
    
    # Associated data
    supporting_themes = models.ManyToManyField(
        Theme, 
        related_name='strategic_insights',
        verbose_name=_('Supporting Themes')
    )
    feedback_count = models.IntegerField(
        _('Feedback Count'),
        default=0, 
        help_text=_("Number of feedback items supporting this insight")
    )
    
    # Confidence and impact
    confidence_level = models.CharField(
        _('Confidence Level'),
        max_length=20, 
        choices=ConfidenceLevel.choices
    )
    business_impact = models.IntegerField(
        _('Business Impact'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Estimated business impact (1-5)")
    )
    
    # Recommendations
    recommendations = models.JSONField(
        _('Recommendations'),
        default=list, 
        help_text=_("AI-generated strategic recommendations")
    )
    key_metrics = models.JSONField(
        _('Key Metrics'),
        default=list, 
        help_text=_("Metrics to track for this insight")
    )
    
    # AI metadata
    generated_by = models.CharField(_('Generated By'), max_length=50, default='gemini-1.5-pro')
    analysis_period_start = models.DateField(_('Analysis Period Start'))
    analysis_period_end = models.DateField(_('Analysis Period End'))
    
    # Status
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('draft', _('Draft')),
            ('reviewed', _('Reviewed')),
            ('actionable', _('Actionable')),
            ('archived', _('Archived')),
        ],
        default='draft',
        db_index=True
    )
    
    class Meta:
        verbose_name = _('Strategic Insight')
        verbose_name_plural = _('Strategic Insights')
        indexes = [
            models.Index(fields=['organization', 'insight_type', 'business_impact']),
            models.Index(fields=['organization', 'confidence_level', 'created_at']),
            models.Index(fields=['organization', 'status']),
        ]
        ordering = ['-business_impact', '-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.organization.name})"

class FeedbackCampaign(TimeStampedModel):
    """Model for managing targeted feedback collection campaigns"""
    
    class CampaignStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        PAUSED = 'PAUSED', 'Paused'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='feedback_campaigns',
        verbose_name=_('Organization')
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Campaign configuration
    target_audience = models.JSONField(default=dict, help_text="Audience segmentation criteria")
    survey_questions = models.JSONField(default=list, help_text="Survey questions if applicable")
    channels = models.JSONField(default=list, help_text="Channels to collect feedback from")
    
    # Timeline
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Goals and tracking
    target_response_count = models.IntegerField(null=True, blank=True)
    actual_response_count = models.IntegerField(default=0)
    primary_metric = models.CharField(
        max_length=50, 
        default='NPS',
        help_text="Primary metric to track (NPS, CSAT, CES, etc.)"
    )
    
    # Status
    status = models.CharField(max_length=20, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT)
    
    # Results
    campaign_insights = models.JSONField(default=dict, help_text="AI-generated insights from campaign")
    success_metrics = models.JSONField(default=dict, help_text="Key performance indicators")
    
    class Meta:
        verbose_name = 'Feedback Campaign'
        verbose_name_plural = 'Feedback Campaigns'
        indexes = [
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['primary_metric', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Campaign: {self.name}"
    
    @property
    def response_rate(self) -> float:
        if self.target_response_count and self.target_response_count > 0:
            return (self.actual_response_count / self.target_response_count) * 100
        return 0.0
    
    @property
    def is_active(self) -> bool:
        from django.utils import timezone
        now = timezone.now()
        if self.status != self.CampaignStatus.ACTIVE:
            return False
        if self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True
    
pre_save.connect(pre_save_organization, sender=Organization)