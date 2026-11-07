"""Windows Update ve sürücüler."""
from __future__ import annotations

import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ...core.tasks import Task
from ...modules import drivers, sysinfo, updates
from ...core.i18n import t
from .. import theme
from ..widgets import Badge, Card, Hint, SectionTitle, TitleLabel
from .base import BasePage


class UpdatesPage(BasePage):
    step_id = "updates"
    title = "Güncellemeler ve sürücüler"
    subtitle = "Windows Update üzerinden güncellemeleri ve sürücüleri tarayıp seçerek kurun."

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.all_updates: list[updates.UpdateInfo] = []
        self._build()

    def _build(self) -> None:
        from PySide6.QtWidgets import QTabWidget
        self.tabs = QTabWidget()
        self.add(self.tabs)

        # -------------------------------------------------------- update
        update_tab = QWidget()
        layout = QVBoxLayout(update_tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        bar = QHBoxLayout()
        self.scan_btn = QPushButton("Tara")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self.scan)
        bar.addWidget(self.scan_btn)

        self.select_all_btn = QPushButton("Güvenli olanları seç")
        self.select_all_btn.setObjectName("Ghost")
        self.select_all_btn.clicked.connect(self._select_safe)
        bar.addWidget(self.select_all_btn)
        bar.addStretch(1)
        self.summary_label = QLabel("henüz taranmadı")
        self.summary_label.setObjectName("Hint")
        bar.addWidget(self.summary_label)
        layout.addLayout(bar)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["", "Güncelleme", "Tür", "KB", "Boyut"])
        self.tree.setColumnWidth(0, 34)
        self.tree.setColumnWidth(1, 420)
        self.tree.setColumnWidth(2, 90)
        self.tree.setColumnWidth(3, 120)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemChanged.connect(self._update_summary)
        layout.addWidget(self.tree, 1)

        layout.addWidget(Hint(
            "Tarama Windows Update servisini kullanır. Kurulum uzun sürebilir; iptal edilebilir. "
            "Sürücüler ayrı sekmede listelenir."
        ))
        self.tabs.addTab(update_tab, "Windows Update")

        # -------------------------------------------------------- drivers
        driver_tab = QWidget()
        dlayout = QVBoxLayout(driver_tab)
        dlayout.setContentsMargins(14, 14, 14, 14)
        dlayout.setSpacing(10)

        maker = sysinfo.manufacturer_key()
        name, url = sysinfo.SUPPORT_LINKS.get(maker, ("Üretici", "https://www.google.com/search?q=driver+download"))
        info_card = Card()
        info_card.add(TitleLabel(f"Üretici: {name}", 13))
        info_card.add(Hint(f"Resmî destek sayfası: {url}"))
        row = QHBoxLayout()
        open_btn = QPushButton("Resmî sürücü sayfasını aç")
        open_btn.setObjectName("Primary")
        open_btn.clicked.connect(lambda: drivers.open_manufacturer_page(url))
        row.addWidget(open_btn)

        export_btn = QPushButton("Sürücüleri yedekle")
        export_btn.setObjectName("Ghost")
        export_btn.clicked.connect(lambda: self.export_drivers())
        row.addWidget(export_btn)

        update_btn = QPushButton("Windows Update'i aç")
        update_btn.setObjectName("Ghost")
        update_btn.clicked.connect(drivers.open_windows_update)
        row.addWidget(update_btn)
        row.addStretch(1)
        info_card.add_layout(row)
        dlayout.addWidget(info_card)

        self.driver_tree = QTreeWidget()
        self.driver_tree.setHeaderLabels(["Aygıt", "Sağlayıcı", "Sürüm", "Tarih"])
        self.driver_tree.setColumnWidth(0, 340)
        self.driver_tree.setColumnWidth(1, 160)
        self.driver_tree.setAlternatingRowColors(True)
        dlayout.addWidget(self.driver_tree, 1)

        load_btn = QPushButton("Sürücü envanterini yükle")
        load_btn.setObjectName("Ghost")
        load_btn.clicked.connect(self.load_drivers)
        dlayout.addWidget(load_btn)
        self.tabs.addTab(driver_tab, "Sürücüler")

    # ------------------------------------------------------------- actions
    def scan(self) -> None:
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("taranıyor…")
        self.summary_label.setText("Windows Update taranıyor, bu birkaç dakika sürebilir…")

        result = {}

        def work():
            items, error = updates.search()
            result["items"] = items
            result["error"] = error

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        thread.join(timeout=900)

        self.all_updates = result.get("items", [])
        self._fill_tree()
        if result.get("error"):
            self.summary_label.setText(t("tarama hatası: {error}", error=result["error"][:80]))
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Yeniden tara")

    def _fill_tree(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        selected = set(self.session.get("updates") or [])
        for item in self.all_updates:
            node = QTreeWidgetItem(["", item.title, item.kind, item.kb, item.size_h])
            node.setFlags(node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            node.setCheckState(0, Qt.CheckState.Checked if item.index in selected else Qt.CheckState.Unchecked)
            node.setData(0, Qt.ItemDataRole.UserRole, item.index)
            if item.mandatory:
                node.setToolTip(2, "Zorunlu güncelleme")
            self.tree.addTopLevelItem(node)
        self.tree.blockSignals(False)
        self._update_summary()

    def _select_safe(self) -> None:
        self.tree.blockSignals(True)
        for index in range(self.tree.topLevelItemCount()):
            node = self.tree.topLevelItem(index)
            update_index = node.data(0, Qt.ItemDataRole.UserRole)
            item = next((u for u in self.all_updates if u.index == update_index), None)
            if item and not item.is_driver:
                node.setCheckState(0, Qt.CheckState.Checked)
        self.tree.blockSignals(False)
        self._update_summary()

    def _update_summary(self, *_) -> None:
        selected = self.selected_updates()
        drivers_count = sum(1 for u in selected if u.is_driver)
        total = sum(u.size for u in selected)
        from ...core.download import human_size
        self.summary_label.setText(
            f"{len(self.all_updates)} güncelleme · {len(selected)} seçili "
            f"({drivers_count} sürücü) · {human_size(total)}"
        )

    def selected_updates(self) -> list[updates.UpdateInfo]:
        indices = set()
        for index in range(self.tree.topLevelItemCount()):
            node = self.tree.topLevelItem(index)
            if node.checkState(0) == Qt.CheckState.Checked:
                indices.add(node.data(0, Qt.ItemDataRole.UserRole))
        return [u for u in self.all_updates if u.index in indices]

    def load_drivers(self) -> None:
        result = {}

        def work():
            result["drivers"] = drivers.inventory()

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        thread.join(timeout=180)

        self.driver_tree.clear()
        for driver in result.get("drivers", []):
            self.driver_tree.addTopLevelItem(
                QTreeWidgetItem([driver.name, driver.provider, driver.version, driver.date[:10]])
            )

    def export_drivers(self) -> None:
        threading.Thread(target=lambda: drivers.export_backup(), daemon=True).start()

    # ---------------------------------------------------------------- state
    def collect(self) -> None:
        self.session.set("updates", [u.index for u in self.selected_updates()])

    def plan(self) -> list[Task]:
        selected = self.selected_updates()
        if not selected:
            return []
        indices = [u.index for u in selected]
        titles = ", ".join(u.title[:28] for u in selected[:2])
        if len(selected) > 2:
            titles += "…"

        def run(ctx):
            ok, message = updates.install(indices, ctx.dry_run, on_line=ctx.log)
            if not ok:
                raise RuntimeError(message or "güncelleme kurulumu başarısız")
            ctx.add("updates_installed", len(indices))

        return [Task(
            key="updates:install",
            group="Güncellemeler",
            title=f"{len(indices)} güncelleme · {titles}",
            fn=run,
            weight=8,
        )]

    def summary(self) -> str:
        count = len(self.selected_updates())
        return f"{count} güncelleme" if count else "seçim yok"
