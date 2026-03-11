import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import pandas as pd
import os
import time
from datetime import datetime
import logging
import json

from config import Config
from mongodb_database import MongoDB
from real_scraper import AliExpressScraper
from price_calculator import PriceCalculator
from platform_formatter import PlatformFormatter
from platform_api import PlatformAPI

class AliExpressScraperApp:
    """AliExpress ürün çekme ve yükleme için ana uygulama."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AliExpress Ürün Çekme ve Aktarma Aracı")
        self.logger = logging.getLogger(__name__)
        
        # Konfigürasyon
        self.config = Config()
        
        # İş parçacığı güvenli mesaj kuyruğu
        self.message_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        
        # Bileşenleri başlat
        self.db = MongoDB(self.config)
        self.scraper = AliExpressScraper(self.config)
        self.price_calculator = PriceCalculator()
        self.formatter = PlatformFormatter()
        self.platform_api = PlatformAPI(self.config)
        
        # İş parçacığı değişkenleri
        self.scrape_thread = None
        self.upload_thread = None
        self.csv_path = None
        self.stop_requested = False
        
        # Arayüz elemanlarını oluştur
        self.create_ui()
        
        # Mesaj kuyruğu işleyicisini başlat
        self.process_message_queue()
        self.process_progress_queue()
        
        # Başlangıç durumu
        self.update_status("Uygulama başlatıldı. Veritabanında " + str(self.db.get_product_count()) + " ürün var.")
    
    def create_ui(self):
        """Tüm gerekli bileşenlerle kullanıcı arayüzünü oluşturur."""
        # Ana çerçeve
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Kategori seçimi
        ttk.Label(main_frame, text="Kategori:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.categories = [
            "Apparel & Accessories", "Automobiles & Motorcycles", "Baby Products",
            "Beauty & Health", "Computer & Office", "Consumer Electronics",
            "Electrical Equipment & Supplies", "Furniture", "Hair Extensions & Wigs",
            "Home & Garden", "Home Appliances", "Home Improvement",
            "Jewelry & Accessories", "Lights & Lighting", "Luggage & Bags",
            "Men's Clothing", "Mother & Kids", "Office & School Supplies",
            "Phones & Telecommunications", "Security & Protection", "Shoes",
            "Sports & Entertainment", "Tools", "Toys & Hobbies",
            "Watches", "Weddings & Events", "Women's Clothing"
        ]
        
        self.category_var = tk.StringVar()
        category_dropdown = ttk.Combobox(main_frame, textvariable=self.category_var, values=self.categories, width=30)
        category_dropdown.grid(row=0, column=1, sticky=tk.W, pady=5)
        category_dropdown.current(5)  # Varsayılan olarak Consumer Electronics
        
        # Depo seçimi
        ttk.Label(main_frame, text="Depo:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.warehouse_var = tk.StringVar(value="US")
        warehouse_dropdown = ttk.Combobox(main_frame, textvariable=self.warehouse_var, values=["US", "EU", "UK", "CN"], width=10)
        warehouse_dropdown.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Ürün sayısı
        ttk.Label(main_frame, text="Ürün Sayısı:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.product_count_var = tk.StringVar(value="50")
        product_count_entry = ttk.Entry(main_frame, textvariable=self.product_count_var, width=10)
        product_count_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Minimum puan
        ttk.Label(main_frame, text="Min. Puan:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.min_rating_var = tk.StringVar(value="4.5")
        min_rating_entry = ttk.Entry(main_frame, textvariable=self.min_rating_var, width=10)
        min_rating_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Minimum sipariş
        ttk.Label(main_frame, text="Min. Sipariş:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.min_orders_var = tk.StringVar(value="300")
        min_orders_entry = ttk.Entry(main_frame, textvariable=self.min_orders_var, width=10)
        min_orders_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Platform seçimi
        ttk.Label(main_frame, text="Platformlar:").grid(row=5, column=0, sticky=tk.W, pady=5)
        platforms_frame = ttk.Frame(main_frame)
        platforms_frame.grid(row=5, column=1, sticky=tk.W, pady=5)
        
        self.ebay_var = tk.BooleanVar(value=True)
        self.walmart_var = tk.BooleanVar(value=False)
        self.shopify_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(platforms_frame, text="eBay", variable=self.ebay_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(platforms_frame, text="Walmart", variable=self.walmart_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(platforms_frame, text="Shopify", variable=self.shopify_var).pack(side=tk.LEFT, padx=5)
        
        # Kâr marjı ayarları
        ttk.Label(main_frame, text="Kâr Marjları:").grid(row=6, column=0, sticky=tk.W, pady=5)
        
        margins_frame = ttk.Frame(main_frame)
        margins_frame.grid(row=6, column=1, sticky=tk.W, pady=5)
        
        margin_options = ["1.5x", "2x", "2.5x", "3x", "3.5x", "4x", "4.5x", "5x", "5.5x", "6x", "7x", "8x", "9x"]
        
        # $0-$5 marjı
        ttk.Label(margins_frame, text="$0-$5:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.margin_0_5_var = tk.StringVar()
        margin_0_5_dropdown = ttk.Combobox(margins_frame, textvariable=self.margin_0_5_var, values=margin_options, width=5)
        margin_0_5_dropdown.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        margin_0_5_dropdown.current(6)  # Varsayılan olarak 4.5x
        
        # $5-$10 marjı
        ttk.Label(margins_frame, text="$5-$10:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.margin_5_10_var = tk.StringVar()
        margin_5_10_dropdown = ttk.Combobox(margins_frame, textvariable=self.margin_5_10_var, values=margin_options, width=5)
        margin_5_10_dropdown.grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)
        margin_5_10_dropdown.current(5)  # Varsayılan olarak 4x
        
        # $10-$20 marjı
        ttk.Label(margins_frame, text="$10-$20:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.margin_10_20_var = tk.StringVar()
        margin_10_20_dropdown = ttk.Combobox(margins_frame, textvariable=self.margin_10_20_var, values=margin_options, width=5)
        margin_10_20_dropdown.grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)
        margin_10_20_dropdown.current(3)  # Varsayılan olarak 3x
        
        # $20+ marjı
        ttk.Label(margins_frame, text="$20+:").grid(row=1, column=2, sticky=tk.W, pady=2)
        self.margin_20_plus_var = tk.StringVar()
        margin_20_plus_dropdown = ttk.Combobox(margins_frame, textvariable=self.margin_20_plus_var, values=margin_options, width=5)
        margin_20_plus_dropdown.grid(row=1, column=3, sticky=tk.W, pady=2, padx=5)
        margin_20_plus_dropdown.current(1)  # Varsayılan olarak 2x
        
        # İşlem butonları
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        self.scrape_button = ttk.Button(buttons_frame, text="Çek ve Göster", command=self.start_scraping)
        self.scrape_button.pack(side=tk.LEFT, padx=10)
        
        self.upload_button = ttk.Button(buttons_frame, text="Yükle", command=self.start_uploading, state=tk.DISABLED)
        self.upload_button.pack(side=tk.LEFT, padx=10)
        
        self.stop_button = ttk.Button(buttons_frame, text="Durdur", command=self.stop_operations, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=10)
        
        self.preview_button = ttk.Button(buttons_frame, text="Önizleme", command=self.show_description_preview, state=tk.DISABLED)
        self.preview_button.pack(side=tk.LEFT, padx=10)
        
        # Durum çerçevesi
        status_frame = ttk.LabelFrame(main_frame, text="Durum")
        status_frame.grid(row=8, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        # Kaydırma çubuğu ile durum metni
        status_scroll = ttk.Scrollbar(status_frame)
        status_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.status_text = tk.Text(status_frame, height=10, width=80, wrap=tk.WORD, yscrollcommand=status_scroll.set)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        status_scroll.config(command=self.status_text.yview)
        
        # İlerleme çubuğu
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=9, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        # Önizleme seçenekleri
        preview_frame = ttk.LabelFrame(main_frame, text="Önizleme Seçenekleri")
        preview_frame.grid(row=10, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        self.preview_platform_var = tk.StringVar(value="eBay")
        ttk.Label(preview_frame, text="Platform:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        preview_platform_dropdown = ttk.Combobox(preview_frame, textvariable=self.preview_platform_var, 
                                                values=["eBay", "Walmart", "Shopify"], width=15)
        preview_platform_dropdown.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # CSV dosyası seçimi
        ttk.Label(preview_frame, text="CSV Dosyası:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)
        self.csv_var = tk.StringVar()
        ttk.Entry(preview_frame, textvariable=self.csv_var, width=30).grid(row=0, column=3, sticky=tk.W, pady=5, padx=5)
        ttk.Button(preview_frame, text="Gözat", command=self.browse_csv).grid(row=0, column=4, sticky=tk.W, pady=5, padx=5)
    
    def browse_csv(self):
        """CSV dosyası seçme iletişim kutusunu açar."""
        filename = filedialog.askopenfilename(
            title="CSV Dosyası Seç",
            filetypes=(("CSV Dosyaları", "*.csv"), ("Tüm Dosyalar", "*.*"))
        )
        if filename:
            self.csv_var.set(filename)
            self.csv_path = filename
            self.preview_button.config(state=tk.NORMAL)
            self.upload_button.config(state=tk.NORMAL)
    
    def show_description_preview(self):
        """Seçilen platform için açıklama önizlemesini gösterir."""
        try:
            csv_path = self.csv_var.get()
            if not csv_path:
                # En son CSV dosyasını bul
                csv_files = [f for f in os.listdir() if f.startswith("products_") and f.endswith(".csv")]
                if not csv_files:
                    messagebox.showinfo("Bilgi", "Önizleme için CSV dosyası bulunamadı. Lütfen önce ürünleri çekin veya bir CSV dosyası seçin.")
                    return
                
                csv_path = max(csv_files, key=os.path.getctime)
            
            # CSV'yi oku (sadece ilk satırı)
            df = pd.read_csv(csv_path, nrows=1)
            if df.empty:
                messagebox.showinfo("Bilgi", "CSV dosyası boş.")
                return
            
            # İlk ürünü al
            product = df.iloc[0].to_dict()
            
            # Seçilen platform
            platform = self.preview_platform_var.get()
            
            # Başlığı formatla
            formatted_title = self.formatter.format_title(product["name"], platform)
            
            # Açıklamayı formatla
            formatted_description = self.formatter.format_description(product, platform)
            
            # Önizleme penceresini ayrı bir iş parçacığında oluştur
            threading.Thread(target=self._create_preview_window, 
                            args=(platform, product, formatted_title, formatted_description), 
                            daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Önizleme gösterilirken hata oluştu: {str(e)}")
    
    def _create_preview_window(self, platform, product, formatted_title, formatted_description):
        """Önizleme penceresini oluşturur (ayrı iş parçacığında)."""
        preview_window = tk.Toplevel(self.root)
        preview_window.title(f"{platform} Önizlemesi")
        preview_window.geometry("800x600")
        
        # Başlık
        ttk.Label(preview_window, text=f"Platform: {platform}", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Ürün bilgileri
        info_frame = ttk.LabelFrame(preview_window, text="Ürün Bilgileri")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(info_frame, text=f"Orijinal Başlık: {product['name']}", wraplength=750).pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(info_frame, text=f"Formatlanmış Başlık: {formatted_title}", wraplength=750, font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(info_frame, text=f"Fiyat: {product.get('new_price', product.get('price', 'N/A'))}").pack(anchor=tk.W, padx=10, pady=2)
        
        # Açıklama
        desc_frame = ttk.LabelFrame(preview_window, text="Formatlanmış Açıklama")
        desc_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Kaydırma çubuğu ile metin alanı
        scrollbar = ttk.Scrollbar(desc_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        description_text = tk.Text(desc_frame, wrap=tk.WORD, padx=10, pady=10, yscrollcommand=scrollbar.set)
        description_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=description_text.yview)
        
        # HTML içeriği gösterme
        if platform == "eBay" and formatted_description.strip().startswith("<"):
            description_text.insert(tk.END, "HTML İçeriği (eBay):\n\n")
            description_text.insert(tk.END, formatted_description)
        else:
            description_text.insert(tk.END, formatted_description)
        
        # Kapat butonu
        ttk.Button(preview_window, text="Kapat", command=preview_window.destroy).pack(pady=10)
    
    def start_scraping(self):
        """Çekme işlemini ayrı bir iş parçacığında başlatır."""
        self.update_status("Çekme işlemi başlatılıyor...")
        self.scrape_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.stop_requested = False
        
        # Marj ayarlarını al
        margins = {
            "0-5": float(self.margin_0_5_var.get().replace('x', '')),
            "5-10": float(self.margin_5_10_var.get().replace('x', '')),
            "10-20": float(self.margin_10_20_var.get().replace('x', '')),
            "20+": float(self.margin_20_plus_var.get().replace('x', ''))
        }
        
        # Fiyat hesaplayıcıyı yapılandır
        self.price_calculator.set_margins(margins)
        
        # İlerleme çubuğunu sıfırla
        self.update_progress(0)
        
        # Parametreleri al
        try:
            category = self.category_var.get()
            warehouse = self.warehouse_var.get()
            product_count = int(self.product_count_var.get())
            min_rating = float(self.min_rating_var.get())
            min_orders = int(self.min_orders_var.get())
            
            # Çekme işlemini ayrı bir iş parçacığında başlat
            self.scrape_thread = threading.Thread(
                target=self.scrape_products,
                args=(category, warehouse, product_count, min_rating, min_orders),
                daemon=True
            )
            self.scrape_thread.start()
            
        except ValueError as e:
            messagebox.showerror("Hata", f"Geçersiz parametre: {str(e)}")
            self.scrape_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
    
    def scrape_products(self, category, warehouse, product_count, min_rating, min_orders):
        """Seçilen kriterlere göre AliExpress'ten ürünleri çeker."""
        try:
            self.update_status(f"{category} kategorisinden {warehouse} deposundaki ürünler çekiliyor...")
            self.update_progress(5)
            
            # Kategori URL'sini al
            category_url = self.scraper.get_category_url(category)
            self.update_status(f"Kategori URL: {category_url}")
            
            # Ürünleri çek (durdurma kontrolü ile)
            products = []
            batch_size = min(50, product_count)  # Her seferde en fazla 50 ürün çek
            
            for offset in range(0, product_count, batch_size):
                if self.stop_requested:
                    self.update_status("Çekme işlemi kullanıcı tarafından durduruldu.")
                    break
                
                current_batch_size = min(batch_size, product_count - offset)
                self.update_status(f"Ürünler çekiliyor: {offset+1}-{offset+current_batch_size}/{product_count}")
                
                batch_products = self.scraper.scrape_products(
                    category_url, 
                    min_rating=min_rating, 
                    min_orders=min_orders, 
                    warehouse=warehouse, 
                    limit=current_batch_size,
                    offset=offset
                )
                
                products.extend(batch_products)
                
                # İlerleme çubuğunu güncelle
                progress = min(40, (offset + current_batch_size) * 40 / product_count)
                self.update_progress(progress)
                
                # Kısa bir bekleme ile UI'ın yanıt vermesine izin ver
                time.sleep(0.1)
            
            if self.stop_requested:
                return
            
            self.update_status(f"{len(products)} ürün bulundu. Tekrarlar filtreleniyor...")
            
            # Veritabanında zaten olan ürünleri filtrele
            filtered_products = self.db.filter_existing_products(products)
            self.update_status(f"Filtreleme sonrası: {len(filtered_products)} yeni ürün.")
            
            self.update_progress(50)
            
            if not filtered_products:
                self.update_status("Yeni ürün bulunamadı. İşlem tamamlandı.")
                self.root.after(0, lambda: self.scrape_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
                self.update_progress(100)
                return
            
            # Fiyatları hesapla
            for i, product in enumerate(filtered_products):
                if self.stop_requested:
                    self.update_status("Fiyat hesaplama işlemi kullanıcı tarafından durduruldu.")
                    break
                
                original_price = float(product['price'].replace('$', ''))
                new_price = self.price_calculator.calculate_price(original_price)
                product['original_price'] = original_price
                product['markup_factor'] = self.price_calculator.get_factor_for_price(original_price)
                product['new_price'] = new_price
                
                # Her 10 üründe bir ilerlemeyi güncelle
                if (i + 1) % 10 == 0:
                    progress = 50 + min(30, (i + 1) * 30 / len(filtered_products))
                    self.update_progress(progress)
            
            if self.stop_requested:
                return
            
            self.update_progress(80)
            
            # CSV'ye kaydet
            csv_path = self.save_to_csv(filtered_products)
            self.update_status(f"Ürünler {csv_path} dosyasına kaydedildi")
            
            # Veritabanına kaydet
            self.db.save_products(filtered_products)
            self.update_status(f"Ürünler veritabanına kaydedildi")
            
            self.update_progress(100)
            self.update_status("Çekme işlemi tamamlandı. CSV dosyasını inceleyin ve hazır olduğunuzda 'Yükle' butonuna tıklayın.")
            
            # CSV yolunu sakla
            self.csv_path = csv_path
            self.csv_var.set(csv_path)
            
            # Butonları güncelle
            self.root.after(0, lambda: self.upload_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.preview_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.scrape_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
            
        except Exception as e:
            self.update_status(f"Hata: {str(e)}")
            self.logger.error(f"Çekme işlemi sırasında hata: {str(e)}", exc_info=True)
            self.root.after(0, lambda: self.scrape_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
            self.db.log_error(str(e))
    
    def save_to_csv(self, products):
        """Ürünleri CSV dosyasına kaydeder."""
        df = pd.DataFrame(products)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"products_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        
        return csv_path
    
    def start_uploading(self):
        """Yükleme işlemini ayrı bir iş parçacığında başlatır."""
        self.update_status("Yükleme işlemi başlatılıyor...")
        self.upload_button.config(state=tk.DISABLED)
        self.scrape_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.stop_requested = False
        
        # Seçilen platformları al
        platforms = []
        if self.ebay_var.get():
            platforms.append("ebay")
        if self.walmart_var.get():
            platforms.append("walmart")
        if self.shopify_var.get():
            platforms.append("shopify")
        
        if not platforms:
            messagebox.showwarning("Platform Seçilmedi", "Lütfen en az bir platform seçin.")
            self.upload_button.config(state=tk.NORMAL)
            self.scrape_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            return
        
        # CSV dosyasını kontrol et
        csv_path = self.csv_var.get()
        if not csv_path:
            messagebox.showwarning("CSV Dosyası Seçilmedi", "Lütfen bir CSV dosyası seçin veya önce ürünleri çekin.")
            self.upload_button.config(state=tk.NORMAL)
            self.scrape_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            return
        
        # İlerleme çubuğunu sıfırla
        self.update_progress(0)
        
        # Yükleme işlemini ayrı bir iş parçacığında başlat
        self.upload_thread = threading.Thread(
            target=self.upload_products,
            args=(platforms, csv_path),
            daemon=True
        )
        self.upload_thread.start()
    
    def upload_products(self, platforms, csv_path):
        """Ürünleri seçilen platformlara yükler."""
        try:
            self.update_status(f"CSV dosyası okunuyor: {csv_path}")
            
            # CSV'yi oku
            df = pd.read_csv(csv_path)
            products = df.to_dict('records')
            
            self.update_status(f"{len(products)} ürün {', '.join(platforms)} platformlarına yükleniyor...")
            self.update_progress(10)
            
            # Her platforma yükle
            results = {}
            progress_step = 80 / len(platforms)
            current_progress = 10
            
            for platform in platforms:
                if self.stop_requested:
                    self.update_status(f"{platform} platformuna yükleme işlemi kullanıcı tarafından durduruldu.")
                    break
                
                self.update_status(f"{platform} platformuna yükleniyor...")
                
                # Ürünleri küçük gruplar halinde yükle
                batch_size = 5
                total_uploaded = 0
                
                for i in range(0, len(products), batch_size):
                    if self.stop_requested:
                        break
                    
                    batch = products[i:i+batch_size]
                    batch_uploaded = 0
                    
                    for product in batch:
                        if self.stop_requested:
                            break
                        
                        # Ürünü platforma göre formatla
                        formatted_product = product.copy()
                        formatted_product["formatted_title"] = self.formatter.format_title(product["name"], platform)
                        formatted_product["formatted_description"] = self.formatter.format_description(product, platform)
                        formatted_product["keywords"] = self.formatter.generate_keywords(product, platform)
                        
                        # Ürünü platforma yükle
                        success, result = self.platform_api.upload_product(platform, formatted_product)
                        
                        if success:
                            # Veritabanında yükleme durumunu güncelle
                            self.db.update_product_upload_status(product["id"], platform)
                            batch_uploaded += 1
                            self.update_status(f"{platform}: Ürün başarıyla yüklendi: {result}")
                        else:
                            self.update_status(f"{platform}: Ürün yüklenirken hata: {result}")
                        
                        # Kısa bir bekleme ile API limitlerini aşmayı önle
                        time.sleep(1)
                    
                    total_uploaded += batch_uploaded
                    
                    # İlerlemeyi güncelle
                    batch_progress = (i + len(batch)) / len(products) * progress_step
                    self.update_progress(current_progress + batch_progress)
                    
                    # Durum güncellemesi
                    self.update_status(f"{platform}: {i+len(batch)}/{len(products)} ürün işlendi, {total_uploaded} ürün yüklendi")
                    
                    # Kısa bir bekleme ile UI'ın yanıt vermesine izin ver
                    time.sleep(0.1)
                
                results[platform] = total_uploaded
                current_progress += progress_step
                
                if self.stop_requested:
                    break
            
            self.update_progress(100)
            
            # Sonuçları göster
            result_message = "Yükleme tamamlandı:\n"
            for platform, count in results.items():
                result_message += f"- {platform}: {count} ürün yüklendi\n"
            
            self.update_status(result_message)
            
            # Butonları güncelle
            self.root.after(0, lambda: self.scrape_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.upload_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
            
        except Exception as e:
            self.update_status(f"Hata: {str(e)}")
            self.logger.error(f"Yükleme işlemi sırasında hata: {str(e)}", exc_info=True)
            self.root.after(0, lambda: self.scrape_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.upload_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
            self.db.log_error(str(e))
    
    def stop_operations(self):
        """Devam eden işlemleri durdurur."""
        self.stop_requested = True
        self.update_status("İşlem durdurma talebi gönderildi. Lütfen bekleyin...")
        self.stop_button.config(state=tk.DISABLED)
    
    def update_status(self, message):
        """Durum mesajını kuyruğa ekler."""
        self.message_queue.put(message)
    
    def process_message_queue(self):
        """Mesaj kuyruğundaki mesajları işler."""
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                self._update_status_text(message)
        except queue.Empty:
            pass
        
        # Her 100ms'de bir kuyruğu kontrol et
        self.root.after(100, self.process_message_queue)
    
    def _update_status_text(self, message):
        """Durum metnini güncellemek için dahili metot."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Metni ekle ve otomatik kaydır
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        
        # Arayüzü hemen güncelle
        self.root.update_idletasks()
    
    def update_progress(self, value):
        """İlerleme değerini kuyruğa ekler."""
        self.progress_queue.put(value)
    
    def process_progress_queue(self):
        """İlerleme kuyruğundaki değerleri işler."""
        try:
            while not self.progress_queue.empty():
                value = self.progress_queue.get_nowait()
                self._update_progress_value(value)
        except queue.Empty:
            pass
        
        # Her 100ms'de bir kuyruğu kontrol et
        self.root.after(100, self.process_progress_queue)
    
    def _update_progress_value(self, value):
        """İlerleme çubuğu değerini güncellemek için dahili metot."""
        self.progress_var.set(value)
        # Arayüzü hemen güncelle
        self.root.update_idletasks()