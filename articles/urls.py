from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArticleViewSet, CategoryViewSet, TagViewSet
from . import views







router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='article')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')


urlpatterns = [
    path('', include(router.urls)),

    # Custom endpoint
    path('popular/', views.popular_articles, name='popular-articles'),
    path('api/categories/', views.category_list, name='category-list'),
]