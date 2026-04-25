import requests
import feedparser
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.utils.text import slugify
from .models import Article, Category, Author
from django.contrib.auth import get_user_model








User = get_user_model()



# NewsAPI.org configuration
NEWS_API_KEY = getattr(settings, 'NEWS_API_KEY', '')
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"
NEWS_API_EVERYTHING_URL = "https://newsapi.org/v2/everything"

# TRUSTED SOURCES FOR AUTO-PUBLISHING
TRUSTED_SOURCES = {
    # Auto-publish from these sources
    "auto_publish": [
        "bbc", "reuters", "ap news", "associated press", "npr",
        "the guardian", "techcrunch", "wired", "ars technica",
        "microsoft", "apple", "google", "github", "cnn", "fox news",
        "nbc news", "abc news", "cbs news", "al jazeera",
    ],
    # Premium sources (auto-publish but mark as premium tier)
    "premium_auto_publish": [
        "bloomberg", "wall street journal", "wsj", "financial times", "ft.com",
        "the economist", "harvard", "mit", "stanford", "nature", "science",
    ],
    # Never auto-publish - always manual review
    "manual_review": [
        "the sun", "daily mail", "breitbart", "infowars",
    ],
    # Categories that auto-publish regardless of source
    "auto_publish_categories": ["technology", "science", "business"],
}

# RSS FEEDS - Comprehensive list
RSS_FEEDS = {
    # Major News Outlets
    "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "CNN Top Stories": "http://rss.cnn.com/rss/cnn_topstories.rss",
    "CNN World": "http://rss.cnn.com/rss/cnn_world.rss",
    "Reuters Top News": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
    "Reuters Technology": "https://www.reutersagency.com/feed/?taxonomy=technology&post_type=best",
    "AP News": "https://apnews.com/feed",
    "NPR News": "https://feeds.npr.org/1001/rss.xml",
    "The Guardian World": "https://www.theguardian.com/world/rss",
    "The Guardian US": "https://www.theguardian.com/us-news/rss",
    
    # Technology
    "TechCrunch": "https://techcrunch.com/feed/",
    "Wired": "https://www.wired.com/feed/rss",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "CNET": "https://www.cnet.com/rss/news/",
    "ZDNet": "https://www.zdnet.com/news/rss.xml",
    "VentureBeat": "https://venturebeat.com/feed/",
    "Mashable": "https://mashable.com/feeds/rss/all",
    
    # Business & Finance
    "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "Financial Times": "https://www.ft.com/?format=rss",
    "Wall Street Journal": "https://feeds.a.dj.com/rss/WSJcom.xml",
    "Business Insider": "https://www.businessinsider.com/rss",
    "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "MarketWatch": "http://feeds.marketwatch.com/marketwatch/topstories/",
    "Fortune": "https://fortune.com/feed/",
    
    # Science & Health
    "Scientific American": "https://rss.sciam.com/sciam/content",
    "Nature": "https://www.nature.com/nature.rss",
    "Science Daily": "https://www.sciencedaily.com/rss/all.xml",
    "New Scientist": "https://www.newscientist.com/feed/home",
    "Medical News Today": "https://www.medicalnewstoday.com/feed",
    "WebMD": "https://feeds.webmd.com/rss/rss.xml",
    
    # Entertainment & Culture
    "Variety": "https://variety.com/feed/",
    "Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
    "Rolling Stone": "https://www.rollingstone.com/feed/",
    "Pitchfork": "https://pitchfork.com/rss/news/",
    "Billboard": "https://www.billboard.com/feed/",
    
    # Sports
    "ESPN": "https://www.espn.com/espn/rss/news",
    "BBC Sport": "http://feeds.bbci.co.uk/sport/rss.xml",
    "Sky Sports": "https://www.skysports.com/rss/12040",
    
    # Independent & Niche
    "Hacker News": "https://news.ycombinator.com/rss",
    "Product Hunt": "https://www.producthunt.com/feed",
    "Smashing Magazine": "https://www.smashingmagazine.com/feed/",
    "DEV Community": "https://dev.to/feed",
    "FreeCodeCamp": "https://www.freecodecamp.org/news/rss/",
}


def create_unique_slug(title):
    """Create a unique slug from a title"""
    base_slug = slugify(title)
    # Limit to leave room for counter 
    base_slug = base_slug[:190]
    slug = base_slug
    counter = 1
    
    while Article.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"[:198]      # total length under 200
        counter += 1
    
    return slug


