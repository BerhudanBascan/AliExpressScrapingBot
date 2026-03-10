import logging
import time
import random
import threading
import requests
import json
import base64
import hmac
import hashlib
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

class PlatformAPI:
    """Çeşitli e-ticaret platformlarına API entegrasyonu sağlayan sınıf."""
    
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.lock = threading.Lock()
        
        # API token'ları ve oturum bilgileri
        self.tokens = {}
        
        # API token'larını yükle
        self._load_tokens()
    
    def _load_tokens(self):
        """API token'larını yükler veya yeniler."""
        try:
            # eBay token'ı
            if self.config.get("platforms", "ebay", {}).get("enabled", False):
                self._refresh_ebay_token()
            
            # Walmart token'ı
            if self.config.get("platforms", "walmart", {}).get("enabled", False):
                self._refresh_walmart_token()
            
            # Shopify token'ı (token yenileme gerekmez)
            if self.config.get("platforms", "shopify", {}).get("enabled", False):
                self.tokens["shopify"] = {
                    "api_key": self.config.get("platforms", "shopify", {}).get("api_key", ""),
                    "api_password": self.config.get("platforms", "shopify", {}).get("api_password", ""),
                    "shop_url": self.config.get("platforms", "shopify", {}).get("shop_url", "")
                }
            
            self.logger.info("API token'ları yüklendi")
            
        except Exception as e:
            self.logger.error(f"API token'ları yüklenirken hata: {str(e)}")
    
    def _refresh_ebay_token(self):
        """eBay API için OAuth token alır veya yeniler."""
        try:
            ebay_config = self.config.get("platforms", "ebay", {})
            client_id = ebay_config.get("client_id", "")
            client_secret = ebay_config.get("client_secret", "")
            refresh_token = ebay_config.get("refresh_token", "")
            
            if not client_id or not client_secret or not refresh_token:
                self.logger.warning("eBay API bilgileri eksik")
                return
            
            auth_url = "https://api.ebay.com/identity/v1/oauth2/token"
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()}"
            }
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory"
            }
            
            response = requests.post(auth_url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            self.tokens["ebay"] = {
                "access_token": token_data["access_token"],
                "expires_at": datetime.now() + timedelta(seconds=token_data["expires_in"] - 300)  # 5 dakika önce sona ersin
            }
            
            self.logger.info("eBay token'ı yenilendi")
            
        except Exception as e:
            self.logger.error(f"eBay token'ı yenilenirken hata: {str(e)}")
    
    def _refresh_walmart_token(self):
        """Walmart API için token alır."""
        try:
            walmart_config = self.config.get("platforms", "walmart", {})
            client_id = walmart_config.get("client_id", "")
            client_secret = walmart_config.get("client_secret", "")
            
            if not client_id or not client_secret:
                self.logger.warning("Walmart API bilgileri eksik")
                return
            
            auth_url = "https://marketplace.walmartapis.com/v3/token"
            
            # Walmart'ın istediği özel imza
            timestamp = str(int(time.time() * 1000))
            signature = base64.b64encode(hmac.new(
                client_secret.encode(),
                f"{client_id}\n{timestamp}\n".encode(),
                hashlib.sha256
            ).digest()).decode()
            
            headers = {
                "WM_SVC.NAME": "Walmart Marketplace",
                "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
                "WM_SEC.TIMESTAMP": timestamp,
                "WM_SEC.AUTH_SIGNATURE": signature,
                "WM_CONSUMER.ID": client_id,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "client_credentials"
            }
            
            response = requests.post(auth_url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            self.tokens["walmart"] = {
                "access_token": token_data["access_token"],
                "expires_at": datetime.now() + timedelta(seconds=token_data["expires_in"] - 300)  # 5 dakika önce sona ersin
            }
            
            self.logger.info("Walmart token'ı alındı")
            
        except Exception as e:
            self.logger.error(f"Walmart token'ı alınırken hata: {str(e)}")
    
    def _check_and_refresh_token(self, platform):
        """Token'ın geçerliliğini kontrol eder ve gerekirse yeniler."""
        with self.lock:
            if platform not in self.tokens:
                if platform == "ebay":
                    self._refresh_ebay_token()
                elif platform == "walmart":
                    self._refresh_walmart_token()
                return
            
            # Token süresi dolmuş mu kontrol et
            if platform in ["ebay", "walmart"]:
                if datetime.now() >= self.tokens[platform].get("expires_at", datetime.now()):
                    if platform == "ebay":
                        self._refresh_ebay_token()
                    elif platform == "walmart":
                        self._refresh_walmart_token()
    
    def upload_to_ebay(self, product):
        """
        Ürünü eBay'e yükler.
        
        Args:
            product: Ürün bilgilerini içeren sözlük
            
        Returns:
            (başarı durumu, hata mesajı veya ürün ID'si)
        """
        try:
            self._check_and_refresh_token("ebay")
            
            if "ebay" not in self.tokens:
                return False, "eBay token'ı bulunamadı"
            
            # eBay API endpoint'i
            inventory_url = "https://api.ebay.com/sell/inventory/v1/inventory_item"
            offer_url = "https://api.ebay.com/sell/inventory/v1/offer"
            
            # Benzersiz SKU oluştur
            sku = f"ALI-{product['id']}-{int(time.time())}"
            
            # Ürün başlığını ve açıklamasını hazırla
            title = product.get("formatted_title", product.get("name", ""))[:80]
            description = product.get("formatted_description", product.get("description", ""))
            
            # Envanter öğesi oluştur
            inventory_payload = {
                "sku": sku,
                "product": {
                    "title": title,
                    "description": description,
                    "aspects": {},
                    "imageUrls": [product.get("image_url", "")]
                },
                "availability": {
                    "shipToLocationAvailability": {
                        "quantity": 10
                    }
                },
                "condition": "NEW"
            }
            
            # Ürün özelliklerini ekle
            if "specifications" in product and product["specifications"]:
                aspects = {}
                for key, value in product["specifications"].items():
                    # eBay'in beklediği formata dönüştür
                    aspect_key = key.title().replace(" ", "")
                    aspects[aspect_key] = [value]
                
                inventory_payload["product"]["aspects"] = aspects
            
            # Envanter öğesini oluştur
            headers = {
                "Authorization": f"Bearer {self.tokens['ebay']['access_token']}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            response = requests.put(
                f"{inventory_url}/{sku}",
                headers=headers,
                json=inventory_payload
            )
            
            if response.status_code not in [200, 201, 204]:
                error_msg = f"eBay envanter öğesi oluşturma hatası: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # Fiyatı hazırla
            price = product.get("new_price", "").replace("$", "")
            if not price:
                price = "29.99"  # Varsayılan fiyat
            
            # Teklif oluştur
            offer_payload = {
                "sku": sku,
                "marketplaceId": "EBAY_US",
                "format": "FIXED_PRICE",
                "availableQuantity": 10,
                "categoryId": "9355",  # Varsayılan kategori (güncellenmeli)
                "listingDescription": description,
                "listingPolicies": {
                    "fulfillmentPolicies": [
                        {
                            "fulfillmentPolicyId": "3*********7"  # Gerçek politika ID'si ile değiştirilmeli
                        }
                    ],
                    "paymentPolicies": [
                        {
                            "paymentPolicyId": "3*********8"  # Gerçek politika ID'si ile değiştirilmeli
                        }
                    ],
                    "returnPolicies": [
                        {
                            "returnPolicyId": "3*********9"  # Gerçek politika ID'si ile değiştirilmeli
                        }
                    ]
                },
                "pricingSummary": {
                    "price": {
                        "currency": "USD",
                        "value": price
                    }
                },
                "merchantLocationKey": "default"
            }
            
            # Teklifi oluştur
            response = requests.post(
                offer_url,
                headers=headers,
                json=offer_payload
            )
            
            if response.status_code not in [200, 201]:
                error_msg = f"eBay teklif oluşturma hatası: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return False, error_msg
            
            offer_id = response.json().get("offerId")
            
            # Teklifi yayınla
            publish_url = f"{offer_url}/{offer_id}/publish"
            response = requests.post(publish_url, headers=headers)
            
            if response.status_code not in [200, 201]:
                error_msg = f"eBay teklif yayınlama hatası: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return False, error_msg
            
            listing_id = response.json().get("listingId")
            
            self.logger.info(f"Ürün eBay'e başarıyla yüklendi: {listing_id}")
            return True, listing_id
            
        except Exception as e:
            error_msg = f"eBay'e yükleme sırasında hata: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def upload_to_walmart(self, product):
        """
        Ürünü Walmart'a yükler.
        
        Args:
            product: Ürün bilgilerini içeren sözlük
            
        Returns:
            (başarı durumu, hata mesajı veya ürün ID'si)
        """
        try:
            self._check_and_refresh_token("walmart")
            
            if "walmart" not in self.tokens:
                return False, "Walmart token'ı bulunamadı"
            
            # Walmart API endpoint'i
            items_url = "https://marketplace.walmartapis.com/v3/items"
            
            # Benzersiz SKU oluştur
            sku = f"ALI-{product['id']}-{int(time.time())}"
            
            # Ürün başlığını ve açıklamasını hazırla
            title = product.get("formatted_title", product.get("name", ""))[:200]
            description = product.get("formatted_description", product.get("description", ""))
            
            # Fiyatı hazırla
            price = product.get("new_price", "").replace("$", "")
            if not price:
                price = "29.99"  # Varsayılan fiyat
            
            # Walmart API için ürün verilerini hazırla
            payload = {
                "sku": sku,
                "productName": title,
                "longDescription": description,
                "price": price,
                "productIdentifiers": {
                    "productIdType": "UPC",
                    "productId": "123456789012"  # Gerçek UPC ile değiştirilmeli
                },
                "productImageUrls": {
                    "productImageUrl": product.get("image_url", "")
                },
                "ShippingWeight": 1.0,
                "brand": "Generic",
                "fulfillmentLagTime": 3
            }
            
            # API çağrısı
            headers = {
                "WM_SEC.ACCESS_TOKEN": self.tokens["walmart"]["access_token"],
                "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
                "WM_SVC.NAME": "Walmart Marketplace",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            response = requests.post(items_url, headers=headers, json=payload)
            
            if response.status_code not in [200, 201]:
                error_msg = f"Walmart ürün yükleme hatası: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # Walmart genellikle bir işlem ID'si döndürür
            result = response.json()
            feed_id = result.get("feedId", "")
            
            self.logger.info(f"Ürün Walmart'a başarıyla gönderildi: {feed_id}")
            return True, feed_id
            
        except Exception as e:
            error_msg = f"Walmart'a yükleme sırasında hata: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def upload_to_shopify(self, product):
        """
        Ürünü Shopify'a yükler.
        
        Args:
            product: Ürün bilgilerini içeren sözlük
            
        Returns:
            (başarı durumu, hata mesajı veya ürün ID'si)
        """
        try:
            if "shopify" not in self.tokens:
                return False, "Shopify bilgileri bulunamadı"
            
            shop_url = self.tokens["shopify"]["shop_url"]
            api_key = self.tokens["shopify"]["api_key"]
            api_password = self.tokens["shopify"]["api_password"]
            
            if not shop_url or not api_key or not api_password:
                return False, "Shopify API bilgileri eksik"
            
            # Shopify API endpoint'i
            products_url = f"https://{api_key}:{api_password}@{shop_url}/admin/api/2023-01/products.json"
            
            # Ürün başlığını ve açıklamasını hazırla
            title = product.get("formatted_title", product.get("name", ""))
            description = product.get("formatted_description", product.get("description", ""))
            
            # Fiyatı hazırla
            price = product.get("new_price", "").replace("$", "")
            if not price:
                price = "29.99"  # Varsayılan fiyat
            
            # Shopify API için ürün verilerini hazırla
            payload = {
                "product": {
                    "title": title,
                    "body_html": f"<p>{description}</p>",
                    "vendor": "AliExpress",
                    "product_type": product.get("category", ""),
                    "tags": product.get("keywords", []),
                    "variants": [
                        {
                            "price": price,
                            "sku": f"ALI-{product['id']}",
                            "inventory_management": "shopify",
                            "inventory_quantity": 10
                        }
                    ],
                    "images": [
                        {
                            "src": product.get("image_url", "")
                        }
                    ]
                }
            }
            
            # API çağrısı
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            response = requests.post(products_url, headers=headers, json=payload)
            
            if response.status_code not in [200, 201]:
                error_msg = f"Shopify ürün yükleme hatası: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # Shopify ürün ID'sini al
            result = response.json()
            product_id = result.get("product", {}).get("id", "")
            
            self.logger.info(f"Ürün Shopify'a başarıyla yüklendi: {product_id}")
            return True, product_id
            
        except Exception as e:
            error_msg = f"Shopify'a yükleme sırasında hata: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def upload_product(self, platform, product):
        """
        Ürünü belirtilen platforma yükler.
        
        Args:
            platform: Platform adı (ebay, walmart, shopify)
            product: Ürün bilgilerini içeren sözlük
            
        Returns:
            (başarı durumu, hata mesajı veya ürün ID'si)
        """
        if platform.lower() == "ebay":
            return self.upload_to_ebay(product)
        elif platform.lower() == "walmart":
            return self.upload_to_walmart(product)
        elif platform.lower() == "shopify":
            return self.upload_to_shopify(product)
        else:
            return False, f"Desteklenmeyen platform: {platform}"