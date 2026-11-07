"""Temizlik, OFGB, debloat, dil kuralları ve Appx için İngilizce katmanlar."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "app" / "data"

CLEANUP = {
    "user_temp": ("User temporary files", "Temporary files in %TEMP%. Some may be locked while apps run."),
    "windows_temp": ("Windows temporary files", "Contents of C:\\Windows\\Temp."),
    "prefetch": ("Prefetch cache", "Windows recreates it; frees space with no lasting performance impact."),
    "thumbcache": ("Thumbnail cache", "File Explorer thumbnail databases."),
    "crashdumps": ("Crash dumps", "Error dumps in the CrashDumps folder."),
    "gpu_cache": ("GPU shader caches", "NVIDIA DXCache and AMD DxCache folders."),
    "windows_update_cache": ("Windows Update download cache", "Contents of SoftwareDistribution\\Download. Services are stopped temporarily."),
    "delivery_optimization": ("Delivery Optimization cache", "Update fragments shared with other computers."),
    "old_logs": ("Old setup and update logs", "CBS, DISM and Windows Update log files."),
    "recycle_bin": ("Recycle Bin", "Permanently empties deleted files."),
    "windows_old": ("Windows.old (previous version)", "Previous Windows installation left after an upgrade. No rollback remains."),
    "dism_cleanup": ("WinSxS component cleanup (DISM)", "Removes unused Windows components. May take a long time."),
}
CLEANUP_GROUPS = {
    "Geçici Dosyalar": "Temporary Files",
    "Windows Update": "Windows Update",
    "Çöp Kutusu": "Recycle Bin",
    "Sistem Bileşenleri": "System Components",
}
CLEANUP_WARNINGS = {
    "windows_update_cache": "Downloaded but not yet installed updates are deleted; they will be downloaded again.",
    "recycle_bin": "Files in the Recycle Bin cannot be recovered.",
    "windows_old": "You can no longer roll back to the previous Windows version. Usually frees 10-30 GB.",
    "dism_cleanup": "This can take 10-40 minutes. Updates can no longer be uninstalled.",
}

OFGB = {
    "sync_provider": ("File Explorer sync notifications", "Turns off promotional notifications from providers like OneDrive in File Explorer."),
    "lockscreen_tips": ("Lock screen tips and fun facts", "Turns off suggestions, tips and promotions shown on the lock screen."),
    "settings_suggestions": ("Suggested content in Settings", "Turns off suggestion cards on the Settings home page."),
    "windows_tips": ("Windows usage tips", "Turns off suggestions and tips shown while using Windows."),
    "scoobe": ("Setup completion suggestions", "Turns off 'Get the most out of your device' suggestions."),
    "welcome_experience": ("Post-update welcome experience", "Turns off the 'what's new' screen shown after updates."),
    "advertising_id": ("Advertising ID", "Prevents apps from using your advertising ID for personalized ads."),
    "tailored_experiences": ("Tailored experiences", "Turns off suggestions personalized from diagnostic data."),
    "start_recommendations": ("Start menu recommendations", "Turns off 'recommended' app and tip cards in the Start menu."),
    "smart_optout": ("Unused app notifications", "Turns off 'you haven't opened these apps in a while' style suggestions."),
    "bing_search": ("Bing results in Search", "Turns off web/Bing results in Windows Search (policy key)."),
    "edge_widget": ("Edge desktop search widget", "Turns off the desktop search widget opened by Edge (policy key)."),
}
OFGB_CATEGORIES = {
    "Dosya Gezgini": "File Explorer",
    "Kilit Ekranı": "Lock Screen",
    "Ayarlar": "Settings",
    "Genel": "General",
    "Gizlilik": "Privacy",
    "Başlat Menüsü": "Start Menu",
    "Bildirimler": "Notifications",
    "Arama": "Search",
    "Edge": "Edge",
}

DEBLOAT = {
    "telemetry": ("Telemetry and diagnostic data", "Turns off diagnostic data, activity history and app-launch tracking."),
    "suggestions": ("Suggestions and ads", "Turns off suggestions, tips and ads across Windows."),
    "bing": ("Bing and Copilot in Search", "Turns off web results in Windows Search."),
    "location": ("Location services", "Turns off Windows location services and app location access."),
    "findmydevice": ("Find My Device", "Stops sending location data to Microsoft."),
    "activity_history": ("Activity history", "Turns off activity history and app-launch tracking."),
    "copilot": ("Copilot", "Disables and uninstalls Microsoft Copilot."),
    "recall": ("Windows Recall", "Turns off Recall, which records screen history."),
    "clicktodo": ("Click to Do", "Turns off AI-powered text/image analysis."),
    "ai_svc": ("AI service auto-start", "Prevents the WSAIFabricSvc service from starting automatically."),
    "edge_ai": ("Edge AI features", "Turns off the AI sidebar and Copilot features in Edge."),
    "edge_ads": ("Edge ads and MSN feed", "Turns off ads, suggestions and the news feed in Edge."),
    "paint_ai": ("Paint AI", "Turns off image generation tools in Paint."),
    "notepad_ai": ("Notepad AI", "Turns off writing suggestions in Notepad."),
    "chrome_ai": ("Chrome AI", "Turns off Gemini and AI features in Chrome."),
    "brave_bloat": ("Brave extras", "Turns off AI, crypto, news and VPN features in Brave."),
    "dark_mode": ("Dark theme", "Enables dark theme for the system and apps."),
    "transparency": ("Disable transparency effects", "Turns off transparency; speeds up older hardware."),
    "animations": ("Disable animations", "Turns off UI animations for a snappier feel."),
    "context_menu": ("Classic context menu", "Restores the Windows 10 style right-click menu."),
    "mouse_accel": ("Disable mouse acceleration", "Makes mouse movement more consistent."),
    "sticky_keys": ("Sticky Keys shortcut", "Turns off the dialog shown when pressing Shift 5 times."),
    "file_ext": ("Show file extensions", "Shows extensions for known file types."),
    "hidden_files": ("Show hidden files", "Makes hidden files and folders visible."),
    "hide_gallery": ("Hide Gallery section", "Removes Gallery from the navigation pane."),
    "hide_home": ("Hide Home section", "Removes Home from the navigation pane."),
    "hide_onedrive": ("Hide OneDrive section", "Removes OneDrive from the navigation pane."),
    "explorer_thispc": ("Open to This PC", "File Explorer starts at 'This PC'."),
    "add_folders": ("Add folders to This PC", "Adds Desktop, Documents, Downloads and more."),
    "taskbar_left": ("Align taskbar to the left", "Left-aligns taskbar buttons."),
    "hide_taskview": ("Hide Task View button", "Removes the Task View button from the taskbar."),
    "hide_search": ("Hide search box", "Removes the search box from the taskbar."),
    "widgets": ("Disable widgets", "Turns off taskbar and lock screen widgets."),
    "end_task": ("'End task' in taskbar", "Adds end-task to the right-click menu."),
    "last_active_click": ("Switch to last active window", "Taskbar click switches to the last active window."),
    "disable_snap": ("Disable window snapping", "Turns off drag-to-edge snapping."),
    "start_recommended": ("Hide Start recommendations", "Turns off the recommended section in the Start menu."),
    "start_phone_link": ("Phone Link in Start", "Removes the phone integration from the Start menu."),
    "clear_start": ("Clear pinned apps", "Removes pinned apps from the Start menu."),
    "delivery_optimization": ("Delivery Optimization sharing", "Turns off sharing updates with other PCs."),
    "driver_updates": ("Disable driver updates", "Blocks driver updates via Windows Update."),
    "prevent_reboot": ("Block automatic restart", "Prevents automatic restart after updates while signed in."),
    "update_asap": ("Don't get updates first", "Stops getting new feature updates early."),
    "storage_sense": ("Disable Storage Sense", "Turns off automatic disk cleanup."),
    "fast_startup": ("Disable fast startup", "Ensures a full shutdown; fixes some issues."),
    "gamebar": ("Xbox Game Bar integration", "Turns off game bar integration and recording."),
    "dvr": ("Game recording (DVR)", "Turns off background game recording."),
    "notifications": ("Windows notifications", "Turns off system and app notifications."),
    "settings_home": ("Remove Settings home", "Hides the home page in the Settings app."),
    "settings_ads": ("Microsoft 365 ads in Settings", "Turns off Microsoft 365 ads on the Settings home page."),
    "store_suggestions": ("Store search suggestions", "Turns off Store app suggestions in search."),
    "bitlocker": ("BitLocker auto-encryption", "Prevents automatic device encryption."),
    "standby_net": ("Network during modern standby", "Turns off network in sleep mode; saves battery."),
    "wsl": ("Windows Subsystem for Linux (WSL)", "Enables the WSL feature."),
}
DEBLOAT_CATEGORIES = {
    "Gizlilik": "Privacy",
    "Yapay Zekâ": "AI",
    "Görünüm": "Appearance",
    "Dosya Gezgini": "File Explorer",
    "Görev Çubuğu": "Taskbar",
    "Başlat Menüsü": "Start Menu",
    "Windows Update": "Windows Update",
    "Oyun": "Gaming",
    "Sistem": "System",
    "Genel": "General",
}

DEV = {
    "python": ("Python", "Scripting, data science and automation. VS Code + Python extension installed automatically.", "pip and venv come with Python."),
    "cpp": ("C / C++", "MSVC compiler toolchain and C/C++ extensions.", "Build Tools takes several GB."),
    "node": ("JavaScript / TypeScript", "Node.js LTS + web development extensions.", "npm comes with Node.js."),
    "java": ("Java", "OpenJDK 21 + Java extension pack.", "JAVA_HOME is set automatically (new terminal required)."),
    "dotnet": ("C# / .NET", ".NET SDK 8 + C# Dev Kit.", "The 'dotnet' command is ready in a new terminal."),
    "web": ("Web (HTML/CSS)", "Live preview and HTML/CSS helpers.", "VS Code and a browser are enough."),
    "git": ("Git / Version Control", "Git + GitHub Pull Requests extensions.", ""),
    "data": ("Data Science", "Python + Jupyter extensions.", "Packages like pandas/numpy must be installed separately."),
}

APPX_FRIENDLY = {
    "microsoft.bingnews": "Bing News",
    "microsoft.bingweather": "Weather",
    "microsoft.gethelp": "Get Help",
    "microsoft.getstarted": "Get Started",
    "microsoft.microsoft3dviewer": "3D Viewer",
    "microsoft.microsoftsolitairecollection": "Solitaire Collection",
    "microsoft.microsoftofficehub": "Office Hub",
    "microsoft.mixedreality.portal": "Mixed Reality Portal",
    "microsoft.people": "People",
    "microsoft.skypeapp": "Skype",
    "microsoft.windowsmaps": "Maps",
    "microsoft.windowscommunicationsapps": "Mail and Calendar",
    "microsoft.xboxapp": "Xbox Console",
    "microsoft.xboxgamingoverlay": "Xbox Game Bar",
    "microsoft.zuneaudio": "Groove Music",
    "microsoft.zunevideo": "Movies & TV",
    "linkedinforwindows": "LinkedIn",
    "microsoft.family": "Microsoft Family",
    "microsoft.todos": "To Do",
    "clipchamp.clipchamp": "Clipchamp",
    "microsoft.powerautomate": "Power Automate",
    "microsoft.windowsfeedbackhub": "Feedback Hub",
    "microsoft.windowscamera": "Camera",
    "microsoft.screensketch": "Snipping Tool",
    "microsoft.windowsnotepad": "Notepad",
    "microsoft.windowspaint": "Paint",
    "microsoft.windowsterminal": "Windows Terminal",
    "microsoft.windowsphotos": "Photos",
    "microsoft.windowscalculator": "Calculator",
    "microsoft.windowssoundrecorder": "Sound Recorder",
    "microsoft.windowsalarms": "Alarms & Clock",
    "microsoft.microsoftstickynotes": "Sticky Notes",
}


def write(name: str, payload: dict) -> None:
    (DATA / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{name}: yazıldı")


def main() -> int:
    # --- cleanup
    base = json.loads((DATA / "cleanup_targets.json").read_text(encoding="utf-8"))
    patch = {"__comment": "English overlay for cleanup_targets.json", "targets": {}}
    for target in base.get("targets", []):
        tid = target["id"]
        entry = {}
        if tid in CLEANUP:
            entry["name"], entry["description"] = CLEANUP[tid]
        group = target.get("group", "")
        if group in CLEANUP_GROUPS:
            entry["group"] = CLEANUP_GROUPS[group]
        if tid in CLEANUP_WARNINGS:
            entry["warning"] = CLEANUP_WARNINGS[tid]
        if entry:
            patch["targets"][tid] = entry
    write("cleanup_targets.en.json", patch)

    # --- ofgb
    base = json.loads((DATA / "ofgb_tweaks.json").read_text(encoding="utf-8"))
    patch = {"__comment": "English overlay for ofgb_tweaks.json", "toggles": {}}
    for toggle in base.get("toggles", []):
        tid = toggle["id"]
        entry = {}
        if tid in OFGB:
            entry["title"], entry["description"] = OFGB[tid]
        cat = toggle.get("category", "")
        if cat in OFGB_CATEGORIES:
            entry["category"] = OFGB_CATEGORIES[cat]
        if entry:
            patch["toggles"][tid] = entry
    write("ofgb_tweaks.en.json", patch)

    # --- debloat
    base = json.loads((DATA / "debloat_tweaks.json").read_text(encoding="utf-8"))
    patch = {"__comment": "English overlay for debloat_tweaks.json", "tweaks": {}}
    for tweak in base.get("tweaks", []):
        tid = tweak["id"]
        entry = {}
        if tid in DEBLOAT:
            entry["title"], entry["description"] = DEBLOAT[tid]
        cat = tweak.get("category", "")
        if cat in DEBLOAT_CATEGORIES:
            entry["category"] = DEBLOAT_CATEGORIES[cat]
        if entry:
            patch["tweaks"][tid] = entry
    write("debloat_tweaks.en.json", patch)

    # --- dev rules
    base = json.loads((DATA / "dev_rules.json").read_text(encoding="utf-8"))
    patch = {"__comment": "English overlay for dev_rules.json", "languages": {}}
    for lang in base.get("languages", []):
        lid = lang["id"]
        if lid in DEV:
            title, description, notes = DEV[lid]
            patch["languages"][lid] = {"title": title, "description": description, "notes": notes}
    write("dev_rules.en.json", patch)

    # --- appx friendly names
    write("appx_blocklist.en.json", {
        "__comment": "English overlay for appx_blocklist.json",
        "friendly": APPX_FRIENDLY,
    })

    # --- categories for catalog
    base = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    write("catalog_categories.en.json", {
        "__comment": "English category list",
        "categories": [CATEGORY_EN for CATEGORY_EN in [
            "System Tools", "Browsers", "Developer", "Runtimes", "Media",
            "Communication", "Office", "Archiving", "Security", "Gaming",
        ]],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
