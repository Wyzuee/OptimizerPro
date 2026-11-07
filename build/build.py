"""PyInstaller derleme betiği."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build" / "_pyi"


def main() -> int:
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    python = str(venv_py) if venv_py.exists() else sys.executable

    args = [
        python, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--uac-admin",
        "--name", "Optimizer Pro",
        "--icon", str(ROOT / "app" / "assets" / "app.ico"),
        "--version-file", str(ROOT / "build" / "version_info.txt"),
        "--add-data", f"{ROOT / 'app' / 'data'};data",
        "--add-data", f"{ROOT / 'app' / 'assets'};assets",
        "--add-data", f"{ROOT / 'app' / 'i18n'};i18n",
        "--add-binary", f"{ROOT / 'tools' / 'Optimizer.exe'};tools",
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
        "--specpath", str(ROOT / "build"),
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "PySide6.QtMultimedia",
        "--exclude-module", "PySide6.QtCharts",
        "--exclude-module", "PySide6.QtDataVisualization",
        "--exclude-module", "tkinter",
        "--exclude-module", "unittest",
        "--exclude-module", "pytest",
        str(ROOT / "app" / "main.py"),
    ]
    print("çalıştırılıyor:", " ".join(args[:8]), "…")
    result = subprocess.run(args, cwd=str(ROOT))
    if result.returncode == 0:
        exe = DIST / "Optimizer Pro.exe"
        size = exe.stat().st_size / (1024 * 1024) if exe.exists() else 0
        print(f"\n[OK] derlendi: {exe} ({size:.1f} MB)")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
