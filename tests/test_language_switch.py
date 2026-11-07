"""Dil değiştirme akışını test eder: TR -> EN -> TR aynı adımda kalmalı."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.pop("QT_QPA_PLATFORM", None)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core import i18n  # noqa: E402
from app.core.state import SESSION  # noqa: E402
from app.ui import theme  # noqa: E402
from app.ui.shell import STEPS, MainWindow  # noqa: E402

OUT = ROOT / "build" / "_shots"


def settle(app, rounds: int = 10) -> None:
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.04)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    i18n.initialize("tr", fallback_to_system=False)
    SESSION.set("language", "tr")

    app = QApplication(sys.argv[:1])
    theme.apply(app)
    window = MainWindow()
    window.resize(1280, 860)
    window.show()

    problems = 0
    target = next(i for i, s in enumerate(STEPS) if s[0] == "programs")
    window._go_to(target)
    settle(app)
    print(f"TR: adım={window.current_index} başlık={window.page_title.text()!r}")
    if window.page_title.text() != "Programlar":
        problems += 1
        print("  FAIL: TR başlık")

    # EN'e geç
    window._change_language("en")
    settle(app)
    print(f"EN: adım={window.current_index} başlık={window.page_title.text()!r} "
          f"buton={window.next_btn.text()!r} dry={window.dry_btn.text()!r}")
    if window.page_title.text() != "Programs":
        problems += 1
        print("  FAIL: EN başlık")
    if window.current_index != target:
        problems += 1
        print("  FAIL: adım değişti")
    if SESSION.get("language") != "en":
        problems += 1
        print("  FAIL: dil kaydedilmedi")
    window.grab().save(str(OUT / "switch_en.png"))

    # TR'ye dön
    window._change_language("tr")
    settle(app)
    print(f"TR: adım={window.current_index} başlık={window.page_title.text()!r}")
    if window.page_title.text() != "Programlar":
        problems += 1
        print("  FAIL: TR'ye dönüş")
    window.grab().save(str(OUT / "switch_tr.png"))

    # Sayfa önbelleği gerçekten yenilendi mi?
    fresh = window.pages.get("programs")
    if fresh is None:
        problems += 1
        print("  FAIL: sayfa yeniden kurulmadı")

    print(f"\nsorun: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
