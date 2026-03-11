"""
Walmart API Entegrasyonu
"""
import time
import base64
import hashlib
import hmac
import uuid
import logging
import requests
from typing import Tuple, Optional, List
from platforms.base_platform import BasePlatformAPI
from utils.helpers import generate_sku, retry

logger = logging.getLogger(__name__)


class WalmartAPI(BasePlatformAPI):
    """Walmart Marketplace API entegrasyonu."""
    PLATFORM_NAME = "walmart"
    BASE_URL = "https://marketplace.walmartapis.com/v3"

    def __init__(self, config=None):
        super().__init__(config)
        self.platform_config = self._get_platform_config()

    def authenticate(self) -> bool:
        try:
            client_id = self.platform_config.get("client_id", "")
            client_secret = self.platform_config.get("client_secret", "")
            if not client_id or not client_secret:
                return False

            timestamp = str(int(time.time() * 1000))
            sig_string = f"{client_id}\n{timestamp}\n"
            signature = base64.b64encode(
                hmac.new(client_secret.encode(), sig_string.encode(), hashlib.sha256).digest()
            ).decode()

            resp = requests.post(
                f"{self.BASE_URL}/token",
                headers={
                    "WM_SVC.NAME": "Walmart Marketplace",
                    "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
                    "WM_SEC.TIMESTAMP": timestamp,
                    "WM_SEC.AUTH_SIGNATURE": signature,
                    "WM_CONSUMER.ID": client_id,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
                timeout=30,
            )
            resp.raise_for_status()
            token_data = resp.json()
            self._token = token_data["access_token"]
            self._token_expiry = time.time() + token_data.get("expires_in", 900) - 60
            self.is_authenticated = True
            logger.info("Walmart kimlik doğrulaması başarılı")
            return True
        except Exception as e:
            logger.error(f"Walmart auth hatası: {e}")
            return False

    def _get_headers(self) -> dict:
        if not self.is_authenticated or time.time() >= self._token_expiry:
            self.authenticate()
        return {
            "WM_SEC.ACCESS_TOKEN": self._token,
            "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
            "WM_SVC.NAME": "Walmart Marketplace",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @retry(max_retries=2, delay=2.0)
    def upload_product(self, product: dict) -> Tuple[bool, str]:
        try:
            self.rate_limit()
            sku = product.get("sku") or generate_sku(product.get("id", ""), "WMT")
            title = (product.get("formatted_title") or product.get("name", ""))[:200]
            description = product.get("formatted_description") or product.get("description", "")
            price = str(product.get("calculated_price") or product.get("new_price", "0")).replace("$", "")

            payload = {
                "sku": sku,
                "productName": title,
                "longDescription": description,
                "price": price,
                "productImageUrls": {"productImageUrl": product.get("image_url", "")},
                "ShippingWeight": product.get("weight", 1.0),
                "brand": product.get("brand", "Generic"),
                "fulfillmentLagTime": 3,
            }

            resp = requests.post(
                f"{self.BASE_URL}/items",
                headers=self._get_headers(),
                json=payload,
                timeout=30,
            )
            if resp.status_code in [200, 201]:
                feed_id = resp.json().get("feedId", sku)
                logger.info(f"Walmart'a yüklendi: {feed_id}")
                return True, feed_id
            return False, f"Walmart hatası: {resp.status_code} - {resp.text[:200]}"
        except Exception as e:
            return False, f"Walmart hatası: {str(e)}"

    def update_product(self, listing_id: str, product: dict) -> Tuple[bool, str]:
        try:
            self.rate_limit()
            resp = requests.put(
                f"{self.BASE_URL}/items/{listing_id}",
                headers=self._get_headers(),
                json=product,
                timeout=30,
            )
            return (True, listing_id) if resp.status_code in [200, 204] else (False, f"Hata: {resp.status_code}")
        except Exception as e:
            return False, str(e)

    def delete_product(self, listing_id: str) -> Tuple[bool, str]:
        try:
            self.rate_limit()
            resp = requests.delete(
                f"{self.BASE_URL}/items/{listing_id}",
                headers=self._get_headers(),
                timeout=30,
            )
            return (True, listing_id) if resp.status_code in [200, 204] else (False, f"Hata: {resp.status_code}")
        except Exception as e:
            return False, str(e)

    def get_product(self, listing_id: str) -> Optional[dict]:
        try:
            self.rate_limit()
            resp = requests.get(f"{self.BASE_URL}/items/{listing_id}", headers=self._get_headers(), timeout=15)
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None

    def validate_config(self) -> Tuple[bool, List[str]]:
        errors = []
        for field in ["client_id", "client_secret"]:
            if not self.platform_config.get(field):
                errors.append(f"Walmart '{field}' zorunludur")
        return len(errors) == 0, errors
