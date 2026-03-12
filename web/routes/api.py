"""
REST API Endpoints
AJAX ve frontend iletişimi için JSON API'ler.
"""

import logging
import threading
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)

# Aktif işlemler takibi
active_jobs = {}


@api_bp.route("/stats")
def get_stats():
    """Dashboard istatistikleri."""
    try:
        db = current_app.config.get("DB")
        stats = db.get_dashboard_stats() if db else {}
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@api_bp.route("/scrape", methods=["POST"])
def start_scraping():
    """Scraping işlemini başlatır."""
    try:
        data = request.json or {}
        category = data.get("category", "Consumer Electronics")
        warehouse = data.get("warehouse", "US")
        limit = min(int(data.get("limit", 50)), 500)
        min_rating = float(data.get("min_rating", 4.0))
        min_orders = int(data.get("min_orders", 100))
        simulation = data.get("simulation", True)

        job_id = f"scrape_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        active_jobs[job_id] = {
            "type": "scrape",
            "status": "running",
            "progress": 0,
            "message": "Başlatılıyor...",
            "results": [],
            "started_at": datetime.utcnow().isoformat(),
        }

        def run_scrape():
            try:
                scraper = current_app.config.get("SCRAPER")
                db = current_app.config.get("DB")
                price_engine = current_app.config.get("PRICE_ENGINE")
                formatter = current_app.config.get("FORMATTER")
                notification = current_app.config.get("NOTIFICATION")

                def progress_cb(progress, message):
                    active_jobs[job_id]["progress"] = progress
                    active_jobs[job_id]["message"] = message

                products = scraper.scrape_products(
                    category=category,
                    warehouse=warehouse,
                    limit=limit,
                    min_rating=min_rating,
                    min_orders=min_orders,
                    use_simulation=simulation,
                    progress_callback=progress_cb,
                )

                active_jobs[job_id]["message"] = "Fiyatlar hesaplanıyor..."
                active_jobs[job_id]["progress"] = 70

                # Fiyatları hesapla
                for product in products:
                    price_result = price_engine.calculate_price(product.get("price", 0))
                    product["calculated_price"] = price_result["selling_price"]
                    product["markup_factor"] = price_result["factor"]
                    product["profit"] = price_result["profit"]
                    product["new_price"] = price_result["formatted_price"]

                active_jobs[job_id]["message"] = "Filtre uygulanıyor..."
                active_jobs[job_id]["progress"] = 80

                # Mevcut ürünleri filtrele
                if db:
                    products = db.filter_existing_products(products)

                active_jobs[job_id]["message"] = "Veritabanına kaydediliyor..."
                active_jobs[job_id]["progress"] = 90

                # Kaydet
                if db and products:
                    db.save_products(products)

                active_jobs[job_id]["status"] = "completed"
                active_jobs[job_id]["progress"] = 100
                active_jobs[job_id]["message"] = f"{len(products)} ürün başarıyla çekildi ve kaydedildi"
                active_jobs[job_id]["results"] = [{"id": p.get("id"), "name": p.get("name"), "price": p.get("new_price")} for p in products[:50]]

                if notification:
                    notification.send_scraping_complete(len(products), category)

            except Exception as e:
                logger.error(f"Scraping hatası: {e}", exc_info=True)
                active_jobs[job_id]["status"] = "error"
                active_jobs[job_id]["message"] = str(e)

        # App context'i thread'e taşı
        app = current_app._get_current_object()
        def thread_target():
            with app.app_context():
                run_scrape()

        threading.Thread(target=thread_target, daemon=True).start()

        return jsonify({"success": True, "job_id": job_id})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@api_bp.route("/upload", methods=["POST"])
