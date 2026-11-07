"""Programlar sayfası görsel kontrolü (yerleşim tamamlanmasını bekler)."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.pop("QT_QPA_PLATFORM", None)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core.state import SESSION  # noqa: E402
from app.ui import theme  # noqa: E402
from app.ui.shell import STEPS, MainWindow  # noqa: E402

OUT = ROOT / "build" / "_shots"


def settle(app: QApplication, rounds: int = 12) -> None:
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.04)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    theme.apply(app)
    window = MainWindow()
    window.resize(1280, 860)
    window.show()

    index = next(i for i, s in enumerate(STEPS) if s[0] == "programs")
    window._go_to(index)
    settle(app)
    window.grab().save(str(OUT / "07_programs.png"))

    page = window.pages["programs"]
    page.search.setText("python")
    settle(app)
    window.grab().save(str(OUT / "07b_programs_search.png"))

    page.search.setText("")
    page.category_combo.setCurrentText("Geliştirici")
    settle(app)
    window.grab().save(str(OUT / "07c_programs_category.png"))

    print("kaydedildi:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
