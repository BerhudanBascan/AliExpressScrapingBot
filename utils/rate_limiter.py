"""
API Rate Limiter
Platform API'larının istek limitlerini yönetir.
"""

import time
import threading
import logging
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket algoritması ile API rate limiting."""

    def __init__(self, calls_per_second: float = 1.0, burst: int = 5):
        """
        Args:
            calls_per_second: Saniyede izin verilen çağrı sayısı
            burst: Burst modda izin verilen maksimum çağrı sayısı
        """
        self.calls_per_second = calls_per_second
        self.burst = burst
        self.tokens = burst
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        """Bir token alır, gerekirse bekler.

        Args:
            timeout: Maksimum bekleme süresi (saniye)

        Returns:
            Token alındı mı
        """
        start_time = time.monotonic()

        while True:
            with self.lock:
                self._refill()

                if self.tokens >= 1:
                    self.tokens -= 1
                    return True

            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                logger.warning(f"Rate limiter timeout ({timeout}s)")
                return False

            # Bir sonraki token'ı bekle
            wait_time = min(1.0 / self.calls_per_second, timeout - elapsed)
            time.sleep(wait_time)

    def _refill(self):
        """Token kovuyu yeniler."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.calls_per_second
        self.tokens = min(self.burst, self.tokens + new_tokens)
        self.last_refill = now


class PlatformRateLimiter:
    """Platform bazlı rate limiting yöneticisi."""

    # Platform bazlı varsayılan limitler
    DEFAULT_LIMITS = {
        "ebay": {"calls_per_second": 5.0, "burst": 10},
        "walmart": {"calls_per_second": 2.0, "burst": 5},
        "shopify": {"calls_per_second": 2.0, "burst": 4},
        "amazon": {"calls_per_second": 1.0, "burst": 5},
        "etsy": {"calls_per_second": 5.0, "burst": 10},
        "aliexpress": {"calls_per_second": 0.5, "burst": 2},
    }

    def __init__(self):
        self._limiters = {}
        self.lock = threading.Lock()

    def get_limiter(self, platform: str) -> RateLimiter:
        """Platform için rate limiter döndürür."""
        with self.lock:
            if platform not in self._limiters:
                limits = self.DEFAULT_LIMITS.get(
                    platform.lower(),
                    {"calls_per_second": 1.0, "burst": 5}
                )
                self._limiters[platform] = RateLimiter(**limits)
            return self._limiters[platform]

    def acquire(self, platform: str, timeout: float = 30.0) -> bool:
        """Platform için token alır."""
        limiter = self.get_limiter(platform)
        return limiter.acquire(timeout)


# Global rate limiter instance
platform_rate_limiter = PlatformRateLimiter()
