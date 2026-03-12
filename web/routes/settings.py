"""
Settings Routes
Uygulama ayarları yönetimi.
"""

import logging
from flask import Blueprint, render_template, request, current_app, jsonify, redirect, url_for, flash

logger = logging.getLogger(__name__)

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/")
def settings_page():
    """Ayarlar sayfası."""
    try:
        config = current_app.config.get("APP_CONFIG")
        price_engine = current_app.config.get("PRICE_ENGINE")
        platform_manager = current_app.config.get("PLATFORM_MANAGER")

        return render_template(
            "settings.html",
            config=config.to_dict() if config else {},
            price_settings=price_engine.get_settings() if price_engine else {},
            platform_status=platform_manager.get_platform_status() if platform_manager else {},
        )
    except Exception as e:
        logger.error(f"Ayarlar hatası: {e}")
        return render_template("settings.html", config={}, price_settings={}, platform_status={})


@settings_bp.route("/pricing", methods=["POST"])
def update_pricing():
    """Fiyatlandırma ayarlarını günceller."""
    try:
        data = request.json or request.form.to_dict()
        price_engine = current_app.config.get("PRICE_ENGINE")

        if "shipping_cost" in data:
            price_engine.shipping_cost = float(data["shipping_cost"])
        if "min_profit" in data:
            price_engine.min_profit = float(data["min_profit"])
        if "active_strategy" in data:
            price_engine.active_strategy = data["active_strategy"]
        if "margins" in data:
            price_engine.set_margins(data["margins"])

        price_engine.save_settings()

        if request.is_json:
            return jsonify({"success": True})
        flash("Fiyat ayarları güncellendi", "success")
        return redirect(url_for("settings.settings_page"))
    except Exception as e:
        if request.is_json:
            return jsonify({"success": False, "error": str(e)})
        flash(f"Hata: {e}", "error")
        return redirect(url_for("settings.settings_page"))
