from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

import time
import re
from bs4 import BeautifulSoup

from FileWriter import Writer
from typing import List, Tuple, Dict, Any, Optional

from pprint import pprint


class Parser:
    def __init__(self) -> None:
        self.__final_json: str = "responses/parsed_page.json"
        self.__link: str = "https://www.prospektmaschine.de/hypermarkte/"

        self.__options = webdriver.ChromeOptions()
        self.__options.add_argument("--headless")
        self.__options.add_argument("--disable-gpu")
        self.__options.add_argument("--window-size=1920,1080")

        self.__driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.__options)
    
    def send_request(self, load_time_s: int = 2) -> str:
        self.__driver.get(self.__link)
        time.sleep(load_time_s)
        return self.__driver.page_source

    def parse_info(self, html: str, override: bool = True) -> List[Dict[str, str]]:  
        soup: BeautifulSoup = BeautifulSoup(html, "html.parser")

        brochures = soup.find_all("div", attrs={"class": "brochure-thumb"})

        brochures_parsed: List[Dict[str, str]] = []
        for brochure in brochures:
            try:
                description_tag = brochure.find("div", attrs={"class": "letak-description"})
                title_tag = description_tag.find("strong")
                dates_tag = description_tag.find("small", attrs={"class": "hidden-sm"})
                shop_name_tag = description_tag.find("a").find("div", attrs={"class": "grid-logo"}).find("img", alt=True)
                
                image_tag = brochure.find("div", attrs={"class": "img-container"}).find("img")

                if dates_tag:
                    parsed_date: Tuple[datetime, datetime] = Parser.parse_date(dates_tag.text)
                    valid_from: datetime = parsed_date[0]
                    valid_to: datetime = parsed_date[1]

                shop_name: str = shop_name_tag.get("alt").replace("Logo", "").strip() if shop_name_tag else "Not found"

                info = {
                    "title": title_tag.text if title_tag else "Not found",
                    "thumbnail": image_tag.get("src") or image_tag.get("data-src") if image_tag else "Not found",
                    "shop_name": shop_name,
                    "valid_from": valid_from.strftime('%m-%d-%Y') if valid_to else "Not found",
                    "valid_to": valid_to.strftime('%m-%d-%Y') if valid_to else "Not specified",
                    "parsed_time": datetime.now().strftime("%m-%d-%Y %H:%M:%S")
                }
                brochures_parsed.append(info)
            except Exception as e:
                print(e)

        if override:
            Writer.write_to_json(brochures_parsed, self.__final_json)

        return brochures_parsed
    
    def close_connection(self) -> None:
        self.__driver.quit()

    @staticmethod
    def parse_date(date: str) -> Tuple[Optional[datetime]]:
        try:
            if date.find("-") == -1:
                clean_date = re.sub(r"[^\d.]", "", date).replace(" ", "")
                valid_from = datetime.strptime(clean_date, "%d.%m.%Y")
                return (valid_from, None)
            else:
                date_splitted = date.replace(" ", "").split("-")
                valid_from = datetime.strptime(date_splitted[0], "%d.%m.%Y")
                valid_to = datetime.strptime(date_splitted[1], "%d.%m.%Y")
                return (valid_from, valid_to)
        except ValueError as ve:
            print(f"Incorrect date format...: {ve}")
            return (None, None)
        except Exception as e:
            print(f"Date parsing error occured...: {e}")
            return (None, None)

    @staticmethod
    def log(data: Any) -> None:
        filename: str = "logging/log.txt"
        Writer.write_to_file(f"Log Date: {datetime.now()}\n\n{data}", filename)
