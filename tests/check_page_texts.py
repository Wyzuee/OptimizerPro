"""Sayfa başlık/alt başlıklarının çeviri anahtarlarını doğrular."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ui.shell import STEPS  # noqa: E402

EN = ROOT / "app" / "i18n" / "en.json"


def main() -> int:
    catalog = json.loads(EN.read_text(encoding="utf-8"))
    from app.core import i18n
    i18n.initialize("en", fallback_to_system=False)

    missing = 0
    for step_id, _, factory in STEPS:
        for attr in ("title", "subtitle"):
            text = getattr(factory, attr, "")
            if not text:
                continue
            translated = catalog.get(text)
            status = "OK  " if translated else "EKSİK"
            if not translated:
                missing += 1
            print(f"{status} {step_id:10s} {attr:9s} {text[:70]}")
            if translated:
                print(f"            -> {translated[:70]}")

    print(f"\neksik: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
