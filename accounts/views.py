import logging
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordResetView,
    PasswordResetDoneView, PasswordResetConfirmView,
    PasswordResetCompleteView, PasswordChangeView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, UpdateView, TemplateView, FormView
from django.views import View
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseRedirect
from django.contrib.auth import views as auth_views
from django.contrib.messages.views import SuccessMessageMixin
from .forms import (
    CustomUserRegistrationForm, CustomAuthenticationForm,
    CustomPasswordResetForm, CustomSetPasswordForm,
    CustomPasswordChangeForm, UserProfileUpdateForm,
    CustomerProfileUpdateForm, EmailChangeForm,
    AccountDeletionForm
)
from core.models import *
from common.utils import *

logger = logging.getLogger(__name__)
User = get_user_model()

class HomePageView(TemplateView):
    context_object_name = "data"
    template_name = "accounts/home-page.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add your data to context
        context['data'] = {
            'welcome_message': 'Welcome to our site!',
            'features': ['Feature 1', 'Feature 2', 'Feature 3']
        }
        return context

def home_page(request):
    context = {
        'data': {
            'welcome_message': 'Welcome to our site!',
            'features': ['Feature 1', 'Feature 2', 'Feature 3']
        }
    }
    return render(request, 'accounts/home-page.html', context)
   

def aboutus(request):
    
    return render(request, 'accounts/aboutus.html')

def privacy(request):
    return render(request, 'accounts/privacy_policy.html')

def conditions(request):
    return render(request, 'accounts/terms_and_conditions.html')

def careers(request):
    return render(request, 'accounts/careers.html')

def contact(request):
    return render(request, 'accounts/contact.html')

def help(request):
    return render(request, 'accounts/help.html')

def doc(request):
    return render(request, 'accounts/doc.html')

def api_docs(request):
    return render(request, 'accounts/api-docs.html')

def services(request):
    return render(request, 'accounts/services.html')

def status(request):
    return render(request, 'accounts/status.html')
def packages(request):
    return render(request, 'accounts/packages.html')

def compliance(request):
    return render(request, 'accounts/compliance.html')
     
