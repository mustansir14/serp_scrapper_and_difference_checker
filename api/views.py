from rest_framework.viewsets import ModelViewSet
from api.serializers import QuerySerializer
from api.models import Query

# Create your views here.


class QueryViewSet(ModelViewSet):

    serializer_class = QuerySerializer
    queryset = Query.objects.all()

    def perform_create(self, serializer):
        serializer.save()
