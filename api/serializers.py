from rest_framework import serializers
from api.models import Query, Scrape, Result, Difference


class QuerySerializer(serializers.ModelSerializer):

    interval_no_of_months = serializers.IntegerField(
        required=True, min_value=1, max_value=12)

    class Meta:
        model = Query
        fields = ("query", "interval_no_of_months", "id")
        read_only_fields = ("id", )


class ScrapeSerializer(serializers.ModelSerializer):

    query = QuerySerializer(read_only=True)
    query_id = serializers.SlugRelatedField(
        slug_field="id", queryset=Query.objects.all(), write_only=True, allow_null=True)

    class Meta:
        model = Scrape
        fields = "__all__"
        read_only_fields = ("query", "started_at",
                            "completed_at", "status", "log")

    def create(self, validated_data):
        scrape = Scrape(
            query=validated_data.pop('query_id'),
            **validated_data
        )
        scrape.save()
        return scrape


class ResultDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Result
        fields = "__all__"


class ResultListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Result
        fields = ("id", "page_title", "page_link",
                  "page_ranking", "scrape", "page_scrape_status", "page_scrape_log")


class DifferenceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Difference
        exclude = ("has_difference", )


class DifferenceSerializerArray(serializers.ModelSerializer):

    content_difference = serializers.ListField(child=serializers.CharField())
    title_difference = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = Difference
        exclude = ("has_difference", )
