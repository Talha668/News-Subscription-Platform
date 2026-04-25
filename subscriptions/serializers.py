from rest_framework import serializers
from .models import Plan, Subscription





class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_details = PlanSerializer(source='plan', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    is_active_status = serializers.BooleanField(source='is_active', read_only=True)

    class Meta:
        model = Subscription
        fields = '__all__'
        depth = 1