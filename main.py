"""
AliExpress Dropshipping Pro - Ana Giriş Noktası
Profesyonel çok platformlu dropshipping otomasyon sistemi.
"""

import os
import sys
import argparse
import logging

# Proje kökünü path'e ekle
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def check_dependencies():
    """Zorunlu bağımlılıkları kontrol eder."""
    required = [
        ("flask", "Flask"),
        ("pymongo", "pymongo"),
        ("selenium", "selenium"),
        ("dotenv", "python-dotenv"),
        ("requests", "requests"),
    ]

    missing = []
    for import_name, package_name in required:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)

    if missing:
        print("⚠️  Eksik bağımlılıklar tespit edildi:")
        for pkg in missing:
            print(f"   - {pkg}")
        print(f"\n🔧 Yüklemek için: pip install {' '.join(missing)}")
        print(f"   veya: pip install -r requirements.txt")

        response = input("\nŞimdi yüklensin mi? (e/h): ").strip().lower()
        if response in ("e", "y", "yes", "evet"):
            import subprocess
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r",
                os.path.join(PROJECT_ROOT, "requirements.txt")
            ])
            print("✅ Bağımlılıklar yüklendi")
        else:
            print("❌ Bağımlılıklar olmadan devam edilemez")
            sys.exit(1)


def setup_directories():
    """Gerekli dizinleri oluşturur."""
    dirs = ["logs", "exports", "cache", "data"]
    for d in dirs:
        path = os.path.join(PROJECT_ROOT, d)
        os.makedirs(path, exist_ok=True)


def run_web():
    """Flask web sunucusunu başlatır."""
    from utils.logger import setup_logging
    setup_logging(level="INFO", app_name="DropShipPro")

    from web.app import create_app
    app = create_app()

    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", 5000))
    debug = os.environ.get("APP_DEBUG", "true").lower() == "true"

    logger = logging.getLogger(__name__)
    logger.info(f"🚀 AliExpress Dropshipping Pro başlatılıyor...")
    logger.info(f"🌐 Dashboard: http://localhost:{port}")
    logger.info(f"📊 API: http://localhost:{port}/api/health")

    print(f"""
╔══════════════════════════════════════════════════╗
║    🚀 AliExpress Dropshipping Pro v2.0           ║
║    ────────────────────────────────               ║
║    Dashboard: http://localhost:{port:<8}            ║
║    API:       http://localhost:{port}/api/health  ║
║    Mode:      {'⚡ Debug' if debug else '🔒 Production':<20}         ║
╚══════════════════════════════════════════════════╝
    """)

    app.run(host=host, port=port, debug=debug, threaded=True)


def run_scrape(args):
    """CLI üzerinden scraping yapar."""
    from utils.logger import setup_logging
    setup_logging(level="INFO", app_name="DropShipPro-CLI")

    from config import Config
    from scrapers.proxy_manager import ProxyManager
    from scrapers.aliexpress_scraper import AliExpressScraper
    from services.price_engine import PriceEngine

    logger = logging.getLogger(__name__)
    config = Config()

    proxy_manager = ProxyManager(config)
    scraper = AliExpressScraper(config, proxy_manager)
    price_engine = PriceEngine()

    logger.info(f"Scraping başlatılıyor: {args.category}, {args.limit} ürün")

    def progress(pct, msg):
        print(f"\r[{'█' * int(pct / 2) + '░' * (50 - int(pct / 2))}] {pct:.0f}% - {msg}", end="", flush=True)

    products = scraper.scrape_products(
        category=args.category,
        warehouse=args.warehouse,
        limit=args.limit,
        min_rating=args.min_rating,
        min_orders=args.min_orders,
        use_simulation=args.simulation,
        progress_callback=progress,
    )

    print(f"\n\n✅ {len(products)} ürün çekildi")

    # Fiyat hesapla
    for product in products:
        result = price_engine.calculate_price(product.get("price", 0))
        product["new_price"] = result["formatted_price"]
        product["profit"] = result["profit"]

    # Veritabanına kaydet
    if products:
        try:
            from database.mongodb_manager import MongoDB
            db = MongoDB(config)
            success, errors = db.save_products(products)
            print(f"💾 {success} ürün kaydedildi, {errors} hata")
        except Exception as e:
            logger.warning(f"Veritabanı kaydı atlandı: {e}")

    # İlk 10 ürünü göster
    print(f"\n{'='*60}")
    for i, p in enumerate(products[:10], 1):
        print(f"  {i}. {p.get('name', 'N/A')[:50]}")
        print(f"     Orijinal: ${p.get('price', 0):.2f} → Yeni: {p.get('new_price', 'N/A')} (Kâr: ${p.get('profit', 0):.2f})")

    scraper.close_driver()


def main():
    """Ana giriş noktası."""
    parser = argparse.ArgumentParser(
        description="AliExpress Dropshipping Pro - Profesyonel Dropshipping Botu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Komutlar")

    # web komutu
    web_parser = subparsers.add_parser("web", help="Web dashboard'u başlat")

    # scrape komutu
    scrape_parser = subparsers.add_parser("scrape", help="CLI üzerinden ürün çek")
    scrape_parser.add_argument("--category", "-c", default="Consumer Electronics", help="Kategori")
    scrape_parser.add_argument("--warehouse", "-w", default="US", help="Depo (US, EU, UK, CN)")
    scrape_parser.add_argument("--limit", "-l", type=int, default=50, help="Ürün sayısı")
    scrape_parser.add_argument("--min-rating", "-r", type=float, default=4.0, help="Min puan")
    scrape_parser.add_argument("--min-orders", "-o", type=int, default=100, help="Min sipariş")
    scrape_parser.add_argument("--simulation", "-s", action="store_true", help="Simülasyon modu")

    # health komutu
    health_parser = subparsers.add_parser("health", help="Sistem sağlık kontrolü")

    args = parser.parse_args()

    # Önce kurulum
    check_dependencies()
    setup_directories()

    if args.command == "web":
        run_web()
    elif args.command == "scrape":
        run_scrape(args)
    elif args.command == "health":
        run_health_check()
    else:
        # Varsayılan: web dashboard
        run_web()


def run_health_check():
    """Sistem sağlık kontrolü."""
    print("🏥 Sistem Sağlık Kontrolü")
    print("=" * 40)

    # Python
    print(f"✅ Python: {sys.version.split()[0]}")

    # MongoDB
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        print("✅ MongoDB: Bağlı")
        client.close()
    except Exception as e:
        print(f"❌ MongoDB: {e}")

    # Bağımlılıklar
    packages = ["flask", "selenium", "requests", "pymongo", "dotenv"]
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg} - eksik!")

    # Dizinler
    for d in ["logs", "exports", "cache"]:
        path = os.path.join(PROJECT_ROOT, d)
        status = "✅" if os.path.exists(path) else "❌"
        print(f"  {status} {d}/")


if __name__ == "__main__":
    main()