"""Uygulama günlüğü: dönen dosya + bellek içi son satırlar."""
from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Callable, Deque

from .paths import logs_dir

_MAX_MEMORY_LINES = 5000
VERBOSE = 15
_buffer: Deque[str] = deque(maxlen=_MAX_MEMORY_LINES)
_subscribers: list[Callable[[str], None]] = []
_lock = threading.Lock()
_configured = False


def configure() -> logging.Logger:
    global _configured
    logger = logging.getLogger("optimizerpro")
    if _configured:
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    stamp = datetime.now().strftime("%Y%m%d")
    handler = RotatingFileHandler(
        logs_dir() / f"optimizer-{stamp}.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
    logging.addLevelName(VERBOSE, "VERBOSE")
    _configured = True
    return logger


def get() -> logging.Logger:
    return configure()


def subscribe(callback: Callable[[str], None]) -> None:
    with _lock:
        _subscribers.append(callback)


def unsubscribe(callback: Callable[[str], None]) -> None:
    with _lock:
        if callback in _subscribers:
            _subscribers.remove(callback)


def log(message: str, level: int = logging.INFO) -> None:
    """Hem dosyaya hem belleğe hem abonelere yazar."""
    logger = configure()
    logger.log(level, message)

    line = f"[{datetime.now():%H:%M:%S}] {message}"
    with _lock:
        _buffer.append(line)
        targets = list(_subscribers)
    for cb in targets:
        try:
            cb(line)
        except Exception:  # abone hatası uygulamayı durdurmaz
            pass


def info(message: str) -> None:
    log(message, logging.INFO)


def warn(message: str) -> None:
    log(message, logging.WARNING)


def error(message: str) -> None:
    log(message, logging.ERROR)


def verbose(message: str) -> None:
    """Ayrıntılı tanılama satırı (arayüzde gösterilmez, dosyaya yazılır)."""
    configure().log(VERBOSE, message)


def recent(limit: int = 2000) -> list[str]:
    with _lock:
        return list(_buffer)[-limit:]


def current_log_path() -> str:
    stamp = datetime.now().strftime("%Y%m%d")
    return str(logs_dir() / f"optimizer-{stamp}.log")
