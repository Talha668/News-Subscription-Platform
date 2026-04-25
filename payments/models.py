from django.db import models
from django.contrib.auth import get_user_model
from subscriptions.models import Subscription






User = get_user_model()


class PaymentTransaction(models.Model):
    """Track payment transactions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    subscription_id = models.CharField(max_length=100, blank=True)  # Store as string to avoid circular import
    lemon_squeezy_order_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - ${self.amount} - {self.status}"