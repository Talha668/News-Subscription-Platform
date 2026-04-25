from django.core.management.base import BaseCommand
from articles.tasks import fetch_all_news_sources






class Command(BaseCommand):
    help = "Fetch news from all sources (API + RSS)"

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting comprehensive news fetch......")
        result = fetch_all_news_sources()
        self.stdout.write(self.style.SUCCESS(f"✅ Completed! Created {result} new articles"))