# surveys/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import NPSResponse
from surveys.tasks import analyze_nps_sentiment
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

@receiver(post_save, sender=NPSResponse)
def handle_nps_response_save(sender, instance, created, **kwargs):
    """
    Handle NPS response post-save operations
    """
    if created:
        # Log the response
        logger.info(f"New NPS response created: {instance.id} with score {instance.score}")
        
        # Update organization NPS statistics
        update_organization_nps_stats(instance.organization)
        
        # Trigger follow-up actions based on score
        trigger_follow_up_actions(instance)
        
        # Queue sentiment analysis if there's text content
        if instance.reason or instance.follow_up_question_responses:
            instance.analysis_status = 'pending'
            instance.save(update_fields=['analysis_status'])
            
            if not settings.DEBUG:
                analyze_nps_sentiment.delay(instance.id)

def update_organization_nps_stats(organization):
    """Update organization's NPS statistics"""
    from django.db.models import Avg, Count, Case, When, IntegerField
    from django.db.models.functions import ExtractMonth
    
    responses = NPSResponse.objects.filter(
        organization=organization,
        created_at__gte=timezone.now() - timezone.timedelta(days=90)
    )
    
    # Calculate current NPS
    promoter_count = responses.filter(category='promoter').count()
    detractor_count = responses.filter(category='detractor').count()
    total_responses = responses.count()
    
    if total_responses > 0:
        nps_score = ((promoter_count - detractor_count) / total_responses) * 100
        organization.nps_score = round(nps_score, 1)
        organization.save(update_fields=['nps_score'])

def trigger_follow_up_actions(response):
    """Trigger automated follow-up actions based on NPS score"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    if response.score <= 6:  # Detractor
        # Send alert to customer success team
        subject = f"Detractor Alert: NPS Score {response.score} from {response.customer.email}"
        
        context = {
            'response': response,
            'customer': response.customer,
            'reason': response.reason,
        }
        
        html_message = render_to_string('emails/detractor_alert.html', context)
        plain_message = render_to_string('emails/detractor_alert.txt', context)
        
        # Send to customer success team
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CUSTOMER_SUCCESS_EMAIL],
            html_message=html_message,
            fail_silently=True
        )
    
    elif response.score >= 9:  # Promoter
        # Send thank you and request testimonial
        if not response.customer.is_anonymous:
            send_mail(
                subject=_("Thank you for your feedback!"),
                message=_("We're thrilled you're a promoter! Would you consider sharing a testimonial?"),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[response.customer.email],
                fail_silently=True
            )