def detect_category_from_source(source_name):
    """Helper to determine category based on source name"""
    source_lower = source_name.lower()
    
    if any(w in source_lower for w in ['tech', 'wired', 'verge', 'cnet', 'zdnet', 'ars', 'venturebeat', 'mashable', 'hacker', 'product hunt']):
        return "Technology"
    elif any(w in source_lower for w in ['business', 'bloomberg', 'ft.com', 'wsj', 'marketwatch', 'fortune', 'finance']):
        return "Business"
    elif any(w in source_lower for w in ['science', 'nature', 'scientific', 'medical', 'health', 'webmd']):
        return "Science & Health"
    elif any(w in source_lower for w in ['sport', 'espn', 'bbc sport', 'sky sports']):
        return "Sports"
    elif any(w in source_lower for w in ['variety', 'hollywood', 'rolling stone', 'pitchfork', 'billboard', 'entertainment']):
        return "Entertainment"
    elif any(w in source_lower for w in ['bbc', 'cnn', 'reuters', 'ap news', 'npr', 'guardian']):
        return "World News"
    else:
        return "General"


def should_auto_publish(source_name, category_name, article_title):
    """
    Determine if an article should be auto-published or saved as draft
    
    Returns:
        (should_publish, required_tier, reason)
    """
    source_lower = source_name.lower()
    category_lower = category_name.lower()
    title_lower = article_title.lower()
    
    # 1. Check for manual review sources (never auto-publish)
    for blocked in TRUSTED_SOURCES["manual_review"]:
        if blocked in source_lower:
            return False, "free", f"Source {source_name} requires manual review"
    
    # 2. Check for premium auto-publish sources
    for premium in TRUSTED_SOURCES["premium_auto_publish"]:
        if premium in source_lower:
            return True, "premium", f"Premium source {source_name} auto-published"
    
    # 3. Check for regular auto-publish sources
    for trusted in TRUSTED_SOURCES["auto_publish"]:
        if trusted in source_lower:
            return True, "free", f"Trusted source {source_name} auto-published"
    
    # 4. Auto-publish based on category
    if category_lower in TRUSTED_SOURCES["auto_publish_categories"]:
        return True, "free", f"Category {category_name} auto-published"
    
    # 5. Check for high-value keywords in title
    high_value_keywords = ["exclusive", "breaking", "urgent", "important", "analysis"]
    for keyword in high_value_keywords:
        if keyword in title_lower:
            return True, "premium", f"High-value keyword '{keyword}' found"
    
    # Default: save as draft for manual review
    return False, "free", "Default - needs manual review"


