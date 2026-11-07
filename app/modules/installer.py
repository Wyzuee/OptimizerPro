"""Kurulum motoru: winget -> doğrudan indirme -> Ninite sırasıyla dener."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..core import logger, ps
from ..core.download import download, human_size
from ..core.paths import downloads_dir
from .catalog import CatalogApp


@dataclass
class InstallResult:
    app_id: str
    status: str      # installed | skipped | failed
    method: str = ""
    message: str = ""


def _winget_available() -> bool:
    return ps.which("winget") is not None


def _target_dir(drive: str, app_id: str) -> str:
    r"""D:\Apps\<id> biçiminde hedef klasör."""
    drive = (drive or "C").strip().rstrip(":\\/").upper()[:1]
    base = f"{drive}:\\Apps"
    return os.path.join(base, app_id)


def install_with_winget(app: CatalogApp, drive: str = "C", dry_run: bool = False,
                        on_line=None, timeout: float = 1800) -> InstallResult:
    if not app.winget:
        return InstallResult(app.id, "failed", "winget", "winget kimliği tanımlı değil")
    if not _winget_available():
        return InstallResult(app.id, "failed", "winget", "winget bulunamadı")

    args = [
        "winget", "install", "--id", app.winget, "-e",
        "--silent", "--accept-package-agreements", "--accept-source-agreements",
        "--disable-interactivity",
    ]
    if drive and drive.upper() != "C":
        args += ["--location", _target_dir(drive, app.id)]

    if dry_run:
        logger.info(f"[DRY-RUN] {' '.join(args)}")
        return InstallResult(app.id, "installed", "winget", "dry-run")

    result = ps.run_command(args, on_line=on_line, timeout=timeout, label=f"winget: {app.name}")
    if result.ok:
        logger.info(f"Kuruldu: {app.name}")
        return InstallResult(app.id, "installed", "winget")

    # Bazı durumlarda "zaten kurulu" çıkış kodu 0x8A150061 üretir
    combined = (result.output or "").lower()
    if "already installed" in combined or "zaten yüklü" in combined or "no applicable update" in combined:
        return InstallResult(app.id, "skipped", "winget", "zaten kurulu")

    return InstallResult(app.id, "failed", "winget", f"çıkış kodu {result.code}")


def install_direct(app: CatalogApp, dry_run: bool = False, on_line=None,
                   timeout: float = 1800) -> InstallResult:
    if not app.direct_url:
        return InstallResult(app.id, "failed", "direct", "doğrudan indirme adresi yok")

    filename = app.direct_url.split("/")[-1].split("?")[0] or f"{app.id}.exe"
    target = downloads_dir() / filename

    if dry_run:
        logger.info(f"[DRY-RUN] İndirilecek: {app.direct_url}")
        return InstallResult(app.id, "installed", "direct", "dry-run")

    try:
        if not target.exists():
            download(app.direct_url, target,
                     on_progress=(lambda done, total: on_line(f"  {human_size(done)} / {human_size(total)}"))
                     if on_line else None)
    except Exception as exc:  # noqa: BLE001
        return InstallResult(app.id, "failed", "direct", f"indirme hatası: {exc}")

    args = [str(target)] + (app.direct_args.split() if app.direct_args else ["/S"])
    try:
        result = ps.run_command(args, on_line=on_line, timeout=timeout, label=f"kur: {app.name}")
    except Exception as exc:  # noqa: BLE001
        return InstallResult(app.id, "failed", "direct", str(exc))

    if result.ok:
        return InstallResult(app.id, "installed", "direct")
    return InstallResult(app.id, "failed", "direct", f"çıkış kodu {result.code}")


def install(app: CatalogApp, drive: str = "C", dry_run: bool = False,
            on_line=None, allow_direct: bool = True) -> InstallResult:
    if app.installed:
        logger.info(f"Atlandı (zaten yüklü): {app.name}")
        return InstallResult(app.id, "skipped", "", "zaten yüklü")

    result = install_with_winget(app, drive, dry_run, on_line)
    if result.status == "installed" or result.status == "skipped":
        return result

    if allow_direct and app.direct_url:
        logger.warn(f"winget başarısız, doğrudan indirme denenecek: {app.name}")
        return install_direct(app, dry_run, on_line)

    return result


def refresh_path() -> None:
    """Kurulum sonrası PATH'i güncelle (yeni terminal açmadan)."""
    try:
        machine = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Environment]::GetEnvironmentVariable('Path','Machine')"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000,
        ).stdout.strip()
        user = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Environment]::GetEnvironmentVariable('Path','User')"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000,
        ).stdout.strip()
        combined = ";".join(p for p in (machine, user) if p)
        if combined:
            os.environ["PATH"] = combined
    except Exception:
        pass
