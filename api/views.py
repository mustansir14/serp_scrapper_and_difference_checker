from typing import Tuple

from rest_framework.viewsets import ModelViewSet
from rest_framework import mixins, viewsets
from api.serializers import QuerySerializer, ScrapeSerializer, ResultListSerializer, ResultDetailSerializer
from api.models import Query, Scrape, Status, Result
from api.scraper import Scraper
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.request import Request
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
            return ResultListSerializer
        return ResultDetailSerializer

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
        return Response({"status": "error", "message": "Invalid scrape1_id"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        scrape2 = Scrape.objects.get(id=scrape2_id)
    except Scrape.DoesNotExist:
        return Response({"status": "error", "message": "Invalid scrape2_id"}, status=status.HTTP_400_BAD_REQUEST)

    if scrape1.query != scrape2.query:
        return Response({"status": "error", "message": "Both scrapes belong to different queries"}, status=status.HTTP_400_BAD_REQUEST)

    return scrape1, scrape2


def get_difference(request: Request, html: bool, as_arrays: bool = False) -> Response:

    page_link = request.query_params.get("page_link")
    scrape1, scrape2 = get_scrapes_from_params(request)

    try:
        result1 = Result.objects.get(scrape=scrape1, page_link=page_link)
    except Result.DoesNotExist:
        return Response({"status": "error", "message": "Result with given page_link does not exist for Scrape 1"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result2 = Result.objects.get(scrape=scrape2, page_link=page_link)
    except Result.DoesNotExist:
        return Response({"status": "error", "message": "Result with given page_link does not exist for Scrape 2"}, status=status.HTTP_400_BAD_REQUEST)

    d = difflib.Differ()
    if html:
        text1_lines = result1.page_content_html.splitlines()
        text2_lines = result2.page_content_html.splitlines()
    else:
        text1_lines = result1.page_content_text.splitlines()
        text2_lines = result2.page_content_text.splitlines()
    diff = d.compare(text1_lines, text2_lines)
    if not as_arrays:
        diff = "\n".join(diff)
    data = {"scrape1": ScrapeSerializer(
        scrape1).data, "scrape2": ScrapeSerializer(scrape2).data, "page_link": page_link, "difference": diff}
    return Response(data, status=status.HTTP_200_OK)


difference_views_parameters = [
    openapi.Parameter('scrape1_id', openapi.IN_QUERY,
                      description="ID of scrape 1 to get difference",
                      type=openapi.TYPE_INTEGER,
                      required=True),
    openapi.Parameter('scrape2_id', openapi.IN_QUERY,
                      description="ID of scrape 2 to get difference",
                      type=openapi.TYPE_INTEGER,
                      required=True),
    openapi.Parameter('page_link', openapi.IN_QUERY,
                      description="The URL of the page for which difference is to be returned",
                      type=openapi.TYPE_STRING,
                      required=True)
]


@swagger_auto_schema(
    method='get',
    manual_parameters=difference_views_parameters
)
@api_view(('GET', ))
@renderer_classes((JSONRenderer, ))
def get_difference_html(request) -> Response:

    return get_difference(request, True, False)


@swagger_auto_schema(
    method='get',
    manual_parameters=difference_views_parameters
)
@api_view(('GET', ))
@renderer_classes((JSONRenderer, ))
def get_difference_text(request) -> Response:

    return get_difference(request, False, False)


@swagger_auto_schema(
    method='get',
    manual_parameters=difference_views_parameters
)
@api_view(('GET', ))
@renderer_classes((JSONRenderer, ))
def get_difference_html_as_arrays(request) -> Response:

    return get_difference(request, True, True)


@swagger_auto_schema(
    method='get',
    manual_parameters=difference_views_parameters
)
@api_view(('GET', ))
@renderer_classes((JSONRenderer, ))
def get_difference_text_as_arrays(request) -> Response:

    return get_difference(request, False, True)


@swagger_auto_schema(
    method='get',
    manual_parameters=difference_views_parameters[:2]
)
@api_view(('GET', ))
@renderer_classes((JSONRenderer, ))
def get_difference_urls(request: Request) -> Response:

    scrape1, scrape2 = get_scrapes_from_params(request)

    urls1 = set(
        [result.page_link for result in Result.objects.filter(scrape=scrape1)])
    urls2 = set(
        [result.page_link for result in Result.objects.filter(scrape=scrape2)])

    data = {"scrape1": ScrapeSerializer(
        scrape1).data, "scrape2": ScrapeSerializer(scrape2).data, "urls_added": list(urls2 - urls1), "urls_removed": list(urls1 - urls2)}
    return Response(data, status=status.HTTP_200_OK)
