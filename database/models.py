"""
Veri Modelleri
Pydantic tabanlı veri modelleri ve şemaları.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ProductStatus(str, Enum):
    """Ürün durumu."""
    SCRAPED = "scraped"
    VALIDATED = "validated"
    PRICED = "priced"
    FORMATTED = "formatted"
    UPLOADED = "uploaded"
    ERROR = "error"
    ARCHIVED = "archived"


class UploadStatus(str, Enum):
    """Yükleme durumu."""
    PENDING = "pending"
    UPLOADING = "uploading"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class Platform(str, Enum):
    """Desteklenen platformlar."""
    EBAY = "ebay"
    WALMART = "walmart"
    SHOPIFY = "shopify"
    AMAZON = "amazon"
    ETSY = "etsy"


class Product:
    """Ürün veri modeli."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")
        self.aliexpress_id = kwargs.get("aliexpress_id", "")
        self.name = kwargs.get("name", "")
        self.description = kwargs.get("description", "")
        self.price = kwargs.get("price", 0.0)
        self.original_price = kwargs.get("original_price", 0.0)
        self.calculated_price = kwargs.get("calculated_price", 0.0)
        self.markup_factor = kwargs.get("markup_factor", 1.0)
        self.currency = kwargs.get("currency", "USD")
        self.image_url = kwargs.get("image_url", "")
        self.image_urls = kwargs.get("image_urls", [])
        self.url = kwargs.get("url", "")
        self.category = kwargs.get("category", "")
        self.subcategory = kwargs.get("subcategory", "")
        self.rating = kwargs.get("rating", 0.0)
        self.review_count = kwargs.get("review_count", 0)
        self.orders = kwargs.get("orders", 0)
        self.warehouse = kwargs.get("warehouse", "")
        self.specifications = kwargs.get("specifications", {})
        self.variants = kwargs.get("variants", [])
        self.tags = kwargs.get("tags", [])
        self.keywords = kwargs.get("keywords", [])
        self.status = kwargs.get("status", ProductStatus.SCRAPED)
        self.upload_status = kwargs.get("upload_status", {})
        self.platform_ids = kwargs.get("platform_ids", {})
        self.formatted_titles = kwargs.get("formatted_titles", {})
        self.formatted_descriptions = kwargs.get("formatted_descriptions", {})
        self.sku = kwargs.get("sku", "")
        self.weight = kwargs.get("weight", 0.0)
        self.dimensions = kwargs.get("dimensions", {})
        self.shipping_info = kwargs.get("shipping_info", {})
        self.seller_info = kwargs.get("seller_info", {})
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())
        self.scraped_at = kwargs.get("scraped_at", datetime.utcnow())
        self.error_log = kwargs.get("error_log", [])

    def to_dict(self) -> dict:
        """Sözlüğe dönüştürür."""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Product":
        """Sözlükten oluşturur."""
        # Datetime alanlarını dönüştür
        for field in ["created_at", "updated_at", "scraped_at"]:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except (ValueError, TypeError):
                    data[field] = datetime.utcnow()
        return cls(**data)

    def __repr__(self):
        return f"<Product id='{self.id}' name='{self.name[:50]}' price={self.price}>"


class ScrapingJob:
    """Scraping iş modeli."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")
        self.category = kwargs.get("category", "")
        self.warehouse = kwargs.get("warehouse", "US")
        self.target_count = kwargs.get("target_count", 50)
        self.scraped_count = kwargs.get("scraped_count", 0)
        self.filtered_count = kwargs.get("filtered_count", 0)
        self.min_rating = kwargs.get("min_rating", 4.5)
        self.min_orders = kwargs.get("min_orders", 300)
        self.status = kwargs.get("status", "pending")
        self.progress = kwargs.get("progress", 0)
        self.errors = kwargs.get("errors", [])
        self.started_at = kwargs.get("started_at")
        self.completed_at = kwargs.get("completed_at")
        self.created_at = kwargs.get("created_at", datetime.utcnow())

    def to_dict(self) -> dict:
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            else:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapingJob":
        for field in ["started_at", "completed_at", "created_at"]:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except (ValueError, TypeError):
                    pass
        return cls(**data)


class UploadJob:
    """Upload iş modeli."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")
        self.platforms = kwargs.get("platforms", [])
        self.product_ids = kwargs.get("product_ids", [])
        self.total_count = kwargs.get("total_count", 0)
        self.uploaded_count = kwargs.get("uploaded_count", 0)
        self.failed_count = kwargs.get("failed_count", 0)
        self.status = kwargs.get("status", "pending")
        self.progress = kwargs.get("progress", 0)
        self.results = kwargs.get("results", {})
        self.errors = kwargs.get("errors", [])
        self.started_at = kwargs.get("started_at")
        self.completed_at = kwargs.get("completed_at")
        self.created_at = kwargs.get("created_at", datetime.utcnow())

    def to_dict(self) -> dict:
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            else:
                data[key] = value
        return data


class AnalyticsEvent:
    """Analitik olay modeli."""

    def __init__(self, event_type: str, data: dict = None, **kwargs):
        self.event_type = event_type
        self.data = data or {}
        self.timestamp = kwargs.get("timestamp", datetime.utcnow())
        self.source = kwargs.get("source", "system")

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }
