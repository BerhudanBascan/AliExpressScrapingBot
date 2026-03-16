# AliExpress Dropshipping Pro 🚀

## Profesyonel Çok Platformlu Dropshipping Otomasyon Sistemi

AliExpress'ten ürünleri otomatik çekerek eBay, Walmart, Shopify, Amazon ve Etsy platformlarına yüklemenizi sağlayan eksiksiz bir dropshipping otomasyon çözümü.

---

## ✨ Özellikler

### 🕷️ Akıllı Ürün Çekme

- AliExpress'ten otomatik ürün scraping (Selenium tabanlı)
- Anti-detection mekanizması (User-Agent rotasyonu, anti-bot bypass)
- Kategori bazlı filtreleme (puan, sipariş sayısı, depo)
- Proxy rotasyonu ve sağlık kontrolü
- Simülasyon modu (test amaçlı)

### 💰 Gelişmiş Fiyatlandırma

- 4 hazır fiyatlandırma stratejisi (Agresif, Moderato, Konservatif, Özel)
- Platform bazlı komisyon hesaplama
- Otomatik kâr optimizasyonu
- $X.99 yuvarlaması
- Kargo ve ek maliyet entegrasyonu

### 🏪 Çoklu Platform Desteği

- **eBay** - Inventory API & Offer API entegrasyonu
- **Shopify** - Admin REST API entegrasyonu
- **Walmart** - Marketplace API entegrasyonu
- **Amazon** - SP-API desteği (genişletilebilir)
- **Etsy** - API desteği (genişletilebilir)

### 📊 Web Dashboard

- Modern dark-theme arayüz (Flask tabanlı)
- Gerçek zamanlı istatistikler ve grafikler (Chart.js)
- Ürün yönetimi (CRUD, filtreleme, sayfalama)
- Canlı scraping/upload izleme
- Fiyat hesaplayıcı
- Veri dışa aktarma (CSV, JSON, Excel)

### 🔔 Bildirimler

- Telegram bot entegrasyonu
- Email bildirimleri
- Scraping/Upload tamamlandı alerts

### 🏗️ Profesyonel Mimari

- Modüler ve genişletilebilir yapı
- Singleton pattern ile konfigürasyon
- Rate limiting (Token bucket algoritması)
- Bellek ve dosya tabanlı cache
- Thread-safe operasyonlar
- Profesyonel loglama sistemi

---

## 📁 Proje Yapısı

```
├── main.py                  # Ana giriş noktası (CLI & Web)
├── config.py                # Singleton konfigürasyon yönetimi
├── requirements.txt         # Python bağımlılıkları
├── Dockerfile               # Docker imajı
├── docker-compose.yml       # Docker Compose (App + MongoDB + Redis)
├── .env.example             # Ortam değişkenleri şablonu
├── .gitignore               # Git ignore dosyası
│
├── database/                # Veritabanı katmanı
│   ├── models.py            # Veri modelleri (Product, Job, Analytics)
│   └── mongodb_manager.py   # MongoDB CRUD, indeksleme, aggregation
│
├── scrapers/                # Scraper modülleri
│   ├── base_scraper.py      # Temel scraper sınıfı (abstract)
│   ├── aliexpress_scraper.py # AliExpress scraper motoru
│   └── proxy_manager.py     # Proxy rotasyonu ve yönetimi
│
├── platforms/               # Platform API entegrasyonları
│   ├── base_platform.py     # Temel platform API (abstract)
│   ├── ebay_api.py          # eBay entegrasyonu
│   ├── shopify_api.py       # Shopify entegrasyonu
│   ├── walmart_api.py       # Walmart entegrasyonu
│   └── platform_manager.py  # Platform yönetici
│
├── services/                # İş mantığı katmanı
│   ├── price_engine.py      # Gelişmiş fiyat motoru
│   ├── formatter_engine.py  # Platform formatlayıcı
│   ├── export_manager.py    # CSV/JSON/Excel dışa aktarma
│   └── notification_service.py # Telegram & Email bildirimleri
│
├── utils/                   # Yardımcı modüller
│   ├── logger.py            # Gelişmiş loglama
│   ├── helpers.py           # Utility fonksiyonlar
│   ├── validators.py        # Veri validasyonu
│   ├── rate_limiter.py      # API rate limiter
│   └── cache_manager.py     # Bellek & dosya cache
│
└── web/                     # Web Dashboard
    ├── app.py               # Flask uygulama fabrikası
    ├── routes/              # Route modülleri
    │   ├── dashboard.py     # Dashboard sayfaları
    │   ├── products.py      # Ürün yönetimi
    │   ├── api.py           # REST API endpoints
    │   └── settings.py      # Ayarlar
    ├── templates/           # Jinja2 HTML şablonları
    │   ├── base.html        # Ana şablon
    │   ├── dashboard.html   # Dashboard
    │   ├── scraper.html     # Scraper kontrolü
    │   ├── products.html    # Ürün listesi
    │   ├── product_detail.html
    │   ├── upload.html      # Platform yükleme
    │   ├── analytics.html   # Analitik
    │   ├── settings.html    # Ayarlar
    │   ├── 404.html
    │   └── 500.html
    └── static/
        ├── css/style.css    # Premium dark theme CSS
        └── js/app.js        # Frontend JavaScript
```

