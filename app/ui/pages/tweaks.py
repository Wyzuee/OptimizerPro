"""Win11Debloat: gizlilik ve sistem ayarları."""
from __future__ import annotations

import sys
import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ...core.i18n import t
from ...core import logger
from ...core.tasks import Task
from ...modules import debloat
from .. import theme
from ..widgets import Badge, Card, Hint, SearchInput, SectionTitle, TitleLabel
from .base import BasePage


class TweaksPage(BasePage):
    step_id = "tweaks"
    title = "Gizlilik ve sistem ayarları"
    subtitle = "Win11Debloat parametreleriyle eşlenen ayarlar. Seçimler doğrudan uygulanır."

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.build_number = 0
        try:
            self.build_number = sys.getwindowsversion().build
        except Exception:
            self.build_number = 0
        self.tweaks = debloat.load_tweaks()
        self.rows: dict[str, QCheckBox] = {}
        self._build()
        self._restore()

    def _build(self) -> None:
        header = Card()
        row = QHBoxLayout()
        row.setSpacing(10)
        self.search = SearchInput("Ayar ara…")
        self.search.textChanged.connect(self._apply_filter)
        row.addWidget(self.search, 1)

        self.preview_btn = QPushButton("Komutu önizle")
        self.preview_btn.setObjectName("Ghost")
        self.preview_btn.clicked.connect(self._preview_command)
        row.addWidget(self.preview_btn)

        self.defaults_btn = QPushButton("Önerilenleri seç")
        self.defaults_btn.setObjectName("Ghost")
        self.defaults_btn.clicked.connect(self._select_defaults)
        row.addWidget(self.defaults_btn)
        header.add_layout(row)

        self.preview_label = QLabel("")
        self.preview_label.setObjectName("Hint")
        self.preview_label.setWordWrap(True)
        header.add(self.preview_label)
        self.add(header)

        self.group_widgets: list[tuple[QWidget, list[str]]] = []
        self.filter_rows: list[tuple[QWidget, str]] = []
        categories: dict[str, list[debloat.Tweak]] = {}
        for tweak in self.tweaks:
            categories.setdefault(tweak.category, []).append(tweak)

        for category, tweaks in categories.items():
            card = Card()
            card.add(SectionTitle(category.upper()))
            keys = []
            for tweak in tweaks:
                row = QHBoxLayout()
                row.setSpacing(10)
                checkbox = QCheckBox()
                row.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignTop)

                texts = QVBoxLayout()
                texts.setSpacing(1)
                title_row = QHBoxLayout()
                title_row.setSpacing(8)
                title_row.addWidget(TitleLabel(tweak.title, 12.5), 1)
                if tweak.risk == "medium":
                    title_row.addWidget(Badge("dikkat", "warn"))
                texts.addLayout(title_row)
                if tweak.description:
                    texts.addWidget(Hint(tweak.description))
                row.addLayout(texts, 1)

                supported = tweak.supported(self.build_number)
                if not supported:
                    checkbox.setEnabled(False)
                    badge = Badge(t("build {build}+", build=tweak.min_build), "warn")
                    row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
                else:
                    self.rows[tweak.id] = checkbox

                holder = QWidget()
                holder.setLayout(row)
                card.add(holder)
                keys.append(tweak.id)
                self.filter_rows.append(
                    (holder, (tweak.title + " " + tweak.description + " " + tweak.category).lower())
                )
            self.add(card)
            self.group_widgets.append((card, keys))

        self.add_stretch()

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for holder, haystack in self.filter_rows:
            holder.setVisible(not needle or needle in haystack)
        for card, _ in self.group_widgets:
            card.setVisible(not needle or any(
                haystack.find(needle) >= 0 for holder, haystack in self.filter_rows
                if card.isAncestorOf(holder)
            ))

    def _select_defaults(self) -> None:
        for tweak in self.tweaks:
            checkbox = self.rows.get(tweak.id)
            if checkbox and tweak.default and checkbox.isEnabled():
                checkbox.setChecked(True)

    def _preview_command(self) -> None:
        selected = [tid for tid, cb in self.rows.items() if cb.isChecked()]
        args = debloat.build_args(selected, self.build_number, restore_point=True)
        text = "Win11Debloat.ps1 " + " ".join(args[:14])
        if len(args) > 14:
            text += f" … (+{len(args) - 14} parametre)"
        self.preview_label.setText(text)

    # ---------------------------------------------------------------- state
    def _restore(self) -> None:
        saved = self.session.get("debloat") or {}
        if saved:
            for tweak_id, value in saved.items():
                checkbox = self.rows.get(tweak_id)
                if checkbox and value:
                    checkbox.setChecked(True)
        else:
            self._select_defaults()

    def collect(self) -> None:
        self.session.set("debloat", {tid: cb.isChecked() for tid, cb in self.rows.items() if cb.isChecked()})

    def plan(self) -> list[Task]:
        selected = [tid for tid, cb in self.rows.items() if cb.isChecked()]
        if not selected:
            return []

        def run(ctx):
            result = debloat.run(selected, self.build_number, dry_run=ctx.dry_run, on_line=ctx.log)
            if not result.ok and not ctx.dry_run:
                raise RuntimeError(f"Win11Debloat çıkış kodu {result.code}")
            ctx.add("tweaks_applied", len(selected))

        return [Task(
            key="debloat:run",
            group="Gizlilik / Tweaks",
            title=f"Win11Debloat · {len(selected)} ayar",
            fn=run,
            weight=5,
        )]

    def summary(self) -> str:
        count = sum(1 for cb in self.rows.values() if cb.isChecked())
        return f"{count} ayar" if count else "seçim yok"
