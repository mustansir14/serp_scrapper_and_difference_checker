from django.urls import include, path
from api import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'queries', views.QueryViewSet, basename='query')
router.register(r'scrapes', views.ScrapeViewSet, basename='scrape')
router.register(r'results', views.ResultsViewSet, basename='result')

urlpatterns = [
    path('', include(router.urls)),
    path('get_difference_html', views.get_difference_html),
    path('get_difference_text', views.get_difference_text),
    path('get_difference_html_as_array', views.get_difference_html_as_arrays),
    path('get_difference_text_as_array', views.get_difference_text_as_arrays),
    path('get_difference_urls', views.get_difference_urls),
]
