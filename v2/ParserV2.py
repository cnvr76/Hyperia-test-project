import logging

from RequestMaker import Requester

from bs4 import BeautifulSoup

import asyncio

from datetime import datetime
import re
import json
from typing import List, Dict, Tuple, Any, Optional, Union


logging.basicConfig(level=logging.INFO, format="format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'")
logger = logging.getLogger(__name__)


class Parser:
    def __init__(self, max_browsers: int = 3, max_concurrent: int = 8, base_delay: float = 1.0) -> None:
        self.requester = Requester(max_browsers, max_concurrent, base_delay)
        self.json_output: str = "./result.json"
        self.base_url: str = "https://www.prospektmaschine.de/hypermarkte/"
    

    async def __aenter__(self):
        await self.requester.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.requester.__aexit__(exc_type, exc_val, exc_tb)


    async def get_all_shop_data(self):
        results: List[Dict[str, Any]] = []
        completed: int = 0

        shop_data: List[Dict[str, str]] = self.get_leftside_shop_list()

        logger.info(f"Found {len(shop_data)} shops")
        logger.info(f"Using Firefox with settings: {self.requester.pool.maxsize} browsers, {self.requester.semaphore._value} concurrent, {self.requester.base_delay}s base delay")
        
        tasks = [
            self.requester.send_shop_request(shop_name=shop.get("shop_name"), url=shop.get("link"), parse_shop_page_func=self.parse_info)
            for shop in shop_data
        ]

        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1

            logger.info(f"""
                Progress: {completed}/{len(tasks)},
                Success: {self.requester.successful_requests},
                Failed: {self.requester.failed_requests},
                Errors: {self.requester.error_count}
            """)

        logger.info("--PARSING COMPLETED--")
        
        successful_results = [result[0] for result in results if result and result[0]]
        return successful_results

    def get_leftside_shop_list(self) -> List[Dict[str, str]]:
        """Returns the list of all the shops inside the side panel with info like url and shop's name"""
        html: str = self.requester.send_request(self.base_url)
        
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
                logger.error(f"Error while parsing html of {shop_name}: {str(e)}")

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
    
    def check_output_file_exists(self) -> bool:
        try:        
            with open(self.json_output, "w", encoding="utf-8") as file:
                return True
        except FileNotFoundError as fnfe:
            return False

    def write_to_json(self, data: List[Dict[str, Any]]):
        try:        
            with open(self.json_output, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)
                return True
        except FileNotFoundError as fnfe:
            print(f"'{self.json_output=}' not found...")
            return False
