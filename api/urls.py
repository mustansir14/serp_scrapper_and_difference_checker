from django.urls import include, path
from api import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'queries', views.QueryViewSet, basename='query')
router.register(r'scrapes', views.ScrapeViewSet, basename='scrape')
router.register(r'results', views.ResultsViewSet, basename='result')

urlpatterns = [
    path('', include(router.urls)),
]
