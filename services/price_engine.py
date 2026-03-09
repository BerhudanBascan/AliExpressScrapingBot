"""
Gelişmiş Fiyat Motoru
Dinamik fiyatlandırma, çoklu strateji ve kâr optimizasyonu.
"""

import json
import os
import math
import logging
import threading
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PricingStrategy:
    """Fiyatlandırma stratejisi."""

    def __init__(self, name: str, ranges: List[Dict]):
        self.name = name
        self.ranges = ranges  # [{"min": 0, "max": 5, "factor": 4.5}, ...]

    def get_factor(self, price: float) -> float:
        for r in self.ranges:
            if r["min"] <= price < r.get("max", float("inf")):
                return r["factor"]
        return self.ranges[-1]["factor"] if self.ranges else 2.0


class PriceEngine:
    """Gelişmiş fiyat hesaplama motoru."""

    DEFAULT_STRATEGIES = {
        "aggressive": [
            {"min": 0, "max": 5, "factor": 5.0},
            {"min": 5, "max": 10, "factor": 4.5},
            {"min": 10, "max": 20, "factor": 3.5},
            {"min": 20, "max": 50, "factor": 2.5},
            {"min": 50, "max": float("inf"), "factor": 2.0},
        ],
        "moderate": [
            {"min": 0, "max": 5, "factor": 4.0},
            {"min": 5, "max": 10, "factor": 3.5},
            {"min": 10, "max": 20, "factor": 3.0},
            {"min": 20, "max": 50, "factor": 2.0},
            {"min": 50, "max": float("inf"), "factor": 1.8},
        ],
        "conservative": [
            {"min": 0, "max": 5, "factor": 3.0},
            {"min": 5, "max": 10, "factor": 2.5},
            {"min": 10, "max": 20, "factor": 2.0},
            {"min": 20, "max": 50, "factor": 1.7},
            {"min": 50, "max": float("inf"), "factor": 1.5},
        ],
        "custom": [
            {"min": 0, "max": 5, "factor": 4.5},
            {"min": 5, "max": 10, "factor": 4.0},
            {"min": 10, "max": 20, "factor": 3.0},
            {"min": 20, "max": float("inf"), "factor": 2.0},
        ],
    }

    # Platform bazlı ek ücretler
    PLATFORM_FEES = {
        "ebay": {"percentage": 12.9, "fixed": 0.30},
        "walmart": {"percentage": 8.0, "fixed": 0.0},
        "shopify": {"percentage": 2.9, "fixed": 0.30},
        "amazon": {"percentage": 15.0, "fixed": 0.0},
        "etsy": {"percentage": 6.5, "fixed": 0.20},
    }

    def __init__(self, settings_file: str = "price_settings.json"):
        self.settings_file = settings_file
        self.lock = threading.Lock()

        # Varsayılan ayarlar
        self.active_strategy = "custom"
        self.strategies = {}
        self.shipping_cost = 6.99
        self.handling_cost = 0.0
        self.tax_rate = 0.0
        self.round_to_99 = True
        self.min_profit = 2.0
        self.include_platform_fees = True

        # Stratejileri yükle
        self._load_strategies()
        self.load_settings()

    def _load_strategies(self):
        """Varsayılan stratejileri yükler."""
        for name, ranges in self.DEFAULT_STRATEGIES.items():
            self.strategies[name] = PricingStrategy(name, ranges)

    def load_settings(self):
        """Ayarları dosyadan yükler."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)

                self.shipping_cost = settings.get("shipping_cost", self.shipping_cost)
                self.handling_cost = settings.get("handling_cost", self.handling_cost)
                self.tax_rate = settings.get("tax_rate", self.tax_rate)
                self.round_to_99 = settings.get("round_to_99", self.round_to_99)
                self.min_profit = settings.get("min_profit", self.min_profit)
                self.active_strategy = settings.get("active_strategy", self.active_strategy)
                self.include_platform_fees = settings.get("include_platform_fees", True)

                if "custom_ranges" in settings:
                    self.strategies["custom"] = PricingStrategy("custom", settings["custom_ranges"])

                logger.info("Fiyat ayarları yüklendi")
        except Exception as e:
            logger.error(f"Fiyat ayarları yükleme hatası: {e}")

    def save_settings(self) -> bool:
        """Ayarları dosyaya kaydeder."""
        try:
            settings = {
                "shipping_cost": self.shipping_cost,
                "handling_cost": self.handling_cost,
                "tax_rate": self.tax_rate,
                "round_to_99": self.round_to_99,
                "min_profit": self.min_profit,
                "active_strategy": self.active_strategy,
                "include_platform_fees": self.include_platform_fees,
                "custom_ranges": self.strategies.get("custom", PricingStrategy("custom", [])).ranges,
            }
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Fiyat ayarları kaydetme hatası: {e}")
            return False

    def calculate_price(
        self,
        original_price: float,
        platform: str = None,
        strategy: str = None,
    ) -> Dict:
        """Fiyatı hesaplar ve detayları döndürür.

        Returns:
            {
                "original_price": float,
                "factor": float,
                "base_price": float,
                "shipping": float,
                "handling": float,
                "platform_fee": float,
                "tax": float,
                "total_cost": float,
                "selling_price": float,
                "profit": float,
                "profit_margin": float,
                "formatted_price": str,
            }
        """
        with self.lock:
            strategy_name = strategy or self.active_strategy
            pricing_strategy = self.strategies.get(strategy_name)

            if not pricing_strategy:
                pricing_strategy = self.strategies.get("moderate")

            factor = pricing_strategy.get_factor(original_price)

            # Temel fiyat hesaplama
            base_price = original_price * factor

            # Ek maliyetler
            shipping = self.shipping_cost
            handling = self.handling_cost
            tax = base_price * (self.tax_rate / 100) if self.tax_rate else 0

            # Platform komisyonu
            platform_fee = 0
            if platform and self.include_platform_fees:
                fee_info = self.PLATFORM_FEES.get(platform.lower(), {})
                platform_fee = base_price * (fee_info.get("percentage", 0) / 100) + fee_info.get("fixed", 0)

            # Toplam maliyet
            total_cost = original_price + shipping + handling + tax + platform_fee

            # Satış fiyatı
            selling_price = base_price + shipping

            # Minimum kâr kontrolü
            profit = selling_price - total_cost
            if profit < self.min_profit:
                selling_price = total_cost + self.min_profit

            # $X.99 formatına yuvarla
            if self.round_to_99:
                selling_price = math.ceil(selling_price) - 0.01

            # Kâr ve marj
            profit = selling_price - total_cost
            profit_margin = (profit / selling_price * 100) if selling_price > 0 else 0

            return {
                "original_price": round(original_price, 2),
                "factor": factor,
                "base_price": round(base_price, 2),
                "shipping": round(shipping, 2),
                "handling": round(handling, 2),
                "platform_fee": round(platform_fee, 2),
                "tax": round(tax, 2),
                "total_cost": round(total_cost, 2),
                "selling_price": round(selling_price, 2),
                "profit": round(profit, 2),
                "profit_margin": round(profit_margin, 1),
                "formatted_price": f"${selling_price:.2f}",
            }

    def quick_price(self, original_price: float, platform: str = None) -> str:
        """Hızlı fiyat hesaplama - sadece formatlanmış fiyat döndürür."""
        result = self.calculate_price(original_price, platform)
        return result["formatted_price"]

    def set_margins(self, margins: Dict[str, float]):
        """UI'dan gelen basit marj ayarlarını uygular."""
        ranges = []
        margin_map = {
            "0-5": (0, 5),
            "5-10": (5, 10),
            "10-20": (10, 20),
            "20+": (20, float("inf")),
        }

        for key, (min_val, max_val) in margin_map.items():
            if key in margins:
                ranges.append({"min": min_val, "max": max_val, "factor": margins[key]})

        if ranges:
            self.strategies["custom"] = PricingStrategy("custom", ranges)
            self.active_strategy = "custom"
            self.save_settings()

    def set_shipping_cost(self, cost: float):
        """Kargo maliyetini ayarlar."""
        self.shipping_cost = cost
        self.save_settings()

    def get_strategy_names(self) -> List[str]:
        """Mevcut strateji isimlerini döndürür."""
        return list(self.strategies.keys())

    def get_active_strategy(self) -> Dict:
        """Aktif strateji bilgilerini döndürür."""
        strategy = self.strategies.get(self.active_strategy)
        return {
            "name": self.active_strategy,
            "ranges": strategy.ranges if strategy else [],
        }

    def get_settings(self) -> Dict:
        """Tüm fiyat ayarlarını döndürür."""
        return {
            "shipping_cost": self.shipping_cost,
            "handling_cost": self.handling_cost,
            "tax_rate": self.tax_rate,
            "round_to_99": self.round_to_99,
            "min_profit": self.min_profit,
            "active_strategy": self.active_strategy,
            "include_platform_fees": self.include_platform_fees,
            "strategies": {
                name: {"ranges": s.ranges}
                for name, s in self.strategies.items()
            },
            "platform_fees": self.PLATFORM_FEES,
        }
