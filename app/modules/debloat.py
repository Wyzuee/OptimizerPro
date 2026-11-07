"""Win11Debloat entegrasyonu: indirme, parametre eşlemesi, çalıştırma."""
from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..core import logger, ps
from ..core.paths import cache_dir, data_file
from ..core.version import WIN11DEBLOAT_ZIP


@dataclass
class Tweak:
    id: str
    title: str
    description: str
    param: str
    category: str
    min_build: int = 0
    max_build: int = 0
    risk: str = "low"
    default: bool = False

    def supported(self, build: int) -> bool:
        if self.min_build and build < self.min_build:
            return False
        if self.max_build and build > self.max_build:
            return False
        return True


def load_tweaks() -> list[Tweak]:
    from ..core.i18n import load_json_with_overlay

    raw = load_json_with_overlay("debloat_tweaks.json")
    out = []
    for item in raw.get("tweaks", []):
        out.append(Tweak(
            id=item["id"],
            title=item["title"],
            description=item.get("description", ""),
            param=item["param"],
            category=item.get("category", "Genel"),
            min_build=int(item.get("min_build", 0)),
            max_build=int(item.get("max_build", 0)),
            risk=item.get("risk", "low"),
            default=item.get("default", False),
        ))
    return out


def grouped(tweaks: list[Tweak]) -> dict[str, list[Tweak]]:
    out: dict[str, list[Tweak]] = {}
    for tweak in tweaks:
        out.setdefault(tweak.category, []).append(tweak)
    return out


def build_args(selected_ids: list[str], build: int, restore_point: bool = True) -> list[str]:
    lookup = {t.id: t for t in load_tweaks()}
    args: list[str] = []
    for tweak_id in selected_ids:
        tweak = lookup.get(tweak_id)
        if not tweak or not tweak.supported(build):
            continue
        for part in tweak.param.split():
            if part not in args:
                args.append(part)
    if restore_point:
        args.append("-CreateRestorePoint")
    args += ["-Silent", "-SkipExplorerRestart"]
    return args


def script_dir() -> Path:
    return cache_dir() / "Win11Debloat"


def is_available() -> bool:
    return (script_dir() / "Win11Debloat.ps1").exists()


def download(dry_run: bool = False, on_log=None) -> Path:
    from ..core.download import download as fetch

    target_dir = script_dir()
    script = target_dir / "Win11Debloat.ps1"
    if script.exists():
        logger.info("Win11Debloat zaten indirilmiş, tekrar indirilmiyor.")
        return script

    if dry_run:
        logger.info(f"[DRY-RUN] Win11Debloat indirilecek: {WIN11DEBLOAT_ZIP}")
        return script

    archive = target_dir / "Win11Debloat.zip"
    if on_log:
        on_log("Win11Debloat indiriliyor…")
    fetch(WIN11DEBLOAT_ZIP, archive)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(target_dir)
    archive.unlink(missing_ok=True)

    if not script.exists():
        # Zip içinde alt klasör olabilir
        for candidate in target_dir.rglob("Win11Debloat.ps1"):
            script = candidate
            break
    if not script.exists():
        raise RuntimeError("Win11Debloat indirildi ama Win11Debloat.ps1 bulunamadı.")
    logger.info(f"Win11Debloat hazır: {script}")
    return script


def run(selected_ids: list[str], build: int, dry_run: bool = False,
        whatif: bool = False, on_line=None, timeout: float = 3600) -> ps.Result:
    script = download(dry_run, on_log=on_line)
    args = build_args(selected_ids, build, restore_point=True)
    if whatif:
        args.append("-WhatIf")

    if dry_run:
        logger.info(f"[DRY-RUN] Win11Debloat {' '.join(args)}")
        return ps.Result(code=0, output="", error="dry-run")

    command = (
        f"& '{script}' " + " ".join(f"'{a}'" if " " in a else a for a in args)
    )
    return ps.run_powershell(command, on_line=on_line, timeout=timeout, label="Win11Debloat")


def open_original_menu() -> bool:
    """Upstream interaktif menüyü ayrı pencerede açar."""
    script = download(False)
    if not script.exists():
        return False
    try:
        import subprocess
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            creationflags=0x00000010,  # CREATE_NEW_CONSOLE
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warn(f"Win11Debloat menüsü açılamadı: {exc}")
        return False
