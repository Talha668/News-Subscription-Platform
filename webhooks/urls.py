from django.urls import path
from . import views 




urlpatterns = [
    path('lemon-squeezy/', views.lemon_squeezy_webhook, name='lemon-squeezy-webhook'),
]