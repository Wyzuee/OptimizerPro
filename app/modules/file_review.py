"""Masaüstü / İndirilenler analizi, gruplama, geri dönüşüm kutusuna silme, sınıflandırma."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..core import logger, ps
from ..core.download import human_size

CATEGORIES: dict[str, list[str]] = {
    "Kurulum Dosyaları": [".exe", ".msi", ".msix", ".appx", ".msixbundle"],
    "Arşivler": [".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".img"],
    "Belgeler": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".md", ".rtf", ".odt"],
    "Resimler": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tif", ".tiff", ".ico"],
    "Medya": [".mp3", ".mp4", ".avi", ".mkv", ".wav", ".flac", ".mov", ".wmv", ".m4a"],
    "Kısayollar": [".lnk", ".url"],
    "Geçici Kalıntılar": [".tmp", ".part", ".crdownload", ".download", ".bak", ".old"],
}

CLASSIFY_FOLDERS = ["Belgeler", "Resimler", "Kurulumlar", "Kısayollar", "Medyalar"]

_CLASSIFY_MAP = {
    "Belgeler": "Belgeler",
    "Resimler": "Resimler",
    "Kurulum Dosyaları": "Kurulumlar",
    "Kısayollar": "Kısayollar",
    "Medya": "Medyalar",
}


@dataclass
class FileItem:
    path: str
    name: str
    size: int
    mtime: float
    category: str
    source: str  # Desktop | Downloads
    selected: bool = False

    @property
    def size_h(self) -> str:
        return human_size(self.size)

    @property
    def date_h(self) -> str:
        return time.strftime("%Y-%m-%d", time.localtime(self.mtime))

    @property
    def age_days(self) -> int:
        return int((time.time() - self.mtime) / 86400)


def _category_for(ext: str) -> str:
    ext = ext.lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return "Diğer"


def scan(include: list[str] | None = None, max_items: int = 3000) -> list[FileItem]:
    from ..core.paths import user_desktop, user_downloads

    roots = {"Masaüstü": user_desktop(), "İndirilenler": user_downloads()}
    if include:
        roots = {k: v for k, v in roots.items() if k in include}

    items: list[FileItem] = []
    for label, folder in roots.items():
        if not folder.exists():
            continue
        try:
            for entry in os.scandir(folder):
                if len(items) >= max_items:
                    break
                if not entry.is_file(follow_symlinks=False):
                    continue
                try:
                    stat = entry.stat()
                except OSError:
                    continue
                items.append(FileItem(
                    path=entry.path,
                    name=entry.name,
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                    category=_category_for(os.path.splitext(entry.name)[1]),
                    source=label,
                ))
        except OSError as exc:
            logger.warn(f"Klasör okunamadı ({folder}): {exc}")
    return items


def big_and_old(items: list[FileItem], min_mb: int = 100, days: int = 90) -> list[FileItem]:
    return [i for i in items if i.size >= min_mb * 1024 * 1024 or i.age_days >= days]


def group_items(items: list[FileItem]) -> dict[str, list[FileItem]]:
    out: dict[str, list[FileItem]] = {}
    for item in items:
        out.setdefault(item.category, []).append(item)
    for lst in out.values():
        lst.sort(key=lambda i: -i.size)
    return dict(sorted(out.items(), key=lambda kv: -sum(i.size for i in kv[1])))


def total_size(items: list[FileItem]) -> int:
    return sum(i.size for i in items)


def delete_to_recycle(paths: list[str], dry_run: bool = False) -> tuple[int, int]:
    """Dosyaları Geri Dönüşüm Kutusu'na taşır. (başarılı, başarısız)"""
    if not paths:
        return 0, 0
    if dry_run:
        for p in paths:
            logger.info(f"[DRY-RUN] Geri dönüşüm kutusuna: {p}")
        return len(paths), 0

    payload = json.dumps(paths, ensure_ascii=False)
    script = f"""
$json = @'
{payload}
'@
$paths = $json | ConvertFrom-Json
Add-Type -AssemblyName Microsoft.VisualBasic
$ok = 0; $fail = 0
foreach ($p in $paths) {{
  try {{
    if (Test-Path -LiteralPath $p) {{
      [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($p, 'OnlyErrorDialogs', 'SendToRecycleBin')
      $ok++
    }}
  }} catch {{ $fail++ }}
}}
[pscustomobject]@{{ok=$ok;fail=$fail}} | ConvertTo-Json
"""
    data = ps.ps_json(script, timeout=600) or {}
    return int(data.get("ok") or 0), int(data.get("fail") or 0)


def plan_classification(items: list[FileItem]) -> dict[str, list[FileItem]]:
    """Kategori -> hedef klasör eşlemesi."""
    plan: dict[str, list[FileItem]] = {}
    for item in items:
        folder = _CLASSIFY_MAP.get(item.category)
        if not folder:
            continue
        plan.setdefault(folder, []).append(item)
    return plan


def apply_classification(plan: dict[str, list[FileItem]], dry_run: bool = False) -> tuple[int, int]:
    moved, failed = 0, 0
    for folder, items in plan.items():
        for item in items:
            target_dir = Path(item.path).parent / folder
            target = target_dir / item.name
            if target.exists():
                stem, ext = os.path.splitext(item.name)
                index = 2
                while target.exists():
                    target = target_dir / f"{stem} ({index}){ext}"
                    index += 1
            if dry_run:
                logger.info(f"[DRY-RUN] Taşınacak: {item.path} -> {target}")
                moved += 1
                continue
            try:
                target_dir.mkdir(exist_ok=True)
                os.replace(item.path, target)
                from ..core import undo
                undo.record("file", {"src": str(target), "dst": item.path}, note=f"sınıflandırma: {item.name}")
                moved += 1
            except OSError as exc:
                logger.warn(f"Taşınamadı ({item.name}): {exc}")
                failed += 1
    return moved, failed
