"""
Export Manager
CSV, Excel ve JSON formatlarında ürün verilerini dışa aktarır.
"""

import os
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ExportManager:
    """Veri dışa aktarma yöneticisi."""

    def __init__(self, export_dir: str = "exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_to_csv(self, products: List[Dict], filename: str = None) -> str:
        """Ürünleri CSV dosyasına aktarır."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"products_{timestamp}.csv"

        filepath = self.export_dir / filename

        try:
            if not products:
                logger.warning("Dışa aktarılacak ürün yok")
                return ""

            # Tüm alanları topla
            all_fields = set()
            for p in products:
                all_fields.update(p.keys())

            # _id ve karmaşık alanları çıkar
            skip_fields = {"_id", "error_log", "formatted_titles", "formatted_descriptions"}
            fields = sorted(all_fields - skip_fields)

            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()

                for product in products:
                    row = {}
                    for field in fields:
                        value = product.get(field, "")
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value, ensure_ascii=False)
                        row[field] = value
                    writer.writerow(row)

            logger.info(f"CSV dışa aktarıldı: {filepath} ({len(products)} ürün)")
            return str(filepath)

        except Exception as e:
            logger.error(f"CSV dışa aktarma hatası: {e}")
            return ""

    def export_to_json(self, products: List[Dict], filename: str = None) -> str:
        """Ürünleri JSON dosyasına aktarır."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"products_{timestamp}.json"

        filepath = self.export_dir / filename

        try:
            # _id alanlarını string'e çevir
            clean_products = []
            for p in products:
                product = p.copy()
                if "_id" in product:
                    product["_id"] = str(product["_id"])
                clean_products.append(product)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(clean_products, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"JSON dışa aktarıldı: {filepath} ({len(products)} ürün)")
            return str(filepath)

        except Exception as e:
            logger.error(f"JSON dışa aktarma hatası: {e}")
            return ""

    def export_to_excel(self, products: List[Dict], filename: str = None) -> str:
        """Ürünleri Excel dosyasına aktarır."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"products_{timestamp}.xlsx"

        filepath = self.export_dir / filename

        try:
            import pandas as pd

            # Karmaşık alanları düzleştir
            flat_products = []
            for p in products:
                flat = {}
                for k, v in p.items():
                    if k == "_id":
                        continue
                    if isinstance(v, (list, dict)):
                        flat[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        flat[k] = v
                flat_products.append(flat)

            df = pd.DataFrame(flat_products)
            df.to_excel(filepath, index=False, engine="openpyxl")

            logger.info(f"Excel dışa aktarıldı: {filepath} ({len(products)} ürün)")
            return str(filepath)

        except ImportError:
            logger.warning("openpyxl yüklü değil, CSV'ye dönülüyor")
            return self.export_to_csv(products, filename.replace(".xlsx", ".csv"))
        except Exception as e:
            logger.error(f"Excel dışa aktarma hatası: {e}")
            return ""

    def get_exports_list(self) -> List[Dict]:
        """Mevcut export dosyalarını listeler."""
        exports = []
        for file in sorted(self.export_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True):
            if file.suffix in [".csv", ".json", ".xlsx"]:
                stat = file.stat()
                exports.append({
                    "filename": file.name,
                    "path": str(file),
                    "size": stat.st_size,
                    "size_human": self._human_size(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": file.suffix[1:].upper(),
                })
        return exports

    @staticmethod
    def _human_size(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