class RegisterView(CreateView):
    """
    User registration view with automatic profile creation
    """
    template_name = 'accounts/register.html'
    form_class = CustomUserRegistrationForm
    success_url = reverse_lazy('accounts:login')
    
    def dispatch(self, request, *args, **kwargs):
        """Redirect authenticated users to dashboard"""
        if request.user.is_authenticated:
            messages.info(request, _('You are already logged in.'))
            return redirect('accounts:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Handle successful registration"""
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                
                # Log registration
                logger.info(
                    f'New user registered: {self.object.username} ({self.object.email})'
                )
                
                # Send welcome email
                self.send_welcome_email(self.object)
                
                # Success message
                messages.success(
                    self.request,
                    _(
                        'Registration successful! Welcome to our platform. '
                        'Please log in with your credentials.'
                    )
                )
                
                return response
                
        except Exception as e:
            logger.error(f'Error during registration: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred during registration. Please try again.')
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Handle registration errors"""
        messages.error(
            self.request,
            _('Please correct the errors below.')
        )
        return super().form_invalid(form)
    
    def send_welcome_email(self, user):
        """Send welcome email to new user"""
        try:
            subject = _('Welcome to Customer Experience Platform')
            message = _(
                f'Hello {user.get_full_name()},\n\n'
                f'Welcome to our Customer Experience Platform! '
                f'Your account has been successfully created.\n\n'
                f'Username: {user.username}\n'
                f'Email: {user.email}\n\n'
                f'You can now log in and start using the platform.\n\n'
                f'Best regards,\n'
                f'The CX Platform Team'
            )
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f'Error sending welcome email: {str(e)}')
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Create Your Account')
        context['page_title'] = _('Register')
        return context


class CustomLoginView(LoginView):
    """
    Enhanced login view with remember me functionality
    """
    template_name = 'accounts/login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('accounts:home-page')
    
    def form_valid(self, form):
        """Handle successful login"""
        remember_me = form.cleaned_data.get('remember_me')
        
        if not remember_me:
            # Session expires when browser closes
            self.request.session.set_expiry(0)
        else:
            # Session expires after 30 days
            self.request.session.set_expiry(30 * 24 * 60 * 60)
        
        # Log successful login
        logger.info(
            f'User logged in: {form.get_user().username} '
            f'from IP: {self.get_client_ip()}'
        )
        
        messages.success(
            self.request,
            _('Welcome back, %(name)s!') % {'name': form.get_user().get_full_name()}
        )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Handle login errors"""
        messages.error(
            self.request,
            _('Invalid username/email or password. Please try again.')
        )
        
        # Log failed login attempt
        username = form.cleaned_data.get('username', 'unknown')
        logger.warning(
            f'Failed login attempt for: {username} '
            f'from IP: {self.get_client_ip()}'
        )
        
        return super().form_invalid(form)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Sign In to Your Account')
        context['page_title'] = _('Login')
        return context


class CustomLogoutView(LogoutView):
    """
    Enhanced logout view
    """
    next_page = reverse_lazy('accounts:login')
    
    def dispatch(self, request, *args, **kwargs):
        """Log logout action"""
        if request.user.is_authenticated:
            logger.info(f'User logged out: {request.user.username}')
            messages.success(
                request,
                _('You have been successfully logged out.')
            )
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordResetView(PasswordResetView):
    """
    Enhanced password reset request view
    """
    template_name = 'accounts/password-reset.html'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('accounts:password-reset-done')
    email_template_name = 'accounts/emails/password-reset-email.html'
    subject_template_name = 'accounts/emails/password-reset-subject.txt'

    def form_valid(self, form):
        """Handle valid password reset request"""
        # Log password reset request
        email = form.cleaned_data.get('email')
        logger.info(f'Password reset requested for email: {email}')
        
        messages.success(
            self.request,
            _(
                'If an account exists with this email address, '
                'you will receive password reset instructions shortly.'
            )
        )
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Reset Your Password')
        context['page_title'] = _('Password Reset')
        return context


class CustomPasswordResetDoneView(PasswordResetDoneView):
    """
    Password reset email sent confirmation
    """
    template_name = 'accounts/password-reset-done.html'
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Password Reset Email Sent')
        context['page_title'] = _('Check Your Email')
        return context


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Password reset confirmation view (from email link)
    """
    template_name = 'accounts/password-reset-confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('accounts:password-reset-complete')
    
    def form_valid(self, form):
        """Handle successful password reset"""
        # Log password reset
        user = form.user
        logger.info(f'Password reset completed for user: {user.username}')
        
        messages.success(
            self.request,
            _('Your password has been reset successfully. You can now log in.')
        )
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Enter New Password')
        context['page_title'] = _('Reset Password')
        return context


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """
    Password reset completion confirmation
    """
    template_name = 'accounts/password-reset-complete.html'
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Password Reset Complete')
        context['page_title'] = _('Success')
        return context


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """
    Password change view for authenticated users
    """
    template_name = 'accounts/password-change.html'
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy('accounts:password-change-done')
    
    def form_valid(self, form):
        """Handle successful password change"""
        # Log password change
        logger.info(f'Password changed for user: {self.request.user.username}')
        
        # Update session to prevent logout
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        
        messages.success(
            self.request,
            _('Your password has been changed successfully.')
        )
        
        return response
    
    def form_invalid(self, form):
        """Handle password change errors"""
        messages.error(
            self.request,
            _('Please correct the errors below.')
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Change Your Password')
        context['page_title'] = _('Change Password')
        return context


class PasswordChangeDoneView(LoginRequiredMixin, TemplateView):
    """
    Password change success confirmation
    """
    template_name = 'accounts/password-change-done.html'
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Password Changed Successfully')
        context['page_title'] = _('Success')
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    User profile view (display only)
    """
    template_name = 'accounts/profile.html'
    
    def get_context_data(self, **kwargs):
        """Add user and customer profile data"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Your Profile')
        context['page_title'] = _('Profile')
        
        # Get customer profile
        try:
            customer = Customer.objects.get(user=self.request.user)
            context['customer'] = customer
            context['organization'] = customer.organization
        except Customer.DoesNotExist:
            context['customer'] = None
            logger.warning(
                f'Customer profile not found for user: {self.request.user.username}'
            )
        
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    User profile update view
    """
    template_name = 'accounts/profile-update.html'
    form_class = UserProfileUpdateForm
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self, queryset=None):
        """Return the current user"""
        return self.request.user
    
    def get_context_data(self, **kwargs):
        """Add customer form to context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Edit Your Profile')
        context['page_title'] = _('Edit Profile')
        
        if self.request.POST:
            context['customer_form'] = CustomerProfileUpdateForm(
                self.request.POST,
                instance=self.get_customer()
            )
        else:
            context['customer_form'] = CustomerProfileUpdateForm(
                instance=self.get_customer()
            )
        
        return context
    
    def get_customer(self):
        """Get or create customer profile"""
        try:
            return Customer.objects.get(user=self.request.user)
        except Customer.DoesNotExist:
            # Create customer profile if it doesn't exist
            org, _ = Organization.objects.get_or_create(
                slug=f'user-{self.request.user.username}',
                defaults={'name': f"{self.request.user.get_full_name()}'s Organization"}
            )
            return Customer.objects.create(
                organization=org,
                user=self.request.user,
                customer_id=f'CUST-{self.request.user.id}',
                email=self.request.user.email,
                first_name=self.request.user.first_name,
                last_name=self.request.user.last_name,
            )
    
    def form_valid(self, form):
        """Handle both user and customer form validation"""
        context = self.get_context_data()
        customer_form = context['customer_form']
        
        if customer_form.is_valid():
            try:
                with transaction.atomic():
                    # Save user profile
                    self.object = form.save()
                    
                    # Save customer profile
                    customer_form.save()
                    
                    # Update customer email to match user email
                    customer = self.get_customer()
                    customer.email = self.object.email
                    customer.first_name = self.object.first_name
                    customer.last_name = self.object.last_name
                    customer.save()
                    
                    logger.info(
                        f'Profile updated for user: {self.request.user.username}'
                    )
                    
                    messages.success(
                        self.request,
                        _('Your profile has been updated successfully.')
                    )
                    
                    return HttpResponseRedirect(self.success_url)
                    
            except Exception as e:
                logger.error(f'Error updating profile: {str(e)}')
                messages.error(
                    self.request,
                    _('An error occurred while updating your profile.')
                )
                return self.form_invalid(form)
        else:
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Handle validation errors"""
        messages.error(
            self.request,
            _('Please correct the errors below.')
        )
        return super().form_invalid(form)


