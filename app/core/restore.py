"""Geri alma motoru: undo.json kayıtlarını uygular."""
from __future__ import annotations

import os
from pathlib import Path

from . import logger, ps, registry, undo


def restore_all(dry_run: bool = False) -> tuple[int, int, list[str]]:
    """Kayıtlı tüm değişiklikleri geri alır. (başarılı, başarısız, mesajlar)"""
    entries = undo.entries()
    ok = fail = 0
    messages: list[str] = []

    for entry in entries:
        kind = entry.get("kind")
        payload = entry.get("payload") or {}
        try:
            if kind == "registry":
                if dry_run:
                    messages.append(f"[dry-run] registry: {payload.get('path')}\\{payload.get('name')}")
                    ok += 1
                elif registry.restore(payload):
                    ok += 1
                else:
                    fail += 1
                    messages.append(f"registry geri yüklenemedi: {payload.get('path')}")

            elif kind == "file":
                src = Path(payload.get("src", ""))
                dst = Path(payload.get("dst", ""))
                if dry_run:
                    messages.append(f"[dry-run] taşı: {src} -> {dst}")
                    ok += 1
                elif src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(src, dst)
                    ok += 1
                else:
                    fail += 1
                    messages.append(f"dosya bulunamadı: {src}")

            elif kind == "power":
                guid = payload.get("guid")
                if guid:
                    if not dry_run:
                        ps.run_command(["powercfg", "/setactive", guid], timeout=30)
                    ok += 1
                else:
                    fail += 1

            elif kind == "boot":
                backup = payload.get("backup")
                if backup and Path(backup).exists():
                    if not dry_run:
                        ps.run_command(["bcdedit", "/import", backup], timeout=60)
                    ok += 1
                else:
                    fail += 1
            else:
                messages.append(f"bilinmeyen kayıt türü: {kind}")
        except Exception as exc:  # noqa: BLE001
            fail += 1
            messages.append(f"{kind}: {exc}")

    logger.info(f"Geri alma tamamlandı: {ok} başarılı, {fail} başarısız")
    return ok, fail, messages
