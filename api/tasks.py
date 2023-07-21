import logging
from datetime import datetime

from celery import shared_task

from api.models import Query, Scrape, Status
from api.scraper import Scraper
from serp_checker.celery import app

logging.basicConfig(
    format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %H:%M:%S", level=logging.INFO
)


@shared_task
def scrape_queries():
    logging.info(f"[Scheduled]: Running task to scrape queries")
    # Get all queries
    queries = Query.objects.all()

    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Iterate over the queries
    for query in queries:
        created_month = query.created_at.month
        created_year = query.created_at.year

        # Calculate the number of months since the query was created
        num_months = (current_year - created_year) * 12 + (
            current_month - created_month
        )

        # Check if the query should be scraped this month based on the interval
        if num_months % query.interval_no_of_months == 0:
            # Scrape the query
            # Your scraping logic goes here
            logging.info(f"[Scheduled]: Scraping query: {query.query}")

            scrape = Scrape(query=query, status=Status.PENDING)
            scrape.save()
            scraper = Scraper(scrape)
            scraper.start()


@app.task
def perform_scrape(scrape_id: int):
    scrape = Scrape.objects.get(id=scrape_id)
    scraper = Scraper(scrape)
    scraper.start()
