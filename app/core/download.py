"""İndirme yardımcıları: ilerleme, SHA256 doğrulama, boyut biçimlendirme."""
from __future__ import annotations

import hashlib
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from . import logger

USER_AGENT = "OptimizerPro/1.0 (+https://github.com/Raphire/Win11Debloat)"
BLOCKED_HOSTS = {"": 0}


def human_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}" if unit != "B" else f"{int(num)} B"
        num /= 1024.0
    return f"{num:.1f} PB"


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def download(
    url: str,
    target: str | Path,
    on_progress: Callable[[int, int], None] | None = None,
    timeout: float = 60.0,
    cancel_event=None,
) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"İndiriliyor: {url}")

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        total = int(response.headers.get("Content-Length") or 0)
        tmp = target.with_suffix(target.suffix + ".part")
        read = 0
        with open(tmp, "wb") as fh:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    fh.close()
                    tmp.unlink(missing_ok=True)
                    raise RuntimeError("İndirme iptal edildi")
                chunk = response.read(1024 * 128)
                if not chunk:
                    break
                fh.write(chunk)
                read += len(chunk)
                if on_progress:
                    try:
                        on_progress(read, total)
                    except Exception:
                        pass
        tmp.replace(target)
    logger.info(f"İndirme tamam: {target} ({human_size(target.stat().st_size)})")
    return target


def fetch_text(url: str, timeout: float = 20.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def verify(path: str | Path, expected_sha256: str) -> bool:
    try:
        actual = sha256(path)
    except Exception as exc:  # noqa: BLE001
        logger.warn(f"Hash hesaplanamadı: {exc}")
        return False
    ok = actual.upper() == expected_sha256.upper()
    if not ok:
        logger.error(f"SHA256 uyuşmuyor: {actual} != {expected_sha256}")
    return ok
