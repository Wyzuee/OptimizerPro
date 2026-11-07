"""Sayfaların ekran görüntüsünü alır (tasarım kontrolü için)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.pop("QT_QPA_PLATFORM", None)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core.state import SESSION  # noqa: E402
from app.ui import theme  # noqa: E402
from app.ui.shell import STEPS, MainWindow  # noqa: E402

OUT = ROOT / "build" / "_shots"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    theme.apply(app)
    window = MainWindow()
    window.resize(1280, 820)
    window.show()

    wanted = {"welcome", "cleanup", "programs", "ads", "summary"}
    for index, (step_id, _, _) in enumerate(STEPS):
        if step_id not in wanted:
            continue
        window._go_to(index)
        app.processEvents()
        window.grab().save(str(OUT / f"{index:02d}_{step_id}.png"))

    print(f"kaydedildi: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
