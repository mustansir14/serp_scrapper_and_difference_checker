from django.db import models

# Create your models here.


class Query(models.Model):

    query = models.TextField(null=False, blank=False, unique=True)
    interval_no_of_months = models.PositiveIntegerField(
        null=False, blank=False)


class Scrape(models.Model):

    class Status(models.TextChoices):

        SUCCESS = "success"
        FAILED = "failed"
        PENDING = "pending"

    query = models.ForeignKey(Query, on_delete=models.CASCADE)
    started_at = models.DateTimeField(null=False, blank=False)
    completed_at = models.DateTimeField(null=False, blank=True)
    status = models.CharField(choices=Status.choices,
                              default=Status.PENDING, null=False, blank=False, max_length=15)


class Result(models.Model):

    scrape = models.ForeignKey(Scrape, on_delete=models.CASCADE)
    page_title = models.TextField(null=False, blank=False)
    page_link = models.TextField(null=False, blank=False)
    page_ranking = models.PositiveIntegerField(null=False, blank=False)
    page_content = models.TextField(null=False, blank=False)
    status_code = models.PositiveIntegerField(null=False, blank=False)
