from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter





router = DefaultRouter()   
router.register(r'plans', views.PlanViewSet, basename='plan')
router.register(r'subscriptions', views.SubscriptionViewSet, basename='subscription')


urlpatterns = [
    path('pricing/', views.pricing, name='pricing'),
    path('checkout/<int:plan_id>/', views.create_checkout, name='create_checkout'),
    path('my-subscription/', views.subscription_detail, name='subscription_detail'),
    path('cancel/<int:subscription_id>/', views.cancel_subscription, name='cancel_subscription'),
    path('resume/<int:subscription_id>/', views.resume_subscription, name='resume-subscription'),
    path('history/', views.subscription_history, name='subscription_history'),

    # API endpoints
    path('api/', include(router.urls)),
    path('api/plans/', views.plans_api, name='plans_api'),
    path('api/my-subscription/', views.user_subscription_api, name='user_subscription_api'),
]