from rest_framework import serializers
from .models import PaymentTransaction
from subscriptions.models import Plan, Subscription







class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for payment transaction"""
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'user', 'user_email', 'subscription_id', 'lemon_squeezy_order_id',
            'amount', 'currency', 'status', 'payment_data', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plan"""
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'description', 'price', 'interval',
            'features', 'tier', 'free_articles_per_month', 'is_active'
        ]


class SubscriptionStatusSerializer(serializers.ModelSerializer):
    """Serializer for checking subscription status"""
    plan_details = PlanSerializer(source='plan', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user_email', 'plan_details', 'status',
            'current_period_start', 'current_period_end',
            'cancel_at_period_end', 'cancelled_at'
        ]


class CreateCheckoutResponseSerializer(serializers.Serializer):
    """Serializer for checkout response"""
    checkout_url = serializers.URLField()
    plan = PlanSerializer()


class WebhookPayloadSerializer(serializers.Serializer):
    """Serializer for validating webhook payloads"""
    event_name = serializers.CharField()
    customer_email = serializers.EmailField()
    variant_id = serializers.CharField()
    subscription_id = serializers.CharField(required=False, allow_null=True)
    order_id = serializers.CharField(required=False, allow_null=True)