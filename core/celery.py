import os
from celery import Celery
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from celery.schedules import crontab




os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()



@shared_task
def send_subscription_expiration_reminder():
    from subscriptions.models import Subscription

    # Get subscriptions expiring in exactly 3 days that haven't received a reminder
    three_days_from_now = timezone.now() + timedelta(days=3)

    # Only check for subscriptions expiring in the next 3 days
    subscriptions = Subscription.objects.filter(
        status='active',
        current_period_end__date=three_days_from_now.date(),
        expiration_reminder_sent=False
    )

    for subscription in subscriptions:
        send_mail(
            'Subscription Expiration Reminder',
            f'Your subscription will expire on {subscription.current_period_end.date()}. Please renew to continue access',
            'noreply@ourapp.com',
            [subscription.user.email],
            fail_silently=False,
        )
        subscription.expiration_reminder_sent=True
        subscription.save()


app.conf.beat_schedule = {
    # Send subscription expiration reminders daily at 9 AM
    'send-subscription-expiration-reminder': {
        'task': 'core.celery.send_subscription_expiration_reminder',
        'schedule': crontab(minute='0', hour='9'),
    },
    
    # Fetch all news (API + RSS) every 2 hours
    'fetch-all-news-filtered': {
        'task': 'articles.tasks.fetch_all_news_sources_filtered',
        'schedule': crontab(minute='0', hour='*/2'),
    },

    # Clean up old drafts daily at 3 AM
    'cleanup-old-drafts': {
        'task': 'articles.tasks.cleanup_old_draft_articles',
        'schedule': crontab(minute='0', hour='3'),
        'args': (30,),
    },
}