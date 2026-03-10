"""
Base Platform API
Tüm platform API'leri için temel sınıf.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Optional, List
from utils.rate_limiter import platform_rate_limiter
from utils.helpers import retry

logger = logging.getLogger(__name__)


class BasePlatformAPI(ABC):
    """Tüm platform API'leri için temel sınıf."""

    PLATFORM_NAME = "base"

    def __init__(self, config=None):
        self.config = config
        self.is_authenticated = False
        self._token = None
        self._token_expiry = 0

    @abstractmethod
    def authenticate(self) -> bool:
        """Platform ile kimlik doğrulama yapar."""
        pass

    @abstractmethod
    def upload_product(self, product: dict) -> Tuple[bool, str]:
        """Ürünü platforma yükler.
        Returns: (başarı, listing_id veya hata mesajı)
        """
        pass

    @abstractmethod
    def update_product(self, listing_id: str, product: dict) -> Tuple[bool, str]:
        """Mevcut ürünü günceller."""
        pass

    @abstractmethod
    def delete_product(self, listing_id: str) -> Tuple[bool, str]:
        """Ürünü platformdan siler."""
        pass

    @abstractmethod
    def get_product(self, listing_id: str) -> Optional[dict]:
        """Platform'dan ürün bilgisi alır."""
        pass

    def validate_config(self) -> Tuple[bool, List[str]]:
        """Platform konfigürasyonunu doğrular."""
        return True, []

    def rate_limit(self):
        """Rate limit kontrolü yapar."""
        platform_rate_limiter.acquire(self.PLATFORM_NAME)

    @property
    def is_enabled(self) -> bool:
        """Platform etkin mi?"""
        if self.config:
            return self.config.get("platforms", self.PLATFORM_NAME, "enabled", default=False)
        return False

    def _get_platform_config(self) -> dict:
        """Platform konfigürasyonunu döndürür."""
        if self.config:
            return self.config.get("platforms", self.PLATFORM_NAME, default={})
        return {}

    def __repr__(self):
        return f"<{self.__class__.__name__} platform='{self.PLATFORM_NAME}' enabled={self.is_enabled}>"
