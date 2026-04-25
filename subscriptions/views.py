from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, render, redirect
from .models import Plan, Subscription
from .serializers import PlanSerializer, SubscriptionSerializer
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from payments.lemon_squeezy import lemon_api
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from payments.models import PaymentTransaction
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta












class PlanListView(generics.ListAPIView):
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]


def pricing(request):
    """Display pricing page"""
    plans = Plan.objects.filter(is_active=True)
    user_subscription = None
    if request.user.is_authenticated:
        try:
            user_subscription = Subscription.objects.get(request=request.user, status='active')
        except Subscription.DoesNotExist:
            pass

    context = {
        'plans': plans,
        'user_subscription': user_subscription,
    }    
    return render(request, 'subscriptions/pricing.html', context)


@login_required
def create_checkout(request, plan_id):
    """Create a Lemon Squeezy checkout session"""
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    
    try:
        response = lemon_api.create_checkout(
            variant_id=plan.lemon_squeezy_variant_id,
            customer_email=request.user.email,
            customer_name=request.user.get_full_name() or request.user.email,
            custom_data={
                'user_id': request.user.id,
                'plan_id': plan.id
            }
        )
        
        checkout_url = response['data']['attributes']['url']
        return redirect(checkout_url)
        
    except Exception as e:
        messages.error(request, f'Error creating checkout: {str(e)}')
        return redirect('pricing')


@login_required
def subscription_detail(request):
    """View current subscription details"""
    try:
        subscription = Subscription.objects.get(user=request.user, status='active')
        
        # Try to fetch subscription from lemon squeezy
        try:
            ls_subscription = lemon_api.get_subscription(subscription.lemon_squeezy_subscription_id)
            ls_data = ls_subscription.get('data', {}).get('attributes', {})
        except:
            ls_data = {}

        context = {
            'subscription': subscription,
            'ls_data': ls_data
        }
        return render(request, 'subscriptions/detail.html', context)
        
    except Subscription.DoesNotExist:
        return render(request, 'subscriptions/no_active.html')


@login_required
def cancel_subscription(request, subscription_id):
    """Cancel a subscription"""
    subscription = get_object_or_404(
        Subscription, 
        id=subscription_id, 
        user=request.user
    )
    
    try:
        lemon_api.cancel_subscription(subscription.lemon_squeezy_subscription_id)
        
        subscription.cancel_at_period_end = True
        subscription.save()
        
        messages.success(request, 'Your subscription will be cancelled at the end of the billing period.')
        
    except Exception as e:
        messages.error(request, f'Error cancelling subscription: {str(e)}')
    
    return redirect('subscription_detail')


@login_required
def resume_subscription(request, subscription_id):
    """Resume a cancelled subscription"""
    subscription = get_object_or_404(
        Subscription,
        id=subscription_id,
        user=request.user
    )

    if not subscription.cancel_at_period_end:
        messages.info(request, 'Your subscription is not scheduled for cancellation.')
        return redirect('subscription_detail')
    
    # For lemon squeezy resuming requires creating a new plan 
    # So redirect to pricing page to select a plan
    messages.info(request, 'Please select a plan to resume your subscription.')
    return redirect('pricing')
  

@login_required
def subscription_history(request):
    """View subscription payment history"""
    transactions = PaymentTransaction.objects.filter(user=request.user).order_by('-created_at')

    # Calculate summery
    total_spent = sum(t.amount for t in transactions if t.status == 'paid')
    success_count = transactions.filter(status='paid').count()
    first_transaction = transactions.last()
    first_transaction_date = first_transaction.created_at.strftime('%b %d, %Y') if first_transaction else None

    context = {
        'transactions': transactions,
        'total_spent': total_spent,
        'success_count': success_count,
        'first_transaction_date': first_transaction_date,
    }
    return render(request, 'subscriptions/history.html', context)

@require_http_methods(['GET'])
def plans_api(reqeust):
    """API endpoints to get plans"""
    plans = Plan.objects.filter(is_active=True).values('id', 'name', 'price', 'interval', 'features', 'subscription')
    return JsonResponse({'plans': list(plans)}, safe=False)


login_required
@require_http_methods(['GET'])
def user_subscription_api(request):
    """API to get user's current subscription"""
    try:
        subscription = Subscription.objects.get(user=request.user, status='active')
        data = {
            'has_subscription': True,
            'plan_id': subscription.plan.id if subscription.plan else None,
            'plan_name': subscription.plan.name if subscription.plan else None,
            'price': float(subscription.plan.price) if subscription.plan else None,
            'interval': subscription.plan.interval if subscription.plan else None,
            'status': subscription.status,
            'current_period_end': subscription.current_period_end.isoformat(),
            'cancel_at_period_end': subscription.cancel_at_period_end,
        }
    except Subscription.DoesNotExist:
        data = {'has_subscription': False}

    return JsonResponse(data)


@staff_member_required
def admin_subscription_stats(request):
    """Admin endpoint for subscription statistics"""
    total_subscriptions = Subscription.objects.count()
    active_subscriptions = Subscription.objects.filter(status='active').count()
    cancelled_subscriptions = Subscription.objects.filter(status='cancelled').count()

    # Revenue by plan
    revenue_by_plan = Subscription.objects.filter(
        status='active'
    ).values('plan__name').annotate(
        total=sum('plan__price')
    )

    # Subscription by plab
    subscription_by_plan = Subscription.objects.values('plan__name').annotate(
        count=Count('id')
    )

    # Recent activity (last 30 days)
    last_30_days = timezone.now() - timedelta(days=30)
    new_subscriptions = Subscription.objects.filter(created_at__gte=last_30_days).count()

    data = {
        'total': total_subscriptions,
        'active': active_subscriptions,
        'cancelled': cancelled_subscriptions,
        'new_last_30_days': new_subscriptions,
        'revenue_by_plan': list(revenue_by_plan),
        'subscription_by_plan': list(subscription_by_plan),
    }
    return JsonResponse(data)


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing plans"""
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        """Get all plans including inactive ones (admin only)"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        plans = Plan.objects.all()
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)


class SubscriptionViewSet(viewsets.ModelViewSet):
    """API endpoint for managing subscriptions"""
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current active subscription"""
        try:
            subscription = Subscription.objects.get(user=request.user, status='active')
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        except Subscription.DoesNotExist:
            return Response({'has_subscription': False}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a subscription"""
        subscription = self.get_object()
        
        if subscription.status != 'active':
            return Response({'error': 'Subscription is not active'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from payments.lemon_squeezy import lemon_api
            lemon_api.cancel_subscription(subscription.lemon_squeezy_subscription_id)
            
            subscription.cancel_at_period_end = True
            subscription.save()
            
            return Response({'message': 'Subscription will be cancelled at period end'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a cancelled subscription"""
        subscription = self.get_object()
        
        if not subscription.cancel_at_period_end:
            return Response({'error': 'Subscription is not scheduled for cancellation'}, status=status.HTTP_400_BAD_REQUEST)
        
        # For Lemon Squeezy, resuming requires creating a new checkout
        return Response({
            'message': 'Please create a new checkout to resume your subscription',
            'action': 'redirect_to_checkout'
        })