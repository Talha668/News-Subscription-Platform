from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone




# class WebhookEvent(models.Model):
#     stripe_event_id = models.CharField(max_length=225, unique=True)
#     event_type = models.CharField(max_length=100)
#     data = JSONField()
#     processed = models.BooleanField(default=False)
#     processed_at = models.DateTimeField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'webhook_events'
#         indexes = [
#             models.Index(fields=['stripe_event_id']),
#             models.Index(fields=['event_type']),
#             models.Index(fields=['processed']),
#         ]

class WebhookEvent(models.Model):
    """Store incoming webhook events from Lemon Squeezy"""
    event_id = models.CharField(max_length=255, unique=True)
    event_name = models.CharField(max_length=100, db_index=True)
    data = models.JSONField(default=dict, blank=True)  # Changed from django.contrib.postgres.fields.JSONField
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.event_name} - {self.event_id}"
    
    def mark_processed(self):
        """Mark webhook as processed"""
        self.processed = True
        self.processed_at = timezone.now()
        self.save()