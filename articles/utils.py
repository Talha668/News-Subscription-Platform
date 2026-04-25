from datetime import date
from django.utils import timezone
from subscriptions.models import Subscription
from .models import ArticleView







def get_user_active_subscription(user):
    """Get user's active subscription or return none"""
    if not user.is_authenticated:
        return None
    
    try:
        subscription = Subscription.objects.filter(
            user=user,
            status='active',
            current_period_end___gt=timezone.now()
        ).select_related('plan').first()
        return subscription
    except Subscription.DoesNotExist:
        return None
    

def get_user_tier(user):
    """Get user's subscription tier (free, premium, or pro)"""
    subscription = get_user_active_subscription(user)
    if subscription and subscription.plan:
        return subscription.plan.tier
    return 'free'


def get_remaining_free_articles(user):
    """Get how mant free acticles user can view this month"""
    if not user.is_authenticated:
        return 0
    
    subscription = get_user_active_subscription(user)

    if not subscription:
        # User has no subscription at all
        return 0
    
    # Check if we need to reset the monthly counter
    today = date.today()
    if subscription.last_reset_date !=today:
        subscription.articles_viewed_this_month = 0
        subscription.last_reset_date = today
        subscription.save()

    free_limit = subscription.plan.free_articles_per_month if subscription.plan else 5
    remaining = free_limit - subscription.articles_viewed_this_month
    return max(0, remaining)


def can_access_article(user, article):
    """
    Check if user can access a specific article.
    Returns (can_access, requires_upgrade, remaining_free_articles)
    """
    # Free articles are always accessible
    if article.required_tier == 'free':
        return True, False, None
    
    user_tier = get_user_tier(user)

    # Check tier access
    tier_access_map = {
        'free': {'free': True, 'premium': False, 'pro': False},
        'premium': {'free': True, 'premium': True, 'pro': False},
        'pro': {'free': True, 'premium': True, 'pro': True},
    }

    can_access = tier_access_map.get(user_tier, {}).get(article.required_tier, False)

    if can_access:
        return True, False, None
    
    # User can't access this tier - check if they have remaining free acticles
    # (Only applies if articles is premium but user is free tier)
    if user_tier == 'free' and article.required_tier == 'premium':
        remaining = get_remaining_free_articles(user)
        if remaining > 0:
            # They can view this as a free preview
            return True, False, remaining
        
    # They need to upgrade
    required_plan = article.required_tier
    return False, True, required_plan


def track_article_view(user, article, request):
    """Track when a user views an article for analytics and free tier counting"""
    from .models import ArticleView

    # Record the view
    ArticleView.objects.create(
        user=user if user.is_authenticated else None,
        article=article,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

    # Increment article view count
    article.view_count += 1
    article.save()

    # If user is on free tier and viewed a premium articele , count it toward monthly limit
    if user.is_authenticated and article.required_tier == 'premium':
        subscription = get_user_active_subscription(user)
        if subscription and subscription.plan and subscription.plan.tier == 'free':
            subscription.articles_viewed_this_month += 1
            subscription.save()