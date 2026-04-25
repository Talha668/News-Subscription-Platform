import requests
from celery import shared_task
from .models import Article, Category
from django.utils import timezone
from django.conf import settings







def fetch_news_from_api(category="general"):
    """Fetch news from the api"""
    url = f"https://newsapi.org/v2/top-headlines"

    params = {
        "country": "us",
        "category": category,
        "apiKey": settings.NEWS_API_KEY,
        "pagesize": 100,
    }
    response = requests.get(url, params=params)
    # Print statements to Debug the API Key
    print(f"API Status Code:", response.status_code)
    if response.status_code != 200:
        print(f"⚠ API Error: {response.status_code} - {response.text}")
        return []

    return response.json().get("articles", [])


@shared_task
def fetch_and_store_news():
    """Celery task to fetch news periodically"""
    for category in ["general", "technology", "business", "science"]:
        articles = fetch_news_from_api(category)
        for item in articles:
            Article.objects.update_or_create(
                external_id=item.get("url"),
                defaults={
                    "title": item.get("title"),
                    "summary": item.get("description"),
                    "content": item.get("content"),
                    "featured_image": item.get("urlToImage"),
                    "cource_name": item.get("source", {}).get("name"),
                    "source_url": item.get("url"),
                    "published_at": item.get("publishedAt") or timezone.now(),
                }
            )