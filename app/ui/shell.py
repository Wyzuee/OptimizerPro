"""Ana pencere: adım kabuğu, gezinme, günlük paneli."""
from __future__ import annotations

import sys
from typing import Callable

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from ..core import i18n, logger, ps
from ..core.elevation import is_admin
from ..core.i18n import t
from ..core.paths import asset
from ..core.state import SESSION
from ..core.version import APP_NAME, APP_TAGLINE, APP_VERSION
from . import theme, translator
from .pages.ads import AdsPage
from .pages.apps import AppsPage
from .pages.cleanup import CleanupPage
from .pages.devtools import DevToolsPage
from .pages.files import FilesPage
from .pages.finish import FinishPage
from .pages.programs import ProgramsPage
from .pages.startup import StartupPage
from .pages.summary import SummaryPage
from .pages.terminal import TerminalPage
from .pages.tweaks import TweaksPage
from .pages.updates import UpdatesPage
from .pages.welcome import WelcomePage
from .widgets import Badge, Divider, LogView

STEPS: list[tuple[str, str, Callable]] = [
    ("welcome", "Hoş geldin", WelcomePage),
    ("cleanup", "Disk temizliği", CleanupPage),
    ("files", "Dosya düzeni", FilesPage),
    ("startup", "Başlangıç ve boot", StartupPage),
    ("apps", "Windows uygulamaları", AppsPage),
    ("tweaks", "Gizlilik ve tweaks", TweaksPage),
    ("ads", "Reklamları kapat", AdsPage),
    ("programs", "Programlar", ProgramsPage),
    ("devtools", "Geliştirici araçları", DevToolsPage),
    ("updates", "Güncellemeler", UpdatesPage),
    ("summary", "Özet ve uygula", SummaryPage),
    ("terminal", "Klasik terminal", TerminalPage),
]


