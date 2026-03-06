"""
Yardımcı Fonksiyonlar
Proje genelinde kullanılan ortak yardımcı fonksiyonlar.
"""

import re
import hashlib
import uuid
import time
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def generate_sku(product_id: str, platform: str = "ALI") -> str:
    """Benzersiz SKU oluşturur."""
    timestamp = int(time.time())
    short_hash = hashlib.md5(f"{product_id}{timestamp}".encode()).hexdigest()[:6].upper()
    return f"{platform}-{short_hash}-{timestamp % 10000}"


def generate_uuid() -> str:
    """Benzersiz UUID oluşturur."""
    return str(uuid.uuid4())


def clean_text(text: str) -> str:
    """Metni temizler ve normalizar."""
    if not text:
        return ""
    # Çoklu boşlukları tek boşluğa düşür
    cleaned = re.sub(r'\s+', ' ', text).strip()
    # Kontrol karakterlerini kaldır
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
    return cleaned


def clean_price(price_str: str) -> float:
    """Fiyat string'ini float'a çevirir."""
    if not price_str:
        return 0.0
    # $ işareti ve boşlukları kaldır
    cleaned = re.sub(r'[^\d.,]', '', str(price_str))
    # Virgülü noktaya çevir
    cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def format_price(price: float, currency: str = "$") -> str:
    """Float fiyatı formatlanmış string'e çevirir."""
    return f"{currency}{price:.2f}"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Metni belirli uzunlukta keser."""
    if not text or len(text) <= max_length:
        return text or ""
    return text[:max_length - len(suffix)] + suffix


def slugify(text: str) -> str:
    """Metni URL-uyumlu slug'a çevirir."""
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def time_ago(dt: datetime) -> str:
    """Datetime'ı insanca okunabilir 'zaman önce' formatına çevirir."""
    now = datetime.utcnow()
    diff = now - dt

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} yıl önce"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} ay önce"
    elif diff.days > 0:
        return f"{diff.days} gün önce"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} saat önce"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} dakika önce"
    else:
        return "az önce"


def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions=(Exception,)):
    """Hata durumunda otomatik yeniden deneme decorator'ü."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} başarısız (deneme {attempt + 1}/{max_retries}): {e}. "
                            f"{current_delay:.1f}s sonra tekrar denenecek."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} {max_retries} denemeden sonra başarısız: {e}")

            raise last_exception
        return wrapper
    return decorator


def chunk_list(lst: list, chunk_size: int) -> list:
    """Listeyi belirli boyutta parçalara böler."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_get(data: dict, *keys, default=None) -> Any:
    """İç içe sözlükten güvenli şekilde değer alır."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
        if current is None:
            return default
    return current


def calculate_percentage(part: float, whole: float) -> float:
    """Yüzde hesaplar."""
    if whole == 0:
        return 0.0
    return round((part / whole) * 100, 2)


def mask_sensitive(text: str, visible_chars: int = 4) -> str:
    """Hassas bilgiyi maskeler."""
    if not text or len(text) <= visible_chars:
        return "****"
    return text[:visible_chars] + "*" * (len(text) - visible_chars)
