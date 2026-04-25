from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArticleViewSet, CategoryViewSet, TagViewSet








router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='article')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')


urlpatterns = [
    path('api/', include(router.urls)),
]