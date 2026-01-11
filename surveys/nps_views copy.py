# surveys/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.generic import CreateView, TemplateView, DetailView
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.contrib import messages
from django.urls import reverse_lazy
import json
import uuid
from .forms import NPSResponseForm, QuickNPSForm
from core.models import *



class NPSResponseCreateView(CreateView):
    """
    Main view for collecting NPS responses with full experience
    """
    model = NPSResponse
    form_class = NPSResponseForm
    template_name = 'nps_responses/nps-response-form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.survey = get_object_or_404(
            Survey.objects.select_related('organization'),
            pk=kwargs.get('survey_id'),
            status='active',
            survey_type='nps'
        )
        
        # Check if survey is active
        if not self.is_survey_active():
            return render(request, 'nps_responses/survey-inactive.html', {
                'survey': self.survey
            })
        
        # Get or create customer from session/token
        self.customer = self.get_customer()
        self.channel = self.get_channel()
        
        return super().dispatch(request, *args, **kwargs)
    
    def is_survey_active(self):
        """Check if survey is within active dates"""
        now = timezone.now()
        
        if self.survey.start_date and self.survey.start_date > now:
            return False
        if self.survey.end_date and self.survey.end_date < now:
            return False
        if self.survey.response_limit and self.survey.total_responses >= self.survey.response_limit:
            return False
        
        return True
    def get_customer(self):
        """Get or create customer based on session/context"""
        customer_id = self.request.session.get('customer_id')
        email = self.request.GET.get('email')
        
        if customer_id:
            try:
                return Customer.objects.get(pk=customer_id, organization=self.survey.organization)
            except Customer.DoesNotExist:
                pass
        
        # Create anonymous customer if no email provided
        if not email:
            # Generate unique customer ID for anonymous customer
            customer_id_str = f"anon_{uuid.uuid4().hex[:8]}"
            return Customer.objects.create(
                organization=self.survey.organization,
                customer_id=customer_id_str,  # REQUIRED FIELD
                email=f"{customer_id_str}@anonymous.com",
                customer_type='anonymous',
                segment='anonymous'  # Also set segment as it has a default but anonymous should have it
            )
        
        # Get or create customer by email
        # First check if customer with this email already exists
        try:
            customer = Customer.objects.get(
                organization=self.survey.organization,
                email=email
            )
            return customer
        except Customer.DoesNotExist:
            # Create new customer with email
            customer_id_str = f"cust_{uuid.uuid4().hex[:8]}"
            customer = Customer.objects.create(
                organization=self.survey.organization,
                customer_id=customer_id_str,  # REQUIRED FIELD
                email=email,
                customer_type='identified',  # Changed from 'anonymous' to 'identified'
                segment='new'  # Default segment for new customers
            )
            return customer
     

    def get_channel(self):
        """Determine channel from request"""
        channel_name = self.request.GET.get('channel', 'web')
        try:
            return Channel.objects.get(name=channel_name, organization=self.survey.organization)
        except Channel.DoesNotExist:
            return None
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'survey': self.survey,
            'customer': self.customer,
            'channel': self.channel
        })
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'survey': self.survey,
            'theme_settings': self.survey.theme_settings,
            'questions': self.survey.questions,
            'customer': self.customer,
            'is_embedded': self.request.GET.get('embedded', False)
        })
        return context
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                response = form.save()
                
                # Update survey statistics
                self.survey.total_responses += 1
                self.survey.save(update_fields=['total_responses', 'updated_at'])
                
                # Store customer ID in session
                if not response.customer.is_anonymous:
                    self.request.session['customer_id'] = response.customer.id
                
                # Determine redirect based on score
                if response.score >= 9:
                    success_url = reverse_lazy('nps_thank_you_promoter', kwargs={'response_id': response.id})
                elif response.score >= 7:
                    success_url = reverse_lazy('nps_thank_you_passive', kwargs={'response_id': response.id})
                else:
                    success_url = reverse_lazy('nps_follow_up', kwargs={'response_id': response.id})
                
                return redirect(success_url)
                
        except Exception as e:
            messages.error(self.request, _('An error occurred while saving your response. Please try again.'))
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Please check the form for errors.'))
        return super().form_invalid(form)


