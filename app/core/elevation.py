"""Yönetici izni kontrolü ve yeniden başlatma."""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(extra_args: list[str] | None = None) -> bool:
    """Mevcut exe'yi yönetici olarak yeniden başlatır."""
    if getattr(sys, "frozen", False):
        exe = sys.executable
        params = " ".join(extra_args or [])
    else:
        exe = sys.executable
        script = os.path.abspath(sys.argv[0])
        params = f'"{script}" ' + " ".join(extra_args or [])
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        return rc > 32
    except Exception:
        return False


def is_windows() -> bool:
    return os.name == "nt"


def windows_build() -> int:
    try:
        return int(subprocess.run(
            ["cmd", "/c", "ver"], capture_output=True, text=True, timeout=10,
            creationflags=0x08000000,
        ).stdout.split(".")[2])
    except Exception:
        try:
            return sys.getwindowsversion().build
        except Exception:
            return 0
