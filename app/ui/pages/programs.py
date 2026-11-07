"""Program kurulum sayfası: Ninite tarzı gruplu seçim + winget kuyruğu."""
from __future__ import annotations

import threading

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from ...core.tasks import Task
from ...modules import catalog as catalog_mod
from ...modules import installer, ninite
from ...core.i18n import t
from .. import icons, theme
from ..widgets import Badge, Card, Hint, SearchInput, SectionTitle, TitleLabel
from .base import BasePage


class ProgramCard(QFrame):
    """Tek program kartı: ikon + ad + açıklama + rozetler."""

    toggled = Signal()

    def __init__(self, app: catalog_mod.CatalogApp, parent=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(124)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        top = QHBoxLayout()
        top.setSpacing(9)

        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(lambda _: self.toggled.emit())
        top.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignVCenter)

        icon_label = QLabel()
        icon_label.setFixedSize(34, 34)
        icon_label.setPixmap(icons.pixmap(app.id, app.name, app.category, 34))
        icon_label.setToolTip(app.name)
        top.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        name = QLabel(app.name)
        name.setObjectName("CardTitle")
        name.setWordWrap(True)
        top.addWidget(name, 1)

        self.installed_badge = Badge(t("yüklü"), "ok") if app.installed else None
        if self.installed_badge:
            top.addWidget(self.installed_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(top)

        desc = QLabel(app.description)
        desc.setObjectName("CardSubtitle")
        desc.setWordWrap(True)
        desc.setMinimumHeight(28)
        desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(desc)

        bottom = QHBoxLayout()
        bottom.setSpacing(5)
        bottom.addWidget(Badge(f"{app.size_mb} MB", "muted"))
        bottom.addWidget(Badge(app.source, "info"))
        bottom.addStretch(1)
        if app.notes:
            note = QLabel("i")
            note.setObjectName("Warn")
            note.setToolTip(app.notes)
            bottom.addWidget(note)
        layout.addLayout(bottom)

        self.checkbox.setChecked(False)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, value: bool) -> None:
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(value)
        self.checkbox.blockSignals(False)

    def refresh_installed(self) -> None:
        if self.app.installed and self.installed_badge is None:
            self.installed_badge = Badge(t("yüklü"), "ok")
            self.layout().itemAt(0).layout().addWidget(self.installed_badge)
        if self.app.installed:
            self.checkbox.setChecked(False)
            self.checkbox.setEnabled(False)
            self.checkbox.setToolTip("Zaten yüklü — atlanacak")


