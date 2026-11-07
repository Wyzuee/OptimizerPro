"""Geri alma kayıtları: registry değerleri, dosya taşımaları, boot ayarları."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from . import logger
from .paths import backups_dir

UNDO_FILE = backups_dir() / "undo.json"


def _load() -> dict:
    if not UNDO_FILE.exists():
        return {"entries": []}
    try:
        data = json.loads(UNDO_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "entries" not in data:
            return {"entries": []}
        return data
    except Exception:
        return {"entries": []}


def _save(data: dict) -> None:
    try:
        UNDO_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warn(f"Geri alma kaydı yazılamadı: {exc}")


def record(kind: str, payload: dict[str, Any], note: str = "") -> None:
    """kind: registry | file | boot | startup | power"""
    data = _load()
    data["entries"].append(
        {
            "kind": kind,
            "note": note,
            "at": datetime.now().isoformat(timespec="seconds"),
            "payload": payload,
        }
    )
    _save(data)


def entries() -> list[dict]:
    return list(reversed(_load().get("entries", [])))


def clear() -> None:
    _save({"entries": []})


def count() -> int:
    return len(_load().get("entries", []))


def export_backup_file(prefix: str = "registry") -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return backups_dir() / f"{prefix}-{stamp}.reg"
