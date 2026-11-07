"""Registry yardımcıları: tür koruyan okuma/yazma, otomatik geri alma kaydı."""
from __future__ import annotations

import winreg
from typing import Any

from . import logger, undo

ROOTS = {
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
    "HKU": winreg.HKEY_USERS,
}

_VIEWS = [winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]


def parse_path(full: str) -> tuple[int, str]:
    """'HKCU\\Software\\...' -> (hkey, subpath)"""
    parts = full.split("\\", 1)
    if not parts or parts[0].upper() not in ROOTS:
        raise ValueError(f"Geçersiz registry yolu: {full}")
    return ROOTS[parts[0].upper()], (parts[1] if len(parts) > 1 else "")


def read_value(full_path: str, name: str) -> tuple[Any, int] | None:
    """(değer, tür) döndürür; yoksa None."""
    hkey, sub = parse_path(full_path)
    for view in _VIEWS:
        try:
            with winreg.OpenKey(hkey, sub, 0, winreg.KEY_READ | view) as key:
                value, vtype = winreg.QueryValueEx(key, name)
                return value, vtype
        except FileNotFoundError:
            continue
        except OSError:
            continue
    return None


def read_dword(full_path: str, name: str, default: int = 0) -> int:
    res = read_value(full_path, name)
    if res is None:
        return default
    try:
        return int(res[0])
    except (TypeError, ValueError):
        return default


def list_subkeys(full_path: str) -> list[str]:
    hkey, sub = parse_path(full_path)
    for view in _VIEWS:
        try:
            with winreg.OpenKey(hkey, sub, 0, winreg.KEY_READ | view) as key:
                names = []
                index = 0
                while True:
                    try:
                        names.append(winreg.EnumKey(key, index))
                        index += 1
                    except OSError:
                        break
                return names
        except FileNotFoundError:
            continue
        except OSError:
            continue
    return []


def ensure_key(full_path: str) -> None:
    hkey, sub = parse_path(full_path)
    winreg.CreateKeyEx(hkey, sub, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY)


def write_dword(full_path: str, name: str, value: int, record_undo: bool = True) -> bool:
    """DWORD yazar. Önceki değeri geri alma kaydına ekler."""
    previous = read_value(full_path, name)
    if record_undo:
        undo.record(
            "registry",
            {
                "path": full_path,
                "name": name,
                "existed": previous is not None,
                "value": previous[0] if previous else None,
                "type": previous[1] if previous else None,
            },
            note=f"{full_path}\\{name}",
        )
    try:
        hkey, sub = parse_path(full_path)
        with winreg.CreateKeyEx(hkey, sub, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value) & 0xFFFFFFFF)
        return True
    except OSError as exc:
        logger.warn(f"Registry yazılamadı ({full_path}\\{name}): {exc}")
        return False


def delete_value(full_path: str, name: str, record_undo: bool = True) -> bool:
    previous = read_value(full_path, name)
    if previous is None:
        return True
    if record_undo:
        undo.record(
            "registry",
            {
                "path": full_path,
                "name": name,
                "existed": True,
                "value": previous[0],
                "type": previous[1],
            },
            note=f"silindi: {full_path}\\{name}",
        )
    try:
        hkey, sub = parse_path(full_path)
        with winreg.OpenKey(hkey, sub, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            winreg.DeleteValue(key, name)
        return True
    except OSError:
        return False


def restore(entry: dict) -> bool:
    """undo.record ile yazılmış bir registry kaydını geri yükler."""
    try:
        path = entry["path"]
        name = entry["name"]
        if entry.get("existed"):
            hkey, sub = parse_path(path)
            with winreg.CreateKeyEx(hkey, sub, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key, name, 0, int(entry["type"]), entry["value"])
        else:
            hkey, sub = parse_path(path)
            with winreg.OpenKey(hkey, sub, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
                winreg.DeleteValue(key, name)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warn(f"Geri yüklenemedi: {exc}")
        return False
