import logging
import requests
import os
from base64 import b64encode
from dotenv import load_dotenv
from typing import List
from api.models import Scrape, Status, Result, Difference
from datetime import datetime, timezone
from threading import Thread
from bs4 import BeautifulSoup
from undetected_chromedriver import Chrome
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import difflib
import json
import time

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

        self.driver = None

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

        previous_scrape = Scrape.objects.filter(query=self.scrape.query, completed_at__isnull=False).exclude(
            id=self.scrape.id).order_by('-completed_at').first()

        try:
            data = self.get_serp_data()
            for serp_item in data:

                if serp_item['type'] != "organic":
                    continue

                result = self.get_result(serp_item)

                if not result or not previous_scrape:
                    continue

                try:
                    previous_result = Result.objects.get(
                        scrape=previous_scrape, page_link=result.page_link)
                    self.get_difference(previous_result, result)
                except Result.DoesNotExist:
                    pass

            self.update_scrape(Status.SUCCESS)
        except Exception as e:
            logging.error("Error: " + str(e))
            self.update_scrape(Status.FAILED, str(e))

        self.kill_driver()

    def get_result(self, serp_item: dict) -> Result | None:

        result = Result(
            scrape=self.scrape, page_title=serp_item['title'], page_link=serp_item['url'], page_ranking=serp_item['rank_absolute'])
        try:
            result.page_content_text = self.request_page(
                serp_item['url'])
        except Exception as e:
            logging.error("Error in requesting page: ", str(e))
            return None
        result.save()
        return result

    def get_difference(self, result1: Result, result2: Result):

        difference = Difference(
            result1=result1, result2=result2)
        d = difflib.Differ()
        text1_lines = result1.page_content_text.splitlines()
        text2_lines = result2.page_content_text.splitlines()
        difference.content_difference = json.dumps(
            list(d.compare(text1_lines, text2_lines)))
        difference.title_difference = json.dumps(
            list(d.compare([result1.page_title], [result2.page_title])))
        difference.ranking_difference = result2.page_ranking - result1.page_ranking
        difference.has_difference = result1.page_content_text != result2.page_content_text or result1.page_title != result2.page_title
        difference.save()

    def start_async(self) -> None:
        thread = Thread(target=self.start)
        thread.start()

    def request_page(self, url: str) -> str:

        logging.info(f"Fetching Page content for {url}")
        if not self.driver:
            self.init_driver()
        for i in range(3):
            try:
                self.driver.get(url)
                break
            except:
                logging.info("Error in requesting page. Trying again...")
                self.kill_driver()
                self.init_driver()
        if i == 3:
            raise Exception("Page load Exception.")
        time.sleep(5)
        return self.driver.find_element(By.TAG_NAME, "body").text

    def update_scrape(self, status: str, log: str = "") -> None:
        self.scrape.status = status
        self.scrape.log = log
        if status == Status.SUCCESS:
            self.scrape.completed_at = datetime.now(timezone.utc)
        self.scrape.save()

    def init_driver(self) -> None:
        self.driver = Chrome(
            headless=os.getenv('ENVIRON') == 'prod')
        self.driver.set_page_load_timeout(30)

    def kill_driver(self) -> None:
        try:
            self.driver.quit()
        except:
            pass
        self.driver = None
