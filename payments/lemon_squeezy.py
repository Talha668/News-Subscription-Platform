import requests
from django.conf import settings

class LemonSqueezyAPI:
    BASE_URL = "https://api.lemonsqueezy.com/v1"
    
    def __init__(self):
        self.api_key = settings.LEMON_SQUEEZY_API_KEY
        self.store_id = settings.LEMON_SQUEEZY_STORE_ID
        self.headers = {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def _request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_products(self):
        """Get all products from your store"""
        return self._request("GET", "products")
    
    def get_variants(self, product_id=None):
        """Get variants (pricing tiers) for a product"""
        if product_id:
            return self._request("GET", f"products/{product_id}/variants")
        return self._request("GET", "variants")
    
    def create_checkout(self, variant_id, customer_email, customer_name=None, custom_data=None):
        """Create a checkout URL for customer"""
        data = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "email": customer_email,
                        "name": customer_name,
                        "custom": custom_data or {}
                    }
                },
                "relationships": {
                    "store": {
                        "data": {
                            "type": "stores",
                            "id": str(self.store_id)
                        }
                    },
                    "variant": {
                        "data": {
                            "type": "variants",
                            "id": str(variant_id)
                        }
                    }
                }
            }
        }
        return self._request("POST", "checkouts", data)
    
    def get_subscription(self, subscription_id):
        """Get subscription details"""
        return self._request("GET", f"subscriptions/{subscription_id}")
    
    def cancel_subscription(self, subscription_id):
        """Cancel a subscription"""
        return self._request("DELETE", f"subscriptions/{subscription_id}")
    
    def update_subscription(self, subscription_id, variant_id):
        """Update subscription variant (upgrade/downgrade)"""
        data = {
            "data": {
                "type": "subscriptions",
                "id": str(subscription_id),
                "relationships": {
                    "variant": {
                        "data": {
                            "type": "variants",
                            "id": str(variant_id)
                        }
                    }
                }
            }
        }
        return self._request("PATCH", f"subscriptions/{subscription_id}", data)
    
    def get_customer_subscriptions(self, customer_email):
        """Get all subscriptions for a customer"""
        params = f"filter[customer_email]={customer_email}"
        return self._request("GET", f"subscriptions?{params}")
    
    def get_orders(self, customer_email=None):
        """Get orders, optionally filtered by customer"""
        endpoint = "orders"
        if customer_email:
            endpoint += f"?filter[customer_email]={customer_email}"
        return self._request("GET", endpoint)


# Create a single instance to be used throughout the app
lemon_api = LemonSqueezyAPI()