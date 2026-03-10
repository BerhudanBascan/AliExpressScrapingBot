"""
Bildirim Servisi
Telegram ve Email bildirimleri.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import threading
import requests

logger = logging.getLogger(__name__)


class NotificationService:
    """Bildirim gönderim servisi."""

    def __init__(self, config=None):
        self.config = config

    def send_notification(self, title: str, message: str, level: str = "info"):
        """Tüm aktif kanallara bildirim gönderir."""
        threading.Thread(
            target=self._send_all, args=(title, message, level), daemon=True
        ).start()

    def _send_all(self, title: str, message: str, level: str):
        if self.config:
            # Telegram
            if self.config.get("notifications", "telegram", "enabled", default=False):
                self._send_telegram(title, message, level)

            # Email
            if self.config.get("notifications", "email", "enabled", default=False):
                self._send_email(title, message, level)

    def _send_telegram(self, title: str, message: str, level: str):
        """Telegram bildirimi gönderir."""
        try:
            bot_token = self.config.get("notifications", "telegram", "bot_token", default="")
            chat_id = self.config.get("notifications", "telegram", "chat_id", default="")

            if not bot_token or not chat_id:
                return

            emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "📌")
            text = f"{emoji} *{title}*\n\n{message}"

            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            logger.debug(f"Telegram bildirimi gönderildi: {title}")

        except Exception as e:
            logger.error(f"Telegram bildirimi hatası: {e}")

    def _send_email(self, title: str, message: str, level: str):
        """Email bildirimi gönderir."""
        try:
            email_cfg = self.config.get("notifications", "email", default={})

            msg = MIMEMultipart()
            msg["Subject"] = f"[Dropshipping Bot] {title}"
            msg["From"] = email_cfg.get("from_addr", "")
            msg["To"] = email_cfg.get("to_addr", "")

            body = f"""
            <html>
            <body style="font-family:Arial,sans-serif;">
                <div style="background:#f5f5f5;padding:20px;border-radius:10px;">
                    <h2 style="color:#333;">{title}</h2>
                    <p style="color:#666;line-height:1.6;">{message}</p>
                    <hr style="border-color:#ddd;">
                    <p style="color:#999;font-size:12px;">AliExpress Dropshipping Pro</p>
                </div>
            </body>
            </html>"""

            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(email_cfg.get("smtp_host", ""), email_cfg.get("smtp_port", 587)) as server:
                server.starttls()
                server.login(email_cfg.get("username", ""), email_cfg.get("password", ""))
                server.send_message(msg)

            logger.debug(f"Email bildirimi gönderildi: {title}")

        except Exception as e:
            logger.error(f"Email bildirimi hatası: {e}")

    def send_scraping_complete(self, count: int, category: str):
        """Scraping tamamlandı bildirimi."""
        self.send_notification(
            "Scraping Tamamlandı",
            f"{category} kategorisinden {count} ürün başarıyla çekildi.",
            "success"
        )

    def send_upload_complete(self, platform: str, success: int, failed: int):
        """Upload tamamlandı bildirimi."""
        self.send_notification(
            "Yükleme Tamamlandı",
            f"{platform.upper()}: {success} başarılı, {failed} başarısız yükleme.",
            "success" if failed == 0 else "warning"
        )

    def send_error(self, error_msg: str, source: str = ""):
        """Hata bildirimi."""
        self.send_notification(
            f"Hata - {source}" if source else "Hata",
            error_msg,
            "error"
        )
