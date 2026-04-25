from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone




User = get_user_model()


class Plan(models.Model):
    """Subscription plans"""
    INTERVAL_CHOICES = [
        ('month', 'Monthly'),
        ('year', 'Yearly'),
    ]
    """Tier choices"""
    TIER_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('pro', 'Pro'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    lemon_squeezy_variant_id = models.CharField(max_length=100, unique=True)
    lemon_squeezy_product_id = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    interval = models.CharField(max_length=20, choices=INTERVAL_CHOICES, default='month')
    features = models.JSONField(default=list, blank=True)  # Changed from django.contrib.postgres.fields.JSONField
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='free')

    # Limit for free tier
    free_articles_per_month = models.IntegerField(default=3, help_text="Number of articles per month for free tier users")
    
    def __str__(self):
        return f"{self.name} - ${self.price}/{self.interval}"


class Subscription(models.Model):
    """User subscriptions"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('on_trial', 'On Trial'),
        ('paused', 'Paused'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    lemon_squeezy_subscription_id = models.CharField(max_length=100, unique=True)
    lemon_squeezy_order_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    articles_viewed_this_month = models.IntegerField(default=0)
    last_reset_date = models.DateField(default=timezone.now)
    expiration_reminder_sent = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan.name if self.plan else 'No Plan'}"

    def is_active(self):
        return self.status == 'active' and self.current_period_end > timezone.now()