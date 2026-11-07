"""Boot yapılandırması: timeout ve işlemci sayısı (msconfig gelişmiş seçenekleri)."""
from __future__ import annotations

import re
import subprocess
from datetime import datetime

from ..core import logger, ps
from ..core.paths import backups_dir

_CREATE_NO_WINDOW = 0x08000000


def _bcdedit(args: list[str], timeout: float = 40) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["bcdedit"] + args,
            capture_output=True, text=True, timeout=timeout,
            creationflags=_CREATE_NO_WINDOW, encoding="utf-8", errors="replace",
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:  # noqa: BLE001
        return -1, str(exc)


def current_entry() -> dict:
    code, out = _bcdedit(["/enum", "{current}"])
    info = {"raw": out, "timeout": 30, "numproc": 0, "maxmem": 0, "safeboot": "", "description": ""}
    if code != 0:
        return info
    for line in out.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "timeout" and value.isdigit():
            info["timeout"] = int(value)
        elif key == "numproc" and value.isdigit():
            info["numproc"] = int(value)
        elif key == "truncatememory":
            m = re.search(r"0x([0-9a-fA-F]+)|(\d+)", value)
            if m:
                try:
                    info["maxmem"] = int(m.group(1) or m.group(2), 16 if m.group(1) else 10)
                except ValueError:
                    pass
        elif key == "safeboot":
            info["safeboot"] = value
        elif key == "description":
            info["description"] = value
    return info


def backup() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = backups_dir() / f"bcd-{stamp}.bcd"
    code, out = _bcdedit(["/export", str(path)])
    if code == 0 and path.exists():
        logger.info(f"Boot yapılandırması yedeklendi: {path}")
        return str(path)
    logger.warn(f"Boot yedeği alınamadı: {out.strip()[:200]}")
    return ""


def set_timeout(seconds: int, dry_run: bool = False) -> bool:
    if dry_run:
        logger.info(f"[DRY-RUN] bcdedit /timeout {seconds}")
        return True
    backup()
    code, out = _bcdedit(["/timeout", str(int(seconds))])
    ok = code == 0
    logger.info(f"Boot timeout {seconds}s: {'tamam' if ok else out[:200]}")
    return ok


def set_numproc(count: int, dry_run: bool = False) -> bool:
    """count=0 -> ayarı kaldır (tüm çekirdekler)."""
    if dry_run:
        logger.info(f"[DRY-RUN] numproc = {count}")
        return True
    backup()
    if count <= 0:
        code, out = _bcdedit(["/deletevalue", "{current}", "numproc"])
    else:
        code, out = _bcdedit(["/set", "{current}", "numproc", str(int(count))])
    ok = code == 0 or "bulunamadı" in out.lower()
    logger.info(f"İşlemci sayısı {count or 'otomatik'}: {'tamam' if ok else out[:200]}")
    return ok


def set_maxmem(mb: int, dry_run: bool = False) -> bool:
    if dry_run:
        logger.info(f"[DRY-RUN] maxmem = {mb} MB")
        return True
    backup()
    if mb <= 0:
        code, out = _bcdedit(["/deletevalue", "{current}", "truncatememory"])
    else:
        code, out = _bcdedit(["/set", "{current}", "truncatememory", f"0x{int(mb) * 1024 * 1024:x}"])
    ok = code == 0 or "bulunamadı" in out.lower()
    logger.info(f"Bellek sınırı {mb or 'yok'} MB: {'tamam' if ok else out[:200]}")
    return ok


def cpu_counts() -> tuple[int, int]:
    data = ps.ps_json(
        "[pscustomobject]@{c=(Get-CimInstance Win32_Processor).NumberOfCores;"
        "t=(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors}|ConvertTo-Json",
        timeout=30,
    ) or {}
    return int(data.get("c") or 1), int(data.get("t") or 1)
