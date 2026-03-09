"""
Proxy Yönetim Sistemi
Proxy rotasyonu, sağlık kontrolü ve akıllı proxy seçimi.
"""

import time
import random
import logging
import threading
import requests
from typing import Optional, List, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


class ProxyInfo:
    """Proxy bilgi modeli."""

    def __init__(self, url: str):
        self.url = url
        self.is_alive = True
        self.fail_count = 0
        self.success_count = 0
        self.last_used = 0
        self.last_check = 0
        self.avg_response_time = 0
        self._response_times = []

    def record_success(self, response_time: float):
        """Başarılı kullanımı kaydeder."""
        self.success_count += 1
        self.fail_count = 0
        self.last_used = time.time()
        self._response_times.append(response_time)
        if len(self._response_times) > 10:
            self._response_times.pop(0)
        self.avg_response_time = sum(self._response_times) / len(self._response_times)

    def record_failure(self):
        """Başarısız kullanımı kaydeder."""
        self.fail_count += 1
        self.last_used = time.time()
        if self.fail_count >= 3:
            self.is_alive = False
            logger.warning(f"Proxy devre dışı bırakıldı: {self.url} ({self.fail_count} başarısız)")

    @property
    def score(self) -> float:
        """Proxy'nin performans skorunu hesaplar."""
        if not self.is_alive:
            return -1
        total = self.success_count + self.fail_count
        if total == 0:
            return 50.0
        success_rate = self.success_count / total * 100
        time_penalty = min(self.avg_response_time * 10, 30) if self.avg_response_time else 0
        return success_rate - time_penalty

    def __repr__(self):
        return f"<Proxy url='{self.url}' alive={self.is_alive} score={self.score:.1f}>"


class ProxyManager:
    """Proxy rotasyonu ve yönetim sistemi."""

    def __init__(self, config=None):
        self.config = config
        self.proxies: List[ProxyInfo] = []
        self.lock = threading.Lock()
        self._current_index = 0

        # Config'den proxy'leri yükle
        if config:
            proxy_list = config.get("proxy", "list", default=[])
            for proxy_url in proxy_list:
                if proxy_url:
                    self.add_proxy(proxy_url)

    def add_proxy(self, proxy_url: str):
        """Proxy ekler."""
        with self.lock:
            # Duplicate kontrolü
            if not any(p.url == proxy_url for p in self.proxies):
                self.proxies.append(ProxyInfo(proxy_url))
                logger.info(f"Proxy eklendi: {proxy_url}")

    def remove_proxy(self, proxy_url: str):
        """Proxy kaldırır."""
        with self.lock:
            self.proxies = [p for p in self.proxies if p.url != proxy_url]
            logger.info(f"Proxy kaldırıldı: {proxy_url}")

    def get_proxy(self) -> Optional[str]:
        """En iyi proxy'yi seçer ve döndürür."""
        with self.lock:
            alive_proxies = [p for p in self.proxies if p.is_alive]

            if not alive_proxies:
                # Devre dışı proxy'leri kontrol et
                self._revive_proxies()
                alive_proxies = [p for p in self.proxies if p.is_alive]

                if not alive_proxies:
                    logger.warning("Kullanılabilir proxy yok")
                    return None

            # Skor bazlı seçim (en yüksek skorlu proxy'leri tercih et)
            alive_proxies.sort(key=lambda p: p.score, reverse=True)

            # Ağırlıklı rastgele seçim (üst %50'den)
            top_half = alive_proxies[:max(1, len(alive_proxies) // 2)]
            selected = random.choice(top_half)
            selected.last_used = time.time()

            return selected.url

    def get_proxy_dict(self) -> Optional[Dict[str, str]]:
        """Requests kütüphanesi için proxy dict döndürür."""
        proxy_url = self.get_proxy()
        if proxy_url:
            return {
                "http": proxy_url,
                "https": proxy_url,
            }
        return None

    def report_success(self, proxy_url: str, response_time: float = 0):
        """Proxy başarı bildirir."""
        with self.lock:
            proxy = self._find_proxy(proxy_url)
            if proxy:
                proxy.record_success(response_time)

    def report_failure(self, proxy_url: str):
        """Proxy hata bildirir."""
        with self.lock:
            proxy = self._find_proxy(proxy_url)
            if proxy:
                proxy.record_failure()

    def check_all_proxies(self):
        """Tüm proxy'leri kontrol eder."""
        logger.info(f"{len(self.proxies)} proxy kontrol ediliyor...")

        for proxy in self.proxies:
            self._check_proxy(proxy)

        alive = sum(1 for p in self.proxies if p.is_alive)
        logger.info(f"Proxy kontrol tamamlandı: {alive}/{len(self.proxies)} aktif")

    def _check_proxy(self, proxy: ProxyInfo):
        """Tek bir proxy'yi kontrol eder."""
        try:
            start = time.time()
            response = requests.get(
                "https://httpbin.org/ip",
                proxies={"http": proxy.url, "https": proxy.url},
                timeout=10
            )
            elapsed = time.time() - start

            if response.status_code == 200:
                proxy.is_alive = True
                proxy.record_success(elapsed)
                proxy.last_check = time.time()
            else:
                proxy.record_failure()

        except Exception:
            proxy.record_failure()

    def _find_proxy(self, proxy_url: str) -> Optional[ProxyInfo]:
        """URL'ye göre proxy bulur."""
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                return proxy
        return None

    def _revive_proxies(self):
        """Devre dışı proxy'leri yeniden canlandırmayı dener."""
        now = time.time()
        for proxy in self.proxies:
            if not proxy.is_alive and (now - proxy.last_used) > 300:
                proxy.is_alive = True
                proxy.fail_count = 0
                logger.info(f"Proxy yeniden aktifleştirildi: {proxy.url}")

    def get_stats(self) -> dict:
        """Proxy istatistiklerini döndürür."""
        with self.lock:
            alive = [p for p in self.proxies if p.is_alive]
            return {
                "total": len(self.proxies),
                "alive": len(alive),
                "dead": len(self.proxies) - len(alive),
                "proxies": [
                    {
                        "url": p.url[:30] + "...",
                        "alive": p.is_alive,
                        "score": round(p.score, 1),
                        "success": p.success_count,
                        "fail": p.fail_count,
                        "avg_time": round(p.avg_response_time, 2),
                    }
                    for p in self.proxies
                ]
            }

    @property
    def has_proxies(self) -> bool:
        """Kullanılabilir proxy var mı?"""
        return any(p.is_alive for p in self.proxies)

    @property
    def count(self) -> int:
        """Toplam proxy sayısını döndürür."""
        return len(self.proxies)
