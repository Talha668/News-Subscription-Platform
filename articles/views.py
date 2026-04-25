from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count
from django.utils import timezone
from .models import Article, Category, Tag, UserReadingList, ArticleBookmark
from .serializers import (
    ArticleDetailSerializer, ArticleListSerializer, CategorySerializers, 
    TagSerializer, ReadingListSerializer, BookmarkSerializer
)
from .utils import can_access_article, track_article_view, get_user_tier









class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset for articles - handles listing, detail, search and filtering
    """
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'excerpt', 'body', 'author__user__email']
    ordering_fields = ['published_at', 'views_count', 'created_at', 'read_time_minutes']
    ordering = ['-published_at']

    def get_queryset(self):
        """filter articels based on user's subscription tier"""
        queryset = Article.objects.filter(status='published')

        # Anonymous users only free articles
        if not self.request.user.is_authenticated:
            return queryset.filter(required_tier='free')
        
        user_tier = get_user_tier(self.request.user)

        # Show appropriate articles based on user's tier
        if user_tier == 'free':
            # Free users see all articles but premium one will be locked in the detailview
            return queryset
        elif user_tier == 'premium':
            # Premium users see free and premium articles but not pro
            return queryset.filter(~Q(required_tier='pro'))
        else:    # Pro users see everything
            return queryset

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'popular' or self.action == 'bt_category':
            return ArticleListSerializer
        return ArticleDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        """Handle article detail with access control"""
        article = self.get_object()

        # check if user can access this article
        can_access, requires_upgrade, upgrade_info = can_access_article(request.user, article)

        # Track the view for analytics
        track_article_view(request.user, article, request)

        if not can_access:
            return Response({
                'error': 'This content requires an upgrade',
                'requires_upgrade': True,
                'required_tier': article.required_tier,
                'current_user_tier': get_user_tier(request.user),
                'upgrade_to':article.required_tier,
                'excerpt': article.excerpt,
                'title': article.title,
                'featured_image': article.featured_image,
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Include remaining free articles in reponse for free tier users
        serializer = self.serializer_class(article, context={'request': request})
        response_data = serializer.data

        if requires_upgrade and isinstance(upgrade_info, int):
            response_data['remaining free articles this month'] = upgrade_info

        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get more viewed articles"""
        limit = request.query_params.get('limit', 10)
        articles = Article.objects.filter(
            status='published',
            published_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).order_by('-view_count')[:int(limit)]
        serializer = ArticleListSerializer(articles, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Filter articles by category slug"""
        category_slug = request.query_params.get('slug')
        if not category_slug:
            return Response({'error': 'Category slug required'}, status=400)
        
        articles = Article.objects.filter(
            status='published',
            categories__slug=category_slug
        )
        serializer = ArticleListSerializer(articles, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_tag(self, request):
        """filter articles by tag skug"""
        tag_slug = request.query_params.get('slug')
        if not tag_slug:
            return Response({'error': 'Tag slug requried'}, status=400)
        
        articles = Article.objects.filter(
            status='published',
            tags__slug=tag_slug
        )
        serializer = ArticleListSerializer(articles, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def save(self, request, pk=None):
        """Save articles to reading list"""
        article = self.get_object()
        reading_list_item, created = UserReadingList.objects.get_or_create(
            user=request.user,
            article=article
        )
        serializer = ReadingListSerializer(reading_list_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def unsave(self, request, pk=None):
        """Remove article from reading list"""
        article = self.get_object()
        deleted, _ = UserReadingList.objects.filter(
            user=request.user,
            article=article
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Article is not in reading list'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def bookmark(self, request, pk=None):
        """Bookmark articles with optional note"""
        article = self.get_object()
        note = request.data.get('none', '')
        bookmark, created = ArticleBookmark.objects.get_or_create(
            user=request.user,
            article=article,
            defaults={'note': note}
        )
        if not created:
            bookmark.note = note
            bookmark.save()
        serializer = BookmarkSerializer(bookmark)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def reading_list(self, request):
        """Get user's reading list"""
        reading_list = UserReadingList.objects.filter(user=request.user).select_related('article')
        serializer = ReadingListSerializer(reading_list, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def bookmarks(self, request):
        """Get user's bookmark"""
        bookmarks = ArticleBookmark.objects.filter(user=request.user).select_related('article')
        serializer = BookmarkSerializer(bookmarks, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for categories"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializers
    lookup_field = 'slug'


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """viewSet for tags"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = 'slug'


@api_view(['GET'])
@permission_classes([AllowAny])
def popular_articles(request):
    """Get popular/featured articles for homepage"""
    limit = int(request.GET.get('limit', 6))

    articles = Article.objects.filter(
        status='published',
        published_at__isnull=False
    ).select_related('author', 'author__user').order_by('-published_at')[:limit]

    data = []
    for article in articles:
        data.append({
            'id': article.id,
            'title': article.title,
            'slug': article.slug,
            'excerpt': article.excerpt,
            'featured_image': article.featured_image,
            'view_count': article.view_count,
            'required_tier': article.required_tier,
            'published_at': article.published_at,
            'author_name': article.author.user.email,
            'category_name': article.categories.first().name if article.categories.exists() else 'Uncategorized',
            'category_slug': article.categories.first().slug if article.categories.exists() else 'Uncategorized',
        })

        return Response(data)
    

@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    """Get all categories with article count"""
    categories = Category.objects.annotate(
        article_count=Count('articles', filter=Q(articles__status='published'))
    ).filter(article_count__gte=0).order_by('-article_count')

    data = []
    for cat in categories:
        data.append({
            'id': cat.id,
            'name': cat.name,
            'slug': cat.slug,
            'description': cat.description,
            'featured_image': cat.featured_image,
            'article_count': cat.article_count,
        })

        return Response(data)