@shared_task
def fetch_news_from_newsapi_with_filter(category="general", country="us", max_articles=50):
    """Fetch news from NewsAPI.org with auto-publish filtering"""
    if not NEWS_API_KEY:
        print("⚠️ NEWS_API_KEY not configured. Skipping NewsAPI fetch.")
        return 0
    
    params = {
        "country": country,
        "category": category,
        "apiKey": NEWS_API_KEY,
        "pageSize": max_articles,
    }
    
    try:
        response = requests.get(NEWS_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Print rate limit info
        remaining = response.headers.get('x-ratelimit-remaining', 'Unknown')
        print(f"NewsAPI rate limit remaining: {remaining}")
        
        if data.get("status") != "ok":
            print(f"NewsAPI error: {data.get('message')}")
            return 0
        
        articles_created = 0
        auto_published = 0
        saved_as_draft = 0
        
        system_user, _ = User.objects.get_or_create(
            username="news_bot",
            defaults={"email": "news@platform.com"}
        )
        author, _ = Author.objects.get_or_create(
            user=system_user,
            defaults={"bio": "Automated news feed"}
        )
        
        category_obj, _ = Category.objects.get_or_create(
            name=category.capitalize(),
            slug=category.lower()
        )
        
        for item in data.get("articles", []):
            if not item.get("title") or not item.get("url"):
                continue
            
            if Article.objects.filter(external_id=item.get("url")).exists():
                continue
            
            source_name = item.get("source", {}).get("name", "Unknown")
            
            # Determine if this article should auto-publish
            should_publish, required_tier, reason = should_auto_publish(
                source_name, category, item.get("title", "")
            )
            
            status = "published" if should_publish else "draft"
            
            article = Article.objects.create(
                title=item.get("title")[:500],
                slug=create_unique_slug(item.get("title")),
                excerpt=item.get("description", "")[:300] or "Read this article for the full story.",
                body=item.get("content") or item.get("description") or f"Full content not available. Read the original at {item.get('url')}",
                featured_image=item.get("urlToImage", ""),
                author=author,
                status=status,
                published_at=timezone.now() if should_publish else None,
                external_id=item.get("url"),
                source_name=source_name,
                source_url=item.get("url"),
                required_tier=required_tier,
            )
            article.categories.add(category_obj)
            articles_created += 1
            
            if should_publish:
                auto_published += 1
                print(f"  📰 AUTO-PUBLISHED: {article.title[:50]}... (Tier: {required_tier}) - {reason}")
            else:
                saved_as_draft += 1
        
        print(f"✅ {category}: {articles_created} total | {auto_published} auto-published | {saved_as_draft} drafts")
        return articles_created
        
    except Exception as e:
        print(f"❌ NewsAPI error ({category}): {str(e)}")
        return 0


@shared_task
def fetch_rss_feeds_with_filter(limit_per_feed=15):
    """Fetch news from RSS feeds with auto-publish filtering"""
    total_articles = 0
    auto_published = 0
    
    system_user, _ = User.objects.get_or_create(
        username="rss_bot",
        defaults={"email": "rss@platform.com"}
    )
    author, _ = Author.objects.get_or_create(
        user=system_user,
        defaults={"bio": "RSS feed aggregator"}
    )
    
    for source_name, feed_url in RSS_FEEDS.items():
        try:
            print(f"Fetching RSS: {source_name}...")
            feed = feedparser.parse(feed_url)
            
            category_name = detect_category_from_source(source_name)
            category_obj, _ = Category.objects.get_or_create(
                name=category_name,
                slug=category_name.lower()
            )
            
            articles_in_feed = 0
            for entry in feed.entries[:limit_per_feed]:
                if not entry.get('title') or not entry.get('link'):
                    continue
                
                if Article.objects.filter(external_id=entry.link).exists():
                    continue
                
                # Determine if this RSS source should auto-publish
                should_publish, required_tier, reason = should_auto_publish(
                    source_name, category_name, entry.get('title', '')
                )
                
                content = entry.get('content', [{}])[0].get('value', '')
                if not content:
                    content = entry.get('summary', entry.get('description', ''))
                if not content:
                    content = f"Read the full article at the source: {entry.link}"
                
                status = "published" if should_publish else "draft"
                
                article = Article.objects.create(
                    title=entry.title[:500],
                    slug=create_unique_slug(entry.title),
                    excerpt=entry.get('summary', entry.title)[:300],
                    body=content[:10000],
                    featured_image="",
                    author=author,
                    status=status,
                    published_at=timezone.now() if should_publish else None,
                    external_id=entry.link,
                    source_name=source_name,
                    source_url=entry.link,
                    required_tier=required_tier,
                )
                article.categories.add(category_obj)
                total_articles += 1
                articles_in_feed += 1
                
                if should_publish:
                    auto_published += 1
            
            print(f"  ✅ {source_name}: {articles_in_feed} articles")
            
        except Exception as e:
            print(f"  ❌ Error fetching {source_name}: {str(e)}")
    
    print(f"✅ RSS Complete: {total_articles} total | {auto_published} auto-published")
    return total_articles


@shared_task
def fetch_all_news_sources_filtered():
    """
    Master task that fetches from ALL sources with auto-publish filtering
    This should be run by Celery beat every 2 hours
    """
    print("🚀 Starting comprehensive filtered news fetch...")
    start_time = timezone.now()
    
    total_api_articles = 0
    total_rss_articles = 0
    
    # 1. Fetch from NewsAPI across categories
    categories = ["general", "technology", "business", "science", "health", "entertainment"]
    
    for category in categories:
        count = fetch_news_from_newsapi_with_filter(category=category, max_articles=50)
        total_api_articles += count
        # Small delay to avoid hitting rate limits
        import time
        time.sleep(1)
    
    # 2. Fetch from all RSS feeds
    total_rss_articles = fetch_rss_feeds_with_filter()
    
    duration = (timezone.now() - start_time).total_seconds()
    
    print("=" * 50)
    print("📊 FETCH SUMMARY")
    print("=" * 50)
    print(f"NewsAPI articles created: {total_api_articles}")
    print(f"RSS articles created: {total_rss_articles}")
    print(f"Total new articles: {total_api_articles + total_rss_articles}")
    print(f"Duration: {duration:.2f} seconds")
    print("=" * 50)
    
    # Store summary in cache for admin dashboard
    cache.set('last_news_fetch_summary', {
        'api_articles': total_api_articles,
        'rss_articles': total_rss_articles,
        'total': total_api_articles + total_rss_articles,
        'timestamp': timezone.now().isoformat(),
        'duration': duration
    }, timeout=86400)
    
    return total_api_articles + total_rss_articles


@shared_task
def cleanup_old_draft_articles(days=30):
    """Clean up old un-reviewed drafts"""
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    old_drafts = Article.objects.filter(
        status='draft',
        created_at__lt=cutoff_date
    )
    count = old_drafts.count()
    old_drafts.delete()
    print(f"✅ Deleted {count} old draft articles (older than {days} days)")
    return count


@shared_task
def fetch_all_news_sources():
    """
    Wrapper function for backward compatibility
    Calls the filtered version
    """
    return fetch_all_news_sources_filtered()