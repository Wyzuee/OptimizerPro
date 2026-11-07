"""Geliştirici araç zincirleri: dil seçimine göre program + eklenti önerisi."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from ..core import logger, ps
from ..core.paths import data_file

VSCODE_CLI_CANDIDATES = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
    os.path.expandvars(r"%PROGRAMFILES%\Microsoft VS Code\bin\code.cmd"),
    os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft VS Code\bin\code.cmd"),
]


@dataclass
class Language:
    id: str
    title: str
    description: str
    icon: str = ""
    apps: list[str] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    post: list[str] = field(default_factory=list)
    notes: str = ""


def load_languages() -> list[Language]:
    from ..core.i18n import load_json_with_overlay

    raw = load_json_with_overlay("dev_rules.json")
    out = []
    for item in raw.get("languages", []):
        out.append(Language(
            id=item["id"],
            title=item["title"],
            description=item.get("description", ""),
            icon=item.get("icon", ""),
            apps=item.get("apps", []),
            extensions=item.get("extensions", []),
            post=item.get("post", []),
            notes=item.get("notes", ""),
        ))
    return out


def vscode_cli() -> str | None:
    for path in VSCODE_CLI_CANDIDATES:
        if os.path.isfile(path):
            return path
    for name in ("code.cmd", "code"):
        found = ps.which(name)
        if found:
            return found
    return None


def install_extensions(extensions: list[str], dry_run: bool = False, on_line=None) -> tuple[int, int]:
    cli = vscode_cli()
    if not cli:
        logger.warn("VS Code CLI bulunamadı, eklentiler kurulamadı")
        return 0, len(extensions)
    if dry_run:
        for ext in extensions:
            logger.info(f"[DRY-RUN] code --install-extension {ext}")
        return len(extensions), 0

    ok = fail = 0
    for ext in extensions:
        result = ps.run_command([cli, "--install-extension", ext, "--force"], on_line=on_line, timeout=300)
        if result.ok:
            ok += 1
            logger.info(f"Eklenti kuruldu: {ext}")
        else:
            fail += 1
            logger.warn(f"Eklenti kurulamadı: {ext}")
    return ok, fail


def run_post_commands(commands: list[str], dry_run: bool = False, on_line=None) -> tuple[int, int]:
    ok = fail = 0
    for command in commands:
        if dry_run:
            logger.info(f"[DRY-RUN] {command}")
            ok += 1
            continue
        result = ps.run_powershell(command, on_line=on_line, timeout=600)
        if result.ok:
            ok += 1
        else:
            fail += 1
            logger.warn(f"Komut başarısız: {command}")
    return ok, fail


def detect_installed_toolchains() -> dict[str, str]:
    """PATH'te bulunan dilleri raporlar."""
    checks = {
        "python": ["python", "python3"],
        "node": ["node"],
        "java": ["java"],
        "git": ["git"],
        "dotnet": ["dotnet"],
        "gcc": ["gcc", "g++"],
        "dotnet-sdk": ["dotnet"],
    }
    found = {}
    for key, names in checks.items():
        for name in names:
            path = ps.which(name)
            if path:
                found[key] = path
                break
    return found
