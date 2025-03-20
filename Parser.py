from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

import asyncio

import re
import random
from bs4 import BeautifulSoup

from FileWriter import Writer
from typing import List, Tuple, Dict, Any, Optional


class Parser:
    def __init__(self) -> None:
        self.__final_json: str = "responses/parsed_page.json"
        self.__link: str = "https://www.prospektmaschine.de/hypermarkte/"

    @property
    def final_json(self):
        return self.__final_json

    def get_leftside_menu_shop_urls(self) -> List[Dict[str, str]]:
        """Returns the list of all the shops inside the side panel with info like url and shop's name"""
        html: str = self.__send_request_selenium(self.__link, 1)
        
        soup: BeautifulSoup = BeautifulSoup(html, 'html.parser')
        
        shops: List[Dict[str, str]] = []
        leftmenu = soup.find("div", attrs={"id": "sidebar"}).find("div", attrs={"class": "box"}) 
        for li in leftmenu.find_all("li"):
            # returns the path parameter ("/<smth>/")
            link: str = li.find("a", href=True).get("href")
            
            if not link:
                continue
            
            shops.append({"shop_name": li.text.strip(),"link": f"https://www.prospektmaschine.de{link}"})
        
        return shops

    async def send_request_async(self, link: str, load_time_s: int = 4):
        """Sends async request with random time interval to avoid oversaturation of the requests"""
        await asyncio.sleep(random.uniform(2, 5))
        return await asyncio.to_thread(self.__send_request_selenium, link, load_time_s)

    def __send_request_selenium(self, link: str, load_time_s: int) -> str:
        """Synchronous function to get html from dynamic websites using selenium"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-features=NetworkService")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            driver.get(link)
            driver.implicitly_wait(load_time_s)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            return driver.page_source
        except Exception as e:
            print(f"Ошибка при загрузке {link}: {e}")
            return ""
        finally:
            driver.quit()

    async def parse_info(self, html: str, shop_name: str) -> List[Dict[str, str]]:  
        soup: BeautifulSoup = BeautifulSoup(html, "html.parser")

        brochures_grid = soup.find("div", attrs={"class": "page-body"}).find("div", attrs={"class": "letaky-grid"})
        brochures = brochures_grid.find_all("div", attrs={"class": "brochure-thumb"})

        brochures_parsed: List[Dict[str, str]] = []
        for brochure in brochures:
            try:
                description_tag = brochure.find("div", attrs={"class": "letak-description"})
                title_tag = description_tag.find("strong")
                dates_tag = description_tag.find("small", attrs={"class": "hidden-sm"})
                
                image_tag = brochure.find("div", attrs={"class": "img-container"}).find("img")

                if dates_tag:
                    parsed_date: Tuple[datetime, datetime] = Parser.parse_date(dates_tag.text)
                    valid_from: datetime = parsed_date[0]
                    valid_to: datetime = parsed_date[1]

                info = {
                    "title": title_tag.text if title_tag else "Not found",
                    "thumbnail": image_tag.get("src") or image_tag.get("data-src") if image_tag else "Not found",
                    "shop_name": shop_name,
                    "valid_from": valid_from.strftime('%m-%d-%Y') if valid_from else "Not found",
                    "valid_to": valid_to.strftime('%m-%d-%Y') if valid_to else "Not specified",
                    "parsed_time": datetime.now().strftime("%m-%d-%Y %H:%M:%S")
                }
                brochures_parsed.append(info)
            except Exception as e:
                print(e)

        return brochures_parsed

    @staticmethod
    def parse_date(date: str) -> Tuple[Optional[datetime]]:
        try:
            # if date has smth like "von Montag 03.03.2025" inside
            if date.find("-") == -1:
                clean_date = re.sub(r"[^\d.]", "", date).replace(" ", "")
                valid_from = datetime.strptime(clean_date, "%d.%m.%Y")
                return (valid_from, None)
            # for formats like this "03.03.2025 - 30.03.2025"
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
        """Used for outputing big chunk of text into log.txt for more redability"""
        filename: str = "logging/log.txt"
        Writer.write_to_file(f"Log Date: {datetime.now()}\n\n{data}", filename)
