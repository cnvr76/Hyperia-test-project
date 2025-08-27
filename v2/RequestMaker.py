import logging

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By

import asyncio
import requests
import time
from contextlib import asynccontextmanager

from typing import List, Dict, Tuple, Any, Optional, Union, Callable
import random


logging.basicConfig(level=logging.INFO, format="format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'")
logger = logging.getLogger(__name__)


class Requester:
    def __init__(self, max_browsers: int = 3, max_concurrent: int = 8, base_delay: float = 1.0) -> None:
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.pool = asyncio.Queue(maxsize=max_browsers)
        self.base_delay = base_delay

        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36", 
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ]

        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.avg_response_time: float = 8.0
        self.error_count: int = 0

    async def __aenter__(self):
        await self.__init_browser_pool()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__cleanup()

    async def __init_browser_pool(self):
        logger.info(f"Initializing pool with max: {self.pool.maxsize}")

        for i in range(self.pool.maxsize):
            options = webdriver.FirefoxOptions()

            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--width=1920")
            options.add_argument("--height=1080")

            profile = webdriver.FirefoxProfile()

            profile.set_preference("dom.webdriver.enabled", False)
            profile.set_preference("useAutomationExtension", False)
            profile.set_preference("marionette.enabled", True)

            profile.set_preference("general.useragent.override", random.choice(self.user_agents))
            
            profile.set_preference("permissions.default.images", 2)
            profile.set_preference("javascript.enabled", True)
            profile.set_preference("media.autoplay.default", 5)
            profile.set_preference("network.http.pipelining", True)
            profile.set_preference("network.http.proxy.pipelining", True)
            profile.set_preference("network.http.pipelining.maxrequests", 8)

            profile.set_preference("dom.push.enabled", False)
            profile.set_preference("dom.webnotifications.enabled", False)
            profile.set_preference("geo.enabled", False)
            profile.set_preference("media.navigator.enabled", False)

            profile.set_preference("privacy.trackingprotection.enabled", False)
            profile.set_preference("browser.safebrowsing.enabled", False)
            profile.set_preference("browser.safebrowsing.malware.enabled", False)

            profile.set_preference("devtools.console.stdout.content", False)

            options.profile = profile

            driver = webdriver.Firefox(
                service=Service(GeckoDriverManager().install()),
                options=options
            )

            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                                  
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                                  
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-Us', 'en', 'de']
                });
            """)

            await self.pool.put(driver)
            logger.info(f"Firefox browser {i + 1}/{self.pool.maxsize} initialized")
    
    async def __cleanup(self):
        while not self.pool.empty():
            driver: webdriver.Firefox = await self.pool.get()
            try:
                driver.quit()
            except:
                pass
        logger.info("All browsers are closed")

    @asynccontextmanager
    async def _get_browser(self):
        driver: webdriver.Firefox = await self.pool.get()
        try:
            yield driver
        finally:
            await self.pool.put(driver)

    def _calculate_delay(self) -> float:
        delay: float = self.base_delay

        if self.error_count > 0:
            delay *= (1.3 ** min(self.error_count, 4))
        
        if self.avg_response_time > 8:
            delay *= 1.4
        elif self.avg_response_time < 4:
            delay *= 0.7

        return random.uniform(delay * 0.7, delay * 1.4)

    def _get_dynamic_page(self, driver: webdriver.Firefox, url: str, shop_name: str) -> Optional[str]:
        try:
            logger.info(f"Getting dynamic page for {shop_name}")

            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)

            driver.get(url)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "page-body"))
            )

            driver.execute_script("window.scrollTo({top: document.body.scrollHeight/4, behavior: 'smooth'})")
            time.sleep(0.8)
            driver.execute_script("window.scrollTo({top: document.body.scrollHeight/2, behavior: 'smooth'})")
            time.sleep(0.8)
            driver.execute_script("window.scrollTo({top: document.body.scrollHeight*3/4, behavior: 'smooth'})")
            time.sleep(0.8)
            driver.execute_script("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})")

            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "brochure-thumb"))
                )
            except:
                logger.warning(f"No brochure-thumb elements were found for {shop_name}")

            time.sleep(1.5)

            return driver.page_source
        
        except Exception as e:
            logger.error(f"Error with dynamic parsing of the {shop_name} page: {str(e)}")
            return None

    
    def send_request(self, url: str) -> Optional[str]:
        try:
            logger.info(f"Sending reqular request to {url}")
            page = requests.get(url)
            return page.text
        except Exception as e:
            logger.error(f"Error occurred while trying to get page by {url=}: {str(e)}")
            return None

    async def send_shop_request(self, shop_name: str, url: str, parse_shop_page_func: Callable) -> Tuple[List[Dict], str]:
        async with self.semaphore:
            try:
                delay: float = self._calculate_delay()
                await asyncio.sleep(delay)

                self.total_requests += 1

                async with self._get_browser() as driver:
                    html: Optional[str] = await asyncio.to_thread(
                        self._get_dynamic_page, driver, url, shop_name
                    )

                    if html:
                        parsed_info: List[Dict[str, Any]] = await parse_shop_page_func(html, shop_name)
                        self.successful_requests += 1

                        logger.info(f"Shop {shop_name} was parsed successfuly! Brochures: {len(parsed_info)}")
                        return parsed_info, shop_name
                    else:
                        logger.warning(f"Empty html received for {shop_name}")
            except Exception as e:
                self.failed_requests += 1
                logger.error(f"Error with {shop_name}: {str(e)}")
                return [], shop_name


    