"""Hoş geldin: sistem özeti, ön kontrol, geri yükleme noktası, profil."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ...core import logger, ps
from ...core.i18n import t
from ...core.preflight import LEVEL_BLOCK, LEVEL_OK, LEVEL_WARN, run_preflight
from ...core.tasks import Task
from ...modules import sysinfo
from .. import theme
from ..widgets import Badge, Card, Hint, SectionTitle, StatCard, TitleLabel
from .base import BasePage


class WelcomePage(BasePage):
    step_id = "welcome"
    title = "Hoş geldiniz"
    subtitle = "Sisteminizi tanıyalım ve güvenli başlangıç için hazırlık yapalım."

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.info = {}
        self.report = None
        self._build()

    # ------------------------------------------------------------------ ui
    def _build(self) -> None:
        self.sys_title = SectionTitle("SİSTEM ÖZETİ")
        self.add(self.sys_title)

        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(12)
        self.add_layout(self.stats_grid)

        self.checks_card = Card()
        self.checks_card.add(TitleLabel("Başlangıç kontrolleri", 13))
        self.checks_box = QVBoxLayout()
        self.checks_box.setSpacing(6)
        self.checks_card.add_layout(self.checks_box)
        self.add(self.checks_card)

        restore_card = Card()
        restore_row = QHBoxLayout()
        restore_row.setSpacing(12)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(TitleLabel("Sistem geri yükleme noktası", 13))
        hint = Hint("Herhangi bir değişiklik yapılmadan önce geri dönüş imkânı sağlar. "
                    "Sistem Koruması kapalıysa Windows izin vermeyebilir.")
        texts.addWidget(hint)
        restore_row.addLayout(texts, 1)
        self.restore_btn = QPushButton("Geri yükleme noktası oluştur")
        self.restore_btn.clicked.connect(self._create_restore_point)
        restore_row.addWidget(self.restore_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self.restore_status = QLabel("")
        self.restore_status.setObjectName("Hint")
        restore_row.addWidget(self.restore_status, 0)
        restore_card.add_layout(restore_row)
        self.add(restore_card)

        profile_card = Card()
        profile_card.add(TitleLabel("Hızlı profil", 13))
        profile_card.add(Hint("Seçimleri tek tıkla doldurun; sonraki adımlarda yine düzenleyebilirsiniz."))
        row = QHBoxLayout()
        row.setSpacing(8)
        for key, label, desc in (
            ("minimal", "Minimal", "Yalnızca güvenli temizlik ve gizlilik"),
            ("recommended", "Önerilen", "Temizlik + gizlilik + reklamsız Windows"),
            ("developer", "Geliştirici", "Önerilen + geliştirici araçları"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("Ghost")
            btn.setToolTip(desc)
            btn.clicked.connect(lambda _=False, k=key: self._apply_profile(k))
            row.addWidget(btn)
        row.addStretch(1)
        profile_card.add_layout(row)
        self.add(profile_card)

        self.add_stretch()

    def add_layout(self, layout, stretch: int = 0):
        self.content.addLayout(layout, stretch)
        return layout

    # --------------------------------------------------------------- data
    def on_show(self) -> None:
        if not self.info:
            self.info = sysinfo.collect()
            self._fill_stats()
        if self.report is None:
            self.report = run_preflight(include_network=True)
            self._fill_checks()

    def _fill_stats(self) -> None:
        info = self.info or {}
        entries = [
            (f"{info.get('ram_gb', '?')} GB", "RAM", "info"),
            (f"{info.get('disk_free', '?')} GB", "Boş disk (C:)", "ok"),
            (f"{info.get('cores', '?')} / {info.get('threads', '?')}", "Çekirdek / İş parçacığı", "info"),
            (str(info.get("os_build") or "?"), "Windows build", "muted"),
        ]
        while self.stats_grid.count():
            item = self.stats_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for col, (value, label, tone) in enumerate(entries):
            self.stats_grid.addWidget(StatCard(value, label, tone), 0, col)

        gpu = info.get("gpu") or "—"
        cpu = info.get("cpu") or "—"
        model = f"{info.get('manufacturer','')} {info.get('model','')}".strip() or "—"
        self.sys_title.setText(t("SİSTEM ÖZETİ · {model}", model=model))
        self.sys_title.setToolTip(f"CPU: {cpu}\nGPU: {gpu}\nOS: {info.get('os_name','')}")

    def _fill_checks(self) -> None:
        while self.checks_box.count():
            item = self.checks_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tone_map = {LEVEL_OK: ("ok", "✓"), LEVEL_WARN: ("warn", "!"), LEVEL_BLOCK: ("err", "✕")}
        for check in self.report.checks:
            row = QHBoxLayout()
            row.setSpacing(10)
            tone, glyph = tone_map.get(check.level, ("muted", "•"))
            mark = QLabel(glyph)
            mark.setFixedWidth(16)
            color = {"ok": theme.GREEN, "warn": theme.AMBER, "err": theme.RED, "muted": theme.MUTED}[tone]
            mark.setStyleSheet(f"color: {color}; font-weight: 700;")
            row.addWidget(mark)

            name = QLabel(t(check.label))
            name.setFixedWidth(170)
            name.setStyleSheet("font-weight: 600;")
            row.addWidget(name)

            detail = QLabel(t(check.detail))
            detail.setObjectName("Hint")
            detail.setWordWrap(True)
            row.addWidget(detail, 1)

            badge = Badge(t({"ok": "hazır", "warn": "dikkat", "err": "engel"}.get(tone, "")), tone)
            row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)

            wrapper = QLabel  # noqa: F841 - sadece tip ipucu
            from PySide6.QtWidgets import QWidget
            box = QWidget()
            box.setLayout(row)
            self.checks_box.addWidget(box)

    # ------------------------------------------------------------- actions
    def _create_restore_point(self) -> None:
        self.restore_btn.setEnabled(False)
        self.restore_status.setText("oluşturuluyor…")
        self.restore_status.setStyleSheet(f"color: {theme.AMBER};")
        script = (
            "$ErrorActionPreference='Stop';"
            "try{"
            "  Enable-ComputerRestore -Drive \"$env:SystemDrive\" -ErrorAction SilentlyContinue;"
            "  Checkpoint-Computer -Description 'Optimizer Pro' -RestorePointType 'MODIFY_SETTINGS';"
            "  'OK'"
            "}catch{ 'HATA: ' + $_.Exception.Message }"
        )
        res = ps.run_powershell(script, timeout=600, dry_run=bool(self.session.get("dry_run")))
        if "OK" in (res.output or ""):
            self.restore_status.setText("✓ oluşturuldu")
            self.restore_status.setStyleSheet(f"color: {theme.GREEN};")
            logger.info("Geri yükleme noktası oluşturuldu")
        else:
            self.restore_status.setText("oluşturulamadı")
            self.restore_status.setStyleSheet(f"color: {theme.RED};")
            logger.warn(f"Geri yükleme noktası oluşturulamadı: {(res.output or '')[:160]}")
        self.restore_btn.setEnabled(True)

    def _apply_profile(self, key: str) -> None:
        from ...modules import ofgb

        # Temizlik
        if key in ("minimal", "recommended", "developer"):
            self.session.set("cleanup", ["user_temp", "windows_temp", "prefetch", "thumbcache", "crashdumps", "recycle_bin"])

        # Reklamlar
        toggles = [t.id for t in ofgb.load_toggles()]
        if key in ("recommended", "developer"):
            self.session.set("ofgb", {tid: True for tid in toggles})

        # Win11Debloat
        if key in ("recommended", "developer"):
            from ...modules import debloat
            defaults = [t.id for t in debloat.load_tweaks() if t.default]
            self.session.set("debloat", {tid: True for tid in defaults})
        elif key == "minimal":
            self.session.set("debloat", {"telemetry": True, "suggestions": True})

        if key == "developer":
            self.session.set("devlangs", ["python", "node", "git"])
            self.session.set("programs", ["vscode", "git", "python312", "nodejs"])

        self.session.set("power", {"enabled": True, "scheme": "ultimate"})
        self.session.mark_step("welcome")
        self.restore_status.setText("profil uygulandı — sonraki adımlarda görebilirsiniz")
        self.restore_status.setStyleSheet(f"color: {theme.ACCENT};")

    # ---------------------------------------------------------------- plan
    def plan(self) -> list[Task]:
        return []
