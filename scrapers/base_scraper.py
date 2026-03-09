"""
Base Scraper
Tüm scraper'lar için temel sınıf.
"""

import random
import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from scrapers.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Tüm scraper'lar için temel sınıf."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]

    def __init__(self, config=None, proxy_manager: ProxyManager = None):
        self.config = config
        self.proxy_manager = proxy_manager
        self.driver = None
        self.driver_lock = threading.Lock()
        self._stop_requested = False

    @property
    def headless(self) -> bool:
        if self.config:
            return self.config.get("scraping", "headless", default=True)
        return True

    @property
    def max_retries(self) -> int:
        if self.config:
            return self.config.get("scraping", "max_retries", default=3)
        return 3

    @property
    def delay_range(self) -> tuple:
        if self.config:
            return (
                self.config.get("scraping", "delay_min", default=1.0),
                self.config.get("scraping", "delay_max", default=3.0),
            )
        return (1.0, 3.0)

    def get_random_user_agent(self) -> str:
        """Rastgele user agent döndürür."""
        return random.choice(self.USER_AGENTS)

    def random_delay(self, min_sec: float = None, max_sec: float = None):
        """Rastgele bekleme süresi."""
        if min_sec is None or max_sec is None:
            min_sec, max_sec = self.delay_range
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def initialize_driver(self, proxy_url: str = None) -> webdriver.Chrome:
        """Chrome webdriver'ı başlatır."""
        with self.driver_lock:
            if self.driver is not None:
                return self.driver

            try:
                chrome_options = Options()

                if self.headless:
                    chrome_options.add_argument("--headless=new")

                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-infobars")
                chrome_options.add_argument(f"--user-agent={self.get_random_user_agent()}")

                # Anti-detection
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)

                # Proxy
                if proxy_url:
                    chrome_options.add_argument(f"--proxy-server={proxy_url}")
                elif self.proxy_manager and self.proxy_manager.has_proxies:
                    proxy = self.proxy_manager.get_proxy()
                    if proxy:
                        chrome_options.add_argument(f"--proxy-server={proxy}")

                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)

                # Anti-detection JavaScript
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                        window.chrome = {runtime: {}};
                    """
                })

                logger.info("Chrome WebDriver başlatıldı")
                return self.driver

            except Exception as e:
                logger.error(f"WebDriver başlatma hatası: {e}")
                raise

    def close_driver(self):
        """WebDriver'ı kapatır."""
        with self.driver_lock:
            if self.driver:
                try:
                    self.driver.quit()
                    self.driver = None
                    logger.info("WebDriver kapatıldı")
                except Exception as e:
                    logger.error(f"WebDriver kapatma hatası: {e}")

    def wait_for_element(self, selector: str, timeout: int = 20, by: By = By.CSS_SELECTOR):
        """Elementin görünmesini bekler."""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )

    def wait_for_elements(self, selector: str, timeout: int = 20, by: By = By.CSS_SELECTOR):
        """Birden fazla elementin görünmesini bekler."""
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return self.driver.find_elements(by, selector)

    def safe_find_element(self, parent, selector: str, by: By = By.CSS_SELECTOR, default: str = "") -> str:
        """Güvenli element bulma - hata vermez."""
        try:
            element = parent.find_element(by, selector)
            return element.text.strip()
        except Exception:
            return default

    def safe_get_attribute(self, parent, selector: str, attribute: str, by: By = By.CSS_SELECTOR, default: str = "") -> str:
        """Güvenli attribute alma."""
        try:
            element = parent.find_element(by, selector)
            return element.get_attribute(attribute) or default
        except Exception:
            return default

    def scroll_page(self, scroll_count: int = 3, delay: float = 1.0):
        """Sayfayı aşağı kaydırır."""
        for i in range(scroll_count):
            self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
            time.sleep(delay)

    def request_stop(self):
        """Durdurma talebi gönderir."""
        self._stop_requested = True

    def reset_stop(self):
        """Durdurma talebini sıfırlar."""
        self._stop_requested = False

    @property
    def should_stop(self) -> bool:
        """Durdurma talep edildi mi?"""
        return self._stop_requested

    @abstractmethod
    def scrape_products(self, **kwargs) -> List[Dict]:
        """Ürünleri çeker. Alt sınıflar tarafından implement edilmelidir."""
        pass

    def __del__(self):
        self.close_driver()
