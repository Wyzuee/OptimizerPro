"""Arayüz için küçük varlıkları (onay işareti) üretir."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen


def make_check(target: Path, color: str = "#04141A", size: int = 64) -> None:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(size * 0.14)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline([
        QPointF(size * 0.22, size * 0.53),
        QPointF(size * 0.42, size * 0.72),
        QPointF(size * 0.79, size * 0.30),
    ])
    painter.end()
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(target), "PNG")


if __name__ == "__main__":
    app = QGuiApplication(sys.argv[:1])  # noqa: F841
    out = Path(__file__).resolve().parent.parent / "app" / "assets"
    make_check(out / "check.png")
    print("üretildi:", out / "check.png")
