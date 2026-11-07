"""Sayfa tabanı: kaydırılabilir içerik + görev üretimi sözleşmesi."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from ...core.state import Session
from ...core.tasks import Task


class BasePage(QWidget):
    step_id: str = ""
    title: str = ""
    subtitle: str = ""

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self.container = QWidget()
        self.content = QVBoxLayout(self.container)
        self.content.setContentsMargins(26, 20, 26, 20)
        self.content.setSpacing(14)
        self.content.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll.setWidget(self.container)
        self._outer.addWidget(self.scroll)

    # ------------------------------------------------------------- hooks
    def on_show(self) -> None:
        """Sayfa görünür olduğunda çağrılır (her seferinde)."""

    def collect(self) -> None:
        """Seçimleri oturuma yaz."""

    def plan(self) -> list[Task]:
        return []

    def skip(self) -> None:
        """'Bu adımı atla' davranışı."""

    def summary(self) -> str:
        tasks = self.plan()
        return f"{len(tasks)} işlem" if tasks else ""

    # ------------------------------------------------------------ helpers
    def add(self, widget: QWidget):
        self.content.addWidget(widget)
        return widget

    def add_layout(self, layout, stretch: int = 0):
        self.content.addLayout(layout, stretch)
        return layout

    def add_stretch(self) -> None:
        self.content.addStretch(1)
