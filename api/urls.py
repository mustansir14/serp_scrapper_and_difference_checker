from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()
router.register(r"queries", views.QueryViewSet, basename="query")
router.register(r"scrapes", views.ScrapeViewSet, basename="scrape")
router.register(r"results", views.ResultsViewSet, basename="result")

urlpatterns = [
    path("", include(router.urls)),
    path("results/difference", views.get_results_with_difference),
    path("results/difference/text/<int:id>", views.get_difference_text),
    path("results/difference/as_array/<int:id>", views.get_difference_text_as_arrays),
    path("results/difference/urls", views.get_difference_urls),
]
