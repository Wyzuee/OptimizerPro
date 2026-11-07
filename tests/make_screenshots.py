"""README ekran görüntülerini üretir (docs/screenshots)."""
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

OUT = ROOT / "docs" / "screenshots"

SHOTS = [
    ("welcome", "01-welcome"),
    ("cleanup", "02-cleanup"),
    ("programs", "03-programs"),
    ("ads", "04-ads"),
    ("devtools", "05-devtools"),
]

LANG = "tr" if "--tr" not in sys.argv else "tr"
if "--en" in sys.argv:
    LANG = "en"


def settle(app, rounds: int = 12) -> None:
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.04)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    i18n.initialize(LANG, fallback_to_system=False)
    SESSION.set("language", LANG)

    app = QApplication(sys.argv[:1])
    theme.apply(app)
    window = MainWindow()
    window.resize(1360, 900)
    window.show()

    for step_id, filename in SHOTS:
        index = next(i for i, s in enumerate(STEPS) if s[0] == step_id)
        window._go_to(index)
        settle(app)
        window.grab().save(str(OUT / f"{filename}.png"))
        print(f"kaydedildi {filename}.png")

    # Bitiş ekranı örnek sonuçla
    class FakeTask:
        def __init__(self, title, group):
            self.title = title
            self.group = group

    class FakeResult:
        def __init__(self, title, group, status, message="", duration=1.0):
            self.task = FakeTask(title, group)
            self.status = status
            self.message = message
            self.duration = duration

    results = [
        FakeResult("Kullanıcı geçici dosyaları", "Temizlik", "done", "", 2.4),
        FakeResult("Prefetch önbelleği", "Temizlik", "done", "", 0.8),
        FakeResult("Windows Update indirme önbelleği", "Temizlik", "failed", "servis durdurulamadı", 12.1),
        FakeResult("Geri Dönüşüm Kutusu", "Temizlik", "skipped", "kullanıcı atladı", 0.1),
        FakeResult("12 reklam ayarını kapat", "Reklamlar", "done", "", 0.6),
        FakeResult("Win11Debloat · 8 ayar", "Gizlilik / Tweaks", "done", "", 46.2),
        FakeResult("Visual Studio Code", "Programlar", "done", "", 32.0),
    ]
    summary = {
        "total": len(results),
        "done": sum(1 for r in results if r.status == "done"),
        "skipped": sum(1 for r in results if r.status == "skipped"),
        "failed": sum(1 for r in results if r.status == "failed"),
        "results": results,
    }
    stats = {
        "cleanup_bytes": 4_935_000_000,
        "programs_installed": 3,
        "ads_applied": 12,
        "tweaks_applied": 8,
        "appx_removed": 6,
        "startup_changed": 4,
        "files_deleted": 23,
    }
    window._show_finish(summary, stats)
    settle(app)
    window.grab().save(str(OUT / "06-finish.png"))
    print("kaydedildi 06-finish.png")

    print("dizin:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
