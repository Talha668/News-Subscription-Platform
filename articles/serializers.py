from rest_framework import serializers
from .models import Article, Category, Tag, Author, UserReadingList, ArticleBookmark






class CategorySerializers(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'featured_image']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class AuthorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Author
        fields = ['id', 'name', 'bio', 'avatar', 'website', 'twitter_handle']


class ArticleListSerializer(serializers.ModelSerializer):
    """Light weight serializer for article listing"""
    category_names = serializers.StringRelatedField(source='categories', many=True, read_only=True)
    author_name = serializers.CharField(source='author.name', read_only=True)

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'excerpt', 'featured_image', 'published_at',
            'required_tier', 'read_time_minutes', 'view_count', 'author_name',
            'category_names'
        ]


class ArticleDetailSerializer(serializers.ModelSerializer):
    """Full serializer for article detail view"""
    categories = CategorySerializers(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author = AuthorSerializer(read_only=True)
    is_saved = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'excerpt', 'body', 'featured_image',
            'author', 'categories', 'tags', 'required_tier', 'published_at',
            'view_count', 'read_time_minutes', 'meta_title', 'meta_description',
            'is_saved', 'is_bookmarked', 'created_at', 'updated_at'
        ]

    def get_is_saved(self, obj):
        user = self.context.get('request').user
        if user and user.is_authenticated:
            return UserReadingList.objects.filter(user=user, article=obj).exists()
        return False

    def get_is_bookmarked(self, obj):
        user = self.context.get('request').user
        if user and user.is_authenticated:
            return ArticleBookmark.objects.filter(user=user, article=obj).exists() 
        return False


class ReadingListSerializer(serializers.ModelSerializer):
    article = ArticleListSerializer(read_only=True)

    class Meta:
        model = UserReadingList
        fields = ['id', 'article', 'added_at']


class BookmarkSerializer(serializers.ModelSerializer):
    article = ArticleListSerializer(read_only=True)

    class Meta:
        model = ArticleBookmark
        fields = ['id', 'article', 'note', 'created_at']