"""Disk temizliği: hedefleri ölçer, güvenli biçimde temizler."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from ..core import logger, ps
from ..core.download import human_size
from ..core.paths import data_file


@dataclass
class Target:
    id: str
    name: str
    group: str
    description: str
    risk: str
    paths: list[str]
    kind: str = "files"          # files | recycle | dism | service_cache
    admin: bool = False
    warning: str = ""

    @property
    def label(self) -> str:
        return self.name


def load_targets() -> list[Target]:
    from ..core.i18n import load_json_with_overlay

    raw = load_json_with_overlay("cleanup_targets.json")
    targets = []
    for item in raw.get("targets", []):
        targets.append(Target(
            id=item["id"],
            name=item["name"],
            group=item.get("group", "Genel"),
            description=item.get("description", ""),
            risk=item.get("risk", "low"),
            paths=item.get("paths", []),
            kind=item.get("kind", "files"),
            admin=item.get("admin", False),
            warning=item.get("warning", ""),
        ))
    return targets


def grouped(targets: list[Target]) -> dict[str, list[Target]]:
    out: dict[str, list[Target]] = {}
    for t in targets:
        out.setdefault(t.group, []).append(t)
    return out


def expand(path: str) -> str:
    return os.path.expandvars(path)


def measure(target: Target) -> int:
    """Bayt cinsinden boyut."""
    if target.kind == "recycle":
        data = ps.ps_json(
            "$s=0;try{$s=(Get-ChildItem 'C:\\$Recycle.Bin' -Recurse -Force -ErrorAction SilentlyContinue | "
            "Measure-Object Length -Sum).Sum}catch{};if(-not $s){$s=0};[pscustomobject]@{b=[long]$s}|ConvertTo-Json",
            timeout=120,
        ) or {}
        return int(data.get("b") or 0)

    if target.kind == "dism":
        return 0

    total = 0
    script_lines = ["$total=0"]
    for path in target.paths:
        p = expand(path).replace("'", "''")
        script_lines.append(
            f"try{{$total += [long]((Get-ChildItem -Path '{p}' -Recurse -Force -ErrorAction SilentlyContinue | "
            f"Measure-Object Length -Sum).Sum)}}catch{{}}"
        )
    script_lines.append("[pscustomobject]@{b=[long]$total}|ConvertTo-Json")
    data = ps.ps_json("\n".join(script_lines), timeout=180) or {}
    try:
        total = int(data.get("b") or 0)
    except (TypeError, ValueError):
        total = 0
    return total


def measure_many(targets: list[Target]) -> dict[str, int]:
    return {t.id: measure(t) for t in targets}


def clean(target: Target, dry_run: bool = False, on_log=None) -> tuple[bool, str]:
    from ..core.tasks import TaskContext

    ctx = TaskContext(dry_run=dry_run, on_log=on_log)
    try:
        if target.kind == "recycle":
            _clean_recycle(dry_run, ctx)
        elif target.kind == "dism":
            _clean_dism(dry_run, ctx)
        elif target.kind == "service_cache":
            _clean_service_cache(target, dry_run, ctx)
        else:
            _clean_files(target, dry_run, ctx)
        return True, "temizlendi"
    except Exception as exc:  # noqa: BLE001
        logger.warn(f"Temizlik başarısız ({target.name}): {exc}")
        return False, str(exc)


def _clean_files(target: Target, dry_run: bool, ctx) -> None:
    for path in target.paths:
        p = expand(path)
        ctx.log(f"  • {p}")
        if dry_run:
            continue
        safe = p.replace("'", "''")
        script = (
            f"$p='{safe}';"
            "if(Test-Path -LiteralPath $p){"
            "  $parent=Split-Path -Parent $p;"
            "  Get-ChildItem -LiteralPath $p -Force -ErrorAction SilentlyContinue | "
            "    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue}"
        )
        ps.run_powershell(script, timeout=600, label=f"temizle: {target.name}")


def _clean_recycle(dry_run: bool, ctx) -> None:
    ctx.log("  • Geri Dönüşüm Kutusu boşaltılıyor")
    if dry_run:
        return
    ps.run_powershell("Clear-RecycleBin -Force -ErrorAction SilentlyContinue; exit 0", timeout=300,
                      label="Geri Dönüşüm Kutusu")


def _clean_dism(dry_run: bool, ctx) -> None:
    ctx.log("  • DISM bileşen temizliği (uzun sürebilir)")
    if dry_run:
        return
    ps.run_command(
        ["dism.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup"],
        timeout=3600,
        label="DISM StartComponentCleanup",
    )


def _clean_service_cache(target: Target, dry_run: bool, ctx) -> None:
    """Windows Update indirme önbelleği: servisleri durdur, sil, başlat."""
    services = ["wuauserv", "bits", "dosvc", "usosvc"]
    ctx.log("  • Servisler durduruluyor: " + ", ".join(services))
    if dry_run:
        return
    stop = ";".join([f"Stop-Service -Name {s} -Force -ErrorAction SilentlyContinue" for s in services])
    start = ";".join([f"Start-Service -Name {s} -ErrorAction SilentlyContinue" for s in services])
    for path in target.paths:
        p = expand(path).replace("'", "''")
        script = (
            f"{stop}; Start-Sleep -Seconds 2;"
            f"if(Test-Path -LiteralPath '{p}'){{Get-ChildItem -LiteralPath '{p}' -Force -ErrorAction SilentlyContinue | "
            "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue};"
            f"{start}"
        )
        ps.run_powershell(script, timeout=900, label=f"temizle: {target.name}")


def total_human(measurements: dict[str, int]) -> str:
    return human_size(sum(measurements.values()))
