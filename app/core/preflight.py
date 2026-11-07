"""Ön kontrol: ortam sorunlarını hiçbir değişiklik yapmadan tespit eder."""
from __future__ import annotations

import os
import shutil
import socket
import sys
from dataclasses import dataclass, field

from . import i18n, ps
from .elevation import is_admin

LEVEL_OK = "ok"
LEVEL_WARN = "warn"
LEVEL_BLOCK = "block"


@dataclass
class Check:
    key: str
    label: str
    level: str
    detail: str = ""


@dataclass
class PreflightReport:
    checks: list[Check] = field(default_factory=list)
    info: dict = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return any(c.level == LEVEL_BLOCK for c in self.checks)

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if c.level == LEVEL_WARN]


def _free_space_gb(path: str) -> float:
    try:
        return shutil.disk_usage(path).free / (1024 ** 3)
    except Exception:
        return 0.0


def has_internet(timeout: float = 3.0) -> bool:
    for host in ("1.1.1.1", "8.8.8.8"):
        try:
            with socket.create_connection((host, 443), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def run_preflight(include_network: bool = True) -> PreflightReport:
    report = PreflightReport()

    # Windows sürümü
    try:
        ver = sys.getwindowsversion()
        build = ver.build
        name = f"Windows {ver.major}.{ver.minor} (build {build})"
    except Exception:
        build, name = 0, "Bilinmeyen Windows"

    report.info["os"] = name
    report.info["build"] = build
    if build >= 22000:
        report.checks.append(Check("os", "Windows 11", LEVEL_OK, name))
    elif build >= 19041:
        report.checks.append(Check("os", "Windows 10", LEVEL_WARN, f"{name} — Win11'e özel ayarlar gizlenecek"))
    else:
        report.checks.append(Check("os", "Desteklenmeyen Windows", LEVEL_BLOCK, f"{name} — en az Windows 10 2004 gerekli"))

    # Yönetici
    admin = is_admin()
    report.info["admin"] = admin
    report.checks.append(
        Check("admin", "Yönetici izni", LEVEL_OK if admin else LEVEL_BLOCK,
              "Yönetici olarak çalışıyor" if admin else "Yönetici izni olmadan temizlik ve kurulum yapılamaz")
    )

    # Python (yalnızca geliştirme modunda anlamlı)
    if not getattr(sys, "frozen", False):
        report.info["python"] = sys.version.split()[0]

    # winget
    winget = ps.which("winget")
    report.info["winget"] = winget or ""
    if winget:
        report.checks.append(Check("winget", "winget", LEVEL_OK, "Program kurulumu için hazır"))
    else:
        report.checks.append(Check("winget", "winget bulunamadı", LEVEL_WARN,
                                   "App Installer eksik — programlar doğrudan indirme ile kurulacak"))

    # PowerShell
    ps_exe = ps.which("powershell")
    report.checks.append(Check("powershell", "PowerShell", LEVEL_OK if ps_exe else LEVEL_BLOCK,
                               "Hazır" if ps_exe else "PowerShell bulunamadı"))

    # Disk alanı
    free = _free_space_gb(os.environ.get("SystemDrive", "C:") + "\\")
    report.info["free_gb"] = round(free, 1)
    if free < 2:
        report.checks.append(Check("disk", "Disk alanı", LEVEL_BLOCK,
                                   i18n.t("Yalnızca {free:.1f} GB boş", free=free)))
    elif free < 10:
        report.checks.append(Check("disk", "Disk alanı", LEVEL_WARN,
                                   i18n.t("{free:.1f} GB boş — temizlik önerilir", free=free)))
    else:
        report.checks.append(Check("disk", "Disk alanı", LEVEL_OK,
                                   i18n.t("{free:.1f} GB boş", free=free)))
    # İnternet
    if include_network:
        online = has_internet()
        report.info["internet"] = online
        report.checks.append(Check("internet", "İnternet", LEVEL_OK if online else LEVEL_WARN,
                                   "Bağlı" if online else "Bağlı değil — indirme gerektiren adımlar atlanacak"))

    # Sistem geri yükleme
    sr = ps.ps_json(
        "try{$s=(Get-ComputerRestorePoint -ErrorAction SilentlyContinue | Measure-Object).Count;"
        "$p=Get-CimInstance -Namespace root/default -ClassName SystemRestoreConfig -ErrorAction SilentlyContinue;"
        "[pscustomobject]@{points=$s;enabled=[bool]$p}|ConvertTo-Json}catch{'{}'}",
        timeout=25,
    ) or {}
    report.info["restore_points"] = int(sr.get("points") or 0)

    # Bekleyen yeniden başlatma
    pending = False
    for key in (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
    ):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key):
                pending = True
        except OSError:
            pass
    report.info["pending_reboot"] = pending
    if pending:
        report.checks.append(Check("reboot", "Bekleyen yeniden başlatma", LEVEL_WARN,
                                   "Değişikliklerin bir kısmı yeniden başlatmadan sonra etkin olur"))

    return report
