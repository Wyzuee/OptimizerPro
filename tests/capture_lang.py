"""İngilizce arayüzü ekran görüntüleriyle doğrular."""
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
    lang = "en" if "--en" in sys.argv else "tr"
    i18n.initialize(lang, fallback_to_system=False)
    SESSION.set("language", lang)

    app = QApplication(sys.argv[:1])
    theme.apply(app)
    window = MainWindow()
    window.resize(1280, 860)
    window.show()

    for step in ("welcome", "cleanup", "programs", "debloat_placeholder"):
        if step == "debloat_placeholder":
            continue
        index = next(i for i, s in enumerate(STEPS) if s[0] == step)
        window._go_to(index)
        settle(app)
        window.grab().save(str(OUT / f"{lang}_{step}.png"))

    ads = next(i for i, s in enumerate(STEPS) if s[0] == "ads")
    window._go_to(ads)
    settle(app)
    window.grab().save(str(OUT / f"{lang}_ads.png"))

    print("kaydedildi", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
