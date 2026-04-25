import json
import hmac
import hashlib
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from subscriptions.models import Plan, Subscription






User = get_user_model()



def verify_webhooks_signature(request):
    """Verify that the webhooks raally came from lemon squeezy"""
    signature = request.headers.get('x-signature')
    if not signature:
        return False
    
    # Get the raw request body
    payload = request.body
    secret = settings.LEMON_SQUEEZY_WEBHOOK_SECRET

    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest() 

    return hmac.compare_digest(signature, expected_signature)


@csrf_exempt
@require_POST
def lemon_squeezy_webhook(request):
    """
    Handle lemon squeexzy webhook events
    """

    # Verify signature 
    if not verify_webhooks_signature(request):
        return JsonResponse({'error': 'Invalid signature'}, status=401)
    
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid json'}, status=400) 

    # Get event name and data
    event_name = payload.get('meta', {}).get('event_name')
    event_data = payload.get('data', {})
    attributes = event_data.get('attributes', {})

    # Extract important id's
    customer_email = attributes.get('customer_email')
    variant_id = attributes.get('variant_id') 
    subscription_id = str(event_data.get('id')) if  event_data.get('id') else None

    # Process different event types
    if event_name == 'order_created':
        # New order places - user just subscribed    
        print(f"📦 Order created for {customer_email}")

        # Find or create user
        user, created = User.objects.get_or_create(
            email=customer_email,
            defaults={'username': customer_email}
        )

        # Get the plan from variant_id
        try:
            plan = Plan.objects.get(lemon_squeezy_variant=variant_id)
        except Plan.DoesNotExist:
            print(f"❌ Plan not found for variant_id: {variant_id}")
            return HttpResponse("OK", status=200)

        # Get subscription dates
        current_period_start = attributes.get('current_period_start')
        current_period_end = attributes.get('current_period_end')

        # Create or update subscriptions
        if subscription_id:
            subscription, created = Subscription.objects.update_or_create(
                lemon_squeezy_subscription_id=subscription_id,
                defaults={
                    'user': user,
                    'plan': plan,
                    'status': 'active',
                    'current_period_start': current_period_start,
                    'current_period_end': current_period_end,
                    'cancel_at_period_end': False,
                }
            )
            print(f"✅ Subscription {'created' if created else 'updated'} for {customer_email}")
    elif event_name == 'subscription_created':
        # New subscription created
        print(f"🔄 Subscription created for {customer_email}")

        user, _ = User.objects.get_or_create(
            email=customer_email,
            defaults={'username': customer_email}
        )            

        try:
            plan = Plan.objects.get(lemon_squeezy_variant_id=variant_id)
        except Plan.DoesNotExist:
            print(f"❌ Plan not found for variant_id: {variant_id}")
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
                'cancel_at_period_end': attributes.get('cancels_at') is not None
            }
        )   
        print(f"✅ Subscription created for {customer_email}")

    elif event_name == 'subscription_updated':
        # Subscription changed - updated, downgrade, renewal
        print(f"🔄 Subscription updated for {customer_email}")

        # Get existing subscription
        try:
            subscription = Subscription.objects.get(lemon_squeezy_subscription_id=subscription_id)
        except Subscription.DoesNotExist:
            print(f"⚠ Subscription {subscription_id} not found, will create")
            # Fall back to creation
            user, _ = User.objects.get_or_create(
                email=customer_email,
                defaults={'username': customer_email}
            )    
        else:
            user = subscription.user

        # Update plan if changed
        try:
            plan = Plan.objects.get_or_create(lemon_squeezy_variant_id=variant_id)
        except Plan.DoesNotExist:
            print(f"❌ Plan not found for variant_id: {variant_id}")
            return HttpResponse("OK", status=200)

        current_period_start = attributes.get('current_period_start')
        current_period_end = attributes.get('current_period_end') 
        status = attributes.get('status', 'active')

        Subscription.objects.update_or_create(
            lemon_squeezy_subscription_id=subscription_id,
            defaults={
                'user': user,
                'plan': plan,
                'status': 'active',
                'current_period_start': current_period_start,
                'cuurent_period_end': current_period_end,
                'cancel_at_period_end': attributes.get('cancels_at') is not None,
            }
        )           
        print(f"✅ Subscription updated for {customer_email}")
    
    elif event_name == 'susbcription_cancelled':
        # Subscription cancelled
        print(f"❌ subscription cancelled for {customer_email}")   

        if subscription_id:
            Subscription.objects.filter(
                lemon_squeezy_subscription_id=subscription_id
            ).update(
                status='cancelled',
                cancelled_at=timezone.now(),
                cancel_at_period_end=True
            ) 
            print(f"✅ Subscription marked as cancelled")

    elif event_name == 'subscription_expired':
        # Subscription expired naturally
        print(f"⏰ Subscription expired for {customer_email}")

        if subscription_id:
            Subscription.objects.filter(
                lemon_squeezy_subscription_id=subscription_id
            ).update(status='expired')

    elif event_name == 'subscription_paused':
        # Subscription paused
        print(f"⏸ Subscription paused for {customer_email}")

        if subscription_id:
            Subscription.objects.filter(
                lemon_squeezy_subscription_id=subscription_id
            ).update(status='paused')

    elif event_name == 'subscription_resumed':
        # Subscription resumed
        print(f"▶ Subscription resumed for {customer_email}")

        if subscription_id:
            Subscription.objects.filter(
                lemon_squeezy_subscription_id=subscription_id
            ).update(status='active')

    # Always return 200 to acknowledge receipt
    return HttpResponse("OK", status=200)                        


# @csrf_exempt
# @require_POST
# def lemon_squeezy_webhook(request):
#     """Handle Lemon Squeezy webhook events - SIMPLE TEST VERSION"""
    
#     print("=" * 50)
#     print("WEBHOOK RECEIVED!")
#     print("=" * 50)
#     print(f"Request body: {request.body}")
    
#     try:
#         payload = json.loads(request.body)
#         print(f"Event: {payload.get('meta', {}).get('event_name', 'unknown')}")
#         print("✅ Webhook processed successfully!")
#     except Exception as e:
#         print(f"Error: {e}")
    
#     # Always return 200 OK
#     return HttpResponse("OK", status=200)