"""Güç planları: Ultimate Performance ekleme ve geri yükleme."""
from __future__ import annotations

import re

from ..core import logger, ps

ULTIMATE_TEMPLATE = "e9a42b02-d5df-448d-aa00-03f14749eb61"
HIGH_PERFORMANCE = "8c5e7fda-e8bf-4a96-9a18-02434455f653"
BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"

SCHEMES = {
    "ultimate": ("Ultimate Performance", ULTIMATE_TEMPLATE),
    "high": ("Yüksek Performans", HIGH_PERFORMANCE),
    "balanced": ("Dengeli", BALANCED),
}

_GUID_RE = re.compile(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})")


def list_schemes() -> list[dict]:
    res = ps.run_command(["powercfg", "/list"], timeout=30)
    out = []
    for line in res.output.splitlines():
        match = _GUID_RE.search(line)
        if not match:
            continue
        name = line.split("(")[-1].split(")")[0] if "(" in line else line
        out.append({"guid": match.group(1), "name": name.strip(), "active": "*" in line})
    return out


def current_guid() -> str:
    res = ps.run_command(["powercfg", "/getactivescheme"], timeout=20)
    match = _GUID_RE.search(res.output)
    return match.group(1) if match else ""


def current_name() -> str:
    res = ps.run_command(["powercfg", "/getactivescheme"], timeout=20)
    if "(" in res.output and ")" in res.output:
        return res.output.split("(")[-1].split(")")[0].strip()
    return "Bilinmiyor"


def enable_ultimate(dry_run: bool = False) -> str:
    """Ultimate Performance planını oluşturup aktif eder. Yeni GUID döner."""
    if dry_run:
        logger.info("[DRY-RUN] Ultimate Performance planı eklenecek ve aktifleştirilecek")
        return ""

    # Zaten var mı?
    for scheme in list_schemes():
        if "ultimate" in scheme["name"].lower():
            ps.run_command(["powercfg", "/setactive", scheme["guid"]], timeout=30)
            logger.info(f"Ultimate Performance zaten mevcut, aktifleştirildi: {scheme['guid']}")
            return scheme["guid"]

    res = ps.run_command(["powercfg", "-duplicatescheme", ULTIMATE_TEMPLATE], timeout=40)
    match = _GUID_RE.search(res.output)
    if not match:
        logger.warn("Ultimate Performance planı oluşturulamadı (desteklenmiyor olabilir)")
        return ""
    guid = match.group(1)
    activate(guid)
    return guid


def activate(guid: str, dry_run: bool = False) -> bool:
    if dry_run:
        logger.info(f"[DRY-RUN] powercfg /setactive {guid}")
        return True
    res = ps.run_command(["powercfg", "/setactive", guid], timeout=30)
    ok = res.ok
    logger.info(f"Güç planı aktifleştirildi: {guid}" if ok else "Güç planı değiştirilemedi")
    return ok


def set_scheme(kind: str, dry_run: bool = False) -> bool:
    from ..core import undo
    previous = current_guid()
    if previous:
        undo.record("power", {"guid": previous}, note="güç planı")
    if kind == "ultimate":
        return bool(enable_ultimate(dry_run)) or dry_run
    guid = SCHEMES.get(kind, (None, BALANCED))[1]
    return activate(guid, dry_run)
