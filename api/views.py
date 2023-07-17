from typing import Tuple

from rest_framework.viewsets import ModelViewSet
from rest_framework import mixins, viewsets
from api.serializers import QuerySerializer, ScrapeSerializer, ResultListSerializer, ResultDetailSerializer, DifferenceSerializer, DifferenceSerializerArray
from api.models import Query, Scrape, Status, Result, Difference
from api.scraper import Scraper
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.exceptions import ValidationError
from rest_framework import status
import json

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
class ScrapeViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet, mixins.DestroyModelMixin):

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
            queryset = Scrape.objects.all()
        return queryset


scrape_id = openapi.Parameter('scrape_id', openapi.IN_QUERY,
                              description="The scrape for which results are to be returned",
                              type=openapi.TYPE_INTEGER,
                              required=True)


@method_decorator(name='list', decorator=swagger_auto_schema(
    manual_parameters=[scrape_id]
))
class ResultsViewSet(viewsets.ReadOnlyModelViewSet):

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ResultDetailSerializer
        return ResultListSerializer

    def get_queryset(self):
        scrape = self.request.query_params.get('scrape_id')
        if scrape is not None:
            queryset = Result.objects.filter(scrape__id=scrape)
        else:
            queryset = Result.objects.all()
        return queryset


def get_scrapes_from_params(request: Request) -> Tuple[Scrape, Scrape]:

    scrape1_id = request.query_params.get("scrape1_id")
    scrape2_id = request.query_params.get("scrape2_id")

    try:
        scrape1 = Scrape.objects.get(id=scrape1_id)
    except Scrape.DoesNotExist:
        raise ValidationError(
            {"status": "error", "message": "Invalid scrape1_id"}, status.HTTP_400_BAD_REQUEST)
    try:
        scrape2 = Scrape.objects.get(id=scrape2_id)
    except Scrape.DoesNotExist:
        raise ValidationError(
            {"status": "error", "message": "Invalid scrape2_id"}, status.HTTP_400_BAD_REQUEST)

    if scrape1.query != scrape2.query:
        raise ValidationError(
            {"status": "error", "message": "Both scrapes belong to different queries"}, status.HTTP_400_BAD_REQUEST)

    return scrape1, scrape2


def get_difference(id: int, as_arrays: bool = False) -> Response:

    try:
        difference = Difference.objects.get(id=id)
    except Difference.DoesNotExist:
        return Response({"status": "error", "message": "Difference with given id does not exist."}, status=status.HTTP_400_BAD_REQUEST)

    difference.content_difference = json.loads(difference.content_difference)
    difference.title_difference = json.loads(difference.title_difference)
    if not as_arrays:
        difference.content_difference = "\n".join(
            difference.content_difference)
        difference.title_difference = "\n".join(difference.title_difference)
        data = DifferenceSerializer(difference).data
    else:
        data = DifferenceSerializerArray(difference).data
    return Response(data, status=status.HTTP_200_OK)


difference_views_parameters = [
    openapi.Parameter('scrape1_id', openapi.IN_QUERY,
                      description="ID of scrape 1 to get difference",
                      type=openapi.TYPE_INTEGER,
                      required=True),
    openapi.Parameter('scrape2_id', openapi.IN_QUERY,
                      description="ID of scrape 2 to get difference",
                      type=openapi.TYPE_INTEGER,
                      required=True)
]


@swagger_auto_schema(
    method='get',
    manual_parameters=difference_views_parameters,
)
@api_view(('GET', ))
@renderer_classes((JSONRenderer, ))
def get_difference_urls(request: Request) -> Response:
    """
    Returns list of urls that are added/removed between two given scrapes
    """

    scrape1, scrape2 = get_scrapes_from_params(request)

    urls1 = set(
        [result.page_link for result in Result.objects.filter(scrape=scrape1)])
    urls2 = set(
        [result.page_link for result in Result.objects.filter(scrape=scrape2)])
    all_urls = set([result.page_link for result in Result.objects.filter(
        scrape__query=scrape1.query).exclude(scrape=scrape2)])

    unique_urls_added = urls2 - all_urls
    urls_added = urls2 - urls1 - unique_urls_added
    data = {"scrape1": ScrapeSerializer(
        scrape1).data, "scrape2": ScrapeSerializer(scrape2).data, "urls_added": list(urls_added), "urls_removed": list(urls1 - urls2), "unique_urls_added": [list(unique_urls_added)]}
    return Response(data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    manual_parameters=difference_views_parameters
)
@api_view(('GET', ))
@renderer_classes((JSONRenderer, ))
def get_results_with_difference(request):
    """
    Returns list of results which contain differences between two given scrapes.
    """

    scrape1, scrape2 = get_scrapes_from_params(request)

    differences = Difference.objects.filter(
        result1__scrape=scrape1, result2__scrape=scrape2, has_difference=True)

    data = {"scrape1": ScrapeSerializer(
        scrape1).data, "scrape2": ScrapeSerializer(scrape2).data, "results": [{'id': difference.id, 'page_link': difference.result2.page_link, 'page_title': difference.result2.page_title} for difference in differences]}
    return Response(data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    responses={200: DifferenceSerializer()}
)
@api_view(('GET', ))
@renderer_classes((JSONRenderer, ))
def get_difference_text(request, id: int) -> Response:
    """
    Returns a single difference instance for the given id, with the difference as text.
    """

    return get_difference(id, False)


@swagger_auto_schema(
    method='get',
    responses={200: DifferenceSerializerArray()}
)
@api_view(('GET', ))
@renderer_classes((JSONRenderer, ))
def get_difference_text_as_arrays(request, id: int) -> Response:
    """
    Returns a single difference instance for the given id, with the difference as arrays.
    """

    return get_difference(id, True)