---

## 🚀 Kurulum

### Gereksinimler

- Python 3.9+
- MongoDB 6.0+
- Chrome/Chromium (scraping için)

### 1. Yerel Kurulum

```bash
# Repoyu klonla
git clone <repo-url>
cd realaliexpress-botu

# Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt

# .env dosyasını oluştur
cp .env.example .env
# .env dosyasını düzenleyin

# Uygulamayı başlat
python main.py
```

### 2. Docker ile Kurulum

```bash
# Tüm servisleri başlat (App + MongoDB + Redis)
docker-compose up -d

# Admin panel ile başlat
docker-compose --profile admin up -d

# Logları görüntüle
docker-compose logs -f app
```

---

## 💻 Kullanım

### Web Dashboard

```bash
python main.py web
# veya direkt:
python main.py
```

Tarayıcınızda `http://localhost:5000` adresine gidin.

### CLI Scraping

```bash
# Varsayılan ayarlarla çek
python main.py scrape

# Özel ayarlarla çek
python main.py scrape -c "Consumer Electronics" -w US -l 100 -r 4.5 -o 200

# Simülasyon modunda çek (test)
python main.py scrape -c "Shoes" -l 20 -s
```

### Sağlık Kontrolü

```bash
python main.py health
```

---

## ⚙️ API Endpoints

| Endpoint                    | Metot  | Açıklama                |
| ---------------------------- | ------ | ----------------------- |
| `/api/stats`                 | GET    | Dashboard istatistikleri |
| `/api/scrape`                | POST   | Scraping başlat          |
| `/api/upload`                | POST   | Platform yükleme başlat  |
| `/api/job/<id>`              | GET    | İş durumu sorgula       |
| `/api/job/<id>/stop`         | POST   | İşi durdur              |
| `/api/products`              | GET    | Ürün listesi             |
| `/api/products/<id>`         | DELETE | Ürün sil                |
| `/api/products/delete-bulk`  | POST   | Toplu ürün sil           |
| `/api/export`                | POST   | Veri dışa aktar          |
| `/api/price/calculate`       | POST   | Fiyat hesapla            |
| `/api/health`                | GET    | Sağlık kontrolü         |

---

## 🔧 Konfigürasyon

### Platform API Ayarları

`.env` dosyasında platform API anahtarlarınızı yapılandırın:

```env
# eBay
EBAY_CLIENT_ID=your_client_id
EBAY_CLIENT_SECRET=your_client_secret
EBAY_REFRESH_TOKEN=your_refresh_token

# Shopify
SHOPIFY_SHOP_URL=your-store.myshopify.com
SHOPIFY_API_KEY=your_api_key
SHOPIFY_API_PASSWORD=your_password

# Walmart
WALMART_CLIENT_ID=your_client_id
WALMART_CLIENT_SECRET=your_client_secret
```

### Fiyatlandırma Stratejileri

Fiyatlandırma ayarları `price_settings.json` dosyasından veya web dashboard üzerinden yapılandırılabilir.

