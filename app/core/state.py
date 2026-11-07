"""Oturum durumu: seçimler, tamamlanan adımlar, son çalıştırma bilgisi."""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from . import logger
from .paths import state_dir

STATE_FILE = state_dir() / "state.json"
DEFAULTS: dict[str, Any] = {
    "cleanup": [],
    "files": {"selected": [], "classify": False},
    "startup": {},
    "boot": {"enabled": False, "numproc": 0, "timeout": 30},
    "appx": [],
    "debloat": {},
    "ofgb": {},
    "programs": [],
    "install_drive": "C",
    "devlangs": [],
    "updates": [],
    "drivers": [],
    "power": {"enabled": False, "scheme": "ultimate"},
    "completed_steps": [],
    "last_run": None,
    "dry_run": False,
    "read_only": False,
    "language": "",
    "version": 1,
}

# Oturumlar arası hatırlanmaması gereken geçici alanlar
_TRANSIENT_KEYS = ("dry_run", "read_only")


def _deep_merge(base: dict, incoming: dict) -> dict:
    out = dict(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


class Session:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.data: dict[str, Any] = json.loads(json.dumps(DEFAULTS))
        self.load()
        if not self.data.get("last_run"):
            self.data["last_run"] = {"status": None, "at": None}

    # ------------------------------------------------------------------ io
    def load(self) -> None:
        if not STATE_FILE.exists():
            return
        try:
            raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key in _TRANSIENT_KEYS:
                    raw.pop(key, None)
                self.data = _deep_merge(DEFAULTS, raw)
        except Exception as exc:  # noqa: BLE001
            logger.warn(f"Durum dosyası okunamadı, varsayılanlar kullanılıyor: {exc}")

    def save(self) -> None:
        with self._lock:
            try:
                payload = {k: v for k, v in self.data.items() if k not in _TRANSIENT_KEYS}
                STATE_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                logger.warn(f"Durum kaydedilemedi: {exc}")

    # ----------------------------------------------------------------- get/set
    def get(self, key: str, default=None):
        with self._lock:
            return self.data.get(key, default)

    def set(self, key: str, value: Any, save: bool = True) -> None:
        with self._lock:
            self.data[key] = value
        if save:
            self.save()

    # --------------------------------------------------------------- helpers
    def mark_step(self, step_id: str) -> None:
        with self._lock:
            done = set(self.data.get("completed_steps") or [])
            done.add(step_id)
            self.data["completed_steps"] = sorted(done)
        self.save()

    def reset_steps(self) -> None:
        self.data["completed_steps"] = []
        self.save()

    def begin_run(self) -> None:
        self.data["last_run"] = {
            "status": "running",
            "at": datetime.now().isoformat(timespec="seconds"),
            "report": None,
        }
        self.save()

    def finish_run(self, status: str, report: dict | None = None) -> None:
        self.data["last_run"] = {
            "status": status,
            "at": datetime.now().isoformat(timespec="seconds"),
            "report": report,
        }
        self.save()

    def reset_selections(self) -> None:
        self.data = json.loads(json.dumps(DEFAULTS))
        self.save()


SESSION = Session()
