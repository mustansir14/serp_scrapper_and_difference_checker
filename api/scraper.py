import difflib
import json
import logging
import os
import re
import time
from base64 import b64encode
from datetime import datetime, timezone
from typing import List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome

from api.models import Difference, Result, Scrape, Status

load_dotenv()
logging.basicConfig(
    format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %H:%M:%S", level=logging.INFO
)


class Scraper:
    def __init__(self, scrape: Scrape) -> None:
        self.scrape = scrape

        base64_bytes = b64encode(
            ("%s:%s" % (os.getenv("DFS_EMAIL"), os.getenv("DFS_PASSWORD"))).encode(
                "ascii"
            )
        ).decode("ascii")

        self.headers = {
            "Authorization": f"Basic {base64_bytes}",
            "Content-Type": "application/json",
        }

        self.driver = None
        self.special_sites = [
            "linkedin.com",
            "instagram.com",
            "facebook.com",
            "pinterest.com",
            "twitter.com",
        ]

    def get_serp_data(self) -> List[dict]:
        logging.info(f"Fetching SERP data for {self.scrape.query.query}")
        url = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"

        payload = [
            {
                "keyword": self.scrape.query.query,
                "location_code": 2826,
                "language_code": "en",
                "device": "desktop",
                "os": "windows",
                "depth": 100,
            }
        ]

        response = requests.request(
            "POST", url, headers=self.headers, json=payload)

        return response.json()["tasks"][0]["result"][0]["items"]

    def start(self) -> None:
        logging.info(f"Starting scraping for {self.scrape.query.query}")

        previous_scrape = (
            Scrape.objects.filter(query=self.scrape.query,
                                  completed_at__isnull=False)
            .exclude(id=self.scrape.id)
            .order_by("-completed_at")
            .first()
        )

        try:
            data = self.get_serp_data()
            for serp_item in data:
                if serp_item["type"] != "organic":
                    continue

                result = self.get_result(serp_item)

                if not result or not previous_scrape:
                    continue

                try:
                    previous_result = Result.objects.get(
                        scrape=previous_scrape, page_link=result.page_link
                    )
                    self.get_difference(previous_result, result)
                except Result.DoesNotExist:
                    pass

            logging.info(f"Scraping finished for {self.scrape.query.query}")
            self.update_scrape(Status.SUCCESS)
        except Exception as e:
            logging.error("Error: " + str(e))
            self.update_scrape(Status.FAILED, str(e))

        self.kill_driver()

    def get_result(self, serp_item: dict) -> Result | None:
        result = Result(
            scrape=self.scrape,
            page_title=serp_item["title"],
            page_link=serp_item["url"],
            page_ranking=serp_item["rank_absolute"],
        )
        try:
            content = self.request_page(serp_item["url"])
            query_lowered = self.scrape.query.query.lower()
            # if (
            #     query_lowered not in serp_item["title"].lower()
            #     and query_lowered
            #     not in serp_item["url"]
            #     .replace("-", " ")
            #     .replace("_", " ")
            #     .replace(".", " ")
            #     and query_lowered.replace(" ", "") not in serp_item["url"]
            # ):
            if query_lowered not in content.lower():
                raise Exception("Query not in returned content.")
            if not self.is_of_special_site(serp_item["url"]):
                content = self.search_text(content)

            # replace multiple \n with two
            content = re.sub(r'\n{2,}', '\n\n', content)

            result.page_content_text = content
        except Exception as e:
            logging.error("Error in requesting page: " + str(e))
            result.page_scrape_status = Status.FAILED
            result.page_scrape_log = str(e)
            result.save()
            return None
        result.page_scrape_status = Status.SUCCESS
        result.page_scrape_log = ""
        result.save()
        return result

    def get_difference(self, result1: Result, result2: Result):
        difference = Difference(result1=result1, result2=result2)
        d = difflib.Differ()
        text1_lines = result1.page_content_text.splitlines()
        text2_lines = result2.page_content_text.splitlines()
        difference.content_difference = json.dumps(
            list(d.compare(text1_lines, text2_lines))
        )
        difference.title_difference = json.dumps(
            list(d.compare([result1.page_title], [result2.page_title]))
        )
        difference.ranking_difference = result2.page_ranking - result1.page_ranking
        difference.has_difference = (
            result1.page_content_text != result2.page_content_text
            or result1.page_title != result2.page_title
        )
        difference.save()

    def request_page(self, url: str) -> str:
        logging.info(f"Fetching Page content for {url}")
        if self.is_of_special_site(url):
            content = self.request_using_selenium(url)
        else:
            content = self.request_using_requests(url)
        content = content.strip()
        if not content:
            raise Exception("Empty content.")
        return content

    def search_text(self, text: str) -> str:
        """
        Returns sections of text where the query or a word from the query is present
        """
        # Prepare the query by splitting it into individual words
        query_words = self.scrape.query.query.lower().split()

        # Create a regex pattern to match any of the query words
        pattern = r"\b(" + "|".join(re.escape(word)
                                    for word in query_words) + r")\b"

        # Find all matches in the text
        matches = re.finditer(pattern, text.lower())

        # Extract the sections around each match
        sections = []
        last_end_index = 0
        end_index = None
        for match in matches:
            start_index = max(last_end_index, match.start() - 300)
            if start_index != last_end_index:
                sections.append("...\n\n")
            end_index = min(len(text), match.end() + 300)
            section = text[start_index:end_index]
            sections.append(section)
            last_end_index = end_index

        if end_index != len(text):
            sections.append("...")

        return "".join(sections)

    def request_using_requests(self, url: str) -> str:
        res = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            },
            timeout=30
        )
        soup = BeautifulSoup(res.content, "html.parser")
        return soup.text

    def request_using_selenium(self, url: str) -> str:
        self.init_driver()
        self.driver.get(url)
        time.sleep(5)
        try:
            if "twitter.com" in url:
                content = "\n".join(
                    [
                        el.text
                        for el in self.driver.find_element(
                            By.CLASS_NAME, "css-1dbjc4n.r-1ifxtd0.r-ymttw5.r-ttdzmv"
                        ).find_elements(By.XPATH, "*")[1:4]
                    ]
                )
            elif "pinterest.com" in url:
                content = "\n".join(
                    [
                        el.text
                        for el in self.driver.find_element(
                            By.CLASS_NAME, "Jea.KS5.a3i.jzS.zI7.iyn.Hsu"
                        ).find_elements(By.XPATH, "*")[1:4]
                    ]
                )
            elif "instagram.com" in url:
                content = self.driver.find_element(By.CLASS_NAME, "_aa_c").text
            elif "linkedin.com" in url:
                content = self.driver.find_element(
                    By.CLASS_NAME, "scaffold-layout__main"
                ).text
            elif "facebook.com" in url:
                content = (
                    self.driver.find_element(By.TAG_NAME, "h1").text.strip()
                    + "\n\n"
                    + self.driver.find_element(By.CLASS_NAME, "x1yztbdb").text.strip()
                )
            else:
                content = self.driver.find_element(By.TAG_NAME, "body").text
        except:
            content = self.driver.find_element(By.TAG_NAME, "body").text
        self.kill_driver()
        return content

    def update_scrape(self, status: str, log: str = "") -> None:
        self.scrape.status = status
        self.scrape.log = log
        if status == Status.SUCCESS:
            self.scrape.completed_at = datetime.now(timezone.utc)
        self.scrape.save()

    def init_driver(self) -> None:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = Chrome(
            options=options, headless=os.getenv("ENVIRON") == "prod")
        self.driver.set_page_load_timeout(30)

    def kill_driver(self) -> None:
        try:
            self.driver.quit()
        except:
            pass
        self.driver = None

    def is_of_special_site(self, url):
        for site in self.special_sites:
            if site in url:
                return True
        return False
