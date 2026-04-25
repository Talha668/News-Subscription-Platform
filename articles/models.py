from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse







User = settings.AUTH_USER_MODEL 



class Author(models.Model):
    """Author profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile')
    bio = models.TextField(blank=True, help_text='Short biography for author')
    avatar = models.URLField(blank=True, help_text="URL to author's pofile picture")
    website = models.URLField(blank=True)
    twitter_handle = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.email
    
    @property
    def name(self):
        return self.user.get_full_name() or self.user.email


class Category(models.Model):
    """Article categories for organizations"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    featured_image = models.URLField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name 


class Tag(models.Model):
    """Tag for categories"""
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Article(models.Model):
    """Main article content model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('scheduled', 'Scheduled'),
        ('archived', 'Archived'),
    ]

    TIER_CHOICES = [
        ('free', 'Free - Everyone can read'),
        ('premium', 'Premium - Premium and Pro subscribers'),
        ('pro', 'Pro - Pro subscribers only'),
    ]

    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=200, unique=True, help_text="URL-friendly version of the title")
    excerpt = models.TextField(max_length=300, help_text="Short summary shown in listings")
    body = models.TextField(help_text="Main article content - supportsHTML/Markdown")   # Rich text content
    featured_image = models.URLField(blank=True, help_text="Main image for the article")
    ready_to_publish = models.BooleanField(default=False, help_text="Mark as ready for auto-publishing")

    # Relations
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='articles')
    categories = models.ManyToManyField(Category, related_name='articles')
    tags = models.ManyToManyField(Tag, related_name='articles', blank=True)

    # Acess control - uses your existing plan.tier system
    required_tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='free')
    
    # News API fields
    source_name = models.CharField(max_length=500, blank=True)      # e.g., "Routers"
    source_url = models.URLField( max_length=2000, blank=True)
    external_id = models.CharField(max_length=500, blank=True, db_index=True)

    # Publishing    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, help_text="When to auto-pulish")

    # Analytics
    view_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    read_time_minutes = models.IntegerField(default=5, help_text="Estimated reading time")

    # Seo
    meta_title = models.CharField(max_length=150, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)

    # timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # For premium paywall
    # requires_premium = models.BooleanField(default=False)
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['slug', 'status']),
            models.Index(fields=['required_tier', 'published_at']),
            models.Index(fields=['published_at', 'status']),
        ]

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_premium(self):
        return self.required_tier in ['premium', 'pro']

    def get_absolute_url(self):
        return reverse('article-detail', kwargs={'slug': self.slug})
           

class UserArticleAccess(models.Model):
    """Track free article views from user"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class UserReadingList(models.Model):
    """Save articles for later reading"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_list')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='saved_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'article']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.email} saved {self.article.title}"


class ArticleView(models.Model):
    """Track article views for analytics and free tier limiting"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='article_views')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='views')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'viewed_at']),
            models.Index(fields=['article', 'viewed_at']),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else f"Anonymous {self.ip_address}"
        return f"{user_str} viewed {self.article.title}"


class ArticleBookmark(models.Model):
    """Differernt from reading list - this is for permanent bookmarks"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='bookmarked_by')
    note = models.TextField(blank=True, help_text="Personal note about this article")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'article']

    def __str__(self):
        return f"{self.user.email} bookmarked {self.article.title}"    