"""Program ikonları: indirilen PNG veya üretilen baş harf rozeti."""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap,
)

from ..core.paths import asset

# Kategoriye göre rozet gradyanları (indirilemeyen logolar için)
_CATEGORY_COLORS: dict[str, tuple[str, str]] = {
    "Sistem Araçları": ("#1E3A8A", "#3B82F6"),
    "Tarayıcı": ("#0C4A6E", "#0EA5E9"),
    "Geliştirici": ("#134E4A", "#14B8A6"),
    "Çalışma Zamanı": ("#3B0764", "#A855F7"),
    "Medya": ("#7C2D12", "#F97316"),
    "İletişim": ("#164E63", "#22D3EE"),
    "Ofis": ("#422006", "#EAB308"),
    "Arşivleme": ("#365314", "#84CC16"),
    "Güvenlik": ("#4C0519", "#F43F5E"),
    "Oyun": ("#312E81", "#6366F1"),
}
_DEFAULT_COLORS = ("#1F2937", "#6B7280")

_cache: dict[str, QPixmap] = {}


def _badge_letter(name: str) -> str:
    words = [w for w in name.replace("+", " ").replace("/", " ").split() if w]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][0].upper()
    # "Visual Studio Code" -> "VS", "7-Zip" -> "7Z"
    return (words[0][0] + words[1][0]).upper()


def _draw_badge(name: str, category: str, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    top, bottom = _CATEGORY_COLORS.get(category, _DEFAULT_COLORS)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor(top))
    gradient.setColorAt(1.0, QColor(bottom))

    path = QPainterPath()
    radius = size * 0.24
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.fillPath(path, QBrush(gradient))

    font = QFont("Segoe UI Variable Display", int(size * 0.38))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#F5FAFF"))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, _badge_letter(name))
    painter.end()
    return pixmap


def pixmap(app_id: str, name: str, category: str, size: int = 40) -> QPixmap:
    key = f"{app_id}@{size}"
    if key in _cache:
        return _cache[key]

    icon_path = asset(f"icons/{app_id}.png")
    pixmap = QPixmap(str(icon_path)) if icon_path.exists() else QPixmap()
    if pixmap.isNull():
        pixmap = _draw_badge(name, category, size)
    else:
        pixmap = pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    _cache[key] = pixmap
    return pixmap


def icon(app_id: str, name: str, category: str, size: int = 40) -> QIcon:
    return QIcon(pixmap(app_id, name, category, size))


def category_badge(category: str, size: int = 20) -> QPixmap:
    return _draw_badge(category, category, size)


def icon_size(size: int = 40) -> QSize:
    return QSize(size, size)
