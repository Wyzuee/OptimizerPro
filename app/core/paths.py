"""Yol yönetimi: geliştirme ve tek-exe (donmuş) modda doğru dizinleri çözer."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Optimizer Pro"
APP_SLUG = "OptimizerPro"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """Paketlenmiş kaynakların kökü (PyInstaller _MEIPASS)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def project_root() -> Path:
    """Exe'nin / projenin bulunduğu klasör."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def _first_existing(*candidates: Path) -> Path:
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def data_dir() -> Path:
    return _first_existing(
        resource_root() / "app" / "data",
        resource_root() / "data",
    )


def assets_dir() -> Path:
    return _first_existing(
        resource_root() / "app" / "assets",
        resource_root() / "assets",
    )


def tools_dir() -> Path:
    return _first_existing(
        resource_root() / "tools",
        project_root() / "tools",
    )


def data_file(name: str) -> Path:
    return data_dir() / name


def asset(name: str) -> Path:
    return assets_dir() / name


def _appdata() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / APP_SLUG


def logs_dir() -> Path:
    p = _appdata() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def state_dir() -> Path:
    p = _appdata() / "state"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = _appdata() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def downloads_dir() -> Path:
    p = _appdata() / "downloads"
    p.mkdir(parents=True, exist_ok=True)
    return p


def backups_dir() -> Path:
    p = _appdata() / "backups"
    p.mkdir(parents=True, exist_ok=True)
    return p


def reports_dir() -> Path:
    p = _appdata() / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def internal_tools_dir() -> Path:
    p = _appdata() / "tools"
    p.mkdir(parents=True, exist_ok=True)
    return p


def user_desktop() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def user_downloads() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads"
