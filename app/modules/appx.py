"""Windows mağaza uygulamaları (Appx): listeleme, boyut, kaldırma."""
from __future__ import annotations

import json

from ..core import logger, ps
from ..core.download import human_size
from ..core.paths import data_file

_LIST_SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$items = Get-AppxPackage | Where-Object { -not $_.IsFramework -and -not $_.IsResourcePackage } | ForEach-Object {
  $size = 0
  if ($_.InstallLocation -and (Test-Path $_.InstallLocation)) {
    try { $size = (Get-ChildItem $_.InstallLocation -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum } catch {}
  }
  [pscustomobject]@{
    name = $_.Name
    full = $_.PackageFullName
    publisher = $_.Publisher
    version = $_.Version
    size = [long]$size
    location = $_.InstallLocation
  }
}
$items | ConvertTo-Json -Compress -Depth 3
"""


class AppxItem:
    __slots__ = ("name", "full", "publisher", "version", "size", "location", "friendly", "critical", "selected")

    def __init__(self, name, full, publisher, version, size, location, friendly="", critical=False):
        self.name = name
        self.full = full
        self.publisher = publisher
        self.version = version
        self.size = size
        self.location = location
        self.friendly = friendly or name
        self.critical = critical
        self.selected = False

    @property
    def size_h(self) -> str:
        return human_size(self.size)

    def __repr__(self) -> str:
        return f"<Appx {self.name}>"


def _load_blocklist() -> dict:
    from ..core.i18n import load_json_with_overlay
    try:
        return load_json_with_overlay("appx_blocklist.json")
    except Exception:
        return {"packages": [], "name_contains": [], "friendly": {}}


def list_packages(dry_run: bool = False) -> list[AppxItem]:
    data = ps.ps_json(_LIST_SCRIPT, timeout=180, dry_run=dry_run, default=[]) or []
    if isinstance(data, dict):
        data = [data]

    block = _load_blocklist()
    packages = {p.lower() for p in block.get("packages", [])}
    contains = [s.lower() for s in block.get("name_contains", [])]
    friendly = {k.lower(): v for k, v in block.get("friendly", {}).items()}

    items: list[AppxItem] = []
    seen = set()
    for row in data:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        lower = name.lower()
        critical = lower in packages or any(c in lower for c in contains)
        items.append(AppxItem(
            name=name,
            full=str(row.get("full") or ""),
            publisher=str(row.get("publisher") or ""),
            version=str(row.get("version") or ""),
            size=int(row.get("size") or 0),
            location=str(row.get("location") or ""),
            friendly=friendly.get(lower, name),
            critical=critical,
        ))
    items.sort(key=lambda i: (i.critical, -i.size))
    return items


def remove(items: list[AppxItem], all_users: bool = False, dry_run: bool = False) -> tuple[int, int]:
    ok, fail = 0, 0
    for item in items:
        if item.critical:
            logger.warn(f"Kritik paket atlandı: {item.name}")
            fail += 1
            continue
        if dry_run:
            logger.info(f"[DRY-RUN] Kaldırılacak: {item.name}")
            ok += 1
            continue
        script = f"Remove-AppxPackage -Package '{item.full}' -ErrorAction Stop"
        res = ps.run_powershell(script, timeout=300)
        if res.ok:
            ok += 1
            logger.info(f"Kaldırıldı: {item.name}")
        else:
            fail += 1
            logger.warn(f"Kaldırılamadı: {item.name}")

        if all_users:
            script2 = (
                f"Get-AppxProvisionedPackage -Online | Where-Object {{ $_.PackageName -eq '{item.name}' }} | "
                "Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue"
            )
            ps.run_powershell(script2, timeout=300)

    return ok, fail
