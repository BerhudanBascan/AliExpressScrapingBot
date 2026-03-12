"""
Flask Web Uygulaması
Ana web sunucusu ve uygulama fabrikası.
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask, render_template, jsonify
from flask_cors import CORS

# Proje kök dizinini path'e ekle
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import Config
from database.mongodb_manager import MongoDB
from services.price_engine import PriceEngine
from services.formatter_engine import FormatterEngine
from services.export_manager import ExportManager
from services.notification_service import NotificationService
from scrapers.aliexpress_scraper import AliExpressScraper
from scrapers.proxy_manager import ProxyManager
from platforms.platform_manager import PlatformManager

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Flask uygulama fabrikası."""

    # Flask uygulamasını oluştur
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    # Konfigürasyon
    config = Config()
    app.secret_key = config.get("app", "secret_key", default="default-secret-key")
    app.config["DEBUG"] = config.get("app", "debug", default=False)

    # CORS
    CORS(app)

    # Servisleri başlat ve app context'e ekle
    try:
        app.config["APP_CONFIG"] = config
        app.config["DB"] = MongoDB(config)
        app.config["PRICE_ENGINE"] = PriceEngine()
        app.config["FORMATTER"] = FormatterEngine()
        app.config["EXPORT_MANAGER"] = ExportManager()
        app.config["NOTIFICATION"] = NotificationService(config)
        app.config["PROXY_MANAGER"] = ProxyManager(config)
        app.config["SCRAPER"] = AliExpressScraper(config, app.config["PROXY_MANAGER"])
        app.config["PLATFORM_MANAGER"] = PlatformManager(config)
    except Exception as e:
        logger.error(f"Servis başlatma hatası: {e}")

    # Blueprint'leri kaydet
    from web.routes.dashboard import dashboard_bp
    from web.routes.products import products_bp
    from web.routes.api import api_bp
    from web.routes.settings import settings_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp, url_prefix="/products")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(settings_bp, url_prefix="/settings")

    # Hata yöneticileri
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    # Context processor
    @app.context_processor
    def inject_globals():
        return {
            "app_name": config.get("app", "name", default="AliExpress Dropshipping Pro"),
            "year": __import__("datetime").datetime.now().year,
        }

    logger.info("Flask uygulaması oluşturuldu")
    return app
