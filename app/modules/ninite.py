"""Ninite entegrasyonu: seçimden URL üretir, indirici dosyasını izler."""
from __future__ import annotations

import os
import threading
import time
import webbrowser
from pathlib import Path

from ..core import logger
from ..core.paths import user_downloads
from .catalog import Catalog, CatalogApp

BASE = "https://ninite.com/"


def build_url(apps: list[CatalogApp]) -> str:
    slugs = [a.ninite for a in apps if a.ninite]
    if not slugs:
        return BASE
    return BASE + "-".join(slugs)


def open_site(apps: list[CatalogApp]) -> str:
    url = build_url(apps)
    logger.info(f"Ninite açılıyor: {url}")
    webbrowser.open(url)
    return url


def open_home() -> None:
    webbrowser.open(BASE)


def find_downloaded(since: float | None = None) -> list[Path]:
    folder = user_downloads()
    if not folder.exists():
        return []
    found = []
    for entry in folder.glob("Ninite*.exe"):
        try:
            if since is None or entry.stat().st_mtime >= since:
                found.append(entry)
        except OSError:
            continue
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def run_installer(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        import subprocess
        subprocess.Popen([str(path)], creationflags=0x00000010)
        logger.info(f"Ninite yükleyici başlatıldı: {path.name}")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warn(f"Ninite yükleyici çalıştırılamadı: {exc}")
        return False


class DownloadWatcher(threading.Thread):
    """İndirilenler klasöründe yeni Ninite*.exe dosyasını bekler."""

    def __init__(self, since: float | None = None, timeout: float = 600.0,
                 on_found=None, cancel_event: threading.Event | None = None):
        super().__init__(daemon=True)
        self.since = since if since is not None else time.time()
        self.timeout = timeout
        self.on_found = on_found
        self.cancel_event = cancel_event or threading.Event()

    def run(self) -> None:
        deadline = time.time() + self.timeout
        while time.time() < deadline and not self.cancel_event.is_set():
            found = find_downloaded(self.since)
            if found:
                if self.on_found:
                    try:
                        self.on_found(found[0])
                    except Exception:
                        pass
                return
            time.sleep(2)
