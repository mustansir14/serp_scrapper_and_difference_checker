from celery import shared_task
from datetime import datetime
from api.models import Query, Scrape
from api.scraper import Scraper
import logging
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)


@shared_task
def scrape_queries():
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
        num_months = (current_year - created_year) * \
            12 + (current_month - created_month)

        # Check if the query should be scraped this month based on the interval
        if num_months % query.interval_no_of_months == 0:
            # Scrape the query
            # Your scraping logic goes here
            logging.info(f"[Scheduled]: Scraping query: {query.query}")

            scrape = Scrape(query=query)
            scrape.save()
            scraper = Scraper(scrape)
            scraper.start()
