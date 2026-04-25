from django.contrib import admin
from .models import Article, Category, Tag, Author, UserReadingList, ArticleBookmark, ArticleView







@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'required_tier', 'status', 'published_at', 'view_count']
    list_filter = ['status', 'required_tier', 'categories', 'tags', 'published_at']
    search_fields = ['title', 'excerpt', 'body']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'body', 'featured_image', 'author')
        }),
        ('Organization', {
            'fields': ('categories', 'tags', 'required_tier')
        }),
        ('Publishing', {
            'fields': ('status', 'scheduled_for', 'published_at')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description')
        }),
        ('Analytics', {
            'fields': ('view_count', 'share_count', 'read_time_minutes'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['user', 'website', 'twitter_handle']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']


@admin.register(UserReadingList)
class UserReadingListAdmin(admin.ModelAdmin):
    list_display = ['user', 'article', 'added_at']


@admin.register(ArticleBookmark)
class ArticleBoolmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'article', 'created_at']


@admin.register(ArticleView)
class ArticleViewAmin(admin.ModelAdmin):
    list_display = ['article', 'user', 'ip_address', 'viewed_at']
    list_filter = ['viewed_at']