class NPSThankYouView(TemplateView):
    """
    Thank you page after NPS submission
    """
    template_name = 'nps_responses/nps-thank-you.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        response_id = self.kwargs.get('response_id')
        
        try:
            nps_response = NPSResponse.objects.select_related(
                'survey', 'customer', 'organization'
            ).get(pk=response_id)
            
            context.update({
                'nps_response': nps_response,
                'survey': nps_response.survey,
                'customer': nps_response.customer,
                'is_promoter': nps_response.category == 'promoter',
                'is_passive': nps_response.category == 'passive',
                'is_detractor': nps_response.category == 'detractor',
                'theme_settings': nps_response.survey.theme_settings if nps_response.survey else {}
            })
        except NPSResponse.DoesNotExist:
            pass
        
        return context


class NPSFollowUpView(DetailView):
    """
    Follow-up view for detractors
    """
    model = NPSResponse
    template_name = 'nps_responses/nps-follow-up.html'
    context_object_name = 'nps_response'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'survey': self.object.survey,
            'customer': self.object.customer,
            'theme_settings': self.object.survey.theme_settings if self.object.survey else {}
        })
        return context


@method_decorator(csrf_exempt, name='dispatch')
class NPSWidgetView(CreateView):
    """
    Lightweight widget view for embedded NPS collection
    """
    form_class = QuickNPSForm
    template_name = 'nps_responses/nps-widget.html'
    http_method_names = ['post']
    
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
    
    def form_valid(self, form):
        try:
            survey_id = self.request.POST.get('survey_id')
            survey = Survey.objects.get(pk=survey_id, status='active', survey_type='nps')
            
            # Get or create customer
            email = form.cleaned_data.get('email')
            if email:
                customer, created = Customer.objects.get_or_create(
                    organization=survey.organization,
                    email=email,
                    defaults={'is_anonymous': False}
                )
            else:
                customer = Customer.objects.create(
                    organization=survey.organization,
                    email=f"anonymous_{uuid.uuid4().hex[:8]}@example.com",
                    is_anonymous=True
                )
            
            # Create NPS response
            nps_response = NPSResponse.objects.create(
                organization=survey.organization,
                customer=customer,
                score=form.cleaned_data['score'],
                reason=form.cleaned_data.get('comment', ''),
                touchpoint='embedded_widget'
            )
            
            # Create survey response
            SurveyResponse.objects.create(
                survey=survey,
                customer=customer,
                response_data={
                    'nps_score': form.cleaned_data['score'],
                    'comment': form.cleaned_data.get('comment', ''),
                    'via_widget': True,
                    'timestamp': timezone.now().isoformat()
                },
                is_complete=True,
                completed_at=timezone.now(),
                device_type='web'
            )
            
            # Update survey stats
            survey.total_responses += 1
            survey.save(update_fields=['total_responses', 'updated_at'])
            
            return JsonResponse({
                'success': True,
                'message': _('Thank you for your feedback!'),
                'category': nps_response.category
            })
            
        except Survey.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': _('Survey not found')
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': _('An error occurred. Please try again.')
            }, status=500)
    
    def form_invalid(self, form):
        errors = form.errors.get_json_data()
        return JsonResponse({
            'success': False,
            'errors': errors,
            'message': _('Please check your input.')
        }, status=400)


@require_http_methods(['GET'])
def nps_score_submit(request):
    """
    AJAX endpoint for scoring in NPS widget
    """
    score = request.GET.get('score')
    survey_id = request.GET.get('survey_id')
    
    if not score or not survey_id:
        return JsonResponse({'error': _('Missing parameters')}, status=400)
    
    try:
        score = int(score)
        if not (0 <= score <= 10):
            return JsonResponse({'error': _('Invalid score')}, status=400)
        
        survey = Survey.objects.get(pk=survey_id)
        
        # Store score in session for form completion
        request.session['nps_score'] = score
        request.session['survey_id'] = survey_id
        
        # Determine next steps based on score
        if score <= 6:
            template = 'nps_responses/partials/detractor_followup.html'
        elif score <= 8:
            template = 'nps_responses/partials/passive_thankyou.html'
        else:
            template = 'nps_responses/partials/promoter_thankyou.html'
        
        return render(request, template, {
            'score': score,
            'survey': survey,
            'theme_settings': survey.theme_settings
        })
        
    except (ValueError, Survey.DoesNotExist):
        return JsonResponse({'error': _('Invalid request')}, status=400)


class NPSSurveyPreviewView(LoginRequiredMixin, TemplateView):
    """
    Preview NPS survey before publishing
    """
    template_name = 'nps_responses/nps-preview.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        survey_id = self.kwargs.get('survey_id')
        
        try:
            survey = Survey.objects.get(
                pk=survey_id,
                organization__members=self.request.user
            )
            context['survey'] = survey
            context['theme_settings'] = survey.theme_settings
            context['is_preview'] = True
        except Survey.DoesNotExist:
            raise PermissionDenied
        
        return context