class MainWindow(QMainWindow):
    log_line = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — {APP_TAGLINE}")
        self.resize(1280, 820)
        self.setMinimumSize(1060, 700)

        icon = asset("app.ico")
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        self.pages: dict[str, QWidget] = {}
        self.step_buttons: dict[str, QPushButton] = {}
        self.skipped: set[str] = set()
        self.current_index = 0

        self._build()
        self.log_line.connect(self._append_log)
        logger.subscribe(self.log_line.emit)
        self._go_to(0, first=True)

    # ------------------------------------------------------------------ ui
    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_sidebar())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_layout.addWidget(self._build_header())

        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentStack")
        right_layout.addWidget(self.stack, 1)

        right_layout.addWidget(self._build_footer())
        right_layout.addWidget(self._build_log_panel())

        outer.addWidget(right, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(232)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(4)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo_path = asset("logo.png")
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(
                38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            logo.setPixmap(pix)
        else:
            logo.setText("◆")
            logo.setStyleSheet(f"color: {theme.ACCENT}; font-size: 26px;")
        brand.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("Optimizer Pro")
        title.setObjectName("LogoTitle")
        titles.addWidget(title)
        sub = QLabel(t("Windows kurulum aracı"))
        sub.setObjectName("LogoSubtitle")
        titles.addWidget(sub)
        brand.addLayout(titles, 1)
        layout.addLayout(brand)
        layout.addSpacing(10)
        layout.addWidget(Divider())
        layout.addSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.setSpacing(2)

        for index, (step_id, title_text, _) in enumerate(STEPS):
            button = QPushButton(f"{index}   {title_text}")
            button.setObjectName("StepButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, i=index: self._go_to(i))
            button.setFixedHeight(34)
            holder_layout.addWidget(button)
            self.step_buttons[step_id] = button
        holder_layout.addStretch(1)
        scroll.setWidget(holder)
        layout.addWidget(scroll, 1)

        layout.addWidget(Divider())
        layout.addSpacing(6)

        layout.addWidget(self._build_language_switcher())

        self.dry_btn = QPushButton(t("Deneme modu: kapalı"))
        self.dry_btn.setObjectName("Ghost")
        self.dry_btn.setCheckable(True)
        self.dry_btn.setChecked(bool(SESSION.get("dry_run")))
        self.dry_btn.clicked.connect(self._toggle_dry)
        self._refresh_dry_button()
        layout.addWidget(self.dry_btn)

        version = QLabel(f"v{APP_VERSION} · {sys.version.split()[0]}")
        version.setObjectName("SidebarVersion")
        layout.addWidget(version)
        return sidebar

    def _build_language_switcher(self) -> QWidget:
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 2)
        row.setSpacing(4)
        self.lang_buttons: dict[str, QPushButton] = {}
        for code, name in i18n.available():
            button = QPushButton(code.upper())
            button.setObjectName("LangButton")
            button.setCheckable(True)
            button.setChecked(code == i18n.current())
            button.setToolTip(name)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, c=code: self._change_language(c))
            row.addWidget(button)
            self.lang_buttons[code] = button
        return holder

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(78)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(26, 12, 20, 12)
        layout.setSpacing(12)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.page_title = QLabel(t("Hoş geldiniz"))
        self.page_title.setObjectName("PageTitle")
        texts.addWidget(self.page_title)
        self.page_subtitle = QLabel("")
        self.page_subtitle.setObjectName("PageSubtitle")
        texts.addWidget(self.page_subtitle)
        layout.addLayout(texts, 1)

        self.admin_badge = Badge(t("yönetici") if is_admin() else t("yönetici değil"),
                                 "ok" if is_admin() else "err")
        layout.addWidget(self.admin_badge)

        self.mode_badge = Badge(t("canlı"), "warn")
        layout.addWidget(self.mode_badge)

        self.log_toggle = QPushButton(t("Günlük"))
        self.log_toggle.setObjectName("Ghost")
        self.log_toggle.setCheckable(True)
        self.log_toggle.clicked.connect(self._toggle_log)
        layout.addWidget(self.log_toggle)
        return header

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("Footer")
        footer.setFixedHeight(66)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(26, 12, 26, 12)
        layout.setSpacing(10)

        self.back_btn = QPushButton(t("← Geri"))
        self.back_btn.setObjectName("Ghost")
        self.back_btn.clicked.connect(self._back)
        layout.addWidget(self.back_btn)

        self.skip_btn = QPushButton(t("Bu adımı atla"))
        self.skip_btn.setObjectName("Ghost")
        self.skip_btn.clicked.connect(self._skip)
        layout.addWidget(self.skip_btn)

        self.hint_label = QLabel("")
        self.hint_label.setObjectName("Hint")
        layout.addWidget(self.hint_label, 1)

        self.next_btn = QPushButton(t("İleri →"))
        self.next_btn.setObjectName("Primary")
        self.next_btn.setMinimumWidth(140)
        self.next_btn.clicked.connect(self._next)
        layout.addWidget(self.next_btn)
        return footer

    def _build_log_panel(self) -> QWidget:
        self.log_panel = QFrame()
        self.log_panel.setObjectName("LogPanel")
        self.log_panel.setVisible(False)
        layout = QVBoxLayout(self.log_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.log_view = LogView()
        self.log_view.setFixedHeight(190)
        layout.addWidget(self.log_view)
        for line in logger.recent(400):
            self.log_view.append_line(line)
        return self.log_panel

    # ------------------------------------------------------------- logging
    def _subscribe_log(self) -> None:
        logger.subscribe(self._on_log_line)

    def _on_log_line(self, line: str) -> None:
        try:
            self.log_view.append_line(line)
        except Exception:
            pass

    # ---------------------------------------------------------- navigation
    def _page_for(self, index: int):
        step_id = STEPS[index][0]
        if step_id not in self.pages:
            factory = STEPS[index][2]
            page = factory(SESSION)
            self.pages[step_id] = page
            self.stack.addWidget(page)
            if step_id == "summary":
                page.run_completed.connect(self._on_run_completed)
            # Statik metinleri aktif dile çevir
            try:
                translator.apply(page)
            except Exception as exc:  # noqa: BLE001
                logger.warn(f"Çeviri uygulanamadı ({step_id}): {exc}")
        return self.pages[step_id]

    def _go_to(self, index: int, first: bool = False) -> None:
        index = max(0, min(index, len(STEPS) - 1))
        if not first and index != self.current_index:
            self._collect_current()

        self.current_index = index
        step_id, title, _ = STEPS[index]
        page = self._page_for(index)
        self.stack.setCurrentWidget(page)

        self.page_title.setText(t(getattr(page, "title", title)))
        self.page_subtitle.setText(t(getattr(page, "subtitle", "")))
        try:
            page.on_show()
        except Exception as exc:  # noqa: BLE001
            logger.warn(f"Sayfa hazırlanamadı ({step_id}): {exc}")
        # on_show dinamik metin yazmış olabilir; tekrar çevir
        try:
            translator.apply(page)
            self.page_title.setText(t(getattr(page, "title", title)))
            self.page_subtitle.setText(t(getattr(page, "subtitle", "")))
        except Exception:
            pass

        self._refresh_steps()
        self._refresh_buttons()
        if step_id == "summary":
            self._refresh_summary()

    def _refresh_steps(self) -> None:
        done = set(SESSION.get("completed_steps") or [])
        on_finish = self.stack.currentWidget() is self.pages.get("finish")
        for index, (step_id, _, _) in enumerate(STEPS):
            button = self.step_buttons.get(step_id)
            if not button:
                continue
            is_current = (index == self.current_index) and not on_finish
            button.setProperty("current", is_current)
            button.setProperty("done", step_id in done)
            prefix = "✓" if step_id in done else str(index)
            label = t(STEPS[index][1])
            button.setText(f"{prefix}   {label}")
            theme.repolish(button)

    def _refresh_buttons(self) -> None:
        step_id = STEPS[self.current_index][0]
        self.back_btn.setEnabled(self.current_index > 0)
        skip_visible = step_id not in ("welcome", "summary", "terminal")
        self.skip_btn.setVisible(skip_visible)

        is_summary = step_id == "summary"
        self.next_btn.setVisible(not is_summary)
        self.next_btn.setText(t("İleri →"))

        if step_id == "terminal":
            self.next_btn.setText(t("Bitir →"))

        self.hint_label.setText("")

    def _collect_current(self) -> None:
        step_id = STEPS[self.current_index][0]
        if step_id in self.skipped:
            return
        page = self.pages.get(step_id)
        if page and hasattr(page, "collect"):
            try:
                page.collect()
            except Exception as exc:  # noqa: BLE001
                logger.warn(f"Seçimler kaydedilemedi ({step_id}): {exc}")

    def _next(self) -> None:
        step_id = STEPS[self.current_index][0]
        self._collect_current()
        SESSION.mark_step(step_id)
        self._refresh_steps()

        if self.current_index == len(STEPS) - 1:
            self._show_finish()
            return
        self._go_to(self.current_index + 1)

    def _back(self) -> None:
        self._go_to(self.current_index - 1)

    def _skip(self) -> None:
        step_id = STEPS[self.current_index][0]
        self.skipped.add(step_id)
        SESSION.mark_step(step_id)
        logger.info(f"Adım atlandı: {step_id}")
        if self.current_index == len(STEPS) - 1:
            self._show_finish()
            return
        self._go_to(self.current_index + 1)

    # -------------------------------------------------------------- summary
    def _refresh_summary(self) -> None:
        page = self.pages.get("summary")
        if page is None:
            return
        page.set_plan(self._gather_plan())

    def _gather_plan(self) -> list:
        tasks = []
        seen: set[str] = set()
        for step_id, _, _ in STEPS:
            if step_id in ("summary", "terminal", "welcome", "finish"):
                continue
            if step_id in self.skipped:
                continue
            page = self.pages.get(step_id)
            if page is None or not hasattr(page, "plan"):
                continue
            try:
                page.collect()
            except Exception:
                pass
            try:
                produced = page.plan()
            except Exception as exc:  # noqa: BLE001
                logger.warn(f"Plan oluşturulamadı ({step_id}): {exc}")
                continue
            for task in produced:
                if task.key in seen:
                    logger.info(f"Yinelenen işlem atlandı: {task.title}")
                    continue
                seen.add(task.key)
                tasks.append(task)
        return tasks

    def _on_run_completed(self, summary, stats) -> None:
        self._show_finish(summary, stats)

    def _show_finish(self, summary=None, stats=None) -> None:
        if "finish" not in self.pages:
            page = FinishPage(SESSION)
            self.pages["finish"] = page
            self.stack.addWidget(page)
            try:
                translator.apply(page)
            except Exception:
                pass
        page = self.pages["finish"]
        self.stack.setCurrentWidget(page)
        SESSION.mark_step("finish")
        self.page_title.setText(t(page.title))
        self.page_subtitle.setText(t(page.subtitle))
        if summary is not None:
            page.show_results(summary, stats or {})
        else:
            page.on_show()
        self.skip_btn.setVisible(False)
        self.next_btn.setVisible(False)
        self.back_btn.setEnabled(True)
        self.hint_label.setText("")
        self._refresh_steps()

    # ----------------------------------------------------------------- misc
    def _toggle_log(self) -> None:
        self.log_panel.setVisible(self.log_toggle.isChecked())

    def _change_language(self, code: str) -> None:
        if code == i18n.current():
            return
        if not i18n.set_language(code):
            return
        SESSION.set("language", code)
        logger.info(f"Dil: {code}")
        self._rebuild_for_language()

    def _rebuild_for_language(self) -> None:
        """Sayfaları aktif dille yeniden kurar; aynı adımda kalır."""
        current_index = self.current_index
        was_finish = self.stack.currentWidget() is self.pages.get("finish")

        # Eski sayfaları bırak
        for page in list(self.pages.values()):
            try:
                page.setParent(None)
                page.deleteLater()
            except Exception:
                pass
        self.pages.clear()
        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()

        for code, button in self.lang_buttons.items():
            button.setChecked(code == i18n.current())

        self.admin_badge.set_state(t("yönetici") if is_admin() else t("yönetici değil"),
                                   "ok" if is_admin() else "err")
        self.mode_badge.set_state(
            t("deneme" if SESSION.get("dry_run") else "canlı"),
            "warn" if SESSION.get("dry_run") else "info",
        )
        self.log_toggle.setText(t("Günlük"))
        self.back_btn.setText(t("← Geri"))
        self.skip_btn.setText(t("Bu adımı atla"))
        self._refresh_dry_button()
        # alt bilgi etiketleri
        logo = self.findChild(QLabel, "LogoSubtitle")
        if logo is not None:
            logo.setText(t("Windows kurulum aracı"))

        if was_finish:
            self._show_finish()
            return
        first = self.current_index == 0
        self._go_to(current_index, first=first)
        self._refresh_steps()
        self._refresh_buttons()

    def _toggle_dry(self) -> None:
        SESSION.set("dry_run", self.dry_btn.isChecked())
        self._refresh_dry_button()

    def _refresh_dry_button(self) -> None:
        enabled = bool(SESSION.get("dry_run"))
        self.dry_btn.setText(t("Deneme modu: açık") if enabled else t("Deneme modu: kapalı"))
        self.dry_btn.setStyleSheet(
            f"border-color: {theme.AMBER}; color: {theme.AMBER};" if enabled else ""
        )
        badge = getattr(self, "mode_badge", None)
        if badge is not None:
            badge.set_state(t("deneme" if enabled else "canlı"), "warn" if enabled else "info")

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            ps.cancel_all()
        except Exception:
            pass
        super().closeEvent(event)

    def _append_log(self, line: str) -> None:
        self.log_view.append_line(line)
