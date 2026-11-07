"""Windows uygulamaları: listele, seç, kaldır."""
from __future__ import annotations

import threading

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem,
)

from ...core.download import human_size
from ...core.tasks import Task
from ...modules import appx as appx_mod
from .. import theme
from ..widgets import Badge, Card, Hint, SearchInput, TitleLabel
from .base import BasePage


def _publisher_name(raw: str) -> str:
    """'CN=Microsoft Corporation, O=...' -> 'Microsoft Corporation'."""
    if not raw:
        return "—"
    for part in raw.split(","):
        part = part.strip()
        if part.upper().startswith("CN="):
            return part[3:]
    return raw[:40]


class AppsPage(BasePage):
    step_id = "apps"
    title = "Windows uygulamaları"
    subtitle = "Paketlenmiş mağaza uygulamalarını kaldırın. Kritik bileşenler kilitlidir."

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.packages: list[appx_mod.AppxItem] = []
        self._build()

    def _build(self) -> None:
        card = Card()
        row = QHBoxLayout()
        row.setSpacing(10)
        self.search = SearchInput("Uygulama ara…")
        self.search.textChanged.connect(self._fill_tree)
        row.addWidget(self.search, 1)

        self.load_btn = QPushButton("Yükle")
        self.load_btn.setObjectName("Primary")
        self.load_btn.clicked.connect(self.load_packages)
        row.addWidget(self.load_btn)
        card.add_layout(row)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.all_users = QCheckBox("Yeni kullanıcı hesaplarında da kurulmasın (provisioned kaldır)")
        row2.addWidget(self.all_users)
        row2.addStretch(1)
        self.count_label = QLabel("")
        self.count_label.setObjectName("Hint")
        row2.addWidget(self.count_label)
        card.add_layout(row2)
        self.add(card)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["", "Uygulama", "Boyut", "Yayıncı"])
        self.tree.setColumnWidth(0, 44)
        self.tree.setColumnWidth(1, 340)
        self.tree.setColumnWidth(2, 90)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setIndentation(4)
        self.tree.itemChanged.connect(self._update_count)
        self.tree.setMinimumHeight(420)
        self.add(self.tree)

        self.add(Hint(
            "Kaldırma işlemi geri alınamaz ancak uygulama Microsoft Store'dan yeniden kurulabilir. "
            "Store, App Installer ve sistem bileşenleri korunur."
        ))

    # ------------------------------------------------------------ loading
    def on_show(self) -> None:
        if not self.packages:
            self.load_packages()

    def load_packages(self) -> None:
        self.load_btn.setEnabled(False)
        self.load_btn.setText("yükleniyor…")

        result = {}

        def work():
            try:
                result["items"] = appx_mod.list_packages(dry_run=False)
            except Exception:
                result["items"] = []

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        thread.join(timeout=180)
        self.packages = result.get("items", [])
        self._fill_tree()
        self.load_btn.setEnabled(True)
        self.load_btn.setText("Yenile")

    def _fill_tree(self) -> None:
        query = self.search.text().strip().lower()
        self.tree.blockSignals(True)
        self.tree.clear()
        selected = set(self.session.get("appx") or [])

        shown = 0
        for item in self.packages:
            label = item.friendly if item.friendly != item.name else item.name
            if query and query not in label.lower() and query not in item.name.lower():
                continue
            shown += 1
            publisher = _publisher_name(item.publisher)
            node = QTreeWidgetItem(["", label, item.size_h, publisher])
            if item.critical:
                node.setFlags(node.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                node.setText(1, label + "  (korumalı)")
                node.setForeground(1, Qt.GlobalColor.gray)
            else:
                node.setFlags(node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                node.setCheckState(0, Qt.CheckState.Checked if item.name in selected else Qt.CheckState.Unchecked)
            node.setData(1, Qt.ItemDataRole.UserRole, item.name)
            node.setToolTip(1, item.name)
            node.setSizeHint(0, QSize(0, 32))
            self.tree.addTopLevelItem(node)
        self.tree.blockSignals(False)
        self._update_count()

    def _update_count(self, *_) -> None:
        selected = self.selected_packages()
        total = sum(p.size for p in selected)
        self.count_label.setText(
            f"{len(self.packages)} paket · {len(selected)} seçili · {human_size(total)} kazanç"
        )

    def selected_packages(self) -> list[appx_mod.AppxItem]:
        names = set()
        for index in range(self.tree.topLevelItemCount()):
            node = self.tree.topLevelItem(index)
            if node.checkState(0) == Qt.CheckState.Checked:
                names.add(node.data(1, Qt.ItemDataRole.UserRole))
        return [p for p in self.packages if p.name in names]

    # ---------------------------------------------------------------- state
    def collect(self) -> None:
        self.session.set("appx", [p.name for p in self.selected_packages()])

    def plan(self) -> list[Task]:
        selected = self.selected_packages()
        all_users = self.all_users.isChecked()
        tasks = []
        for package in selected:
            def make(package=package):
                def run(ctx):
                    ok, fail = appx_mod.remove([package], all_users=all_users, dry_run=ctx.dry_run)
                    if fail and not ok:
                        raise RuntimeError("kaldırılamadı")
                    ctx.add("appx_removed", ok)
                return run

            tasks.append(Task(
                key=f"appx:{package.name}",
                group="Windows uygulamaları",
                title=package.friendly,
                fn=make(),
                weight=max(1.0, min(4.0, package.size / (200 * 1024 * 1024))),
            ))
        return tasks

    def summary(self) -> str:
        count = len(self.selected_packages())
        return f"{count} uygulama" if count else "seçim yok"
