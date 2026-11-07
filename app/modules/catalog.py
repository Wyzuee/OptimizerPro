"""Program kataloğu: yükleme, filtreleme, yüklü tespiti."""
from __future__ import annotations

import json
import os
import re
import winreg
from dataclasses import dataclass, field

from ..core import logger
from ..core.paths import data_file


@dataclass
class CatalogApp:
    id: str
    name: str
    description: str
    category: str
    winget: str = ""
    ninite: str = ""
    direct_url: str = ""
    direct_args: str = ""
    detect: list[str] = field(default_factory=list)
    size_mb: int = 0
    requires_admin: bool = False
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    installed: bool = False

    @property
    def source(self) -> str:
        if self.winget:
            return "winget"
        if self.direct_url:
            return "direct"
        return "ninite"


@dataclass
class Catalog:
    apps: list[CatalogApp]
    categories: list[str]

    def by_id(self, app_id: str) -> CatalogApp | None:
        for app in self.apps:
            if app.id == app_id:
                return app
        return None

    def grouped(self) -> dict[str, list[CatalogApp]]:
        out: dict[str, list[CatalogApp]] = {}
        for app in self.apps:
            out.setdefault(app.category, []).append(app)
        return out


def load_catalog() -> Catalog:
    from ..core.i18n import current, load_json_with_overlay

    raw = load_json_with_overlay("catalog.json")
    apps: list[CatalogApp] = []
    for item in raw.get("apps", []):
        direct = item.get("direct") or {}
        apps.append(CatalogApp(
            id=item["id"],
            name=item["name"],
            description=item.get("description", ""),
            category=item.get("category", "Diğer"),
            winget=item.get("winget", ""),
            ninite=item.get("ninite", ""),
            direct_url=direct.get("url", ""),
            direct_args=direct.get("args", ""),
            detect=item.get("detect", [item["name"]]),
            size_mb=int(item.get("size_mb", 0)),
            requires_admin=bool(item.get("requires_admin", False)),
            tags=item.get("tags", []),
            notes=item.get("notes", ""),
        ))
    categories = raw.get("categories") or sorted({a.category for a in apps})
    return Catalog(apps, list(categories))


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


_UNINSTALL_ROOTS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_64KEY),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_32KEY),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", 0),
]


def installed_display_names() -> set[str]:
    names: set[str] = set()
    for root, path, view in _UNINSTALL_ROOTS:
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_READ | view) as key:
                index = 0
                while True:
                    try:
                        sub = winreg.EnumKey(key, index)
                    except OSError:
                        break
                    index += 1
                    try:
                        with winreg.OpenKey(key, sub) as subkey:
                            display, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            if display:
                                names.add(str(display))
                    except OSError:
                        continue
        except OSError:
            continue
    return names


def installed_appx_names() -> set[str]:
    from ..core import ps
    data = ps.ps_json(
        "Get-AppxPackage | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress",
        timeout=120, default=[],
    ) or []
    if isinstance(data, str):
        data = [data]
    return {str(x) for x in data}


def mark_installed(catalog: Catalog, dry_run: bool = False) -> Catalog:
    if dry_run:
        return catalog
    registry_names = installed_display_names()
    appx_names = installed_appx_names()
    normalized_registry = {_normalize(n) for n in registry_names}
    normalized_appx = {_normalize(n) for n in appx_names}

    for app in catalog.apps:
        if app.winget:
            short = app.winget.split(".")[-1]
            if _normalize(short) in normalized_appx:
                app.installed = True
                continue
        for needle in app.detect:
            key = _normalize(needle)
            if not key:
                continue
            if any(key in name or name in key for name in normalized_registry if len(name) > 3):
                app.installed = True
                break
            if any(key in name or name in key for name in normalized_appx if len(name) > 3):
                app.installed = True
                break
    return catalog


def search(catalog: Catalog, query: str) -> list[CatalogApp]:
    if not query.strip():
        return catalog.apps
    needle = _normalize(query)
    results = []
    for app in catalog.apps:
        haystack = _normalize(app.name + app.description + " " + " ".join(app.tags))
        if needle in haystack:
            results.append(app)
    return results


def ensure_apps_dir_value() -> str:
    return os.environ.get("PROGRAMFILES", r"C:\Program Files")
