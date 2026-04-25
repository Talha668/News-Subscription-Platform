import json
import hmac
import hashlib
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from subscriptions.models import Plan, Subscription
from .models import PaymentTransaction
from .serializers import (
    PlanSerializer, SubscriptionStatusSerializer, 
    CreateCheckoutResponseSerializer, PaymentTransactionSerializer
)
from .lemon_squeezy import lemon_api








class AvailablePlansView(APIView):
    """Get all available subscription plans for the pricing page"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        plans = Plan.objects.filter(is_active=True)
        serializer = PlanSerializer(plans, many=True)
        return Response(serializer.data)


class CreateCheckoutView(APIView):
    """Create a Lemon Squeezy checkout URL for a user to subscribe"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        variant_id = request.data.get('variant_id')
        if not variant_id:
            return Response(
                {'error': 'variant_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the plan exists and is active
        try:
            plan = Plan.objects.get(lemon_squeezy_variant_id=variant_id, is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {'error': 'Invalid or inactive plan'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user already has an active subscription
        existing_sub = Subscription.objects.filter(
            user=request.user, 
            status='active',
            current_period_end__gt=timezone.now()
        ).first()
        
        if existing_sub:
            return Response(
                {'error': 'You already have an active subscription. Please cancel it first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create checkout with Lemon Squeezy API
        try:
            checkout_data = lemon_api.create_checkout(
                variant_id=variant_id,
                customer_email=request.user.email,
                customer_name=request.user.get_full_name() or request.user.email,
                custom_data={'user_id': str(request.user.id)}
            )
            
            # Extract the checkout URL from the response
            checkout_url = checkout_data.get('data', {}).get('attributes', {}).get('url')
            
            if not checkout_url:
                return Response(
                    {'error': 'Failed to create checkout URL'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            response_data = {
                'checkout_url': checkout_url,
                'plan': PlanSerializer(plan).data
            }
            
            # Validate with serializer (optional)
            serializer = CreateCheckoutResponseSerializer(data=response_data)
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create checkout: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CurrentSubscriptionView(APIView):
    """Get the current user's active subscription status"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            subscription = Subscription.objects.filter(
                user=request.user,
                status='active',
                current_period_end__gt=timezone.now()
            ).select_related('plan').first()
            
            if subscription:
                serializer = SubscriptionStatusSerializer(subscription)
                return Response({
                    'has_active_subscription': True,
                    'subscription': serializer.data
                })
            else:
                return Response({
                    'has_active_subscription': False,
                    'subscription': None
                })
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CancelSubscriptionView(APIView):
    """Cancel the user's active subscription"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            subscription = Subscription.objects.get(
                user=request.user,
                status='active',
                current_period_end__gt=timezone.now()
            )
        except Subscription.DoesNotExist:
            return Response(
                {'error': 'No active subscription found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Cancel in Lemon Squeezy
        try:
            lemon_api.cancel_subscription(subscription.lemon_squeezy_subscription_id)
        except Exception as e:
            return Response(
                {'error': f'Failed to cancel with payment provider: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Update local record
        subscription.status = 'cancelled'
        subscription.cancel_at_period_end = True
        subscription.cancelled_at = timezone.now()
        subscription.save()
        
        return Response({
            'message': 'Subscription cancelled successfully. You will have access until {}.'.format(
                subscription.current_period_end.strftime('%B %d, %Y')
            )
        })


class UpdateSubscriptionView(APIView):
    """Upgrade or downgrade user's subscription to a different plan"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        new_variant_id = request.data.get('variant_id')
        if not new_variant_id:
            return Response(
                {'error': 'variant_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the new plan
        try:
            new_plan = Plan.objects.get(lemon_squeezy_variant_id=new_variant_id, is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {'error': 'Invalid or inactive plan'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get current subscription
        try:
            subscription = Subscription.objects.get(
                user=request.user,
                status='active',
                current_period_end__gt=timezone.now()
            )
        except Subscription.DoesNotExist:
            return Response(
                {'error': 'No active subscription found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already on this plan
        if subscription.plan == new_plan:
            return Response(
                {'error': 'You are already on this plan'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update in Lemon Squeezy
        try:
            lemon_api.update_subscription(
                subscription.lemon_squeezy_subscription_id, 
                new_variant_id
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to update subscription: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Update local record
        subscription.plan = new_plan
        subscription.save()
        
        return Response({
            'message': f'Subscription updated to {new_plan.name} plan successfully.',
            'new_plan': PlanSerializer(new_plan).data
        })


class UserTransactionsView(APIView):
    """Get the user's payment transaction history"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        transactions = PaymentTransaction.objects.filter(
            user=request.user
        ).order_by('-created_at')
        
        serializer = PaymentTransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class SubscriptionWebhookView(APIView):
    """Handle Lemon Squeezy webhook events - using DRF for better integration"""
    permission_classes = []  # No authentication for webhooks
    authentication_classes = []  # Disable DRF auth
    
    def verify_signature(self, request):
        """Verify that the webhook really came from Lemon Squeezy"""
        signature = request.headers.get('x-signature')
        if not signature:
            return False
        
        secret = settings.LEMON_SQUEEZY_WEBHOOK_SECRET
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            request.body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def post(self, request):
        # Verify signature
        if not self.verify_signature(request):
            return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        event_name = payload.get('meta', {}).get('event_name')
        event_data = payload.get('data', {})
        attributes = event_data.get('attributes', {})
        
        customer_email = attributes.get('customer_email')
        variant_id = attributes.get('variant_id')
        subscription_id = str(event_data.get('id')) if event_data.get('id') else None
        order_id = attributes.get('order_id')
        amount = attributes.get('total')
        currency = attributes.get('currency', 'USD')
        
        # Get the user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = None
        if customer_email:
            user, _ = User.objects.get_or_create(
                email=customer_email,
                defaults={'username': customer_email}
            )
        
        # Process based on event type
        if event_name in ['order_created', 'subscription_created']:
            # Create payment transaction record
            if user and order_id and amount:
                PaymentTransaction.objects.create(
                    user=user,
                    subscription_id=subscription_id,
                    lemon_squeezy_order_id=order_id,
                    amount=float(amount),
                    currency=currency,
                    status='paid',
                    payment_data=attributes
                )
            
            # Create or update subscription
            if user and variant_id and subscription_id:
                try:
                    plan = Plan.objects.get(lemon_squeezy_variant_id=variant_id)
                except Plan.DoesNotExist:
                    return HttpResponse("OK", status=200)
                
                current_period_start = attributes.get('renews_at') or attributes.get('current_period_start')
                current_period_end = attributes.get('ends_at') or attributes.get('current_period_end')
                
                Subscription.objects.update_or_create(
                    lemon_squeezy_subscription_id=subscription_id,
                    defaults={
                        'user': user,
                        'plan': plan,
                        'status': 'active',
                        'current_period_start': current_period_start or timezone.now(),
                        'current_period_end': current_period_end,
                        'cancel_at_period_end': attributes.get('cancels_at') is not None,
                    }
                )
        
        elif event_name == 'subscription_updated':
            if subscription_id and variant_id:
                try:
                    plan = Plan.objects.get(lemon_squeezy_variant_id=variant_id)
                    Subscription.objects.filter(
                        lemon_squeezy_subscription_id=subscription_id
                    ).update(
                        plan=plan,
                        status='active',
                        cancel_at_period_end=attributes.get('cancels_at') is not None,
                    )
                except Plan.DoesNotExist:
                    pass
        
        elif event_name == 'subscription_cancelled':
            if subscription_id:
                Subscription.objects.filter(
                    lemon_squeezy_subscription_id=subscription_id
                ).update(
                    status='cancelled',
                    cancelled_at=timezone.now(),
                    cancel_at_period_end=True
                )
        
        elif event_name == 'subscription_expired':
            if subscription_id:
                Subscription.objects.filter(
                    lemon_squeezy_subscription_id=subscription_id
                ).update(status='expired')
        
        return HttpResponse("OK", status=200)


# Simple webhook for backward compatibility 
@csrf_exempt
@require_POST
def lemon_squeezy_webhook(request):
    """Legacy webhook view - redirects to DRF version"""
    view = SubscriptionWebhookView.as_view()
    return view(request)