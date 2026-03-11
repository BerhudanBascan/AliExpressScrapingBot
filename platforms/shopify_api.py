"""
Shopify API Entegrasyonu
Shopify Admin REST API ile ürün yönetimi.
"""

import logging
import requests
from typing import Tuple, Optional, List
from platforms.base_platform import BasePlatformAPI
from utils.helpers import generate_sku, retry

logger = logging.getLogger(__name__)


class ShopifyAPI(BasePlatformAPI):
    """Shopify Platform API entegrasyonu."""

    PLATFORM_NAME = "shopify"

    def __init__(self, config=None):
        super().__init__(config)
        self.platform_config = self._get_platform_config()

    def _get_base_url(self) -> str:
        shop_url = self.platform_config.get("shop_url", "")
        api_version = self.platform_config.get("api_version", "2024-01")
        api_key = self.platform_config.get("api_key", "")
        api_password = self.platform_config.get("api_password", "")
        return f"https://{api_key}:{api_password}@{shop_url}/admin/api/{api_version}"

    def authenticate(self) -> bool:
        """Shopify bağlantısını test eder."""
        try:
            resp = requests.get(
                f"{self._get_base_url()}/shop.json",
                timeout=15,
            )
            if resp.status_code == 200:
                self.is_authenticated = True
                shop_info = resp.json().get("shop", {})
                logger.info(f"Shopify bağlantısı kuruldu: {shop_info.get('name', '')}")
                return True
            logger.error(f"Shopify bağlantı hatası: {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"Shopify kimlik doğrulama hatası: {e}")
            return False

    @retry(max_retries=2, delay=2.0)
    def upload_product(self, product: dict) -> Tuple[bool, str]:
        """Ürünü Shopify'a yükler."""
        try:
            self.rate_limit()
            title = product.get("formatted_title") or product.get("name", "")
            description = product.get("formatted_description") or product.get("description", "")
            price = str(product.get("calculated_price") or product.get("new_price", "0")).replace("$", "")
            sku = product.get("sku") or generate_sku(product.get("id", ""), "SHOP")

            payload = {
                "product": {
                    "title": title,
                    "body_html": description,
                    "vendor": product.get("vendor", "Dropship Store"),
                    "product_type": product.get("category", ""),
                    "tags": ", ".join(product.get("keywords", product.get("tags", []))),
                    "status": "draft",
                    "variants": [{
                        "price": price,
                        "sku": sku,
                        "inventory_management": "shopify",
                        "inventory_quantity": 10,
                        "weight": product.get("weight", 0.5),
                        "weight_unit": "kg",
                    }],
                    "images": [{"src": url} for url in (product.get("image_urls", []) or [product.get("image_url", "")]) if url],
                }
            }

            resp = requests.post(
                f"{self._get_base_url()}/products.json",
                json=payload,
                timeout=30,
            )

            if resp.status_code in [200, 201]:
                product_id = str(resp.json().get("product", {}).get("id", ""))
                logger.info(f"Shopify'a yüklendi: {product_id}")
                return True, product_id
            return False, f"Shopify yükleme hatası: {resp.status_code} - {resp.text[:200]}"

        except Exception as e:
            return False, f"Shopify hatası: {str(e)}"

    def update_product(self, listing_id: str, product: dict) -> Tuple[bool, str]:
        """Shopify'daki ürünü günceller."""
        try:
            self.rate_limit()
            update_data = {"product": {"id": int(listing_id)}}

            if "name" in product:
                update_data["product"]["title"] = product["name"]
            if "description" in product:
                update_data["product"]["body_html"] = product["description"]
            if "calculated_price" in product:
                update_data["product"]["variants"] = [{
                    "price": str(product["calculated_price"]).replace("$", "")
                }]

            resp = requests.put(
                f"{self._get_base_url()}/products/{listing_id}.json",
                json=update_data,
                timeout=30,
            )
            if resp.status_code == 200:
                return True, listing_id
            return False, f"Güncelleme hatası: {resp.status_code}"
        except Exception as e:
            return False, str(e)

    def delete_product(self, listing_id: str) -> Tuple[bool, str]:
        """Shopify'dan ürün siler."""
        try:
            self.rate_limit()
            resp = requests.delete(
                f"{self._get_base_url()}/products/{listing_id}.json",
                timeout=30,
            )
            if resp.status_code == 200:
                return True, listing_id
            return False, f"Silme hatası: {resp.status_code}"
        except Exception as e:
            return False, str(e)

    def get_product(self, listing_id: str) -> Optional[dict]:
        """Shopify'dan ürün bilgisi alır."""
        try:
            self.rate_limit()
            resp = requests.get(
                f"{self._get_base_url()}/products/{listing_id}.json",
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json().get("product")
            return None
        except Exception:
            return None

    def get_products_count(self) -> int:
        """Shopify'daki toplam ürün sayısını döndürür."""
        try:
            resp = requests.get(
                f"{self._get_base_url()}/products/count.json",
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json().get("count", 0)
            return 0
        except Exception:
            return 0

    def validate_config(self) -> Tuple[bool, List[str]]:
        errors = []
        for field in ["shop_url", "api_key", "api_password"]:
            if not self.platform_config.get(field):
                errors.append(f"Shopify '{field}' zorunludur")
        shop_url = self.platform_config.get("shop_url", "")
        if shop_url and not shop_url.endswith(".myshopify.com"):
            errors.append("Shop URL '.myshopify.com' ile bitmelidir")
        return len(errors) == 0, errors
