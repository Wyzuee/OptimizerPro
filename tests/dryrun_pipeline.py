"""Deneme modu işlem hattı testi: gerçek değişiklik yapmadan tüm görevleri çalıştırır."""
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
from app.core.tasks import TaskContext, TaskEngine  # noqa: E402
from app.ui import theme  # noqa: E402
from app.ui.shell import STEPS, MainWindow  # noqa: E402


def main() -> int:
    SESSION.set("dry_run", True)
    # Temsili seçimler
    SESSION.set("cleanup", ["user_temp", "prefetch", "thumbcache", "recycle_bin"])
    SESSION.set("ofgb", {"sync_provider": True, "lockscreen_tips": True, "advertising_id": True})
    SESSION.set("debloat", {"telemetry": True, "suggestions": True, "dark_mode": True})
    SESSION.set("programs", ["7zip", "vlc"])
    SESSION.set("devlangs", ["python"])
    SESSION.set("power", {"enabled": True, "scheme": "ultimate"})

    app = QApplication(sys.argv[:1])
    theme.apply(app)
    window = MainWindow()
    for index in range(len(STEPS)):
        window._go_to(index)

    # Özet sayfasına git ve planı topla
    summary_index = next(i for i, s in enumerate(STEPS) if s[0] == "summary")
    window._go_to(summary_index)
    tasks = window._gather_plan()
    print(f"toplanan görev: {len(tasks)}")
    for task in tasks:
        print(f"  - [{task.group}] {task.title}")

    ctx = TaskContext(dry_run=True)
    engine = TaskEngine(tasks, ctx)
    results = engine.run()

    failed = [r for r in results if r.status == "failed"]
    print()
    for r in results:
        mark = {"done": "OK  ", "failed": "FAIL", "skipped": "SKIP"}.get(r.status, "?")
        print(f"{mark} {r.task.title[:52]:<54} {r.message[:40]}")

    print(f"\nbaşarılı={sum(1 for r in results if r.status == 'done')} "
          f"atlandı={sum(1 for r in results if r.status == 'skipped')} hata={len(failed)}")
    if failed:
        print("\nHATALAR:")
        for r in failed:
            print(f"  {r.task.title}: {r.message}")
            print(r.detail)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
