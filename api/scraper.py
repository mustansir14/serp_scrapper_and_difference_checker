import logging
import requests
import os
from base64 import b64encode
from dotenv import load_dotenv
from typing import List
from api.models import Scrape, Status, Result
from datetime import datetime, timezone
from threading import Thread
from bs4 import BeautifulSoup
load_dotenv()
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)


class Scraper:

    def __init__(self, scrape: Scrape) -> None:
        self.scrape = scrape

        base64_bytes = b64encode(
            ("%s:%s" % (os.getenv("DFS_EMAIL"),
             os.getenv("DFS_PASSWORD"))).encode("ascii")
        ).decode("ascii")

        self.headers = {
            'Authorization': f'Basic {base64_bytes}',
            'Content-Type': 'application/json'
        }

    def get_serp_data(self) -> List[dict]:
        logging.info(f"Fetching SERP data for {self.scrape.query.query}")
        url = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"

        payload = [{"keyword": self.scrape.query.query, "location_code": 2826,
                    "language_code": "en", "device": "desktop", "os": "windows", "depth": 20}]

        response = requests.request(
            "POST", url, headers=self.headers, json=payload)

        return response.json()['tasks'][0]['result'][0]['items']

    def start(self) -> None:

        logging.info(f"Starting scraping for {self.scrape.query.query}")

        try:
            data = self.get_serp_data()
            for serp_item in data:

                if serp_item['type'] != "organic":
                    continue

                result = Result(
                    scrape=self.scrape, page_title=serp_item['title'], page_link=serp_item['url'], page_ranking=serp_item['rank_absolute'])
                try:
                    page_response = self.request_page(serp_item['url'])
                except Exception as e:
                    logging.error("Error in requesting page: ", str(e))
                    continue
                result.page_content_html = page_response.text
                result.page_content_text = BeautifulSoup(
                    page_response.text, "html.parser").text
                result.status_code = page_response.status_code
                result.save()

            self.update_scrape(Status.SUCCESS)
        except Exception as e:
            logging.error("Error: ", str(e))
            self.update_scrape(Status.FAILED, str(e))

    def start_async(self) -> None:
        thread = Thread(target=self.start)
        thread.start()

    def request_page(self, url: str) -> requests.Response:

        logging.info(f"Fetching Page content for {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"}
        return requests.get(url, headers=headers)

    def update_scrape(self, status: str, log: str = "") -> None:
        self.scrape.status = status
        self.scrape.log = log
        if status == Status.SUCCESS:
            self.scrape.completed_at = datetime.now(timezone.utc)
        self.scrape.save()
