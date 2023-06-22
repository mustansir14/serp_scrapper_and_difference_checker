from django.db import models

# Enum


class Status(models.TextChoices):

    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


# Create your models here.


class Query(models.Model):

    query = models.TextField(null=False, blank=False, unique=True)
    interval_no_of_months = models.PositiveIntegerField(
        null=False, blank=False)
    created_at = models.DateTimeField(
        null=False, blank=False, auto_now_add=True)


class Scrape(models.Model):

    query = models.ForeignKey(Query, on_delete=models.CASCADE)
    started_at = models.DateTimeField(
        null=False, blank=False, auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(choices=Status.choices,
                              default=Status.PENDING, null=False, blank=False, max_length=15)
    log = models.TextField(default=None, null=True, blank=True)


class Result(models.Model):

    scrape = models.ForeignKey(Scrape, on_delete=models.CASCADE)
    page_title = models.TextField(null=False, blank=False)
    page_link = models.TextField(null=False, blank=False)
    page_ranking = models.PositiveIntegerField(null=False, blank=False)
    page_content_text = models.TextField(null=False, blank=False)
    page_scrape_status = models.CharField(choices=Status.choices,
                                          default=Status.PENDING, null=False, blank=False, max_length=15)
    page_scrape_log = models.TextField(default=None, null=True, blank=True)


class Difference(models.Model):
    result1 = models.ForeignKey(
        Result, on_delete=models.CASCADE, related_name="result1")
    result2 = models.ForeignKey(
        Result, on_delete=models.CASCADE, related_name="result2")
    content_difference = models.TextField(null=True, blank=True)
    title_difference = models.TextField(null=True, blank=True)
    ranking_difference = models.IntegerField(null=False, blank=False)
    has_difference = models.BooleanField(null=False, blank=False)