class ProgramsPage(BasePage):
    step_id = "programs"
    title = "Programlar"
    subtitle = "Kategori kategori gezinin, istediklerinizi işaretleyin. Yüklü olanlar otomatik atlanır."

    detect_finished = Signal()
    detect_started = Signal()

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.catalog = catalog_mod.load_catalog()
        self.cards: dict[str, ProgramCard] = {}
        self.detected = False
        self.detect_started.connect(self._on_detect_started)
        self.detect_finished.connect(self._on_detect_finished)
        self._build()
        self._restore()

    # ------------------------------------------------------------------ ui
    def _build(self) -> None:
        header = Card()
        row = QHBoxLayout()
        row.setSpacing(10)
        self.search = SearchInput("Program ara…")
        self.search.textChanged.connect(self._rebuild_grid)
        row.addWidget(self.search, 1)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Tüm kategoriler")
        for category in self.catalog.categories:
            self.category_combo.addItem(category)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        row.addWidget(self.category_combo)

        row.addWidget(QLabel("Kurulum yeri:"))
        self.drive_combo = QComboBox()
        for letter in self._available_drives():
            self.drive_combo.addItem(f"{letter}:", letter)
        index = self.drive_combo.findData(str(self.session.get("install_drive") or "C"))
        if index >= 0:
            self.drive_combo.setCurrentIndex(index)
        self.drive_combo.setToolTip("C dışı seçilirse programlar <sürücü>:\\Apps altına kurulur.")
        row.addWidget(self.drive_combo)
        header.add_layout(row)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.select_all_btn = QPushButton("Görünenleri seç")
        self.select_all_btn.setObjectName("Ghost")
        self.select_all_btn.clicked.connect(self._select_visible)
        row2.addWidget(self.select_all_btn)

        self.clear_btn = QPushButton("Seçimi temizle")
        self.clear_btn.setObjectName("Ghost")
        self.clear_btn.clicked.connect(self._clear_selection)
        row2.addWidget(self.clear_btn)

        self.detect_btn = QPushButton("Yüklü programları tara")
        self.detect_btn.setObjectName("Ghost")
        self.detect_btn.clicked.connect(self._detect_installed)
        row2.addWidget(self.detect_btn)

        self.ninite_btn = QPushButton("Ninite'de aç")
        self.ninite_btn.setObjectName("Ghost")
        self.ninite_btn.setToolTip("Seçili programlar için ninite.com bağlantısını tarayıcıda açar.")
        self.ninite_btn.clicked.connect(self._open_ninite)
        row2.addWidget(self.ninite_btn)
        row2.addStretch(1)
        self.count_label = QLabel("")
        self.count_label.setObjectName("Hint")
        row2.addWidget(self.count_label)
        header.add_layout(row2)

        header.add(Hint(
            "winget bulunamazsa doğrudan indirme denenir. Kurulum sürücüsü yalnızca winget ile kurulan "
            "programlarda uygulanır; bazı kurulumlar kendi yerini zorunlu tutabilir."
        ))
        self.add(header)

        self.grid_host = QWidget()
        self.grid = QVBoxLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(16)
        self.add(self.grid_host)
        self.add_stretch()

        self._rebuild_grid()

    def _available_drives(self) -> list[str]:
        import string
        from pathlib import Path
        drives = []
        for letter in string.ascii_uppercase:
            if Path(f"{letter}:\\").exists():
                drives.append(letter)
        return drives or ["C"]

    # ---------------------------------------------------------------- grid
    def _visible_apps(self) -> list[catalog_mod.CatalogApp]:
        query = self.search.text().strip()
        apps = catalog_mod.search(self.catalog, query)
        category = self.category_combo.currentText()
        if category != "Tüm kategoriler":
            apps = [a for a in apps if a.category == category]
        return apps

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())
        self.cards = {}

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _rebuild_grid(self) -> None:
        self._clear_grid()
        apps = self._visible_apps()
        if not apps:
            empty = Card()
            empty.add(TitleLabel("Sonuç bulunamadı", 13))
            empty.add(Hint("Arama terimini değiştirin veya kategori filtresini 'Tüm kategoriler' yapın."))
            self.grid.addWidget(empty)
            self._update_count()
            return

        # Kategoriye göre grupla (sıralı)
        order = {name: index for index, name in enumerate(self.catalog.categories)}
        groups: dict[str, list[catalog_mod.CatalogApp]] = {}
        for app in apps:
            groups.setdefault(app.category, []).append(app)

        for category in sorted(groups, key=lambda c: order.get(c, 999)):
            group_apps = groups[category]
            section = QWidget()
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(8)

            head = QHBoxLayout()
            head.setSpacing(8)
            ic = QLabel()
            ic.setPixmap(icons.category_badge(category, 18))
            head.addWidget(ic)
            head.addWidget(SectionTitle(category.upper()))
            head.addWidget(Badge(str(len(group_apps)), "muted"))
            head.addStretch(1)

            select_btn = QPushButton("Bu grubu seç")
            select_btn.setObjectName("Link")
            select_btn.clicked.connect(lambda _=False, c=category: self._select_group(c))
            head.addWidget(select_btn)
            section_layout.addLayout(head)

            cards_row = QGridLayout()
            cards_row.setContentsMargins(0, 0, 0, 0)
            cards_row.setHorizontalSpacing(10)
            cards_row.setVerticalSpacing(10)
            columns = 3
            for index, app in enumerate(group_apps):
                card = ProgramCard(app)
                saved = set(self.session.get("programs") or [])
                card.set_checked(app.id in saved and not app.installed)
                if app.installed:
                    card.refresh_installed()
                card.toggled.connect(self._update_count)
                cards_row.addWidget(card, index // columns, index % columns)
                self.cards[app.id] = card
            for column in range(columns):
                cards_row.setColumnStretch(column, 1)
            section_layout.addLayout(cards_row)
            self.grid.addWidget(section)

        self._update_count()

    def _on_category_changed(self) -> None:
        self._rebuild_grid()

    # ------------------------------------------------------------ selection
    def _select_visible(self) -> None:
        for app in self._visible_apps():
            card = self.cards.get(app.id)
            if card and card.checkbox.isEnabled():
                card.set_checked(True)
        self._update_count()

    def _select_group(self, category: str) -> None:
        for app in self.catalog.apps:
            if app.category != category:
                continue
            card = self.cards.get(app.id)
            if card and card.checkbox.isEnabled():
                card.set_checked(True)
        self._update_count()

    def _clear_selection(self) -> None:
        for card in self.cards.values():
            if card.checkbox.isEnabled():
                card.set_checked(False)
        self._update_count()

    def _update_count(self) -> None:
        selected = self.selected_apps()
        total = sum(a.size_mb for a in selected)
        self.count_label.setText(t("{count} seçili · ~{size} MB", count=len(selected), size=total))

    def selected_apps(self) -> list[catalog_mod.CatalogApp]:
        ids = {app_id for app_id, card in self.cards.items() if card.is_checked()}
        return [a for a in self.catalog.apps if a.id in ids]

    # -------------------------------------------------------------- detect
    def _detect_installed(self) -> None:
        self.detect_started.emit()

        def work():
            try:
                catalog_mod.mark_installed(self.catalog)
            except Exception:
                pass
            finally:
                self.detect_finished.emit()

        threading.Thread(target=work, daemon=True).start()

    def _on_detect_started(self) -> None:
        self.detect_btn.setEnabled(False)
        self.detect_btn.setText("taranıyor…")

    def _on_detect_finished(self) -> None:
        self.detect_btn.setEnabled(True)
        self.detect_btn.setText("Yüklü programları tara")
        self._rebuild_grid()

    def _open_ninite(self) -> None:
        selected = self.selected_apps()
        if not selected:
            self.count_label.setText("önce program seçin")
            return
        ninite.open_site(selected)
        self.count_label.setText(t("ninite.com açıldı · {count} program", count=len(selected)))

    # ---------------------------------------------------------------- state
    def on_show(self) -> None:
        if not self.detected:
            self.detected = True
            self._detect_installed()

    def _restore(self) -> None:
        return

    def collect(self) -> None:
        existing = set(self.session.get("programs") or [])
        visible = {app_id for app_id in self.cards}
        # Görünmeyen (filtre dışı) seçimleri koru
        hidden = existing - set(self.cards)
        chosen = {a.id for a in self.selected_apps()} | hidden
        self.session.set("programs", sorted(chosen))
        self.session.set("install_drive", self.drive_combo.currentData() or "C")

    def plan(self) -> list[Task]:
        saved = list(self.session.get("programs") or [])
        selected = [self.catalog.by_id(app_id) for app_id in saved]
        selected = [a for a in selected if a is not None]
        drive = self.session.get("install_drive") or "C"
        tasks = []
        for app in selected:
            def make(app=app):
                def run(ctx):
                    result = installer.install(app, drive=drive, dry_run=ctx.dry_run, on_line=ctx.log)
                    if result.status == "installed":
                        ctx.add("programs_installed", 1)
                    elif result.status == "skipped":
                        ctx.log(f"Atlandı: {app.name} ({result.message})")
                    else:
                        raise RuntimeError(result.message or "kurulum başarısız")
                return run

            tasks.append(Task(
                key=f"install:{app.id}",
                group="Programlar",
                title=app.name,
                fn=make(),
                weight=max(1.0, app.size_mb / 100.0),
            ))
        return tasks

    def summary(self) -> str:
        count = len(self.session.get("programs") or [])
        return f"{count} program" if count else "seçim yok"
