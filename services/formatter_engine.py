"""
Platform Formatter Engine
Her platform için ürün başlık, açıklama ve anahtar kelime optimizasyonu.
"""

import re
import logging
from html import escape
from typing import List, Dict
import threading

logger = logging.getLogger(__name__)


class FormatterEngine:
    """Platform bazlı ürün formatlaması."""

    TITLE_LIMITS = {"ebay": 80, "walmart": 200, "shopify": 255, "amazon": 200, "etsy": 140}
    DESC_LIMITS = {"ebay": 4000, "walmart": 5000, "shopify": 10000, "amazon": 2000, "etsy": 5000}
    KEYWORD_LIMITS = {"ebay": 15, "walmart": 20, "shopify": 13, "amazon": 250, "etsy": 13}

    STOP_WORDS = {
        "the", "and", "for", "with", "this", "that", "from", "your", "will",
        "are", "was", "has", "have", "been", "not", "but", "can", "all",
    }

    def __init__(self):
        self.lock = threading.Lock()

    def format_title(self, title: str, platform: str) -> str:
        """Başlığı platform gereksinimlerine göre formatlar."""
        if not title:
            return ""

        with self.lock:
            cleaned = self._clean_text(title)
            limit = self.TITLE_LIMITS.get(platform.lower(), 80)

            # Platform spesifik optimizasyonlar
            if platform.lower() == "ebay":
                cleaned = self._optimize_ebay_title(cleaned)
            elif platform.lower() == "amazon":
                cleaned = self._optimize_amazon_title(cleaned)
            elif platform.lower() == "shopify":
                if len(cleaned) < 40:
                    cleaned += " - Premium Quality"

            # Uzunluk kontrolü
            if len(cleaned) > limit:
                cleaned = cleaned[:limit - 3] + "..."

            return cleaned

    def format_description(self, product: dict, platform: str) -> str:
        """Ürün açıklamasını platform'a göre formatlar."""
        with self.lock:
            formatters = {
                "ebay": self._format_ebay_description,
                "walmart": self._format_walmart_description,
                "shopify": self._format_shopify_description,
                "amazon": self._format_amazon_description,
                "etsy": self._format_etsy_description,
            }
            formatter = formatters.get(platform.lower(), self._format_default_description)
            return formatter(product)

    def generate_keywords(self, product: dict, platform: str) -> List[str]:
        """SEO anahtar kelimeler oluşturur."""
        name = product.get("name", "")
        description = product.get("description", "")
        category = product.get("category", "")

        all_text = f"{name} {description} {category}".lower()

        # Kelimeleri çıkar ve filtrele
        words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text)
        words = [w for w in words if w not in self.STOP_WORDS]

        # Frekansa göre sırala
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1

        sorted_words = sorted(set(words), key=lambda x: freq.get(x, 0), reverse=True)

        limit = self.KEYWORD_LIMITS.get(platform.lower(), 15)
        keywords = sorted_words[:limit]

        if category and category.lower() not in [k.lower() for k in keywords]:
            keywords.append(category.lower())

        return keywords

    def format_product_for_platform(self, product: dict, platform: str) -> dict:
        """Ürünü platform için tamamen formatlar."""
        formatted = product.copy()
        formatted["formatted_title"] = self.format_title(product.get("name", ""), platform)
        formatted["formatted_description"] = self.format_description(product, platform)
        formatted["keywords"] = self.generate_keywords(product, platform)
        formatted["tags"] = self.generate_keywords(product, platform)
        return formatted

    # ==================== PLATFORM FORMAT METHODS ====================

    def _format_ebay_description(self, product: dict) -> str:
        name = escape(product.get("name", ""))
        description = escape(product.get("description", ""))
        price = product.get("calculated_price") or product.get("new_price", "")
        image_url = product.get("image_url", "")
        specs = product.get("specifications", {})

        specs_html = ""
        if specs:
            specs_rows = "".join(
                f'<tr><td style="padding:8px;border:1px solid #e0e0e0;font-weight:600;">{escape(k)}</td>'
                f'<td style="padding:8px;border:1px solid #e0e0e0;">{escape(str(v))}</td></tr>'
                for k, v in specs.items()
            )
            specs_html = f'''
            <div style="margin:20px 0;">
                <h2 style="color:#1a1a2e;border-bottom:3px solid #e94560;padding-bottom:8px;">📋 Specifications</h2>
                <table style="width:100%;border-collapse:collapse;margin-top:10px;">{specs_rows}</table>
            </div>'''

        return f'''
        <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:900px;margin:0 auto;color:#333;">
            <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:30px;text-align:center;border-radius:10px 10px 0 0;">
                <h1 style="color:white;margin:0;font-size:24px;">{name}</h1>
            </div>

            {"<div style='text-align:center;padding:20px;'><img src='" + image_url + "' alt='" + name + "' style='max-width:500px;border-radius:10px;box-shadow:0 4px 15px rgba(0,0,0,0.1);'></div>" if image_url else ""}

            <div style="background:#f8f9fa;padding:20px;border-radius:8px;margin:15px 0;">
                <h2 style="color:#1a1a2e;border-bottom:3px solid #e94560;padding-bottom:8px;">📦 Product Description</h2>
                <p style="line-height:1.8;font-size:15px;">{description}</p>
            </div>

            {specs_html}

            <div style="background:#e8f5e9;padding:20px;border-radius:8px;margin:15px 0;">
                <h2 style="color:#2e7d32;">✅ Why Choose Us?</h2>
                <ul style="line-height:2;font-size:14px;">
                    <li><strong>Brand New & High Quality</strong> - Factory sealed packaging</li>
                    <li><strong>Fast Shipping</strong> - Ships within 1-3 business days</li>
                    <li><strong>Customer Satisfaction</strong> - 30-day money back guarantee</li>
                    <li><strong>Secure Payment</strong> - Your purchase is protected</li>
                </ul>
            </div>

            <div style="text-align:center;padding:20px;background:linear-gradient(135deg,#11998e 0%,#38ef7d 100%);border-radius:8px;margin:15px 0;">
                <h2 style="color:white;">🛒 Order Now!</h2>
                <p style="font-size:28px;font-weight:bold;color:white;">{price}</p>
                <p style="color:white;opacity:0.9;">Limited Stock Available - Don't Miss Out!</p>
            </div>

            <div style="text-align:center;font-size:11px;color:#999;margin-top:20px;padding:15px;border-top:1px solid #eee;">
                © {name} - All Rights Reserved
            </div>
        </div>'''

    def _format_walmart_description(self, product: dict) -> str:
        name = product.get("name", "")
        description = product.get("description", "")
        specs = product.get("specifications", {})

        spec_text = ""
        if specs:
            spec_text = "\n\nSPECIFICATIONS:\n" + "\n".join(
                f"• {k}: {v}" for k, v in specs.items()
            )

        return f"""{name.upper()}

PRODUCT DESCRIPTION:
{description}

KEY FEATURES:
• Brand New & High Quality
• Fast Shipping - Ships within 1-3 business days
• 30-Day Money Back Guarantee
• Customer Satisfaction Guaranteed
{spec_text}

WHY CHOOSE US:
✓ Trusted Seller
✓ Fast Delivery
✓ Excellent Customer Service
✓ Easy Return Policy

Order today and experience the difference!"""

    def _format_shopify_description(self, product: dict) -> str:
        name = escape(product.get("name", ""))
        description = escape(product.get("description", ""))
        specs = product.get("specifications", {})

        specs_html = ""
        if specs:
            rows = "".join(
                f'<tr><td style="padding:12px 15px;border-bottom:1px solid #f0f0f0;font-weight:600;color:#555;">{escape(k)}</td>'
                f'<td style="padding:12px 15px;border-bottom:1px solid #f0f0f0;">{escape(str(v))}</td></tr>'
                for k, v in specs.items()
            )
            specs_html = f'''
            <div class="product-specs" style="margin:30px 0;">
                <h3 style="font-size:18px;margin-bottom:15px;">📋 Specifications</h3>
                <table style="width:100%;border-collapse:collapse;">{rows}</table>
            </div>'''

        return f'''
        <div class="product-description" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.8;">
            <div style="margin-bottom:25px;">
                <p style="font-size:16px;color:#444;">{description}</p>
            </div>

            {specs_html}

            <div style="background:#f7f7f7;padding:25px;border-radius:12px;margin:25px 0;">
                <h3 style="margin-top:0;">🚚 Shipping & Returns</h3>
                <ul style="padding-left:20px;">
                    <li>Fast shipping - 1-3 business days processing</li>
                    <li>Secure packaging</li>
                    <li>30-day satisfaction guarantee</li>
                    <li>Easy returns & exchanges</li>
                </ul>
            </div>
        </div>'''

    def _format_amazon_description(self, product: dict) -> str:
        description = product.get("description", "")
        specs = product.get("specifications", {})
        bullets = [f"• {k}: {v}" for k, v in specs.items()]
        bullets.extend([
            "• Brand New & High Quality Product",
            "• Fast & Reliable Shipping",
            "• 100% Customer Satisfaction Guarantee",
        ])
        return f"{description}\n\n" + "\n".join(bullets)

    def _format_etsy_description(self, product: dict) -> str:
        name = product.get("name", "")
        description = product.get("description", "")
        return f"""✨ {name} ✨

{description}

💝 What makes this special:
• High-quality materials
• Carefully packaged for safe shipping
• Perfect for gifts

📦 Shipping:
• Ships within 1-3 business days
• Tracking number provided

💬 Questions? Feel free to message us - we'd love to help!

Thank you for shopping with us! ❤️"""

    def _format_default_description(self, product: dict) -> str:
        name = product.get("name", "")
        description = product.get("description", "")
        return f"{name}\n\n{description}"

    # ==================== HELPER METHODS ====================

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r'\s+', ' ', text).strip()
        cleaned = re.sub(r'[^\w\s\-.,;:!?&()\[\]{}\'\"/$#+@]', '', cleaned)
        return cleaned

    def _optimize_ebay_title(self, title: str) -> str:
        # eBay'de anahtar kelimeler önemli
        title = title.title()
        unnecessary = ["buy now", "best price", "free shipping", "hot sale"]
        for phrase in unnecessary:
            title = re.sub(re.escape(phrase), "", title, flags=re.IGNORECASE).strip()
        return re.sub(r'\s+', ' ', title).strip()

    def _optimize_amazon_title(self, title: str) -> str:
        # Amazon: Marka - Ürün Adı - Özellikler formatı
        parts = [p.strip() for p in title.split("-")]
        if len(parts) == 1:
            title = f"Premium {title}"
        return title.title()
