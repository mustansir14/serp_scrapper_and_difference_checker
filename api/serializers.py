from rest_framework.serializers import ModelSerializer
from api.models import Query


class QuerySerializer(ModelSerializer):

    class Meta:
        model = Query
        fields = "__all__"
