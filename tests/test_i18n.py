"""i18n kapsam testi: TR/EN veri katmanları ve t() davranışı."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core import i18n  # noqa: E402
from app.modules import catalog, cleanup, debloat, devtools, ofgb  # noqa: E402


def main() -> int:
    problems = 0
    for lang in ("tr", "en"):
        i18n.initialize(lang, fallback_to_system=False)
        cat = catalog.load_catalog()
        targets = cleanup.load_targets()
        toggles = ofgb.load_toggles()
        tweaks = debloat.load_tweaks()
        langs = devtools.load_languages()

        print(f"--- {lang} ---")
        print(f"  t('Programlar')      = {i18n.t('Programlar')}")
        print(f"  kategoriler          = {cat.categories[:3]}")
        print(f"  uygulama             = {[(a.name, a.category) for a in cat.apps[:2]]}")
        print(f"  vscode açıklama      = {[a.description for a in cat.apps if a.id == 'vscode']}")
        print(f"  temizlik             = {[t.name for t in targets[:2]]} / {targets[0].group}")
        print(f"  ofgb                 = {[t.title for t in toggles[:2]]} / {toggles[0].category}")
        print(f"  debloat              = {[t.title for t in tweaks[:2]]} / {tweaks[0].category}")
        print(f"  diller               = {[l.title for l in langs[:3]]}")

        if lang == "en":
            checks = {
                "t(Programlar)": i18n.t("Programlar") == "Programs",
                "kategori": cat.categories[0] == "System Tools",
                "temizlik": "User temporary" in targets[0].name,
                "ofgb": "File Explorer" in toggles[0].title,
                "debloat": "Telemetry" in tweaks[0].title,
                "dil C/C++": langs[1].title == "C / C++",
            }
            for label, ok in checks.items():
                print(f"  {'OK  ' if ok else 'FAIL'} {label}")
                if not ok:
                    problems += 1

    print(f"\nsorun: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
