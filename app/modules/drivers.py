"""Sürücü envanteri, yedekleme ve üretici yönlendirmesi."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..core import logger, ps
from ..core.paths import backups_dir


@dataclass
class DriverInfo:
    name: str
    provider: str
    version: str
    date: str
    inf: str


def inventory(dry_run: bool = False) -> list[DriverInfo]:
    if dry_run:
        return []
    data = ps.ps_json(
        "Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceName } | "
        "Select-Object DeviceName,DriverProviderName,DriverVersion,DriverDate,InfName | "
        "ConvertTo-Json -Compress -Depth 2",
        timeout=180, default=[],
    ) or []
    if isinstance(data, dict):
        data = [data]
    out = []
    for row in data:
        if not isinstance(row, dict):
            continue
        out.append(DriverInfo(
            name=str(row.get("DeviceName") or ""),
            provider=str(row.get("DriverProviderName") or ""),
            version=str(row.get("DriverVersion") or ""),
            date=str(row.get("DriverDate") or ""),
            inf=str(row.get("InfName") or ""),
        ))
    logger.info(f"{len(out)} sürücü envanteri alındı")
    return out


def export_backup(dry_run: bool = False) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = backups_dir() / f"drivers-{stamp}"
    if dry_run:
        logger.info(f"[DRY-RUN] Sürücüler yedeklenecek: {folder}")
        return str(folder)
    folder.mkdir(parents=True, exist_ok=True)
    res = ps.run_command(
        ["pnputil", "/export-driver", "*", str(folder)],
        timeout=1800, label="pnputil export-driver",
    )
    if res.ok:
        logger.info(f"Sürücüler yedeklendi: {folder}")
    else:
        logger.warn("Sürücü yedeği alınamadı (yönetici izni gerekebilir)")
    return str(folder)


def open_windows_update() -> None:
    try:
        import os
        os.startfile("ms-settings:windowsupdate-action")
    except Exception:
        pass


def open_manufacturer_page(url: str) -> None:
    import webbrowser
    if url:
        webbrowser.open(url)


def pending_driver_updates(dry_run: bool = False):
    """Windows Update içinden yalnızca sürücüleri döndürür."""
    from . import updates
    all_updates, error = updates.search(dry_run)
    return [u for u in all_updates if u.is_driver], error
