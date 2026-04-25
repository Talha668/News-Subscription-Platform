from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid






class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    stripe_customer_id = models.CharField(max_length=225, blank=True, null=True)
    is_email_verified =models.BooleanField(default=False)
    email_verifiacation_tiken = models.CharField(max_length=225, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['stripe_customer_id']),
        ]

        def __str__(self):
            return self.email
        

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='proifle')
    company_name = models.CharField(max_length=225, blank=True)
    company_size = models.CharField(max_length=50, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    billing_address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'user_profile'