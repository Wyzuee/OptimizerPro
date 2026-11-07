"""Arayüz duman testi: tüm sayfaları oluşturur, plan üretir. Gerçek değişiklik yapmaz."""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core.state import SESSION  # noqa: E402
from app.ui import theme  # noqa: E402
from app.ui.shell import STEPS, MainWindow  # noqa: E402


def main() -> int:
    SESSION.set("dry_run", True)
    app = QApplication(sys.argv[:1])
    theme.apply(app)
    window = MainWindow()

    problems = 0
    for index, (step_id, title, _) in enumerate(STEPS):
        try:
            window._go_to(index)
            page = window.pages.get(step_id)
            if page is not None:
                page.collect()
                tasks = page.plan()
                print(f"OK   {step_id:<10} {len(tasks)} görev  ({title})")
        except Exception:
            problems += 1
            print(f"FAIL {step_id}")
            traceback.print_exc()

    # Özet sayfası plan toplama
    try:
        window._go_to(len(STEPS) - 1)
        window._go_to(10)
        plan = window._gather_plan()
        print(f"OK   summary    toplam {len(plan)} görev")
    except Exception:
        problems += 1
        traceback.print_exc()

    # Bitiş ekranı boş sonuçla
    try:
        window._show_finish({"total": 0, "done": 0, "skipped": 0, "failed": 0, "results": []}, {})
        print("OK   finish")
    except Exception:
        problems += 1
        traceback.print_exc()

    print("\nsorun sayısı:", problems)
    return 1 if problems else 0

if __name__ == "__main__":
    raise SystemExit(main())
