"""
Gelişmiş Loglama Sistemi
Renkli konsol çıktısı, dosya rotasyonu ve uzak loglama desteği.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Konsol çıktısı için renkli formatlayıcı."""

    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[41m",   # Red background
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.colored_levelname = f"{color}{self.BOLD}{record.levelname:8s}{self.RESET}"
        record.colored_name = f"\033[35m{record.name}\033[0m"
        return super().format(record)


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    app_name: str = "aliexpress_bot",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
):
    """Uygulamanın loglama altyapısını kurar.

    Args:
        log_dir: Log dosyalarının kaydedileceği dizin
        log_level: Minimum log seviyesi
        app_name: Uygulama adı (log dosya adı için)
        max_bytes: Maksimum log dosyası boyutu
        backup_count: Tutulacak eski log dosyası sayısı
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Root logger'ı yapılandır
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Mevcut handler'ları temizle
    root_logger.handlers.clear()

    # Konsol handler (renkli)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = "%(colored_levelname)s %(asctime)s │ %(colored_name)s │ %(message)s"
    console_handler.setFormatter(ColoredFormatter(console_format, datefmt="%H:%M:%S"))
    root_logger.addHandler(console_handler)

    # Ana dosya handler (boyut bazlı rotasyon)
    date_str = datetime.now().strftime("%Y%m%d")
    file_handler = RotatingFileHandler(
        log_path / f"{app_name}_{date_str}.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    file_handler.setFormatter(logging.Formatter(file_format))
    root_logger.addHandler(file_handler)

    # Hata dosyası handler (sadece ERROR ve üstü)
    error_handler = RotatingFileHandler(
        log_path / f"{app_name}_errors.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(file_format))
    root_logger.addHandler(error_handler)

    # Üçüncü parti kütüphanelerin log seviyesini düşür
    for lib in ["urllib3", "selenium", "pymongo", "werkzeug"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.info(f"Loglama sistemi başlatıldı - Seviye: {log_level}, Dizin: {log_dir}")


def get_logger(name: str) -> logging.Logger:
    """Belirtilen isimde bir logger döndürür."""
    return logging.getLogger(name)
