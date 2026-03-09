import logging
import json
import os
import threading

class PriceCalculator:
    """Tamamen özelleştirilebilir kâr faktörleri ile ürün fiyatlarını hesaplar."""
    
    def __init__(self, settings_file="price_settings.json"):
        self.logger = logging.getLogger(__name__)
        self.settings_file = settings_file
        self.lock = threading.Lock()
        
        # Varsayılan değerler
        self.shipping_cost = 6.99
        self.price_ranges = [
            {"min": 0, "max": 5, "factor": 4.5},
            {"min": 5, "max": 10, "factor": 4.0},
            {"min": 10, "max": 20, "factor": 3.0},
            {"min": 20, "max": float('inf'), "factor": 2.0}
        ]
        
        # Ayarları dosyadan yükle (varsa)
        self.load_settings()
    
    def load_settings(self):
        """Fiyat hesaplama ayarlarını dosyadan yükler."""
        try:
            with self.lock:
                if os.path.exists(self.settings_file):
                    with open(self.settings_file, "r") as f:
                        settings = json.load(f)
                        
                        if "shipping_cost" in settings:
                            self.shipping_cost = float(settings["shipping_cost"])
                        
                        if "price_ranges" in settings:
                            self.price_ranges = settings["price_ranges"]
                            
                    self.logger.info("Fiyat ayarları dosyadan yüklendi")
        except Exception as e:
            self.logger.error(f"Fiyat ayarları yüklenirken hata: {str(e)}")
    
    def save_settings(self):
        """Mevcut fiyat hesaplama ayarlarını dosyaya kaydeder."""
        try:
            with self.lock:
                settings = {
                    "shipping_cost": self.shipping_cost,
                    "price_ranges": self.price_ranges
                }
                
                with open(self.settings_file, "w") as f:
                    json.dump(settings, f, indent=4)
                    
                self.logger.info("Fiyat ayarları dosyaya kaydedildi")
                return True
        except Exception as e:
            self.logger.error(f"Fiyat ayarları kaydedilirken hata: {str(e)}")
            return False
    
    def set_shipping_cost(self, cost):
        """Kargo maliyetini ayarlar."""
        try:
            with self.lock:
                self.shipping_cost = float(cost)
                self.save_settings()
                return True
        except Exception as e:
            self.logger.error(f"Kargo maliyeti ayarlanırken hata: {str(e)}")
            return False
    
    def set_margins(self, margins):
        """Basit marj ayarlarını kullanarak fiyat aralıklarını ayarlar."""
        try:
            with self.lock:
                # Mevcut aralıkları temizle
                self.price_ranges = []
                
                # Yeni aralıkları ekle
                self.price_ranges.append({"min": 0, "max": 5, "factor": margins["0-5"]})
                self.price_ranges.append({"min": 5, "max": 10, "factor": margins["5-10"]})
                self.price_ranges.append({"min": 10, "max": 20, "factor": margins["10-20"]})
                self.price_ranges.append({"min": 20, "max": float('inf'), "factor": margins["20+"]})
                
                self.save_settings()
                return True
        except Exception as e:
            self.logger.error(f"Marjlar ayarlanırken hata: {str(e)}")
            return False
    
    def get_factor_for_price(self, price):
        """Belirli bir fiyat için uygun kâr faktörünü alır."""
        try:
            with self.lock:
                price = float(price)
                
                for range_item in self.price_ranges:
                    if range_item["min"] <= price < range_item["max"]:
                        return range_item["factor"]
                
                # Eğer hiçbir aralık bulunamazsa, en yüksek aralığın faktörünü kullan
                return self.price_ranges[-1]["factor"]
        except Exception as e:
            self.logger.error(f"Fiyat faktörü alınırken hata: {str(e)}")
            return 3.0  # Varsayılan değer
    
    def calculate_price(self, original_price):
        """
        Orijinal fiyat ve kâr faktörlerine göre yeni fiyatı hesaplar.
        
        Args:
            original_price: Orijinal ürün fiyatı
            
        Returns:
            Kâr ve kargo ile yeni fiyat, $X.99 formatında
        """
        try:
            with self.lock:
                original_price = float(original_price)
                
                # Uygun kâr faktörünü al
                factor = self.get_factor_for_price(original_price)
                
                # Yeni fiyatı hesapla
                new_price = original_price * factor
                
                # Kargo ücretini ekle
                total_price = new_price + self.shipping_cost
                
                # $X.99 formatına getir
                formatted_price = int(total_price) - 0.01
                
                return f"${formatted_price:.2f}"
        except Exception as e:
            self.logger.error(f"Fiyat hesaplanırken hata: {str(e)}")
            # Basit bir 3x kâr ile yedek hesaplama
            return f"${(original_price * 3 + self.shipping_cost):.2f}"
    
    def get_all_price_ranges(self):
        """Tüm fiyat aralıklarını döndürür."""
        with self.lock:
            return self.price_ranges
    
    def get_shipping_cost(self):
        """Kargo maliyetini döndürür."""
        with self.lock:
            return self.shipping_cost