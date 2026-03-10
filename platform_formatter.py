import re
import logging
from html import escape
import threading

class PlatformFormatter:
    """
    Her platform için ürün açıklamalarını optimize eden sınıf.
    Her pazaryerinin özel gereksinimlerine göre içeriği formatlar.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        
        # Platform başlık uzunluk limitleri
        self.title_limits = {
            "eBay": 80,
            "Walmart": 200,
            "Shopify": 255
        }
        
        # Platform açıklama uzunluk limitleri
        self.description_limits = {
            "eBay": 4000,
            "Walmart": 5000,
            "Shopify": 10000
        }
        
        # Platform HTML desteği
        self.html_support = {
            "eBay": True,
            "Walmart": False,
            "Shopify": True
        }
        
        # Platform anahtar kelime limitleri
        self.keyword_limits = {
            "eBay": 15,
            "Walmart": 20,
            "Shopify": 13
        }
    
    def format_title(self, title, platform):
        """
        Başlığı platform gereksinimlerine göre formatlar.
        
        Args:
            title: Orijinal ürün başlığı
            platform: Platform adı
            
        Returns:
            Formatlanmış başlık
        """
        try:
            with self.lock:
                # Başlığı temizle
                clean_title = self._clean_text(title)
                
                # Uzunluk limitine göre kısalt
                limit = self.title_limits.get(platform.lower(), 80)
                if len(clean_title) > limit:
                    clean_title = clean_title[:limit-3] + "..."
                
                # Platform spesifik optimizasyonlar
                if platform.lower() == "ebay":
                    # eBay'de arama sonuçlarında öne çıkmak için anahtar kelimeleri başa ekle
                    if "electronic" in clean_title.lower() and not clean_title.lower().startswith("new"):
                        clean_title = "New " + clean_title
                
                elif platform.lower() == "walmart":
                    # Walmart'ta marka adını başa ekle
                    if "brand" in title.lower() and ":" in title:
                        brand_match = re.search(r"brand\s*:\s*([^\s,]+)", title.lower())
                        if brand_match:
                            brand = brand_match.group(1).title()
                            if not clean_title.startswith(brand):
                                clean_title = f"{brand} - {clean_title}"
                
                elif platform.lower() == "shopify":
                    # Shopify'da SEO için anahtar kelimeleri başlığa ekle
                    if len(clean_title) < 40 and "quality" not in clean_title.lower():
                        clean_title += " - High Quality"
                
                return clean_title
                
        except Exception as e:
            self.logger.error(f"Başlık formatlanırken hata: {str(e)}")
            return title[:self.title_limits.get(platform.lower(), 80)]
    
    def format_description(self, product, platform):
        """
        Ürün açıklamasını platform gereksinimlerine göre formatlar.
        
        Args:
            product: Ürün bilgilerini içeren sözlük
            platform: Platform adı
            
        Returns:
            Formatlanmış açıklama
        """
        try:
            with self.lock:
                # Platform şablonunu seç
                if platform.lower() == "ebay":
                    return self._format_for_ebay(product)
                elif platform.lower() == "walmart":
                    return self._format_for_walmart(product)
                elif platform.lower() == "shopify":
                    return self._format_for_shopify(product)
                else:
                    # Varsayılan format
                    return self._format_default(product)
                    
        except Exception as e:
            self.logger.error(f"Açıklama formatlanırken hata: {str(e)}")
            return product.get('description', '')
    
    def generate_keywords(self, product, platform):
        """
        Ürün için anahtar kelimeler oluşturur.
        
        Args:
            product: Ürün bilgilerini içeren sözlük
            platform: Platform adı
            
        Returns:
            Anahtar kelimeler listesi
        """
        try:
            with self.lock:
                name = product.get('name', '')
                description = product.get('description', '')
                category = product.get('category', '')
                
                # Anahtar kelimeleri çıkar
                all_text = f"{name} {description} {category}".lower()
                
                # Yaygın kelimeleri kaldır
                common_words = ['the', 'and', 'for', 'with', 'this', 'that', 'from', 'your', 'will']
                words = [word for word in re.findall(r'\b\w+\b', all_text) if len(word) > 3 and word not in common_words]
                
                # Tekrarları kaldır ve sırala
                unique_words = sorted(set(words), key=lambda x: all_text.count(x), reverse=True)
                
                # Platform limitine göre kısalt
                limit = self.keyword_limits.get(platform.lower(), 15)
                keywords = unique_words[:limit]
                
                # Kategori adını ekle
                if category.lower() not in [k.lower() for k in keywords]:
                    keywords.append(category.lower())
                
                return keywords
                
        except Exception as e:
            self.logger.error(f"Anahtar kelimeler oluşturulurken hata: {str(e)}")
            return []
    
    def _format_for_ebay(self, product):
        """eBay için ürün açıklaması formatlar."""
        try:
            name = product.get('name', '')
            description = product.get('description', '')
            price = product.get('new_price', '')
            image_url = product.get('image_url', '')
            
            # eBay HTML şablonu
            html_template = f"""
            <div style="font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto;">
                <h1 style="color: #0053a0; text-align: center;">{escape(name)}</h1>
                
                <div style="text-align: center; margin: 20px 0;">
                    <img src="{image_url}" alt="{escape(name)}" style="max-width: 500px; border: 1px solid #ddd; padding: 5px;">
                </div>
                
                <div style="background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h2 style="color: #e53238; border-bottom: 1px solid #ddd; padding-bottom: 10px;">Ürün Açıklaması</h2>
                    <p style="line-height: 1.6;">{escape(description)}</p>
                </div>
                
                <div style="background-color: #fff4e5; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h2 style="color: #f5af02; border-bottom: 1px solid #ddd; padding-bottom: 10px;">Özellikler</h2>
                    <ul style="line-height: 1.6;">
                        <li><strong>Yepyeni ve Yüksek Kaliteli</strong></li>
                        <li><strong>Hızlı Kargo</strong> - Siparişiniz 1-3 iş günü içinde gönderilecektir</li>
                        <li><strong>Müşteri Memnuniyeti</strong> - Herhangi bir sorunuz varsa lütfen bize ulaşın</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 20px 0; padding: 15px; background-color: #e6f2ff; border-radius: 5px;">
                    <h2 style="color: #0053a0;">Bugün Sipariş Verin!</h2>
                    <p style="font-size: 18px; font-weight: bold; color: #e53238;">{price}</p>
                    <p>Sınırlı stok mevcuttur - Kaçırmayın!</p>
                </div>
                
                <div style="font-size: 12px; color: #777; text-align: center; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 10px;">
                    <p>Telif hakkı © {escape(name)} - Tüm hakları saklıdır.</p>
                </div>
            </div>
            """
            
            # HTML uzunluk limitini kontrol et
            if len(html_template) > self.description_limits["ebay"]:
                # Açıklamayı kısalt
                max_desc_length = 1000
                if len(description) > max_desc_length:
                    description = description[:max_desc_length] + "..."
                
                # Yeni şablon oluştur
                html_template = f"""
                <div style="font-family: Arial, sans-serif;">
                    <h1 style="color: #0053a0;">{escape(name)}</h1>
                    <img src="{image_url}" alt="{escape(name)}" style="max-width: 400px;">
                    <h2>Ürün Açıklaması</h2>
                    <p>{escape(description)}</p>
                    <p><strong>Fiyat:</strong> {price}</p>
                </div>
                """
            
            return html_template
            
        except Exception as e:
            self.logger.error(f"eBay formatlaması sırasında hata: {str(e)}")
            return product.get('description', '')
    
    def _format_for_walmart(self, product):
        """Walmart için ürün açıklaması formatlar."""
        try:
            name = product.get('name', '')
            description = product.get('description', '')
            
            # Walmart HTML kullanımını desteklemez, düz metin formatı
            formatted_description = f"""
{name.upper()}

