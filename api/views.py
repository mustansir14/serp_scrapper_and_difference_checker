from rest_framework.viewsets import ModelViewSet
from rest_framework import mixins, viewsets
from api.serializers import QuerySerializer, ScrapeSerializer, ResultSerializer
from api.models import Query, Scrape, Status, Result
from api.scraper import Scraper
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import status
import difflib

# Create your views here.


class QueryViewSet(ModelViewSet):

    serializer_class = QuerySerializer
    queryset = Query.objects.all()

    def perform_create(self, serializer: QuerySerializer) -> None:
        query = serializer.save()

        scrape = Scrape(query=query, status=Status.PENDING)
        scrape.save()

        scraper = Scraper(scrape)
        scraper.start_async()


query_id = openapi.Parameter('query_id', openapi.IN_QUERY,
                             description="The query for which scrapes are to be returned",
                             type=openapi.TYPE_INTEGER,
                             required=True)


@method_decorator(name='list', decorator=swagger_auto_schema(
    manual_parameters=[query_id]
))
class ScrapeViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):

    serializer_class = ScrapeSerializer

    def perform_create(self, serializer: ScrapeSerializer) -> None:
        scrape = serializer.save()

        scraper = Scraper(scrape)
        scraper.start_async()

    def get_queryset(self):
        query = self.request.query_params.get('query_id')
        if query is not None:
            queryset = Scrape.objects.filter(query__id=query)
        else:
            raise ValidationError({"message": "Missing query_id parameter"})
        return queryset


scrape_id = openapi.Parameter('scrape_id', openapi.IN_QUERY,
                              description="The scrape for which results are to be returned",
                              type=openapi.TYPE_INTEGER,
                              required=True)


@method_decorator(name='list', decorator=swagger_auto_schema(
    manual_parameters=[scrape_id]
))
class ResultsViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ResultSerializer

    def get_queryset(self):
        scrape = self.request.query_params.get('scrape_id')
        if scrape is not None:
            queryset = Result.objects.filter(scrape__id=scrape)
        else:
            raise ValidationError({"message": "Missing scrape_id parameter"})
        return queryset


@api_view(('GET', ))
@renderer_classes((JSONRenderer, ))
def get_difference_html(scrape1_id: int, scrape2_id: int, page_link: str) -> Response:

    try:
        scrape1 = Scrape.objects.get(id=scrape1_id)
    except Scrape.DoesNotExist:
        return Response({"status": "error", "message": "Invalid scrape1_id"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        scrape2 = Scrape.objects.get(id=scrape2_id)
    except Scrape.DoesNotExist:
        return Response({"status": "error", "message": "Invalid scrape2_id"}, status=status.HTTP_400_BAD_REQUEST)

    if scrape1.query != scrape2.query:
        return Response({"status": "error", "message": "Both scrapes belong to different queries"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result1 = Result.objects.get(scrape=scrape1, page_link=page_link)
    except Result.DoesNotExist:
        return Response({"status": "error", "message": "Result with given page_link does not exist for Scrape 1"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result2 = Result.objects.get(scrape=scrape2, page_link=page_link)
    except Result.DoesNotExist:
        return Response({"status": "error", "message": "Result with given page_link does not exist for Scrape 2"}, status=status.HTTP_400_BAD_REQUEST)

    # data = {"scrape1": ScrapeSerializer(
    #     scrape1).data, "scrape2": ScrapeSerializer(scrape2).data, "url"}
