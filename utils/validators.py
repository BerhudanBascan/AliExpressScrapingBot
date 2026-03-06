"""
Veri Doğrulama Modülü
Ürün, fiyat ve API verilerinin doğrulanması.
"""

import re
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


class ProductValidator:
    """Ürün verilerini doğrular."""

    REQUIRED_FIELDS = ["name", "price", "id"]
    MAX_TITLE_LENGTH = 500
    MAX_DESCRIPTION_LENGTH = 50000

    @classmethod
    def validate(cls, product: dict) -> Tuple[bool, List[str]]:
        """Ürün verisini doğrular.

        Returns:
            (geçerli mi, hata mesajları listesi)
        """
        errors = []

        # Zorunlu alanlar
        for field in cls.REQUIRED_FIELDS:
            if not product.get(field):
                errors.append(f"'{field}' alanı zorunludur")

        # Başlık kontrolü
        name = product.get("name", "")
        if name and len(name) > cls.MAX_TITLE_LENGTH:
            errors.append(f"Başlık çok uzun ({len(name)} karakter, max: {cls.MAX_TITLE_LENGTH})")

        # Fiyat kontrolü
        price = product.get("price", "")
        if price:
            try:
                price_val = float(str(price).replace("$", "").replace(",", "."))
                if price_val <= 0:
                    errors.append("Fiyat sıfırdan büyük olmalıdır")
                if price_val > 100000:
                    errors.append("Fiyat çok yüksek görünüyor")
            except (ValueError, TypeError):
                errors.append(f"Geçersiz fiyat formatı: {price}")

        # URL kontrolü
        url = product.get("url", "")
        if url and not cls._is_valid_url(url):
            errors.append(f"Geçersiz URL: {url}")

        # Resim URL kontrolü
        image_url = product.get("image_url", "")
        if image_url and not cls._is_valid_url(image_url):
            errors.append(f"Geçersiz resim URL'si: {image_url}")

        # Rating kontrolü
        rating = product.get("rating")
        if rating is not None:
            try:
                rating_val = float(rating)
                if not (0 <= rating_val <= 5):
                    errors.append(f"Puan 0-5 arasında olmalıdır: {rating}")
            except (ValueError, TypeError):
                errors.append(f"Geçersiz puan: {rating}")

        return len(errors) == 0, errors

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """URL'nin geçerli olup olmadığını kontrol eder."""
        pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(pattern.match(url))


class PriceValidator:
    """Fiyat verilerini doğrular."""

    @staticmethod
    def validate_margin(margin: float) -> Tuple[bool, str]:
        """Kâr marjını doğrular."""
        if margin < 1.0:
            return False, "Kâr marjı 1.0'dan küçük olamaz"
        if margin > 20.0:
            return False, "Kâr marjı 20.0'dan büyük olamaz"
        return True, ""

    @staticmethod
    def validate_price_range(min_price: float, max_price: float) -> Tuple[bool, str]:
        """Fiyat aralığını doğrular."""
        if min_price < 0:
            return False, "Minimum fiyat negatif olamaz"
        if max_price <= min_price:
            return False, "Maksimum fiyat, minimum fiyattan büyük olmalıdır"
        return True, ""


class APIConfigValidator:
    """API konfigürasyonlarını doğrular."""

    @staticmethod
    def validate_ebay_config(config: dict) -> Tuple[bool, List[str]]:
        """eBay API konfigürasyonunu doğrular."""
        errors = []
        required = ["client_id", "client_secret", "refresh_token"]
        for field in required:
            if not config.get(field):
                errors.append(f"eBay '{field}' alanı zorunludur")
        return len(errors) == 0, errors

    @staticmethod
    def validate_shopify_config(config: dict) -> Tuple[bool, List[str]]:
        """Shopify API konfigürasyonunu doğrular."""
        errors = []
        required = ["shop_url", "api_key", "api_password"]
        for field in required:
            if not config.get(field):
                errors.append(f"Shopify '{field}' alanı zorunludur")

        shop_url = config.get("shop_url", "")
        if shop_url and not shop_url.endswith(".myshopify.com"):
            errors.append("Shopify URL'si '.myshopify.com' ile bitmelidir")

        return len(errors) == 0, errors

    @staticmethod
    def validate_walmart_config(config: dict) -> Tuple[bool, List[str]]:
        """Walmart API konfigürasyonunu doğrular."""
        errors = []
        required = ["client_id", "client_secret"]
        for field in required:
            if not config.get(field):
                errors.append(f"Walmart '{field}' alanı zorunludur")
        return len(errors) == 0, errors
