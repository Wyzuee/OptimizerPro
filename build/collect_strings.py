"""UI metinlerini toplar (çeviri kataloğu hazırlığı)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "_strings.json"

SKIP = re.compile(
    r"(Get-|Set-|Remove-|New-|Select-|Where-|Convert|\$env|HKCU|HKLM|SOFTWARE|"
    r"\.exe|\.ps1|\.json|\.ico|\.png|%TEMP%|https?://|winget|--[a-z]|"
    r"\{\{|\}\}|;|\|\||\^|\$_|pid=)"
)

QUOTE_PATTERNS = [
    re.compile(r'(?<![\w.])[frbu]{0,2}"((?:[^"\\]|\\.)*)"'),
    re.compile(r"(?<![\w.])[frbu]{0,2}'((?:[^'\\]|\\.)*)'"),
]


def collect() -> list[str]:
    found: dict[str, None] = {}
    for path in sorted(ROOT.glob("app/**/*.py")):
        if "__pycache__" in str(path):
            continue
        src = path.read_text(encoding="utf-8")
        src = re.sub(r'""".*?"""', "", src, flags=re.S)
        src = re.sub(r"'''.*?'''", "", src, flags=re.S)
        src = re.sub(r"#[^\n]*", "", src)
        for pattern in QUOTE_PATTERNS:
            for match in pattern.finditer(src):
                text = match.group(1)
                if len(text) < 2 or len(text) > 300:
                    continue
                if "\\" in text or "%" in text and "%s" in text:
                    continue
                if not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", text):
                    continue
                if SKIP.search(text):
                    continue
                found[text.strip()] = None
    return sorted(found)


def main() -> int:
    strings = collect()
    OUT.write_text(json.dumps(strings, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(strings)} metin -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
