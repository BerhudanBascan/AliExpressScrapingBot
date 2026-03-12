"""
Dashboard Routes
Ana sayfa ve genel durum paneli.
"""

import logging
from flask import Blueprint, render_template, current_app, jsonify

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    """Ana dashboard sayfası."""
    try:
        db = current_app.config.get("DB")
        stats = db.get_dashboard_stats() if db else {}
        platform_manager = current_app.config.get("PLATFORM_MANAGER")
        platform_status = platform_manager.get_platform_status() if platform_manager else {}

        return render_template(
            "dashboard.html",
            stats=stats,
            platform_status=platform_status,
        )
    except Exception as e:
        logger.error(f"Dashboard hatası: {e}")
        return render_template("dashboard.html", stats={}, platform_status={})


@dashboard_bp.route("/scraper")
def scraper():
    """Scraper kontrol sayfası."""
    from scrapers.aliexpress_scraper import AliExpressScraper
    categories = AliExpressScraper.get_categories()
    return render_template("scraper.html", categories=categories)


@dashboard_bp.route("/upload")
def upload():
    """Platform yükleme sayfası."""
    platform_manager = current_app.config.get("PLATFORM_MANAGER")
    platform_status = platform_manager.get_platform_status() if platform_manager else {}
    return render_template("upload.html", platform_status=platform_status)


@dashboard_bp.route("/analytics")
def analytics():
    """Analitik dashboard sayfası."""
    try:
        db = current_app.config.get("DB")
        stats = db.get_dashboard_stats() if db else {}
        daily_stats = db.get_daily_scrape_stats(30) if db else []
        price_dist = db.get_price_distribution() if db else []

        return render_template(
            "analytics.html",
            stats=stats,
            daily_stats=daily_stats,
            price_distribution=price_dist,
        )
    except Exception as e:
        logger.error(f"Analytics hatası: {e}")
        return render_template("analytics.html", stats={}, daily_stats=[], price_distribution=[])
