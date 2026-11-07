"""Dosya düzeni: Masaüstü ve İndirilenler analizi, silme, sınıflandırma."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout,
)

from ...core.download import human_size
from ...core.tasks import Task
from ...modules import file_review
from .. import theme
from ..widgets import Badge, Card, Hint, TitleLabel
from .base import BasePage


class FilesPage(BasePage):
    step_id = "files"
    title = "Dosya düzeni"
    subtitle = "Masaüstü ve İndirilenler klasöründeki artık dosyaları inceleyin. Silme işlemi Geri Dönüşüm Kutusu'na yapılır."

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.items: list[file_review.FileItem] = []
        self._build()

    def _build(self) -> None:
        card = Card()
        row = QHBoxLayout()
        row.setSpacing(10)
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Her ikisi", "Masaüstü", "İndirilenler"])
        row.addWidget(QLabel("Kaynak:"))
        row.addWidget(self.source_combo)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Tüm dosyalar",
            "Sadece kurulum & arşiv",
            "Sadece 100 MB üzeri",
            "Sadece 90 günden eski",
            "Geçici kalıntılar",
        ])
        row.addWidget(QLabel("Filtre:"))
        row.addWidget(self.filter_combo)
        row.addStretch(1)

        self.scan_btn = QPushButton("Tara")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self.scan)
        row.addWidget(self.scan_btn)
        card.add_layout(row)
        self.add(card)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Dosya", "Kategori", "Boyut", "Tarih", "Kaynak"])
        self.tree.setColumnWidth(0, 320)
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        self.tree.itemChanged.connect(self._update_totals)
        self.add(self.tree)

        bottom = Card()
        row2 = QHBoxLayout()
        self.total_label = QLabel("henüz taranmadı")
        self.total_label.setStyleSheet(f"color: {theme.MUTED};")
        row2.addWidget(self.total_label, 1)

        self.classify_check = QCheckBox("Eşleşen dosyaları alt klasörlere taşı (Belgeler / Resimler / Kurulumlar / Kısayollar / Medyalar)")
        self.classify_check.setChecked(bool(self.session.get("files", {}).get("classify")))
        row2.addWidget(self.classify_check)
        bottom.add_layout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(8)
        self.select_old_btn = QPushButton("90+ gün eskileri seç")
        self.select_old_btn.setObjectName("Ghost")
        self.select_old_btn.clicked.connect(self._select_old)
        row3.addWidget(self.select_old_btn)

        self.select_big_btn = QPushButton("100 MB üzerini seç")
        self.select_big_btn.setObjectName("Ghost")
        self.select_big_btn.clicked.connect(self._select_big)
        row3.addWidget(self.select_big_btn)

        self.clear_btn = QPushButton("Seçimi temizle")
        self.clear_btn.setObjectName("Ghost")
        self.clear_btn.clicked.connect(self._clear_selection)
        row3.addWidget(self.clear_btn)
        row3.addStretch(1)
        bottom.add_layout(row3)

        bottom.add(Hint("Silinen dosyalar Geri Dönüşüm Kutusu'na gider; yanlışlıkla silinenler geri getirilebilir."))
        self.add(bottom)
        self.add_stretch()

    # --------------------------------------------------------------- scan
    def scan(self) -> None:
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("taranıyor…")
        source = self.source_combo.currentText()
        include = None if source == "Her ikisi" else [source]
        try:
            self.items = file_review.scan(include)
        except Exception:
            self.items = []
        self._fill_tree()
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Yeniden tara")

    def _filtered(self) -> list[file_review.FileItem]:
        mode = self.filter_combo.currentText()
        if mode == "Sadece kurulum & arşiv":
            return [i for i in self.items if i.category in ("Kurulum Dosyaları", "Arşivler")]
        if mode == "Sadece 100 MB üzeri":
            return [i for i in self.items if i.size >= 100 * 1024 * 1024]
        if mode == "Sadece 90 günden eski":
            return [i for i in self.items if i.age_days >= 90]
        if mode == "Geçici kalıntılar":
            return [i for i in self.items if i.category == "Geçici Kalıntılar"]
        return list(self.items)

    def _fill_tree(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        grouped = file_review.group_items(self._filtered())
        for category, items in grouped.items():
            total = sum(i.size for i in items)
            parent = QTreeWidgetItem([category, f"{len(items)} dosya", human_size(total), "", ""])
            parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            parent.setCheckState(0, Qt.CheckState.Unchecked)
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)
            self.tree.addTopLevelItem(parent)

            for item in items:
                child = QTreeWidgetItem([item.name, item.category, item.size_h, item.date_h, item.source])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)
                child.setData(0, Qt.ItemDataRole.UserRole, item.path)
                child.setToolTip(0, item.path)
                parent.addChild(child)
            parent.setExpanded(True)
        self.tree.blockSignals(False)
        self._update_totals()

    def _update_totals(self, *_) -> None:
        selected = self.selected_items()
        total = sum(i.size for i in selected)
        if not self.items:
            self.total_label.setText("henüz taranmadı")
        else:
            self.total_label.setText(
                f"{len(self.items)} dosya incelendi · {len(selected)} seçili · {human_size(total)}"
            )

    # ----------------------------------------------------------- selection
    def selected_items(self) -> list[file_review.FileItem]:
        by_path = {i.path: i for i in self._filtered()}
        selected = []
        for index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(index)
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                if child.checkState(0) == Qt.CheckState.Checked:
                    path = child.data(0, Qt.ItemDataRole.UserRole)
                    if path in by_path:
                        selected.append(by_path[path])
        return selected

    def _select_old(self) -> None:
        self._bulk_select(lambda i: i.age_days >= 90)

    def _select_big(self) -> None:
        self._bulk_select(lambda i: i.size >= 100 * 1024 * 1024)

    def _bulk_select(self, predicate) -> None:
        self.tree.blockSignals(True)
        for index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(index)
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                path = child.data(0, Qt.ItemDataRole.UserRole)
                item = next((i for i in self.items if i.path == path), None)
                if item and predicate(item):
                    child.setCheckState(0, Qt.CheckState.Checked)
        self.tree.blockSignals(False)
        self._update_totals()

    def _clear_selection(self) -> None:
        self.tree.blockSignals(True)
        for index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(index)
            parent.setCheckState(0, Qt.CheckState.Unchecked)
            for child_index in range(parent.childCount()):
                parent.child(child_index).setCheckState(0, Qt.CheckState.Unchecked)
        self.tree.blockSignals(False)
        self._update_totals()

    # --------------------------------------------------------------- state
    def collect(self) -> None:
        selected = [i.path for i in self.selected_items()]
        self.session.set("files", {"selected": selected, "classify": self.classify_check.isChecked()})

    def plan(self) -> list[Task]:
        selected = self.selected_items()
        classify = self.classify_check.isChecked()
        tasks: list[Task] = []

        if selected:
            def run_delete(ctx):
                ok, fail = file_review.delete_to_recycle([i.path for i in selected], ctx.dry_run)
                ctx.log(f"Geri dönüşüm kutusuna taşındı: {ok}, başarısız: {fail}")
                ctx.add("files_deleted", ok)
                if fail and not ok:
                    raise RuntimeError(f"{fail} dosya silinemedi")

            tasks.append(Task(
                key="files:delete",
                group="Dosya düzeni",
                title=f"{len(selected)} dosyayı geri dönüşüm kutusuna taşı",
                fn=run_delete,
            ))

        if classify:
            plan_map = file_review.plan_classification(self._filtered())
            total = sum(len(v) for v in plan_map.values())

            def run_classify(ctx):
                moved, failed = file_review.apply_classification(plan_map, ctx.dry_run)
                ctx.log(f"Sınıflandırıldı: {moved}, başarısız: {failed}")
                ctx.add("files_moved", moved)

            if total:
                tasks.append(Task(
                    key="files:classify",
                    group="Dosya düzeni",
                    title=f"{total} dosyayı alt klasörlere taşı",
                    fn=run_classify,
                ))
        return tasks

    def summary(self) -> str:
        count = len(self.selected_items())
        extra = " + sınıflandırma" if self.classify_check.isChecked() else ""
        return f"{count} dosya{extra}" if count or extra else "seçim yok"
