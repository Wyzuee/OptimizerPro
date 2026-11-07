"""Optimizer.exe ikonundan çok boyutlu .ico ve logo.png üretir."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QGuiApplication, QImage

SIZES = [16, 24, 32, 48, 64, 128, 256]


def load_source(path: Path) -> QImage:
    image = QImage(str(path))
    if image.isNull():
        raise SystemExit(f"Kaynak görsel okunamadı: {path}")
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def build_ico(source: QImage, target: Path) -> None:
    entries = []
    for size in SIZES:
        scaled = source.scaled(
            size, size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        entries.append((size, png_bytes(scaled)))

    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    directory = b""
    payload = b""
    for size, data in entries:
        width = 0 if size >= 256 else size
        height = 0 if size >= 256 else size
        directory += struct.pack(
            "<BBBBHHII", width, height, 0, 0, 1, 32, len(data), offset
        )
        payload += data
        offset += len(data)

    target.write_bytes(header + directory + payload)


def main() -> int:
    if len(sys.argv) < 3:
        print("kullanım: make_icons.py <kaynak.png> <çıktı_klasörü>")
        return 1
    source_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    app = QGuiApplication(sys.argv[:1])  # noqa: F841
    source = load_source(source_path)

    if source.width() != 256:
        source = source.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)

    build_ico(source, out_dir / "app.ico")
    source.save(str(out_dir / "logo.png"), "PNG")
    print(f"üretildi: {out_dir / 'app.ico'}, {out_dir / 'logo.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
