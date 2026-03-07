import logging
import random
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import threading
import json
from urllib.parse import urlparse, parse_qs

class AliExpressScraper:
    """AliExpress ürünleri için gerçek çekme aracı."""
    
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.driver = None
        self.driver_lock = threading.Lock()
        
        # Kategori URL'leri
        self.category_urls = {
            "Apparel & Accessories": "https://www.aliexpress.com/category/200000875/apparel-accessories.html",
            "Automobiles & Motorcycles": "https://www.aliexpress.com/category/34/automobiles-motorcycles.html",
            "Baby Products": "https://www.aliexpress.com/category/1501/mother-kids.html",
            "Beauty & Health": "https://www.aliexpress.com/category/66/beauty-health.html",
            "Computer & Office": "https://www.aliexpress.com/category/7/computer-office.html",
            "Consumer Electronics": "https://www.aliexpress.com/category/44/consumer-electronics.html",
            "Electrical Equipment & Supplies": "https://www.aliexpress.com/category/5/electrical-equipment-supplies.html",
            "Furniture": "https://www.aliexpress.com/category/1503/furniture.html",
            "Hair Extensions & Wigs": "https://www.aliexpress.com/category/200003567/hair-extensions-wigs.html",
            "Home & Garden": "https://www.aliexpress.com/category/15/home-garden.html",
            "Home Appliances": "https://www.aliexpress.com/category/6/home-appliances.html",
            "Home Improvement": "https://www.aliexpress.com/category/13/home-improvement.html",
            "Jewelry & Accessories": "https://www.aliexpress.com/category/1509/jewelry-accessories.html",
            "Lights & Lighting": "https://www.aliexpress.com/category/39/lights-lighting.html",
            "Luggage & Bags": "https://www.aliexpress.com/category/1524/luggage-bags.html",
            "Men's Clothing": "https://www.aliexpress.com/category/100003070/men-clothing.html",
            "Mother & Kids": "https://www.aliexpress.com/category/1501/mother-kids.html",
            "Office & School Supplies": "https://www.aliexpress.com/category/21/office-school-supplies.html",
            "Phones & Telecommunications": "https://www.aliexpress.com/category/509/phones-telecommunications.html",
            "Security & Protection": "https://www.aliexpress.com/category/30/security-protection.html",
            "Shoes": "https://www.aliexpress.com/category/322/shoes.html",
            "Sports & Entertainment": "https://www.aliexpress.com/category/18/sports-entertainment.html",
            "Tools": "https://www.aliexpress.com/category/1420/tools.html",
            "Toys & Hobbies": "https://www.aliexpress.com/category/26/toys-hobbies.html",
            "Watches": "https://www.aliexpress.com/category/1511/watches.html",
            "Weddings & Events": "https://www.aliexpress.com/category/200003361/weddings-events.html",
            "Women's Clothing": "https://www.aliexpress.com/category/100003109/women-clothing.html"
        }
        
        # Kullanıcı ajanları
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        ]
    
    def get_category_url(self, category):
        """Belirli bir kategori için URL alır."""
        if category in self.category_urls:
            return self.category_urls[category]
        else:
            raise ValueError(f"Bilinmeyen kategori: {category}")
    
    def _get_user_agent(self):
        """Rastgele bir kullanıcı ajanı döndürür."""
        return random.choice(self.user_agents)
    
    def _get_proxy(self):
        """Proxy listesinden rastgele bir proxy döndürür."""
        proxies = self.config.get("proxies", "proxy_list", [])
        
        if not proxies:
            return None
            
        return random.choice(proxies)
    
    def _initialize_driver(self):
        """Selenium web sürücüsünü başlatır."""
        with self.driver_lock:
            if self.driver is None:
                try:
                    chrome_options = Options()
                    
                    # Başsız mod (isteğe bağlı)
                    if not self.config.get("scraping", "headless", False):
                        chrome_options.add_argument("--headless")
                    
                    chrome_options.add_argument("--disable-gpu")
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--window-size=1920,1080")
                    
                    # Kullanıcı ajanı
                    user_agent = self._get_user_agent()
                    chrome_options.add_argument(f"--user-agent={user_agent}")
                    
                    # Proxy (isteğe bağlı)
                    if self.config.get("scraping", "use_proxies", False):
                        proxy = self._get_proxy()
                        if proxy:
                            chrome_options.add_argument(f'--proxy-server={proxy}')
                    
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    self.logger.info("Selenium web sürücüsü başlatıldı")
                except Exception as e:
                    self.logger.error(f"Web sürücüsü başlatılırken hata: {str(e)}")
                    raise
    
    def _close_driver(self):
        """Selenium web sürücüsünü kapatır."""
        with self.driver_lock:
            if self.driver is not None:
                try:
                    self.driver.quit()
                    self.driver = None
                    self.logger.info("Selenium web sürücüsü kapatıldı")
                except Exception as e:
                    self.logger.error(f"Web sürücüsü kapatılırken hata: {str(e)}")
    
    def scrape_products(self, category_url, min_rating=4.5, min_orders=300, warehouse="US", limit=100, offset=0):
        """
        AliExpress'ten ürünleri çeker.
        
        Args:
            category_url: Çekilecek kategorinin URL'si
            min_rating: Minimum ürün puanı (varsayılan: 4.5)
            min_orders: Minimum sipariş sayısı (varsayılan: 300)
            warehouse: Depo konumu (varsayılan: "US")
            limit: Çekilecek maksimum ürün sayısı (varsayılan: 100)
            offset: Başlangıç ofset değeri (varsayılan: 0)
            
        Returns:
            Ürün sözlüklerinin listesi
        """
        self.logger.info(f"Ürünler çekiliyor: {category_url}, limit: {limit}, offset: {offset}")
        
        try:
            self._initialize_driver()
            
            # URL'ye parametreler ekle
            page = offset // 60 + 1  # AliExpress'te her sayfada yaklaşık 60 ürün var
            url = f"{category_url}?shipFromCountry={warehouse}&page={page}"
            
            with self.driver_lock:
                self.driver.get(url)
                
                # Sayfanın yüklenmesini bekle
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".product-card, .product-item, ._3t7zg"))
                )
                
                # Ürün kartlarını bul (AliExpress'in yapısına göre seçicileri güncelle)
                product_cards = self.driver.find_elements(By.CSS_SELECTOR, ".product-card, .product-item, ._3t7zg")
                
                self.logger.info(f"{len(product_cards)} ürün kartı bulundu")
                
                products = []
                count = 0
                
                for card in product_cards:
                    if count >= limit:
                        break
                    
                    try:
                        # Ürün bilgilerini çıkar (AliExpress'in yapısına göre seçicileri güncelle)
                        
                        # Ürün ID'si
                        product_id = card.get_attribute("data-product-id")
                        if not product_id:
                            # ID bulunamadıysa, URL'den çıkarmayı dene
                            link_elem = card.find_element(By.CSS_SELECTOR, "a")
                            product_url = link_elem.get_attribute("href")
                            parsed_url = urlparse(product_url)
                            query_params = parse_qs(parsed_url.query)
                            product_id = query_params.get("productId", [""])[0]
                        
                        # Ürün adı
                        name_elem = card.find_element(By.CSS_SELECTOR, ".product-title, .item-title, ._18_85")
                        name = name_elem.text
                        
                        # Fiyat
                        price_elem = card.find_element(By.CSS_SELECTOR, ".product-price, .price-current, ._12A8D")
                        price = price_elem.text.strip()
                        if not price.startswith("$"):
                            price = "$" + price
                        
                        # Puan
                        try:
                            rating_elem = card.find_element(By.CSS_SELECTOR, ".rating-value, .product-rating, ._1hEhM")
                            rating_text = rating_elem.text.strip()
                            rating = float(rating_text.split()[0])
                        except:
                            rating = 0.0
                        
                        # Sipariş sayısı
                        try:
                            orders_elem = card.find_element(By.CSS_SELECTOR, ".order-count, .product-orders, ._2i3yD")
                            orders_text = orders_elem.text.strip()
                            orders = int(''.join(filter(str.isdigit, orders_text)))
                        except:
                            orders = 0
                        
                        # Minimum değerleri karşılıyorsa ekle
                        if rating >= min_rating and orders >= min_orders:
                            # Resim URL'si
                            try:
                                img_elem = card.find_element(By.CSS_SELECTOR, "img")
                                image_url = img_elem.get_attribute("src")
                                if not image_url:
                                    image_url = img_elem.get_attribute("data-src")
                            except:
                                image_url = ""
                            
                            # Ürün URL'si
                            try:
                                link_elem = card.find_element(By.CSS_SELECTOR, "a")
                                product_url = link_elem.get_attribute("href")
                            except:
                                product_url = f"https://www.aliexpress.com/item/{product_id}.html"
                            
                            # Kategori adını URL'den çıkar
                            category_name = category_url.split("/")[-1].replace(".html", "").replace("-", " ").title()
                            
                            # Ürün detaylarını çek
                            product_details = self._get_product_details(product_url)
                            
                            products.append({
                                "id": product_id,
                                "name": name,
                                "price": price,
                                "image_url": image_url,
                                "rating": rating,
                                "orders": orders,
                                "description": product_details.get("description", ""),
                                "url": product_url,
                                "category": category_name,
                                "warehouse": warehouse,
                                "specifications": product_details.get("specifications", {})
                            })
                            
                            count += 1
                            
                            # Her ürün sonrası kısa bir bekleme
                            time.sleep(0.2)
                    
                    except Exception as e:
                        self.logger.warning(f"Ürün çekilirken hata: {str(e)}")
                
                self.logger.info(f"{len(products)} ürün başarıyla çekildi")
                return products
                
        except Exception as e:
            self.logger.error(f"Web scraping sırasında hata: {str(e)}")
            return []
        
        finally:
            # Sürücüyü kapat (isteğe bağlı, sürekli açık tutmak daha hızlı olabilir)
            # self._close_driver()
            pass
    
    def _get_product_details(self, product_url):
        """Ürün detay sayfasından ek bilgileri çeker."""
        try:
            with self.driver_lock:
                # Yeni bir sekme aç
                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[1])
                
                # Ürün sayfasını yükle
                self.driver.get(product_url)
                
                # Sayfanın yüklenmesini bekle
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".product-description, .product-detail, .detail-tab"))
                )
                
                # Açıklama
                description = ""
                try:
                    description_elem = self.driver.find_element(By.CSS_SELECTOR, ".product-description, .product-detail-description, ._1ukrU")
                    description = description_elem.text
                except:
                    pass
                
                # Özellikler
                specs = {}
                try:
                    spec_elems = self.driver.find_elements(By.CSS_SELECTOR, ".specification-table tr, .product-specs-list li, ._3_Tg4")
                    for spec in spec_elems:
                        try:
                            key_elem = spec.find_element(By.CSS_SELECTOR, "th, .spec-name, ._2jz4S")
                            value_elem = spec.find_element(By.CSS_SELECTOR, "td, .spec-value, ._34iqA")
                            
                            key = key_elem.text.strip()
                            value = value_elem.text.strip()
                            
                            if key and value:
                                specs[key] = value
                        except:
                            pass
                except:
                    pass
                
                # Sekmeyi kapat ve ana sekmeye geri dön
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                
                return {
                    "description": description,
                    "specifications": specs
                }
                
        except Exception as e:
            self.logger.error(f"Ürün detayları çekilirken hata: {str(e)}")
            
            # Hata durumunda ana sekmeye geri dönmeye çalış
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
                
            return {"description": "", "specifications": {}}