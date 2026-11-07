"""Başlangıç öğeleri: registry Run/RunOnce, Startup klasörleri, onay durumu."""
from __future__ import annotations

import os
import winreg
from dataclasses import dataclass
from pathlib import Path

from ..core import logger, registry, undo

RUN_KEYS = [
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
]

APPROVED_RUN = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
APPROVED_RUN32 = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32"
APPROVED_STARTUP = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder"

STATE_ENABLED = 2
STATE_DISABLED = 3


@dataclass
class StartupItem:
    key: str
    name: str
    command: str
    location: str
    kind: str          # registry | folder | task
    enabled: bool
    approved_path: str = ""
    approved_name: str = ""

    @property
    def short_command(self) -> str:
        return self.command if len(self.command) <= 90 else self.command[:87] + "…"


def _approved_state(path: str, name: str) -> bool | None:
    res = registry.read_value(f"HKCU\\{path}", name)
    if res is None:
        return None
    value, _ = res
    try:
        data = bytes(value) if isinstance(value, (bytes, bytearray)) else b""
    except Exception:
        return None
    if len(data) >= 4:
        return data[0] == STATE_ENABLED
    return True


def _set_approved(path: str, name: str, enabled: bool) -> bool:
    state = STATE_ENABLED if enabled else STATE_DISABLED
    payload = bytes([state, 0, 0, 0]) + b"\x00" * 8
    previous = registry.read_value(f"HKCU\\{path}", name)
    undo.record(
        "registry",
        {
            "path": f"HKCU\\{path}",
            "name": name,
            "existed": previous is not None,
            "value": previous[0] if previous else None,
            "type": previous[1] if previous else None,
        },
        note=f"başlangıç: {name}",
    )
    try:
        hkey, sub = registry.parse_path(f"HKCU\\{path}")
        with winreg.CreateKeyEx(hkey, sub, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, payload)
        return True
    except OSError as exc:
        logger.warn(f"Başlangıç durumu yazılamadı ({name}): {exc}")
        return False


def _startup_folders() -> list[tuple[Path, str]]:
    appdata = os.environ.get("APPDATA", "")
    programdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    return [
        (Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup", "Kullanıcı Başlangıç"),
        (Path(programdata) / r"Microsoft\Windows\Start Menu\Programs\Startup", "Ortak Başlangıç"),
    ]


def list_items(include_disabled: bool = True) -> list[StartupItem]:
    items: list[StartupItem] = []

    for root, sub, label in RUN_KEYS:
        approved = APPROVED_RUN32 if "WOW6432Node" in sub else APPROVED_RUN
        try:
            with winreg.OpenKey(root, sub, 0, winreg.KEY_READ) as key:
                index = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    index += 1
                    command = str(value)
                    approved_state = _approved_state(approved, name)
                    enabled = True if approved_state is None else approved_state
                    items.append(StartupItem(
                        key=f"{label}|{sub}|{name}",
                        name=name,
                        command=command,
                        location=f"{label} Run",
                        kind="registry",
                        enabled=enabled,
                        approved_path=approved,
                        approved_name=name,
                    ))
        except OSError:
            continue

    for folder, label in _startup_folders():
        if not folder.exists():
            continue
        try:
            for entry in folder.iterdir():
                if entry.name.lower() == "desktop.ini":
                    continue
                approved_state = _approved_state(APPROVED_STARTUP, entry.name)
                enabled = True if approved_state is None else approved_state
                items.append(StartupItem(
                    key=f"folder|{entry}",
                    name=entry.name,
                    command=str(entry),
                    location=label,
                    kind="folder",
                    enabled=enabled,
                    approved_path=APPROVED_STARTUP,
                    approved_name=entry.name,
                ))
        except OSError as exc:
            logger.warn(f"Başlangıç klasörü okunamadı ({folder}): {exc}")

    items.sort(key=lambda i: (not i.enabled, i.name.lower()))
    if not include_disabled:
        items = [i for i in items if i.enabled]
    return items


def set_enabled(item: StartupItem, enabled: bool, dry_run: bool = False) -> bool:
    if dry_run:
        logger.info(f"[DRY-RUN] Başlangıç {'açılacak' if enabled else 'kapatılacak'}: {item.name}")
        return True
    if not item.approved_path:
        return False
    ok = _set_approved(item.approved_path, item.approved_name, enabled)
    if ok:
        logger.info(f"Başlangıç {'açıldı' if enabled else 'kapatıldı'}: {item.name}")
    return ok


def remove_folder_item(item: StartupItem, dry_run: bool = False) -> bool:
    """Startup klasöründeki .lnk'yi yedekleyip kaldırır (silmez, taşır)."""
    from ..core.paths import backups_dir
    src = Path(item.command)
    if not src.exists():
        return False
    if dry_run:
        logger.info(f"[DRY-RUN] Başlangıçtan kaldırılacak: {src}")
        return True
    dest_dir = backups_dir() / "startup"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    try:
        src.replace(dest)
        undo.record("file", {"src": str(dest), "dst": str(src)}, note=f"başlangıçtan kaldırıldı: {src.name}")
        logger.info(f"Başlangıçtan kaldırıldı (yedek: {dest})")
        return True
    except OSError as exc:
        logger.warn(f"Kaldırılamadı: {exc}")
        return False
