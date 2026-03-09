"""
AliExpress Scraper
Gerçek AliExpress ürün çekme motoru.
"""

import re
import time
import random
import logging
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs, urlencode
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scrapers.base_scraper import BaseScraper
from scrapers.proxy_manager import ProxyManager
from utils.helpers import clean_text, clean_price, generate_uuid

logger = logging.getLogger(__name__)


class AliExpressScraper(BaseScraper):
    """AliExpress ürün çekme motoru."""

    # Kategori URL haritası
    CATEGORIES = {
        "Apparel & Accessories": {"id": "200000875", "slug": "apparel-accessories"},
        "Automobiles & Motorcycles": {"id": "34", "slug": "automobiles-motorcycles"},
        "Baby Products": {"id": "1501", "slug": "mother-kids"},
        "Beauty & Health": {"id": "66", "slug": "beauty-health"},
        "Computer & Office": {"id": "7", "slug": "computer-office"},
        "Consumer Electronics": {"id": "44", "slug": "consumer-electronics"},
        "Electrical Equipment & Supplies": {"id": "5", "slug": "electrical-equipment-supplies"},
        "Furniture": {"id": "1503", "slug": "furniture"},
        "Hair Extensions & Wigs": {"id": "200003567", "slug": "hair-extensions-wigs"},
        "Home & Garden": {"id": "15", "slug": "home-garden"},
        "Home Appliances": {"id": "6", "slug": "home-appliances"},
        "Home Improvement": {"id": "13", "slug": "home-improvement"},
        "Jewelry & Accessories": {"id": "1509", "slug": "jewelry-accessories"},
        "Lights & Lighting": {"id": "39", "slug": "lights-lighting"},
        "Luggage & Bags": {"id": "1524", "slug": "luggage-bags"},
        "Men's Clothing": {"id": "100003070", "slug": "men-clothing"},
        "Mother & Kids": {"id": "1501", "slug": "mother-kids"},
        "Office & School Supplies": {"id": "21", "slug": "office-school-supplies"},
        "Phones & Telecommunications": {"id": "509", "slug": "phones-telecommunications"},
        "Security & Protection": {"id": "30", "slug": "security-protection"},
        "Shoes": {"id": "322", "slug": "shoes"},
        "Sports & Entertainment": {"id": "18", "slug": "sports-entertainment"},
        "Tools": {"id": "1420", "slug": "tools"},
        "Toys & Hobbies": {"id": "26", "slug": "toys-hobbies"},
        "Watches": {"id": "1511", "slug": "watches"},
        "Weddings & Events": {"id": "200003361", "slug": "weddings-events"},
        "Women's Clothing": {"id": "100003109", "slug": "women-clothing"},
    }

    # Ürün kartı CSS selektörleri (AliExpress çok değişken, birden fazla seçenek)
    PRODUCT_CARD_SELECTORS = [
        "div[class*='search-item-card']",
        "div[class*='product-card']",
        ".search-card-item",
        "a[class*='_3t7zg']",
        ".product-snippet_ProductSnippet",
        "div[data-widget-cid*='product']",
    ]

    TITLE_SELECTORS = [
        "h1[class*='title']",
        ".product-title-text",
        "h3[class*='title']",
        "span[class*='title']",
        ".item-title",
    ]

    PRICE_SELECTORS = [
        "div[class*='price'] span",
        ".product-price-value",
        "span[class*='price-current']",
        ".es--wrap--erdmPRe",
    ]

    def __init__(self, config=None, proxy_manager: ProxyManager = None):
        super().__init__(config, proxy_manager)
        self.scraped_ids = set()

    def get_category_url(self, category: str) -> str:
        """Kategori URL'sini oluşturur."""
        if category in self.CATEGORIES:
            cat_info = self.CATEGORIES[category]
            return f"https://www.aliexpress.com/category/{cat_info['id']}/{cat_info['slug']}.html"
        raise ValueError(f"Bilinmeyen kategori: {category}")

    @classmethod
    def get_categories(cls) -> list:
        """Tüm kategorileri döndürür."""
        return list(cls.CATEGORIES.keys())

    def scrape_products(
        self,
        category: str = None,
        category_url: str = None,
        search_query: str = None,
        min_rating: float = 4.0,
        min_orders: int = 100,
        warehouse: str = "US",
        limit: int = 50,
        offset: int = 0,
        use_simulation: bool = False,
        progress_callback=None,
    ) -> List[Dict]:
        """
        AliExpress'ten ürünleri çeker.

        Args:
            category: Kategori adı
            category_url: Direkt kategori URL'si
            search_query: Arama sorgusu
            min_rating: Minimum puan
            min_orders: Minimum sipariş
            warehouse: Depo (US, EU, UK, CN)
            limit: Maksimum ürün sayısı
            offset: Başlangıç ofset
            use_simulation: Simülasyon modu
            progress_callback: İlerleme callback fonksiyonu

        Returns:
            Ürün sözlüklerinin listesi
        """
        self.reset_stop()

        if use_simulation:
            return self._simulate_scraping(
                category or "Consumer Electronics",
                min_rating, min_orders, warehouse, limit, offset, progress_callback
            )

        try:
            # URL oluştur
            if not category_url and category:
                category_url = self.get_category_url(category)
            elif search_query:
                category_url = f"https://www.aliexpress.com/wholesale?SearchText={search_query}"

            if not category_url:
                raise ValueError("Kategori veya arama sorgusu belirtilmelidir")

            # Driver başlat
            self.initialize_driver()
            products = []
            page = (offset // 60) + 1
            max_pages = (limit + 59) // 60

            for current_page in range(page, page + max_pages):
                if self.should_stop or len(products) >= limit:
                    break

                url = self._build_page_url(category_url, warehouse, current_page)
                page_products = self._scrape_page(url, min_rating, min_orders, category or "")

                for product in page_products:
                    if len(products) >= limit:
                        break
                    if product["id"] not in self.scraped_ids:
                        products.append(product)
                        self.scraped_ids.add(product["id"])

                if progress_callback:
                    progress = min(100, len(products) / limit * 100)
                    progress_callback(progress, f"{len(products)}/{limit} ürün çekildi")

                # Sayfalar arası bekleme
                self.random_delay(2.0, 5.0)

            logger.info(f"Toplam {len(products)} ürün çekildi")
            return products

        except Exception as e:
            logger.error(f"Scraping hatası: {e}", exc_info=True)
            return []

    def _build_page_url(self, base_url: str, warehouse: str, page: int) -> str:
        """Sayfa URL'sini oluşturur."""
        separator = "&" if "?" in base_url else "?"
        params = f"page={page}&shipFromCountry={warehouse}&SortType=total_tranpro_desc"
        return f"{base_url}{separator}{params}"

    def _scrape_page(self, url: str, min_rating: float, min_orders: int, category: str) -> List[Dict]:
        """Tek bir sayfadaki ürünleri çeker."""
        products = []

        try:
            logger.info(f"Sayfa çekiliyor: {url}")
            self.driver.get(url)

            # Sayfanın yüklenmesini bekle
            time.sleep(3)

            # Sayfayı kaydır
            self.scroll_page(scroll_count=5, delay=1.5)

            # Ürün kartlarını bul
            product_cards = []
            for selector in self.PRODUCT_CARD_SELECTORS:
                try:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards:
                        product_cards = cards
                        logger.debug(f"Selektör bulundu: {selector} ({len(cards)} kart)")
                        break
                except Exception:
                    continue

            if not product_cards:
                logger.warning("Ürün kartı bulunamadı, alternatif yöntem deneniyor...")
                # Fallback: tüm linkleri tara
                product_cards = self.driver.find_elements(
                    By.CSS_SELECTOR, "a[href*='/item/']"
                )

            logger.info(f"{len(product_cards)} ürün kartı bulundu")

            for card in product_cards:
                if self.should_stop:
                    break

                try:
                    product = self._extract_product_from_card(card, category)
                    if product:
                        rating = product.get("rating", 0)
                        orders = product.get("orders", 0)

                        if rating >= min_rating and orders >= min_orders:
                            products.append(product)

                except Exception as e:
                    logger.debug(f"Ürün kartı işleme hatası: {e}")
                    continue

                # Mini bekleme
                time.sleep(0.1)

        except TimeoutException:
            logger.warning(f"Sayfa yükleme zaman aşımı: {url}")
        except Exception as e:
            logger.error(f"Sayfa çekme hatası: {e}")

        return products

    def _extract_product_from_card(self, card, category: str) -> Optional[Dict]:
        """Ürün kartından bilgi çıkarır."""
        try:
            # Ürün URL'si
            product_url = ""
            try:
                if card.tag_name == "a":
                    product_url = card.get_attribute("href") or ""
                else:
                    link = card.find_element(By.CSS_SELECTOR, "a")
                    product_url = link.get_attribute("href") or ""
            except Exception:
                pass

            if not product_url:
                return None

            # Ürün ID'si
            product_id = self._extract_product_id(product_url)
            if not product_id:
                product_id = generate_uuid()

            # Ürün adı
            name = ""
            for selector in self.TITLE_SELECTORS + ["img[alt]"]:
                try:
                    if selector == "img[alt]":
                        img = card.find_element(By.CSS_SELECTOR, "img")
                        name = img.get_attribute("alt") or ""
                    else:
                        elem = card.find_element(By.CSS_SELECTOR, selector)
                        name = elem.text.strip()
                    if name:
                        break
                except Exception:
                    continue

            if not name:
                return None

            # Fiyat
            price_text = ""
            for selector in self.PRICE_SELECTORS:
                try:
                    elem = card.find_element(By.CSS_SELECTOR, selector)
                    price_text = elem.text.strip()
                    if price_text:
                        break
                except Exception:
                    continue

            price = clean_price(price_text)

            # Puan
            rating = 0.0
            try:
                rating_text = self.safe_find_element(
                    card, "span[class*='rating'], span[class*='star']"
                )
                if rating_text:
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating = float(rating_match.group(1))
            except Exception:
                pass

            # Sipariş sayısı
            orders = 0
            try:
                orders_text = self.safe_find_element(
                    card, "span[class*='sold'], span[class*='order']"
                )
                if orders_text:
                    orders_match = re.search(r'(\d[\d,]*)', orders_text.replace("+", ""))
                    if orders_match:
                        orders = int(orders_match.group(1).replace(",", ""))
            except Exception:
                pass

            # Resim URL'si
            image_url = ""
            try:
                img = card.find_element(By.CSS_SELECTOR, "img")
                image_url = (
                    img.get_attribute("src")
                    or img.get_attribute("data-src")
                    or img.get_attribute("data-lazy-src")
                    or ""
                )
            except Exception:
                pass

            return {
                "id": product_id,
                "aliexpress_id": product_id,
                "name": clean_text(name),
                "price": price,
                "image_url": image_url,
                "image_urls": [image_url] if image_url else [],
                "rating": rating,
                "orders": orders,
                "url": product_url,
                "category": category,
                "warehouse": "",
                "description": "",
                "specifications": {},
                "scraped_at": datetime.utcnow().isoformat(),
                "status": "scraped",
            }

        except Exception as e:
            logger.debug(f"Ürün çıkarma hatası: {e}")
            return None

    def _extract_product_id(self, url: str) -> str:
        """URL'den ürün ID'sini çıkarır."""
        try:
            # /item/1234567890.html formatı
            match = re.search(r'/item/(\d+)', url)
            if match:
                return match.group(1)

            # productId=123456 formatı
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if "productId" in params:
                return params["productId"][0]

            # Son çare: URL hash'i
            return f"ali_{abs(hash(url)) % 10**10}"

        except Exception:
            return ""

    def scrape_product_details(self, product_url: str) -> Dict:
        """Ürün detay sayfasından ek bilgi çeker."""
        details = {"description": "", "specifications": {}, "image_urls": [], "variants": []}

        try:
            self.initialize_driver()

            # Yeni sekme aç
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(product_url)

            time.sleep(3)

            # Açıklama
            try:
                desc_elem = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".product-description, [class*='description'], .detail-desc"
                )
                details["description"] = clean_text(desc_elem.text)
            except Exception:
                pass

            # Özellikler
            try:
                spec_rows = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ".specification-table tr, .product-property-list li, [class*='spec'] li"
                )
                for row in spec_rows:
                    try:
                        cells = row.find_elements(By.CSS_SELECTOR, "td, span, div")
                        if len(cells) >= 2:
                            key = clean_text(cells[0].text)
                            value = clean_text(cells[1].text)
                            if key and value:
                                details["specifications"][key] = value
                    except Exception:
                        continue
            except Exception:
                pass

            # Ek resimler
            try:
                images = self.driver.find_elements(
                    By.CSS_SELECTOR, ".images-view-item img, [class*='thumbnail'] img"
                )
                for img in images[:10]:
                    src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                    if src and src not in details["image_urls"]:
                        details["image_urls"].append(src)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Ürün detayı çekme hatası: {e}")

        finally:
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except Exception:
                pass

        return details

    def _simulate_scraping(
        self, category: str, min_rating: float, min_orders: int,
        warehouse: str, limit: int, offset: int, progress_callback=None
    ) -> List[Dict]:
        """Simülasyon modunda ürün verisi oluşturur."""
        logger.info(f"SİMÜLASYON: {category} kategorisinden {limit} ürün oluşturuluyor")

        sample_products = [
            "Kablosuz Bluetooth Kulaklık TWS Earbuds",
            "Akıllı Saat Fitness Tracker Su Geçirmez",
            "USB-C Hub Çoklu Port Adaptör",
            "LED Masa Lambası Şarj Edilebilir",
            "Mini Taşınabilir Hoparlör Bluetooth",
            "Telefon Tutucu Araç İçi Manyetik",
            "Powerbank 20000mAh Hızlı Şarj",
            "Kablosuz Mouse Ergonomik Sessiz",
            "Webcam 1080P HD Mikrofon",
            "Mekanik Klavye RGB Aydınlatmalı",
            "Akıllı Priz WiFi Uzaktan Kumanda",
            "Taşınabilir SSD 500GB USB 3.0",
            "Drone Mini HD Kamera 4K",
            "Action Kamera Su Geçirmez 4K",
            "Robot Süpürge Akıllı Navigasyon",
        ]

        products = []
        for i in range(limit):
            if self.should_stop:
                break

            product_id = f"sim_{offset + i + 1}_{int(time.time() * 1000) % 1000000}"
            base_name = random.choice(sample_products)

            price = round(random.uniform(2.0, 150.0), 2)
            rating = round(random.uniform(min_rating, 5.0), 1)
            orders = random.randint(min_orders, 10000)

            products.append({
                "id": product_id,
                "aliexpress_id": product_id,
                "name": f"{base_name} Model-{random.randint(100, 999)}",
                "price": price,
                "image_url": f"https://ae01.alicdn.com/kf/placeholder_{i+1}.jpg",
                "image_urls": [f"https://ae01.alicdn.com/kf/placeholder_{i+1}.jpg"],
                "rating": rating,
                "orders": orders,
                "url": f"https://www.aliexpress.com/item/{product_id}.html",
                "category": category,
                "warehouse": warehouse,
                "description": f"Yüksek kaliteli {base_name}. Profesyonel kullanım için tasarlanmış, dayanıklı ve uzun ömürlü bir üründür. Modern tasarımı ve üstün performansı ile fark yaratır.",
                "specifications": {
                    "Marka": "Generic",
                    "Malzeme": random.choice(["ABS", "Metal", "Silikon", "Plastik"]),
                    "Renk": random.choice(["Siyah", "Beyaz", "Gri", "Mavi"]),
                    "Garanti": "1 Yıl",
                },
                "scraped_at": datetime.utcnow().isoformat(),
                "status": "scraped",
            })

            if progress_callback and (i + 1) % 5 == 0:
                progress = min(100, (i + 1) / limit * 100)
                progress_callback(progress, f"{i + 1}/{limit} ürün oluşturuldu")

            time.sleep(0.02)

        logger.info(f"SİMÜLASYON: {len(products)} ürün oluşturuldu")
        return products
