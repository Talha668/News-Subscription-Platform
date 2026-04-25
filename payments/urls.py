from django.urls import path
from .views import (
    AvailablePlansView,
    CreateCheckoutView,
    CurrentSubscriptionView,
    CancelSubscriptionView,
    UpdateSubscriptionView,
    UserTransactionsView,
    SubscriptionWebhookView,
    lemon_squeezy_webhook
)






urlpatterns = [
    # Frontend API endpoints
    path('plans/', AvailablePlansView.as_view(), name='available-plans'),
    path('create-checkout/', CreateCheckoutView.as_view(), name='create-checkout'),
    path('current-subscription/', CurrentSubscriptionView.as_view(), name='current-subscription'),
    path('cancel-subscription/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
    path('update-subscription/', UpdateSubscriptionView.as_view(), name='update-subscription'),
    path('transactions/', UserTransactionsView.as_view(), name='user-transactions'),

    # Webhook endpoints (for lemon squeezy)
    path('webhook/', SubscriptionWebhookView.as_view(), name='subscription-webhook'),
    path('webhook-legacy/', lemon_squeezy_webhook, name='lemon-squeezy-webhook')
]