def start_upload():
    """Platform yükleme işlemini başlatır."""
    try:
        data = request.json or {}
        platforms = data.get("platforms", [])
        product_ids = data.get("product_ids", [])  # boş ise tüm ürünler

        if not platforms:
            return jsonify({"success": False, "error": "Platform seçilmedi"})

        job_id = f"upload_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        active_jobs[job_id] = {
            "type": "upload",
            "status": "running",
            "progress": 0,
            "message": "Başlatılıyor...",
            "results": {},
            "started_at": datetime.utcnow().isoformat(),
        }

        app = current_app._get_current_object()

        def run_upload():
            with app.app_context():
                try:
                    db = app.config.get("DB")
                    platform_manager = app.config.get("PLATFORM_MANAGER")
                    formatter = app.config.get("FORMATTER")
                    notification = app.config.get("NOTIFICATION")

                    # Ürünleri getir
                    if product_ids:
                        products = [db.get_product(pid) for pid in product_ids]
                        products = [p for p in products if p]
                    else:
                        products, _ = db.get_products(status="scraped", limit=100)

                    if not products:
                        active_jobs[job_id]["status"] = "completed"
                        active_jobs[job_id]["message"] = "Yüklenecek ürün bulunamadı"
                        return

                    total = len(products) * len(platforms)
                    completed = 0
                    results = {p: {"success": 0, "failed": 0} for p in platforms}

                    for platform in platforms:
                        for product in products:
                            try:
                                formatted = formatter.format_product_for_platform(product, platform)
                                success, result = platform_manager.upload_product(platform, formatted)

                                if success:
                                    results[platform]["success"] += 1
                                    if db:
                                        db.update_upload_status(
                                            product.get("aliexpress_id") or product.get("id", ""),
                                            platform, "success", result
                                        )
                                else:
                                    results[platform]["failed"] += 1
                                    logger.warning(f"Upload hatası ({platform}): {result}")
                            except Exception as e:
                                results[platform]["failed"] += 1
                                logger.error(f"Upload hatası: {e}")

                            completed += 1
                            active_jobs[job_id]["progress"] = (completed / total) * 100
                            active_jobs[job_id]["message"] = f"{platform}: {completed}/{total} işlendi"

                    active_jobs[job_id]["status"] = "completed"
                    active_jobs[job_id]["progress"] = 100
                    active_jobs[job_id]["results"] = results
                    active_jobs[job_id]["message"] = "Yükleme tamamlandı"

                    if notification:
                        for p, r in results.items():
                            notification.send_upload_complete(p, r["success"], r["failed"])

                except Exception as e:
                    active_jobs[job_id]["status"] = "error"
                    active_jobs[job_id]["message"] = str(e)

        threading.Thread(target=run_upload, daemon=True).start()
        return jsonify({"success": True, "job_id": job_id})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@api_bp.route("/job/<job_id>")
def get_job_status(job_id):
    """İş durumunu sorgular."""
    job = active_jobs.get(job_id)
    if job:
        return jsonify({"success": True, "data": job})
    return jsonify({"success": False, "error": "İş bulunamadı"})


@api_bp.route("/job/<job_id>/stop", methods=["POST"])
def stop_job(job_id):
    """İşi durdurur."""
    try:
        scraper = current_app.config.get("SCRAPER")
        if scraper:
            scraper.request_stop()
        if job_id in active_jobs:
            active_jobs[job_id]["status"] = "stopped"
            active_jobs[job_id]["message"] = "İş durduruldu"
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@api_bp.route("/products", methods=["GET"])
def api_get_products():
    """Ürün listesi API."""
    try:
        db = current_app.config.get("DB")
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        status = request.args.get("status")
        category = request.args.get("category")
        search = request.args.get("search")

        skip = (page - 1) * limit
        products, total = db.get_products(
            status=status, category=category, search=search,
            skip=skip, limit=limit
        ) if db else ([], 0)

        return jsonify({
            "success": True,
            "data": products,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@api_bp.route("/products/<product_id>", methods=["DELETE"])
def api_delete_product(product_id):
    """Ürün silme API."""
    try:
        db = current_app.config.get("DB")
        if db and db.delete_product(product_id):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Ürün silinemedi"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@api_bp.route("/products/delete-bulk", methods=["POST"])
def api_bulk_delete():
    """Toplu ürün silme API."""
    try:
        data = request.json or {}
        product_ids = data.get("product_ids", [])
        db = current_app.config.get("DB")
        if db:
            count = db.delete_products(product_ids)
            return jsonify({"success": True, "deleted": count})
        return jsonify({"success": False, "error": "DB bağlantısı yok"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@api_bp.route("/export", methods=["POST"])
def export_products():
    """Ürünleri dışa aktarır."""
    try:
        data = request.json or {}
        format_type = data.get("format", "csv")
        db = current_app.config.get("DB")
        export_manager = current_app.config.get("EXPORT_MANAGER")

        products, _ = db.get_products(limit=10000) if db else ([], 0)

        if format_type == "csv":
            path = export_manager.export_to_csv(products)
        elif format_type == "json":
            path = export_manager.export_to_json(products)
        elif format_type == "excel":
            path = export_manager.export_to_excel(products)
        else:
            return jsonify({"success": False, "error": "Geçersiz format"})

        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@api_bp.route("/price/calculate", methods=["POST"])
def calculate_price():
    """Fiyat hesaplama API."""
    try:
        data = request.json or {}
        original_price = float(data.get("price", 0))
        platform = data.get("platform")

        price_engine = current_app.config.get("PRICE_ENGINE")
        result = price_engine.calculate_price(original_price, platform)

        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@api_bp.route("/health")
def health_check():
    """Sistem sağlık kontrolü."""
    try:
        db = current_app.config.get("DB")
        db_health = db.health_check() if db else {"status": "not connected"}

        return jsonify({
            "success": True,
            "status": "healthy",
            "database": db_health,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return jsonify({"success": False, "status": "unhealthy", "error": str(e)})
