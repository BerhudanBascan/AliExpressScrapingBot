"""
MongoDB Veritabanı Yöneticisi
Tüm CRUD operasyonları, indexleme, aggregation pipeline'ları.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from bson import ObjectId
import pymongo
from pymongo import MongoClient, IndexModel, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError

from database.models import Product, ScrapingJob, UploadJob, AnalyticsEvent, ProductStatus

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB veritabanı yöneticisi."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config=None):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self.config = config
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        """Veritabanına bağlanır ve indeksleri oluşturur."""
        try:
            uri = "mongodb://localhost:27017/"
            db_name = "aliexpress_dropshipping"

            if self.config:
                uri = self.config.get("database", "uri", default=uri)
                db_name = self.config.get("database", "name", default=db_name)

            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            # Bağlantıyı test et
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            self._create_indexes()
            logger.info(f"MongoDB bağlantısı kuruldu: {db_name}")
        except ConnectionFailure as e:
            logger.error(f"MongoDB bağlantı hatası: {e}")
            raise
        except Exception as e:
            logger.warning(f"MongoDB bağlantısı kurulamadı (uygulama çalışmaya devam edecek): {e}")

    def _create_indexes(self):
        """Veritabanı indekslerini oluşturur."""
        try:
            # Products collection
            self.db.products.create_indexes([
                IndexModel([("aliexpress_id", ASCENDING)], unique=True, sparse=True),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("category", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)]),
                IndexModel([("price", ASCENDING)]),
                IndexModel([("rating", DESCENDING)]),
                IndexModel([("orders", DESCENDING)]),
                IndexModel([("name", "text"), ("description", "text")]),
            ])

            # Scraping jobs collection
            self.db.scraping_jobs.create_indexes([
                IndexModel([("status", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)]),
            ])

            # Upload jobs collection
            self.db.upload_jobs.create_indexes([
                IndexModel([("status", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)]),
            ])

            # Analytics collection
            self.db.analytics.create_indexes([
                IndexModel([("event_type", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("timestamp", DESCENDING)]),
            ])

            # Error logs collection
            self.db.error_logs.create_indexes([
                IndexModel([("timestamp", DESCENDING)]),
                IndexModel([("source", ASCENDING)]),
            ])

            logger.debug("Veritabanı indeksleri oluşturuldu")
        except Exception as e:
            logger.error(f"İndeks oluşturma hatası: {e}")

    # ==================== ÜRÜN İŞLEMLERİ ====================

    def save_product(self, product: dict) -> str:
        """Tek bir ürünü kaydeder veya günceller."""
        try:
            product["updated_at"] = datetime.utcnow().isoformat()
            if "created_at" not in product:
                product["created_at"] = datetime.utcnow().isoformat()

            ali_id = product.get("aliexpress_id") or product.get("id", "")

            result = self.db.products.update_one(
                {"aliexpress_id": ali_id},
                {"$set": product},
                upsert=True
            )

            product_id = str(result.upserted_id) if result.upserted_id else ali_id
            logger.debug(f"Ürün kaydedildi: {product_id}")
            return product_id

        except DuplicateKeyError:
            logger.warning(f"Ürün zaten mevcut: {product.get('name', '')[:50]}")
            return ""
        except Exception as e:
            logger.error(f"Ürün kaydetme hatası: {e}")
            return ""

    def save_products(self, products: list) -> Tuple[int, int]:
        """Birden fazla ürünü kaydeder.

        Returns:
            (başarılı sayısı, hata sayısı)
        """
        success_count = 0
        error_count = 0

        for product in products:
            try:
                product_data = product if isinstance(product, dict) else product.to_dict()
                product_data["aliexpress_id"] = product_data.get("aliexpress_id") or product_data.get("id", "")
                result = self.save_product(product_data)
                if result:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Toplu kaydetme hatası: {e}")
                error_count += 1

        logger.info(f"Toplu kayıt: {success_count} başarılı, {error_count} hata")
        return success_count, error_count

    def get_product(self, product_id: str) -> Optional[dict]:
        """ID'ye göre ürün getirir."""
        try:
            product = self.db.products.find_one(
                {"$or": [
                    {"_id": ObjectId(product_id) if ObjectId.is_valid(product_id) else None},
                    {"aliexpress_id": product_id},
                    {"id": product_id}
                ]}
            )
            if product and "_id" in product:
                product["_id"] = str(product["_id"])
            return product
        except Exception as e:
            logger.error(f"Ürün getirme hatası: {e}")
            return None

    def get_products(
        self,
        status: str = None,
        category: str = None,
        platform: str = None,
        search: str = None,
        min_price: float = None,
        max_price: float = None,
        sort_by: str = "created_at",
        sort_order: int = -1,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[dict], int]:
        """Filtreleri kullanarak ürünleri getirir.

        Returns:
            (ürün listesi, toplam sayı)
        """
        try:
            query = {}

            if status:
                query["status"] = status
            if category:
                query["category"] = category
            if search:
                query["$text"] = {"$search": search}
            if min_price is not None or max_price is not None:
                price_query = {}
                if min_price is not None:
                    price_query["$gte"] = min_price
                if max_price is not None:
                    price_query["$lte"] = max_price
                query["price"] = price_query
            if platform:
                query[f"upload_status.{platform}"] = {"$exists": True}

            total = self.db.products.count_documents(query)

            cursor = self.db.products.find(query).sort(
                sort_by, sort_order
            ).skip(skip).limit(limit)

            products = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                products.append(doc)

            return products, total

        except Exception as e:
            logger.error(f"Ürün listesi getirme hatası: {e}")
            return [], 0

    def update_product(self, product_id: str, update_data: dict) -> bool:
        """Ürünü günceller."""
        try:
            update_data["updated_at"] = datetime.utcnow().isoformat()

            result = self.db.products.update_one(
                {"$or": [
                    {"aliexpress_id": product_id},
                    {"id": product_id}
                ]},
                {"$set": update_data}
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Ürün güncelleme hatası: {e}")
            return False

    def update_upload_status(self, product_id: str, platform: str, status: str, platform_listing_id: str = "") -> bool:
        """Ürünün platform yükleme durumunu günceller."""
        try:
            update = {
                f"upload_status.{platform}": status,
                f"platform_ids.{platform}": platform_listing_id,
                "updated_at": datetime.utcnow().isoformat()
            }

            result = self.db.products.update_one(
                {"$or": [{"aliexpress_id": product_id}, {"id": product_id}]},
                {"$set": update}
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Upload durumu güncelleme hatası: {e}")
            return False

    def delete_product(self, product_id: str) -> bool:
        """Ürünü siler."""
        try:
            result = self.db.products.delete_one(
                {"$or": [{"aliexpress_id": product_id}, {"id": product_id}]}
            )
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Ürün silme hatası: {e}")
            return False

    def delete_products(self, product_ids: list) -> int:
        """Birden fazla ürünü siler."""
        try:
            result = self.db.products.delete_many(
                {"$or": [
                    {"aliexpress_id": {"$in": product_ids}},
                    {"id": {"$in": product_ids}}
                ]}
            )
            return result.deleted_count
        except Exception as e:
            logger.error(f"Toplu silme hatası: {e}")
            return 0

    def filter_existing_products(self, products: list) -> list:
        """Veritabanında zaten var olan ürünleri filtreler."""
        try:
            product_ids = [p.get("aliexpress_id") or p.get("id", "") for p in products]
            existing = set()

            cursor = self.db.products.find(
                {"aliexpress_id": {"$in": product_ids}},
                {"aliexpress_id": 1}
            )

            for doc in cursor:
                existing.add(doc.get("aliexpress_id", ""))

            filtered = [p for p in products if (p.get("aliexpress_id") or p.get("id", "")) not in existing]
            logger.info(f"Filtreleme: {len(products)} -> {len(filtered)} yeni ürün")
            return filtered

        except Exception as e:
            logger.error(f"Filtreleme hatası: {e}")
            return products

    def get_product_count(self, status: str = None) -> int:
        """Ürün sayısını döndürür."""
        try:
            query = {}
            if status:
                query["status"] = status
            return self.db.products.count_documents(query)
        except Exception as e:
            logger.error(f"Ürün sayısı hatası: {e}")
            return 0

    # ==================== JOB İŞLEMLERİ ====================

    def save_scraping_job(self, job: dict) -> str:
        """Scraping job'ını kaydeder."""
        try:
            job["created_at"] = datetime.utcnow().isoformat()
            result = self.db.scraping_jobs.insert_one(job)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Scraping job kaydetme hatası: {e}")
            return ""

    def update_scraping_job(self, job_id: str, update_data: dict) -> bool:
        """Scraping job'ını günceller."""
        try:
            result = self.db.scraping_jobs.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Job güncelleme hatası: {e}")
            return False

    def get_recent_jobs(self, job_type: str = "scraping", limit: int = 20) -> list:
        """Son job'ları getirir."""
        try:
            collection = self.db.scraping_jobs if job_type == "scraping" else self.db.upload_jobs
            cursor = collection.find().sort("created_at", -1).limit(limit)
            jobs = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                jobs.append(doc)
            return jobs
        except Exception as e:
            logger.error(f"Job listesi hatası: {e}")
            return []

    # ==================== ANALİTİK İŞLEMLERİ ====================

    def log_event(self, event_type: str, data: dict = None, source: str = "system"):
        """Analitik olayı kaydeder."""
        try:
            event = {
                "event_type": event_type,
                "data": data or {},
                "source": source,
                "timestamp": datetime.utcnow()
            }
            self.db.analytics.insert_one(event)
        except Exception as e:
            logger.error(f"Event loglama hatası: {e}")

    def log_error(self, error_msg: str, source: str = "system", details: dict = None):
        """Hata kaydeder."""
        try:
            error = {
                "message": error_msg,
                "source": source,
                "details": details or {},
                "timestamp": datetime.utcnow()
            }
            self.db.error_logs.insert_one(error)
        except Exception as e:
            logger.error(f"Hata loglama hatası: {e}")

    def get_dashboard_stats(self) -> dict:
        """Dashboard için istatistikleri döndürür."""
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=7)
            month_start = today_start - timedelta(days=30)

            stats = {
                "total_products": self.db.products.count_documents({}),
                "products_today": self.db.products.count_documents(
                    {"created_at": {"$gte": today_start.isoformat()}}
                ),
                "products_this_week": self.db.products.count_documents(
                    {"created_at": {"$gte": week_start.isoformat()}}
                ),
                "products_this_month": self.db.products.count_documents(
                    {"created_at": {"$gte": month_start.isoformat()}}
                ),
                "by_status": {},
                "by_category": [],
                "by_platform": {},
                "recent_errors": [],
                "avg_price": 0,
                "total_uploaded": 0,
            }

            # Status breakdown
            pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            for doc in self.db.products.aggregate(pipeline):
                stats["by_status"][doc["_id"] or "unknown"] = doc["count"]

            # Category breakdown (top 10)
            pipeline = [
                {"$group": {"_id": "$category", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            stats["by_category"] = [
                {"category": doc["_id"] or "Diğer", "count": doc["count"]}
                for doc in self.db.products.aggregate(pipeline)
            ]

            # Platform upload counts
            for platform in ["ebay", "walmart", "shopify", "amazon", "etsy"]:
                count = self.db.products.count_documents(
                    {f"upload_status.{platform}": "success"}
                )
                if count > 0:
                    stats["by_platform"][platform] = count
                    stats["total_uploaded"] += count

            # Average price
            pipeline = [
                {"$group": {"_id": None, "avg_price": {"$avg": "$price"}}}
            ]
            result = list(self.db.products.aggregate(pipeline))
            if result:
                stats["avg_price"] = round(result[0].get("avg_price", 0), 2)

            # Recent errors
            errors = self.db.error_logs.find().sort("timestamp", -1).limit(5)
            stats["recent_errors"] = [
                {
                    "message": e.get("message", ""),
                    "source": e.get("source", ""),
                    "timestamp": e.get("timestamp", "").isoformat() if isinstance(e.get("timestamp"), datetime) else str(e.get("timestamp", ""))
                }
                for e in errors
            ]

            return stats

        except Exception as e:
            logger.error(f"Dashboard istatistikleri hatası: {e}")
            return {
                "total_products": 0, "products_today": 0,
                "products_this_week": 0, "products_this_month": 0,
                "by_status": {}, "by_category": [], "by_platform": {},
                "recent_errors": [], "avg_price": 0, "total_uploaded": 0
            }

    def get_price_distribution(self) -> list:
        """Fiyat dağılımını döndürür."""
        try:
            pipeline = [
                {"$bucket": {
                    "groupBy": "$price",
                    "boundaries": [0, 5, 10, 20, 50, 100, 500, 10000],
                    "default": "Other",
                    "output": {"count": {"$sum": 1}}
                }}
            ]
            return list(self.db.products.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Fiyat dağılımı hatası: {e}")
            return []

    def get_daily_scrape_stats(self, days: int = 30) -> list:
        """Günlük scraping istatistiklerini döndürür."""
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            pipeline = [
                {"$match": {"created_at": {"$gte": start_date}}},
                {"$group": {
                    "_id": {"$substr": ["$created_at", 0, 10]},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ]

            return [
                {"date": doc["_id"], "count": doc["count"]}
                for doc in self.db.products.aggregate(pipeline)
            ]
        except Exception as e:
            logger.error(f"Günlük istatistik hatası: {e}")
            return []

    # ==================== YARDIMCI İŞLEMLER ====================

    def health_check(self) -> dict:
        """Veritabanı sağlık kontrolü."""
        try:
            self.client.admin.command('ping')
            db_stats = self.db.command('dbStats')
            return {
                "status": "healthy",
                "collections": db_stats.get("collections", 0),
                "data_size": db_stats.get("dataSize", 0),
                "storage_size": db_stats.get("storageSize", 0),
                "indexes": db_stats.get("indexes", 0),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def close(self):
        """Bağlantıyı kapatır."""
        if self.client:
            self.client.close()
            logger.info("MongoDB bağlantısı kapatıldı")
