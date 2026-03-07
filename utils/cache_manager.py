"""
Cache Yönetim Sistemi
Bellekte ve dosya tabanlı cache yönetimi.
"""

import time
import json
import hashlib
import threading
import logging
from pathlib import Path
from typing import Any, Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)


class MemoryCache:
    """Thread-safe bellek tabanlı LRU cache."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Args:
            max_size: Maksimum cache öğesi sayısı
            ttl: Yaşam süresi (saniye)
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache = OrderedDict()
        self.lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Cache'den değer alır."""
        with self.lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    # LRU: erişilen öğeyi sona taşı
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return value
                else:
                    # Süresi dolmuş
                    del self._cache[key]

            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Cache'e değer ekler."""
        with self.lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.max_size:
                # En eski öğeyi kaldır (LRU)
                self._cache.popitem(last=False)

            expiry = time.time() + (ttl or self.ttl)
            self._cache[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        """Cache'den değer siler."""
        with self.lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """Tüm cache'i temizler."""
        with self.lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def cleanup(self):
        """Süresi dolmuş öğeleri temizler."""
        with self.lock:
            now = time.time()
            expired_keys = [
                k for k, (_, expiry) in self._cache.items() if now >= expiry
            ]
            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cache temizlendi: {len(expired_keys)} öğe kaldırıldı")

    @property
    def stats(self) -> dict:
        """Cache istatistiklerini döndürür."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }


class FileCache:
    """Dosya tabanlı kalıcı cache."""

    def __init__(self, cache_dir: str = ".cache", ttl: int = 86400):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl

    def _get_path(self, key: str) -> Path:
        """Cache dosya yolunu oluşturur."""
        hashed = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed}.json"

    def get(self, key: str) -> Optional[Any]:
        """Cache'den değer alır."""
        path = self._get_path(key)
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if time.time() < data.get("expiry", 0):
                    return data["value"]
                else:
                    path.unlink()  # Süresi dolmuş
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.debug(f"Cache okuma hatası: {e}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Cache'e değer ekler."""
        path = self._get_path(key)
        try:
            data = {
                "key": key,
                "value": value,
                "expiry": time.time() + (ttl or self.ttl),
                "created": time.time(),
            }
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except (OSError, TypeError) as e:
            logger.debug(f"Cache yazma hatası: {e}")

    def delete(self, key: str) -> bool:
        """Cache'den değer siler."""
        path = self._get_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self):
        """Tüm cache'i temizler."""
        for file in self.cache_dir.glob("*.json"):
            file.unlink()

    def cleanup(self):
        """Süresi dolmuş dosyaları temizler."""
        now = time.time()
        cleaned = 0
        for file in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if now >= data.get("expiry", 0):
                    file.unlink()
                    cleaned += 1
            except (json.JSONDecodeError, OSError):
                file.unlink()
                cleaned += 1

        if cleaned:
            logger.debug(f"File cache temizlendi: {cleaned} dosya kaldırıldı")


# Global cache instances
product_cache = MemoryCache(max_size=5000, ttl=3600)
api_cache = MemoryCache(max_size=500, ttl=300)
