from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.shortcuts import redirect, render
from drf_yasg import openapi
from django.contrib.admin.views.decorators import staff_member_required
from subscriptions.models import Subscription
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from django.views.generic import TemplateView






User = get_schema_view


schema_view = get_schema_view(
    openapi.Info(
        title="Subscription SaaS API",
        default_version='v1',
        description="API documentation for Subscription saas Platform",
        terms_of_service="http://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@subsaas.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# Admin Dashboard View
@staff_member_required
def admin_dashboard(request):
    """Admin dashboard view"""
    total_users = User.objects.count()
    active_subscriptions = Subscription.objects.filter(status='active').count()

    # Calculate monthly revenue
    current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = Subscription.objects.filter(
        status='active',
        created_at__gte=current_month
    ).aggregate(total=Sum('plan__price'))['total'] or 0
    
    # Calculate churn rate (simplified)
    last_month = current_month - timedelta(days=30)
    previous_active = Subscription.objects.filter(
        status='active',
        created_at__lt=current_month,
        created_at__gte=last_month
    ).count()
    churn_rate = 0
    if previous_active > 0:
        churned = Subscription.objects.filter(
            status='cancelled',
            cancelled_at__gte=last_month,
            cancelled_at__lt=current_month
        ).count()
        churn_rate = round((churned / previous_active) * 100, 1)
    
    recent_subscriptions = Subscription.objects.select_related('user', 'plan').order_by('-created_at')[:10]
    
    context = {
        'total_users': total_users,
        'active_subscriptions': active_subscriptions,
        'monthly_revenue': monthly_revenue,
        'churn_rate': churn_rate,
        'recent_subscriptions': recent_subscriptions,
    }
    return render(request, 'admin_dashboard.html', context)


urlpatterns = [
    # Django Admin 
    path('admin/', admin.site.urls),

    # Admin Dashboard (new)
    path('admin-dashboard/', admin_dashboard, name='admin-dashboard'),
    
    # Home redirect
    #path('', lambda request: redirect('pricing'), name='home'),
    
    # API endpoints
    path('api/accounts/', include('accounts.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/webhooks/', include('webhooks.urls')),
    path('api/articles/', include('articles.urls')),

    # Swagger documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Web views
    path('subscriptions/', include('subscriptions.urls')),

    # Templates
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('articles/', TemplateView.as_view(template_name='articles/article_list.html'), name='article_list'),
    path('articles/<slug:slug>/', TemplateView.as_view(template_name='articles/article_detail.html'), name='article_detail'),
    path('pricing/', TemplateView.as_view(template_name='pricing.html'), name='pricing'),
    path('dashboard/', TemplateView.as_view(template_name='account/dashboard.html'), name='dashboard'),
    path('subscription/', TemplateView.as_view(template_name='account/subscription.html'), name='subscription'),
    path('reading-list/', TemplateView.as_view(template_name='account/reading_list.html'), name='reading_list'),
    path('login/', TemplateView.as_view(template_name='registration/login.html'), name='login'),
    path('signup/', TemplateView.as_view(template_name='registration/signup.html'), name='signup'),
    path('search/', TemplateView.as_view(template_name='articles/search_results.html'), name='search'),
    path('transactions/', TemplateView.as_view(template_name='account/transactions.html'), name='transactions'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('contact/', TemplateView.as_view(template_name='contact.html'), name='contact'),
    path('privacy/', TemplateView.as_view(template_name='privacy.html'), name='privacy'),
    path('terms/', TemplateView.as_view(template_name='terms.html'), name='terms'),
]