class EmailChangeView(LoginRequiredMixin, FormView):
    """
    Email change view with confirmation
    """
    template_name = 'accounts/email-change.html'
    form_class = EmailChangeForm
    success_url = reverse_lazy('accounts:profile')
    
    def get_form_kwargs(self):
        """Pass user to form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Handle email change"""
        try:
            with transaction.atomic():
                new_email = form.cleaned_data['new_email']
                old_email = self.request.user.email
                
                # Update user email
                self.request.user.email = new_email
                self.request.user.save()
                
                # Update customer email
                try:
                    customer = Customer.objects.get(user=self.request.user)
                    customer.email = new_email
                    customer.save()
                except Customer.DoesNotExist:
                    pass
                
                # Log email change
                logger.info(
                    f'Email changed for user {self.request.user.username}: '
                    f'{old_email} -> {new_email}'
                )
                
                # Send notification to both emails
                self.send_email_change_notification(old_email, new_email)
                
                messages.success(
                    self.request,
                    _('Your email address has been changed successfully.')
                )
                
                return super().form_valid(form)
                
        except Exception as e:
            logger.error(f'Error changing email: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while changing your email.')
            )
            return self.form_invalid(form)
    
    def send_email_change_notification(self, old_email, new_email):
        """Send notification about email change"""
        try:
            subject = _('Your Email Address Has Been Changed')
            message = _(
                f'Hello {self.request.user.get_full_name()},\n\n'
                f'This is to confirm that your email address has been changed.\n\n'
                f'Old email: {old_email}\n'
                f'New email: {new_email}\n\n'
                f'If you did not make this change, please contact support immediately.\n\n'
                f'Best regards,\n'
                f'The CX Platform Team'
            )
            
            # Send to both old and new email
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [old_email, new_email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f'Error sending email change notification: {str(e)}')
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Change Your Email Address')
        context['page_title'] = _('Change Email')
        return context


