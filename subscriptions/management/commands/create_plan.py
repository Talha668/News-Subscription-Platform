# subscriptions/management/commands/create_plans.py
from django.core.management.base import BaseCommand
from subscriptions.models import Plan
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class Command(BaseCommand):
    help = 'Create subscription plans'
    
    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Basic',
                'description': 'Perfect for individuals and small projects',
                'interval': 'month',
                'price': 9.99,
                'features': ['5 Projects', '10GB Storage', 'Basic Support'],
                'stripe_price_id': 'price_basic_monthly'
            },
            {
                'name': 'Pro',
                'description': 'Ideal for growing businesses',
                'interval': 'month',
                'price': 29.99,
                'features': ['Unlimited Projects', '100GB Storage', 'Priority Support', 'API Access'],
                'stripe_price_id': 'price_pro_monthly'
            },
            {
                'name': 'Enterprise',
                'description': 'For large organizations',
                'interval': 'month',
                'price': 99.99,
                'features': ['Unlimited Projects', '1TB Storage', '24/7 Support', 'API Access', 'Custom Features'],
                'stripe_price_id': 'price_enterprise_monthly'
            }
        ]
        
        for plan_data in plans:
            plan, created = Plan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created plan: {plan.name}'))
            else:
                self.stdout.write(f'Plan already exists: {plan.name}')