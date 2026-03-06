"""
AliExpress Dropshipping Pro - Gelişmiş Konfigürasyon Yönetimi
Tüm uygulama ayarlarını merkezi olarak yönetir.
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Optional, Dict


class Config:
    """Uygulama konfigürasyonunu merkezi olarak yönetir."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern - tek bir Config instance'ı olmasını sağlar."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_file: str = "config.json"):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        self.base_dir = Path(__file__).parent

        # .env dosyasını yükle
        load_dotenv(self.base_dir / ".env")

        # Konfigürasyonu oluştur
        self.config = self._build_config()

        # Konfigürasyon dosyasını yükle (varsa)
        self._load_config_file()

    def _build_config(self) -> Dict[str, Any]:
        """Tüm konfigürasyon ayarlarını oluşturur."""
        return {
            "app": {
                "name": os.getenv("APP_NAME", "AliExpress Dropshipping Pro"),
                "secret_key": os.getenv("APP_SECRET_KEY", "change-this-secret-key"),
                "debug": os.getenv("APP_DEBUG", "false").lower() == "true",
                "host": os.getenv("APP_HOST", "0.0.0.0"),
                "port": int(os.getenv("APP_PORT", "5000")),
                "base_dir": str(self.base_dir),
            },
            "database": {
                "type": "mongodb",
                "uri": os.getenv("MONGODB_URI", "mongodb://localhost:27017/"),
                "name": os.getenv("MONGODB_DB", "aliexpress_dropshipping"),
            },
            "redis": {
                "url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            },
            "scraping": {
                "headless": os.getenv("SCRAPING_HEADLESS", "true").lower() == "true",
                "max_retries": int(os.getenv("SCRAPING_MAX_RETRIES", "3")),
                "delay_min": float(os.getenv("SCRAPING_DELAY_MIN", "1.0")),
                "delay_max": float(os.getenv("SCRAPING_DELAY_MAX", "3.0")),
                "user_agent_rotation": os.getenv("SCRAPING_USER_AGENT_ROTATION", "true").lower() == "true",
                "max_concurrent": int(os.getenv("SCRAPING_MAX_CONCURRENT", "3")),
            },
            "proxy": {
                "enabled": os.getenv("PROXY_ENABLED", "false").lower() == "true",
                "list": [p.strip() for p in os.getenv("PROXY_LIST", "").split(",") if p.strip()],
                "api_url": os.getenv("PROXY_API_URL", ""),
                "api_key": os.getenv("PROXY_API_KEY", ""),
                "rotation_interval": int(os.getenv("PROXY_ROTATION_INTERVAL", "300")),
            },
            "platforms": {
                "ebay": {
                    "enabled": os.getenv("EBAY_ENABLED", "false").lower() == "true",
                    "sandbox": os.getenv("EBAY_SANDBOX", "true").lower() == "true",
                    "client_id": os.getenv("EBAY_CLIENT_ID", ""),
                    "client_secret": os.getenv("EBAY_CLIENT_SECRET", ""),
                    "refresh_token": os.getenv("EBAY_REFRESH_TOKEN", ""),
                    "marketplace_id": os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US"),
                },
                "walmart": {
                    "enabled": os.getenv("WALMART_ENABLED", "false").lower() == "true",
                    "client_id": os.getenv("WALMART_CLIENT_ID", ""),
                    "client_secret": os.getenv("WALMART_CLIENT_SECRET", ""),
                },
                "shopify": {
                    "enabled": os.getenv("SHOPIFY_ENABLED", "false").lower() == "true",
                    "shop_url": os.getenv("SHOPIFY_SHOP_URL", ""),
                    "api_key": os.getenv("SHOPIFY_API_KEY", ""),
                    "api_password": os.getenv("SHOPIFY_API_PASSWORD", ""),
                    "api_version": os.getenv("SHOPIFY_API_VERSION", "2024-01"),
                },
                "amazon": {
                    "enabled": os.getenv("AMAZON_ENABLED", "false").lower() == "true",
                    "seller_id": os.getenv("AMAZON_SELLER_ID", ""),
                    "access_key": os.getenv("AMAZON_ACCESS_KEY", ""),
                    "secret_key": os.getenv("AMAZON_SECRET_KEY", ""),
                    "refresh_token": os.getenv("AMAZON_REFRESH_TOKEN", ""),
                    "marketplace_id": os.getenv("AMAZON_MARKETPLACE_ID", "ATVPDKIKX0DER"),
                },
                "etsy": {
                    "enabled": os.getenv("ETSY_ENABLED", "false").lower() == "true",
                    "api_key": os.getenv("ETSY_API_KEY", ""),
                    "shared_secret": os.getenv("ETSY_SHARED_SECRET", ""),
                    "shop_id": os.getenv("ETSY_SHOP_ID", ""),
                },
            },
            "notifications": {
                "telegram": {
                    "enabled": os.getenv("TELEGRAM_ENABLED", "false").lower() == "true",
                    "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
                    "chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
                },
                "email": {
                    "enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
                    "smtp_host": os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com"),
                    "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", "587")),
                    "username": os.getenv("EMAIL_USERNAME", ""),
                    "password": os.getenv("EMAIL_PASSWORD", ""),
                    "from_addr": os.getenv("EMAIL_FROM", ""),
                    "to_addr": os.getenv("EMAIL_TO", ""),
                },
            },
            "scheduler": {
                "enabled": os.getenv("SCHEDULER_ENABLED", "false").lower() == "true",
                "scrape_interval": int(os.getenv("SCHEDULER_SCRAPE_INTERVAL", "3600")),
                "upload_interval": int(os.getenv("SCHEDULER_UPLOAD_INTERVAL", "1800")),
                "price_check_interval": int(os.getenv("SCHEDULER_PRICE_CHECK_INTERVAL", "7200")),
            },
            "sentry": {
                "dsn": os.getenv("SENTRY_DSN", ""),
                "environment": os.getenv("SENTRY_ENVIRONMENT", "production"),
            },
        }

    def _load_config_file(self):
        """Konfigürasyon dosyasını yükler ve mevcut konfigürasyonla birleştirir."""
        try:
            config_path = self.base_dir / self.config_file
            if config_path.exists():
                with open(config_path, "r") as f:
                    file_config = json.load(f)
                    self._deep_merge(self.config, file_config)
                self.logger.info(f"Konfigürasyon dosyası yüklendi: {config_path}")
        except Exception as e:
            self.logger.error(f"Konfigürasyon dosyası yüklenirken hata: {e}")

    def save_config(self) -> bool:
        """Konfigürasyonu dosyaya kaydeder (hassas bilgiler hariç)."""
        try:
            safe_config = self._sanitize_config(self.config)
            config_path = self.base_dir / self.config_file
            with open(config_path, "w") as f:
                json.dump(safe_config, f, indent=4, ensure_ascii=False)
            self.logger.info("Konfigürasyon dosyası kaydedildi")
            return True
        except Exception as e:
            self.logger.error(f"Konfigürasyon dosyası kaydedilirken hata: {e}")
            return False

    def get(self, *keys, default=None) -> Any:
        """Nokta notasyonu ile konfigürasyon değeri alır.

        Kullanım:
            config.get("database", "uri")
            config.get("platforms", "ebay", "client_id")
        """
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set(self, *keys_and_value) -> bool:
        """Konfigürasyon değeri ayarlar.

        Kullanım:
            config.set("database", "uri", "mongodb://new-host:27017/")
        """
        if len(keys_and_value) < 2:
            return False

        keys = keys_and_value[:-1]
        value = keys_and_value[-1]

        current = self.config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value
        return True

    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """Belirli bir platform konfigürasyonunu döndürür."""
        return self.get("platforms", platform, default={})

    def get_enabled_platforms(self) -> list:
        """Etkin platformların listesini döndürür."""
        platforms = self.get("platforms", default={})
        return [name for name, cfg in platforms.items() if cfg.get("enabled", False)]

    def _deep_merge(self, target: dict, source: dict):
        """İki sözlüğü derin birleştirme yapar."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _sanitize_config(self, config: dict) -> dict:
        """Hassas bilgileri konfigürasyondan kaldırır."""
        sensitive_keys = {"key", "secret", "password", "token", "dsn"}
        result = {}

        for key, value in config.items():
            if isinstance(value, dict):
                result[key] = self._sanitize_config(value)
            elif any(s in key.lower() for s in sensitive_keys):
                result[key] = "********" if value else ""
            else:
                result[key] = value

        return result

    def to_dict(self) -> dict:
        """Tüm konfigürasyonu sözlük olarak döndürür (sanitized)."""
        return self._sanitize_config(self.config)

    def __repr__(self):
        return f"<Config app='{self.get('app', 'name')}' platforms={self.get_enabled_platforms()}>"