class AccountDeletionView(LoginRequiredMixin, FormView):
    """
    Account deletion view with confirmation
    """
    template_name = 'accounts/account-delete.html'
    form_class = AccountDeletionForm
    success_url = reverse_lazy('accounts:account-deleted')
    
    def get_form_kwargs(self):
        """Pass user to form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Handle account deletion"""
        try:
            with transaction.atomic():
                user = self.request.user
                username = user.username
                email = user.email
                
                # Log account deletion
                logger.warning(
                    f'Account deletion initiated for user: {username} ({email})'
                )
                
                # Send confirmation email before deletion
                self.send_deletion_confirmation_email(user)
                
                # Soft delete: deactivate instead of hard delete
                user.is_active = False
                user.save()
                
                # Deactivate customer profile
                try:
                    customer = Customer.objects.get(user=user)
                    customer.is_active = False
                    customer.save()
                except Customer.DoesNotExist:
                    pass
                
                # Logout user
                logout(self.request)
                
                messages.success(
                    self.request,
                    _('Your account has been deactivated successfully.')
                )
                
                return super().form_valid(form)
                
        except Exception as e:
            logger.error(f'Error deleting account: {str(e)}')
            messages.error(
                self.request,
                _('An error occurred while deleting your account.')
            )
            return self.form_invalid(form)
    
    def send_deletion_confirmation_email(self, user):
        """Send account deletion confirmation email"""
        try:
            subject = _('Your Account Has Been Deleted')
            message = _(
                f'Hello {user.get_full_name()},\n\n'
                f'This is to confirm that your account has been deleted.\n\n'
                f'Username: {user.username}\n'
                f'Email: {user.email}\n\n'
                f'If you did not request this, please contact support immediately.\n\n'
                f'We\'re sorry to see you go. You can create a new account anytime.\n\n'
                f'Best regards,\n'
                f'The CX Platform Team'
            )
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f'Error sending deletion confirmation email: {str(e)}')
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Delete Your Account')
        context['page_title'] = _('Delete Account')
        return context


class AccountDeletedView(TemplateView):
    """
    Account deletion confirmation page
    """
    template_name = 'accounts/account-deleted.html'
    
    def get_context_data(self, **kwargs):
        """Add extra context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Account Deleted')
        context['page_title'] = _('Goodbye')
        return context

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard view (redirect target after login)
    """
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        """Add dashboard data"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Dashboard')
        context['page_title'] = _('Dashboard')
        
        # Get customer data
        try:
            customer = Customer.objects.get(user=self.request.user)
            context['customer'] = customer
            context['organization'] = customer.organization
        except Customer.DoesNotExist:
            context['customer'] = None
        
        # Sample data for dashboard (replace with actual data from your models)
        context['sample_themes'] = [
            {'name': _('User Interface'), 'percentage': 75, 'count': 324, 'color': 'bg-primary'},
            {'name': _('Performance'), 'percentage': 60, 'count': 256, 'color': 'bg-success'},
            {'name': _('Customer Support'), 'percentage': 45, 'count': 198, 'color': 'bg-info'},
            {'name': _('Feature Request'), 'percentage': 30, 'count': 132, 'color': 'bg-warning'},
            {'name': _('Billing'), 'percentage': 20, 'count': 87, 'color': 'bg-danger'},
        ]
        
        context['sample_activities'] = [
            {'icon': 'chat-dots', 'color': 'primary', 'message': _('New feedback collected from web form'), 'time': _('2 minutes ago')},
            {'icon': 'graph-up', 'color': 'success', 'message': _('Weekly report generated'), 'time': _('1 hour ago')},
            {'icon': 'person-plus', 'color': 'info', 'message': _('New team member added'), 'time': _('3 hours ago')},
            {'icon': 'exclamation-triangle', 'color': 'warning', 'message': _('Negative sentiment detected in feedback'), 'time': _('5 hours ago')},
            {'icon': 'check-circle', 'color': 'success', 'message': _('Project status updated'), 'time': _('1 day ago')},
        ]
        
        return context
    
