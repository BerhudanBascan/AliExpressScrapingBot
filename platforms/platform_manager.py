"""
Platform Yöneticisi
Tüm platform API'lerini merkezi olarak yönetir.
"""

import logging
from typing import Dict, Tuple, Optional, List
from platforms.base_platform import BasePlatformAPI
from platforms.ebay_api import eBayAPI
from platforms.shopify_api import ShopifyAPI
from platforms.walmart_api import WalmartAPI

logger = logging.getLogger(__name__)


class PlatformManager:
    """Tüm platform API'lerini merkezi olarak yönetir."""

    def __init__(self, config=None):
        self.config = config
        self._platforms: Dict[str, BasePlatformAPI] = {}
        self._initialize_platforms()

    def _initialize_platforms(self):
        """Platformları başlatır."""
        platform_classes = {
            "ebay": eBayAPI,
            "shopify": ShopifyAPI,
            "walmart": WalmartAPI,
        }

        for name, cls in platform_classes.items():
            try:
                platform = cls(self.config)
                self._platforms[name] = platform
                logger.debug(f"Platform başlatıldı: {name} (enabled={platform.is_enabled})")
            except Exception as e:
                logger.error(f"Platform başlatma hatası ({name}): {e}")

    def get_platform(self, name: str) -> Optional[BasePlatformAPI]:
        """Platform instance'ını döndürür."""
        return self._platforms.get(name.lower())

    def get_enabled_platforms(self) -> Dict[str, BasePlatformAPI]:
        """Etkin platformları döndürür."""
        return {name: p for name, p in self._platforms.items() if p.is_enabled}

    def get_all_platforms(self) -> Dict[str, BasePlatformAPI]:
        """Tüm platformları döndürür."""
        return self._platforms

    def upload_product(self, platform_name: str, product: dict) -> Tuple[bool, str]:
        """Ürünü belirli bir platforma yükler."""
        platform = self.get_platform(platform_name)
        if not platform:
            return False, f"Platform bulunamadı: {platform_name}"
        if not platform.is_enabled:
            return False, f"Platform etkin değil: {platform_name}"
        return platform.upload_product(product)

    def upload_to_all(self, product: dict, platforms: List[str] = None) -> Dict[str, Tuple[bool, str]]:
        """Ürünü birden fazla platforma yükler."""
        results = {}
        target_platforms = platforms or list(self.get_enabled_platforms().keys())

        for name in target_platforms:
            try:
                success, result = self.upload_product(name, product)
                results[name] = (success, result)
            except Exception as e:
                results[name] = (False, str(e))
                logger.error(f"{name} yükleme hatası: {e}")

        return results

    def validate_all_configs(self) -> Dict[str, Tuple[bool, List[str]]]:
        """Tüm platform konfigürasyonlarını doğrular."""
        results = {}
        for name, platform in self._platforms.items():
            results[name] = platform.validate_config()
        return results

    def get_platform_status(self) -> Dict[str, dict]:
        """Tüm platform durumlarını döndürür."""
        status = {}
        for name, platform in self._platforms.items():
            is_valid, errors = platform.validate_config()
            status[name] = {
                "enabled": platform.is_enabled,
                "authenticated": platform.is_authenticated,
                "config_valid": is_valid,
                "errors": errors,
            }
        return status
