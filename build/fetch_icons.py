"""simple-icons CDN'den program logolarını indirip PNG'ye çevirir.

Kaynak: https://simpleicons.org (CC0 1.0). Erişilemeyen programlar için
arayüz çalışma anında baş harf rozeti üretir.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "assets" / "icons"
CACHE = ROOT / "build" / "_icons_svg"
SIZE = 128

# catalog.json id -> simple-icons slug
SLUGS: dict[str, str] = {
    "chrome": "googlechrome",
    "firefox": "firefox",
    "brave": "brave",
    "opera": "opera",
    "vivaldi": "vivaldi",
    "edge": "microsoftedge",
    "cursor": "cursor",
    "git": "git",
    "github-desktop": "github",
    "python312": "python",
    "nodejs": "nodedotjs",
    "jdk21": "openjdk",
    "dotnet-sdk": "dotnet",
    "dotnet-runtime8": "dotnet",
    "notepadpp": "notepadplusplus",
    "sublime": "sublimetext",
    "filezilla": "filezilla",
    "postman": "postman",
    "docker": "docker",
    "wireshark": "wireshark",
    "vlc": "vlcmediaplayer",
    "spotify": "spotify",
    "obs": "obsstudio",
    "audacity": "audacity",
    "gimp": "gimp",
    "krita": "krita",
    "blender": "blender",
    "handbrake": "handbrake",
    "discord": "discord",
    "telegram": "telegram",
    "whatsapp": "whatsapp",
    "zoom": "zoom",
    "slack": "slack",
    "teams": "microsoftteams",
    "libreoffice": "libreoffice",
    "sumatrapdf": "sumatrapdfreader",
    "7zip": "7zip",
    "winrar": "winrar",
    "peazip": "peazip",
    "bitwarden": "bitwarden",
    "keepassxc": "keepassxc",
    "malwarebytes": "malwarebytes",
    "tailscale": "tailscale",
    "wireguard": "wireguard",
    "steam": "steam",
    "epic": "epicgames",
    "eaapp": "ea",
    "qbittorrent": "qbittorrent",
    "sharex": "sharex",
    "powertoys": "microsoft",
    "everything": "everything",
}

DARK_THRESHOLD = 0.28


def fetch_svg(slug: str) -> str | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{slug}.svg"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    url = f"https://cdn.simpleicons.org/{slug}"
    request = urllib.request.Request(url, headers={"User-Agent": "OptimizerPro/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            text = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None
    if "<svg" not in text.lower():
        return None
    cached.write_text(text, encoding="utf-8")
    return text


def _luminance(color: QColor) -> float:
    return (0.2126 * color.redF() + 0.7152 * color.greenF() + 0.0722 * color.blueF())


def _tint(color: QColor) -> QColor:
    """Çok koyu logosu arka planda görünür hale getirir."""
    if _luminance(color) >= DARK_THRESHOLD:
        return color
    light = QColor("#DCE9F3")
    mix = 0.75
    return QColor.fromRgbF(
        color.redF() * (1 - mix) + light.redF() * mix,
        color.greenF() * (1 - mix) + light.greenF() * mix,
        color.blueF() * (1 - mix) + light.blueF() * mix,
    )


def _fill_color(svg: str) -> QColor:
    match = re.search(r'fill="(#[0-9a-fA-F]{3,8})"', svg)
    if not match:
        return QColor("#DCE9F3")
    color = QColor(match.group(1))
    return color if color.isValid() else QColor("#DCE9F3")


def render_png(svg: str, target: Path) -> bool:
    data = QByteArray(svg.encode("utf-8"))
    renderer = QSvgRenderer(data)
    if not renderer.isValid():
        return False

    image = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()

    # Koyu renkli logoları aydınlat
    base = _fill_color(svg)
    tinted = _tint(base)
    if tinted != base:
        for y in range(image.height()):
            for x in range(image.width()):
                pixel = image.pixelColor(x, y)
                if pixel.alpha() > 8:
                    pixel.setRedF(tinted.redF())
                    pixel.setGreenF(tinted.greenF())
                    pixel.setBlueF(tinted.blueF())
                    image.setPixelColor(x, y, pixel)

    target.parent.mkdir(parents=True, exist_ok=True)
    return image.save(str(target), "PNG")


def main() -> int:
    app = QGuiApplication(sys.argv[:1])  # noqa: F841
    OUT.mkdir(parents=True, exist_ok=True)
    ok, miss = 0, []
    for app_id, slug in SLUGS.items():
        target = OUT / f"{app_id}.png"
        if target.exists():
            ok += 1
            continue
        svg = fetch_svg(slug)
        if not svg:
            miss.append(f"{app_id} ({slug})")
            continue
        if render_png(svg, target):
            ok += 1
        else:
            miss.append(f"{app_id} (render)")

    report = {"downloaded": ok, "missing": miss}
    (OUT / "_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"indirilen: {ok}, eksik: {len(miss)}")
    for item in miss:
        print("  eksik:", item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
