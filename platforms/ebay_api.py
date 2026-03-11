"""
eBay API Entegrasyonu
eBay Inventory API ve Offer API ile ürün yönetimi.
"""

import time
import base64
import logging
import requests
from typing import Tuple, Optional, List, Dict
from datetime import datetime, timedelta

from platforms.base_platform import BasePlatformAPI
from utils.helpers import generate_sku, retry

logger = logging.getLogger(__name__)


class eBayAPI(BasePlatformAPI):
    """eBay Platform API entegrasyonu."""

    PLATFORM_NAME = "ebay"

    # API Endpoints
    SANDBOX_URL = "https://api.sandbox.ebay.com"
    PRODUCTION_URL = "https://api.ebay.com"

    def __init__(self, config=None):
        super().__init__(config)
        self.platform_config = self._get_platform_config()
        self.is_sandbox = self.platform_config.get("sandbox", True)
        self.base_url = self.SANDBOX_URL if self.is_sandbox else self.PRODUCTION_URL

    def authenticate(self) -> bool:
        """eBay OAuth token alır."""
        try:
            client_id = self.platform_config.get("client_id", "")
            client_secret = self.platform_config.get("client_secret", "")
            refresh_token = self.platform_config.get("refresh_token", "")

            if not all([client_id, client_secret, refresh_token]):
                logger.warning("eBay API bilgileri eksik")
                return False

            auth_header = base64.b64encode(
                f"{client_id}:{client_secret}".encode()
            ).decode()

            response = requests.post(
                f"{self.base_url}/identity/v1/oauth2/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {auth_header}",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "scope": "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory",
                },
                timeout=30,
            )
            response.raise_for_status()

            token_data = response.json()
            self._token = token_data["access_token"]
            self._token_expiry = time.time() + token_data.get("expires_in", 7200) - 300
            self.is_authenticated = True

            logger.info("eBay kimlik doğrulaması başarılı")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"eBay kimlik doğrulama hatası: {e}")
            return False

    def _ensure_authenticated(self):
        """Token geçerliliğini kontrol eder."""
        if not self.is_authenticated or time.time() >= self._token_expiry:
            self.authenticate()

    def _get_headers(self) -> dict:
        """API başlıklarını döndürür."""
        self._ensure_authenticated()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @retry(max_retries=2, delay=2.0)
    def upload_product(self, product: dict) -> Tuple[bool, str]:
        """Ürünü eBay'e yükler."""
        try:
            self.rate_limit()
            headers = self._get_headers()

            sku = product.get("sku") or generate_sku(product.get("id", ""), "EBAY")
            title = (product.get("formatted_title") or product.get("name", ""))[:80]
            description = product.get("formatted_description") or product.get("description", "")
            price = str(product.get("calculated_price") or product.get("new_price", "0")).replace("$", "")
            image_url = product.get("image_url", "")

            # 1. Inventory Item Oluştur
            inventory_payload = {
                "product": {
                    "title": title,
                    "description": description,
                    "imageUrls": [image_url] if image_url else [],
                    "aspects": self._build_aspects(product),
                },
                "availability": {
                    "shipToLocationAvailability": {"quantity": 10}
                },
                "condition": "NEW",
            }

            resp = requests.put(
                f"{self.base_url}/sell/inventory/v1/inventory_item/{sku}",
                headers=headers,
                json=inventory_payload,
                timeout=30,
            )

            if resp.status_code not in [200, 201, 204]:
                return False, f"Envanter hatası: {resp.status_code} - {resp.text[:200]}"

            # 2. Offer Oluştur
            marketplace = self.platform_config.get("marketplace_id", "EBAY_US")
            offer_payload = {
                "sku": sku,
                "marketplaceId": marketplace,
                "format": "FIXED_PRICE",
                "availableQuantity": 10,
                "categoryId": product.get("ebay_category_id", "9355"),
                "listingDescription": description,
                "pricingSummary": {
                    "price": {"currency": "USD", "value": price}
                },
                "merchantLocationKey": "default",
            }

            resp = requests.post(
                f"{self.base_url}/sell/inventory/v1/offer",
                headers=headers,
                json=offer_payload,
                timeout=30,
            )

            if resp.status_code not in [200, 201]:
                return False, f"Teklif hatası: {resp.status_code} - {resp.text[:200]}"

            offer_id = resp.json().get("offerId", "")

            # 3. Teklifi Yayınla
            resp = requests.post(
                f"{self.base_url}/sell/inventory/v1/offer/{offer_id}/publish",
                headers=headers,
                timeout=30,
            )

            if resp.status_code not in [200, 201]:
                return False, f"Yayınlama hatası: {resp.status_code} - {resp.text[:200]}"

            listing_id = resp.json().get("listingId", offer_id)
            logger.info(f"eBay'e yüklendi: {listing_id}")
            return True, listing_id

        except requests.exceptions.RequestException as e:
            return False, f"eBay API hatası: {str(e)}"
        except Exception as e:
            return False, f"eBay yükleme hatası: {str(e)}"

    def update_product(self, listing_id: str, product: dict) -> Tuple[bool, str]:
        """eBay'deki ürünü günceller."""
        try:
            self.rate_limit()
            headers = self._get_headers()

            update_data = {}
            if "calculated_price" in product:
                update_data["pricingSummary"] = {
                    "price": {
                        "currency": "USD",
                        "value": str(product["calculated_price"]).replace("$", "")
                    }
                }
            if "quantity" in product:
                update_data["availableQuantity"] = product["quantity"]

            if update_data:
                resp = requests.put(
                    f"{self.base_url}/sell/inventory/v1/offer/{listing_id}",
                    headers=headers,
                    json=update_data,
                    timeout=30,
                )
                if resp.status_code not in [200, 204]:
                    return False, f"Güncelleme hatası: {resp.status_code}"

            return True, listing_id
        except Exception as e:
            return False, str(e)

    def delete_product(self, listing_id: str) -> Tuple[bool, str]:
        """eBay'den ürün siler."""
        try:
            self.rate_limit()
            headers = self._get_headers()

            resp = requests.delete(
                f"{self.base_url}/sell/inventory/v1/offer/{listing_id}",
                headers=headers,
                timeout=30,
            )
            if resp.status_code in [200, 204]:
                return True, listing_id
            return False, f"Silme hatası: {resp.status_code}"
        except Exception as e:
            return False, str(e)

    def get_product(self, listing_id: str) -> Optional[dict]:
        """eBay'den ürün bilgisi alır."""
        try:
            self.rate_limit()
            headers = self._get_headers()

            resp = requests.get(
                f"{self.base_url}/sell/inventory/v1/offer/{listing_id}",
                headers=headers,
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    def _build_aspects(self, product: dict) -> dict:
        """eBay ürün özelliklerini oluşturur."""
        aspects = {}
        specs = product.get("specifications", {})
        for key, value in specs.items():
            aspect_key = key.title().replace(" ", "")
            aspects[aspect_key] = [str(value)]
        return aspects

    def validate_config(self) -> Tuple[bool, List[str]]:
        """eBay konfigürasyonunu doğrular."""
        errors = []
        required = ["client_id", "client_secret", "refresh_token"]
        for field in required:
            if not self.platform_config.get(field):
                errors.append(f"eBay '{field}' zorunludur")
        return len(errors) == 0, errors
