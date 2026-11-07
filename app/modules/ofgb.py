"""Reklamları kapat: OFGB v0.4 ile aynı 17 registry anahtarı, yerel uygulama."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..core import logger, registry
from ..core.paths import data_file


@dataclass
class KeySpec:
    path: str
    name: str
    clean: int = 0


@dataclass
class Toggle:
    id: str
    title: str
    description: str
    keys: list[KeySpec] = field(default_factory=list)
    requires_admin: bool = False
    min_build: int = 0
    category: str = "Genel"

    def current_state(self) -> bool:
        """True = reklam/öneri kapalı (temiz durum).

        Anahtar hiç yoksa Windows varsayılanı geçerlidir; bu da reklamların
        AÇIK olduğu anlamına gelir (temiz değil).
        """
        for key in self.keys:
            found = registry.read_value(key.path, key.name)
            if found is None:
                return False
            try:
                if int(found[0]) != int(key.clean):
                    return False
            except (TypeError, ValueError):
                return False
        return True

    def apply(self, clean: bool, dry_run: bool = False) -> bool:
        ok = True
        for key in self.keys:
            target = key.clean if clean else (1 - key.clean)
            if dry_run:
                logger.info(f"[DRY-RUN] {key.path}\\{key.name} = {target}")
                continue
            if not registry.write_dword(key.path, key.name, target):
                ok = False
        return ok


def load_toggles() -> list[Toggle]:
    from ..core.i18n import load_json_with_overlay

    raw = load_json_with_overlay("ofgb_tweaks.json")
    toggles = []
    for item in raw.get("toggles", []):
        keys = [KeySpec(k["path"], k["name"], int(k.get("clean", 0))) for k in item.get("keys", [])]
        toggles.append(Toggle(
            id=item["id"],
            title=item["title"],
            description=item.get("description", ""),
            keys=keys,
            requires_admin=item.get("requires_admin", False),
            min_build=int(item.get("min_build", 0)),
            category=item.get("category", "Genel"),
        ))
    return toggles


def supported(toggle: Toggle, build: int, admin: bool) -> tuple[bool, str]:
    if toggle.min_build and build < toggle.min_build:
        return False, f"Windows build {toggle.min_build}+ gerekli"
    if toggle.requires_admin and not admin:
        return False, "Yönetici izni gerekli"
    return True, ""


def apply_selection(selected_ids: list[str], dry_run: bool = False) -> tuple[int, int]:
    toggles = {t.id: t for t in load_toggles()}
    ok = fail = 0
    for toggle_id in selected_ids:
        toggle = toggles.get(toggle_id)
        if not toggle:
            continue
        if toggle.apply(True, dry_run):
            ok += 1
            logger.info(f"Reklam kapatıldı: {toggle.title}")
        else:
            fail += 1
            logger.warn(f"Uygulanamadı: {toggle.title}")
    return ok, fail


def apply_all(dry_run: bool = False) -> tuple[int, int]:
    return apply_selection([t.id for t in load_toggles()], dry_run)


# ---------------------------------------------------------------- OFGB indirici
def ensure_ofgb_exe(on_log=None) -> str:
    """Resmi imzasız OFGB.exe'yi indirir, SHA256 doğrular. Yol döner."""
    from ..core import ps
    from ..core.download import download, human_size, sha256, verify
    from ..core.paths import downloads_dir
    from ..core.version import OFGB_EXE_SHA256, OFGB_EXE_SIZE, OFGB_VERSION

    target = downloads_dir() / f"OFGB-{OFGB_VERSION}.exe"
    if target.exists() and target.stat().st_size == OFGB_EXE_SIZE:
        if verify(target, OFGB_EXE_SHA256):
            return str(target)
        target.unlink(missing_ok=True)

    # .NET 8 Desktop Runtime gerekli mi?
    runtime = ps.ps_json(
        "try{ $k=Get-ChildItem 'HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall','HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall' "
        "-ErrorAction SilentlyContinue | ForEach-Object { $_.GetValue('DisplayName') } | "
        "Where-Object { $_ -match 'Windows Desktop Runtime' -and $_ -match '8\\.' }; "
        "if($k){[pscustomobject]@{found=$true}|ConvertTo-Json}else{[pscustomobject]@{found=$false}|ConvertTo-Json} }catch{'{\"found\":false}'}",
        timeout=60,
    ) or {}
    has_runtime = bool(runtime.get("found"))

    if not has_runtime:
        if on_log:
            on_log("OFGB.exe için .NET 8 Masaüstü Çalışma Zamanı gerekli görünüyor.")
        raise RuntimeError(
            ".NET 8 Masaüstü Çalışma Zamanı kurulu değil. "
            "Programlar adımından 'Microsoft.DotNet.DesktopRuntime.8' kurup tekrar deneyin."
        )

    url = f"https://github.com/xM4ddy/OFGB/releases/download/{OFGB_VERSION}/OFGB.exe"
    if on_log:
        on_log(f"OFGB indiriliyor ({human_size(OFGB_EXE_SIZE)})…")
    download(url, target, on_progress=lambda done, total: on_log(f"  {human_size(done)} / {human_size(total)}") if on_log else None)
    actual = sha256(target)
    if actual.upper() != OFGB_EXE_SHA256:
        target.unlink(missing_ok=True)
        raise RuntimeError(f"SHA256 doğrulaması başarısız ({actual[:16]}…) — dosya çalıştırılmadı.")
    if on_log:
        on_log("OFGB indirildi ve doğrulandı (SHA256 eşleşti).")
    return str(target)
