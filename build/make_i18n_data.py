"""catalog.en.json üretir: Türkçe katalogtan İngilizce katman.

Ad/açıklama çevirileri elle yazılmış sözlükten gelir; kategori adları da çevrilir.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "app" / "data"

CATEGORIES = {
    "Sistem Araçları": "System Tools",
    "Tarayıcı": "Browsers",
    "Geliştirici": "Developer",
    "Çalışma Zamanı": "Runtimes",
    "Medya": "Media",
    "İletişim": "Communication",
    "Ofis": "Office",
    "Arşivleme": "Archiving",
    "Güvenlik": "Security",
    "Oyun": "Gaming",
}

APPS: dict[str, dict[str, str]] = {
    "pcmanager": {"description": "Microsoft's system maintenance and cleanup tool."},
    "wintoys": {"description": "Manage Windows settings from one place."},
    "revouninstaller": {"description": "Uninstall programs together with their leftovers."},
    "everything": {"description": "Instant file search engine."},
    "powertoys": {"description": "Microsoft's advanced power-user utility set."},
    "wiztree": {"description": "Fast disk usage analyzer with visualization."},
    "windirstat": {"description": "Disk space statistics."},
    "teracopy": {"description": "Fast and reliable file copying."},
    "sharex": {"description": "Screenshot and screen recording tool."},
    "cpuz": {"description": "Hardware information viewer."},
    "hwmonitor": {"description": "Temperature and voltage monitoring."},
    "chrome": {"description": "Google's fast browser."},
    "firefox": {"description": "Open-source browser."},
    "brave": {"description": "Privacy-focused browser with ad blocking."},
    "opera": {"description": "Alternative browser."},
    "vivaldi": {"description": "Highly customizable browser."},
    "edge": {"description": "Browser bundled with Windows."},
    "vscode": {"description": "Popular code editor."},
    "cursor": {"description": "AI-powered code editor."},
    "git": {"description": "Version control system."},
    "github-desktop": {"description": "Desktop GUI for Git."},
    "python312": {"description": "Python programming language."},
    "nodejs": {"description": "JavaScript runtime."},
    "jdk21": {"description": "Java development kit."},
    "dotnet-sdk": {"description": ".NET application development kit."},
    "vs-buildtools": {"description": "C/C++ build tools (MSVC)."},
    "notepadpp": {"description": "Advanced text editor."},
    "sublime": {"description": "Fast text editor."},
    "putty": {"description": "SSH client."},
    "winscp": {"description": "SFTP/SCP client."},
    "filezilla": {"description": "FTP client."},
    "docker": {"description": "Container development platform."},
    "postman": {"description": "API testing tool."},
    "wireshark": {"description": "Network protocol analyzer."},
    "dotnet-runtime8": {"description": "Required by OFGB and many apps."},
    "vcredist": {"description": "Runtime for C++ applications."},
    "jre": {"description": "Runtime for Java applications."},
    "directx": {"description": "DirectX libraries for older games."},
    "vlc": {"description": "Media player that handles every format."},
    "spotify": {"description": "Music streaming service."},
    "obs": {"description": "Screen recording and live streaming."},
    "audacity": {"description": "Audio editing program."},
    "gimp": {"description": "Open-source image editor."},
    "krita": {"description": "Digital painting program."},
    "blender": {"description": "3D modeling and animation."},
    "handbrake": {"description": "Video converter."},
    "klite": {"description": "Video codec pack."},
    "discord": {"description": "Voice and text chat."},
    "telegram": {"description": "Fast messaging app."},
    "whatsapp": {"description": "WhatsApp desktop."},
    "zoom": {"description": "Video conferencing."},
    "slack": {"description": "Team communication."},
    "teams": {"description": "Corporate meetings and chat."},
    "libreoffice": {"description": "Free office suite."},
    "sumatrapdf": {"description": "Lightweight PDF reader."},
    "foxitreader": {"description": "PDF reader."},
    "acrobat": {"description": "Adobe's PDF reader."},
    "7zip": {"description": "File compression tool."},
    "winrar": {"description": "RAR archive manager."},
    "peazip": {"description": "Open-source archive manager."},
    "rufus": {"description": "Bootable USB creator."},
    "bitwarden": {"description": "Open-source password manager."},
    "keepassxc": {"description": "Local password vault."},
    "malwarebytes": {"description": "Malware scanner."},
    "tailscale": {"description": "WireGuard-based mesh VPN."},
    "wireguard": {"description": "Fast VPN tunnel."},
    "steam": {"description": "Game store."},
    "epic": {"description": "Epic games store."},
    "eaapp": {"description": "Electronic Arts game client."},
    "qbittorrent": {"description": "Torrent client."},
}

NOTES = {
    "winrar": "Trial version; a license is required.",
}

# Mağaza (Store) uygulamaları: MS Store kimliğiyle kurulanlarda ad korunur
RENAMES = {
    "pcmanager": "PC Manager",
    "wintoys": "Wintoys",
    "revouninstaller": "Revo Uninstaller",
}


def main() -> int:
    base = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    apps_patch: dict[str, dict[str, str]] = {}
    for app in base.get("apps", []):
        app_id = app["id"]
        patch: dict[str, str] = {}
        category = app.get("category", "")
        if category in CATEGORIES:
            patch["category"] = CATEGORIES[category]
        if app_id in RENAMES:
            patch["name"] = RENAMES[app_id]
        if app_id in APPS:
            patch.update(APPS[app_id])
        if app_id in NOTES:
            patch["notes"] = NOTES[app_id]
        if patch:
            apps_patch[app_id] = patch

    payload = {
        "__comment": "English overlay for catalog.json",
        "categories": list(CATEGORIES.values()),
        "apps": apps_patch,
    }
    (DATA / "catalog.en.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"catalog.en.json: {len(apps_patch)} uygulama katmanı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