ÜRÜN AÇIKLAMASI:
{description}

ÖZELLİKLER:
- Yepyeni ve yüksek kaliteli
- Hızlı kargo - 1-3 iş günü içinde gönderim
- Müşteri memnuniyeti garantisi

NEDEN BİZDEN SATIN ALMALISINIZ:
✓ Güvenilir satıcı
✓ Hızlı teslimat
✓ Mükemmel müşteri hizmetleri
✓ Kolay iade politikası

Bugün sipariş verin ve farkı görün!
            """
            
            # Uzunluk limitini kontrol et
            if len(formatted_description) > self.description_limits["walmart"]:
                # Açıklamayı kısalt
                max_desc_length = 2000
                if len(description) > max_desc_length:
                    description = description[:max_desc_length] + "..."
                
                # Daha kısa bir format
                formatted_description = f"""
{name.upper()}

ÜRÜN AÇIKLAMASI:
{description}

Yepyeni ve yüksek kaliteli ürün. Hızlı kargo ve müşteri memnuniyeti garantisi.
                """
            
            return formatted_description
            
        except Exception as e:
            self.logger.error(f"Walmart formatlaması sırasında hata: {str(e)}")
            return product.get('description', '')
    
    def _format_for_shopify(self, product):
        """Shopify için ürün açıklaması formatlar."""
        try:
            name = product.get('name', '')
            description = product.get('description', '')
            price = product.get('new_price', '')
            image_url = product.get('image_url', '')
            specifications = product.get('specifications', {})
            
            # Shopify HTML şablonu
            html_template = f"""
            <div>
                <h2>{escape(name)}</h2>
                
                <div>
                    <img src="{image_url}" alt="{escape(name)}" style="max-width: 100%;">
                </div>
                
                <div>
                    <h3>Ürün Açıklaması</h3>
                    <p>{escape(description)}</p>
                </div>
            """
            
            # Özellikler tablosu ekle (varsa)
            if specifications:
                html_template += """
                <div>
                    <h3>Teknik Özellikler</h3>
                    <table border="1" cellpadding="5" cellspacing="0" style="width: 100%;">
                        <tr>
                            <th>Özellik</th>
                            <th>Değer</th>
                        </tr>
                """
                
                for key, value in specifications.items():
                    html_template += f"""
                        <tr>
                            <td>{escape(key)}</td>
                            <td>{escape(str(value))}</td>
                        </tr>
                    """
                
                html_template += """
                    </table>
                </div>
                """
            
            # Kargo ve garanti bilgileri
            html_template += """
                <div>
                    <h3>Kargo ve Garanti</h3>
                    <ul>
                        <li>Hızlı kargo - 1-3 iş günü içinde gönderim</li>
                        <li>Güvenli paketleme</li>
                        <li>Müşteri memnuniyeti garantisi</li>
                    </ul>
                </div>
            </div>
            """
            
            # HTML uzunluk limitini kontrol et
            if len(html_template) > self.description_limits["shopify"]:
                # Açıklamayı kısalt
                max_desc_length = 1500
                if len(description) > max_desc_length:
                    description = description[:max_desc_length] + "..."
                
                # Daha kısa bir şablon
                html_template = f"""
                <div>
                    <h2>{escape(name)}</h2>
                    <p>{escape(description)}</p>
                    <p>Hızlı kargo ve müşteri memnuniyeti garantisi.</p>
                </div>
                """
            
            return html_template
            
        except Exception as e:
            self.logger.error(f"Shopify formatlaması sırasında hata: {str(e)}")
            return product.get('description', '')
    
    def _format_default(self, product):
        """Varsayılan ürün açıklaması formatı."""
        try:
            name = product.get('name', '')
            description = product.get('description', '')
            price = product.get('new_price', '')
            
            formatted_description = f"""
{name}

ÜRÜN AÇIKLAMASI:
{description}

Fiyat: {price}
            """
            
            return formatted_description
            
        except Exception as e:
            self.logger.error(f"Varsayılan formatlama sırasında hata: {str(e)}")
            return product.get('description', '')
    
    def _clean_text(self, text):
        """Metni temizler ve formatlar."""
        if not text:
            return ""
        
        # Gereksiz boşlukları temizle
        clean = re.sub(r'\s+', ' ', text).strip()
        
        # Özel karakterleri temizle
        clean = re.sub(r'[^\w\s\-.,;:!?&()\[\]{}]', '', clean)
        
        return clean