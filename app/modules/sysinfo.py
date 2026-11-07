"""Sistem bilgisi toplama."""
from __future__ import annotations

import json

from ..core import ps

_SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1
$sys = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$env:SystemDrive'"
$disks = @(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    [pscustomobject]@{ letter=$_.DeviceID; total=[math]::Round($_.Size/1GB,1); free=[math]::Round($_.FreeSpace/1GB,1) } })
[pscustomobject]@{
  os_name    = $os.Caption
  os_version = $os.Version
  os_build   = $os.BuildNumber
  arch       = $os.OSArchitecture
  hostname   = $cs.Name
  manufacturer = $cs.Manufacturer
  model      = $cs.Model
  cpu        = $cpu.Name
  cores      = $cpu.NumberOfCores
  threads    = $cpu.NumberOfLogicalProcessors
  ram_gb     = [math]::Round($cs.TotalPhysicalMemory/1GB,1)
  gpu        = $gpu.Name
  gpu_ram    = if($gpu.AdapterRAM){[math]::Round($gpu.AdapterRAM/1GB,1)}else{0}
  disk_total = [math]::Round($sys.Size/1GB,1)
  disk_free  = [math]::Round($sys.FreeSpace/1GB,1)
  uptime_h   = [math]::Round(((Get-Date) - $os.LastBootUpTime).TotalHours,1)
  user       = $env:USERNAME
  install_date = if($os.InstallDate){$os.InstallDate.ToString('yyyy-MM-dd')}else{''}
  displays   = @(Get-CimInstance Win32_VideoController | ForEach-Object { $_.CurrentHorizontalResolution })
  disks      = $disks
} | ConvertTo-Json -Compress -Depth 4
"""

_CACHE: dict | None = None


def collect(force: bool = False) -> dict:
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    data = ps.ps_json(_SCRIPT, timeout=60) or {}
    if not isinstance(data, dict):
        data = {}
    _CACHE = data
    return data


def manufacturer_key() -> str:
    info = collect()
    text = f"{info.get('manufacturer','')} {info.get('model','')}".lower()
    mapping = {
        "monster": "monster",
        "dell": "dell",
        "lenovo": "lenovo",
        "hp": "hp",
        "hewlett": "hp",
        "asus": "asus",
        "msi": "msi",
        "micro-star": "msi",
        "acer": "acer",
        "samsung": "samsung",
        "toshiba": "toshiba",
        "dynabook": "toshiba",
        "microsoft": "microsoft",
        "gigabyte": "gigabyte",
        "razer": "razer",
        "casper": "casper",
        "excalibur": "casper",
    }
    for needle, key in mapping.items():
        if needle in text:
            return key
    return "generic"


SUPPORT_LINKS = {
    "monster": ("Monster", "https://support.monsternotebook.com/"),
    "dell": ("Dell", "https://www.dell.com/support/home/tr-tr"),
    "lenovo": ("Lenovo", "https://pcsupport.lenovo.com/"),
    "hp": ("HP", "https://support.hp.com/tr-tr/drivers"),
    "asus": ("ASUS", "https://www.asus.com/tr/support/download-center/"),
    "msi": ("MSI", "https://tr.msi.com/support/download"),
    "acer": ("Acer", "https://www.acer.com/tr-tr/support/drivers-and-manuals"),
    "samsung": ("Samsung", "https://www.samsung.com/tr/support/"),
    "toshiba": ("Toshiba/Dynabook", "https://support.dynabook.com/"),
    "microsoft": ("Microsoft", "https://support.microsoft.com/surface"),
    "gigabyte": ("Gigabyte", "https://www.gigabyte.com/Support"),
    "razer": ("Razer", "https://mysupport.razer.com/"),
    "casper": ("Casper", "https://www.casper.com.tr/destek"),
}
