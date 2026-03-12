"""
Products Routes
Ürün yönetimi sayfaları.
"""

import logging
from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash

logger = logging.getLogger(__name__)

products_bp = Blueprint("products", __name__)


@products_bp.route("/")
def list_products():
    """Ürün listesi sayfası."""
    try:
        db = current_app.config.get("DB")
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        status = request.args.get("status", None)
        category = request.args.get("category", None)
        search = request.args.get("search", None)
        sort_by = request.args.get("sort_by", "created_at")

        skip = (page - 1) * per_page
        products, total = db.get_products(
            status=status, category=category, search=search,
            sort_by=sort_by, skip=skip, limit=per_page
        ) if db else ([], 0)

        total_pages = (total + per_page - 1) // per_page

        return render_template(
            "products.html",
            products=products,
            total=total,
            page=page,
            total_pages=total_pages,
            per_page=per_page,
            status=status,
            category=category,
            search=search,
        )
    except Exception as e:
        logger.error(f"Ürün listesi hatası: {e}")
        return render_template("products.html", products=[], total=0, page=1, total_pages=0)


@products_bp.route("/<product_id>")
def product_detail(product_id):
    """Ürün detay sayfası."""
    try:
        db = current_app.config.get("DB")
        product = db.get_product(product_id) if db else None
        if not product:
            flash("Ürün bulunamadı.", "error")
            return redirect(url_for("products.list_products"))
        return render_template("product_detail.html", product=product)
    except Exception as e:
        logger.error(f"Ürün detay hatası: {e}")
        return redirect(url_for("products.list_products"))


@products_bp.route("/<product_id>/delete", methods=["POST"])
def delete_product(product_id):
    """Ürünü siler."""
    try:
        db = current_app.config.get("DB")
        if db and db.delete_product(product_id):
            flash("Ürün silindi.", "success")
        else:
            flash("Ürün silinemedi.", "error")
    except Exception as e:
        flash(f"Hata: {e}", "error")
    return redirect(url_for("products.list_products"))
