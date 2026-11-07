"""Yeniden kullanılabilir arayüz bileşenleri."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QProgressBar,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from . import theme
from ..core.i18n import t


class Card(QFrame):
    """Yuvarlatılmış içerik kartı."""

    def __init__(self, parent=None, padding: int = 16, spacing: int = 10):
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(spacing)

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget: QWidget, stretch: int = 0) -> QWidget:
        self._layout.addWidget(widget, stretch)
        return widget

    def add_layout(self, layout, stretch: int = 0):
        self._layout.addLayout(layout, stretch)
        return layout


class Badge(QLabel):
    def __init__(self, text: str = "", tone: str = "muted", parent=None):
        super().__init__(text, parent)
        self.setObjectName("Badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        theme.repolish(self)

    def set_state(self, text: str, tone: str) -> None:
        self.setText(text)
        self.set_tone(tone)


class SectionTitle(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("SectionTitle")


class Hint(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("Hint")
        self.setWordWrap(True)


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFixedHeight(1)


class TitleLabel(QLabel):
    def __init__(self, text: str = "", size: int = 14, bold: bool = True, parent=None):
        super().__init__(text, parent)
        font = self.font()
        font.setPointSizeF(size * 0.75)
        font.setBold(bold)
        self.setFont(font)
        self.setWordWrap(True)


class StatCard(Card):
    def __init__(self, value: str, label: str, tone: str = "info", parent=None):
        super().__init__(parent, padding=14, spacing=2)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        vf = self.value_label.font()
        vf.setPointSizeF(17)
        vf.setBold(True)
        self.value_label.setFont(vf)
        colors = {"info": theme.ACCENT, "ok": theme.GREEN, "warn": theme.AMBER, "err": theme.RED}
        self.value_label.setStyleSheet(f"color: {colors.get(tone, theme.TEXT)};")

        self.label = QLabel(label)
        self.label.setObjectName("CardSubtitle")
        self.label.setWordWrap(True)

        self.add(self.value_label)
        self.add(self.label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class LogView(QPlainTextEdit):
    """Otomatik kaydıran, salt okunur günlük görünümü."""

    MAX_LINES = 4000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LogView")
        self.setReadOnly(True)
        self.setMaximumBlockCount(self.MAX_LINES)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont("Cascadia Mono", 9))

    def append_line(self, text: str) -> None:
        self.appendPlainText(text)
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def append_text(self, text: str) -> None:
        """Satır sonu olmadan metin ekler (konsol akışı için)."""
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.setTextCursor(cursor)
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def append_lines(self, lines: list[str]) -> None:
        for line in lines:
            self.appendPlainText(line)
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())


class ToggleRow(QWidget):
    """Başlık + açıklama + rozet içeren, tıklanabilir satır."""

    changed = Signal(bool)

    def __init__(self, title: str, description: str = "", checked: bool = False,
                 badge: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        from PySide6.QtWidgets import QCheckBox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        self.checkbox.stateChanged.connect(lambda _: self.changed.emit(self.checkbox.isChecked()))
        layout.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignTop)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")
        self.title_label.setWordWrap(True)
        texts.addWidget(self.title_label)
        if description:
            self.desc_label = QLabel(description)
            self.desc_label.setObjectName("CardSubtitle")
            self.desc_label.setWordWrap(True)
            texts.addWidget(self.desc_label)
        layout.addLayout(texts, 1)

        self.badge = None
        if badge:
            self.badge = Badge(badge, "muted")
            layout.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, value: bool) -> None:
        self.checkbox.setChecked(value)

    def set_enabled(self, enabled: bool, reason: str = "") -> None:
        self.checkbox.setEnabled(enabled)
        if not enabled:
            self.checkbox.setChecked(False)
            if reason and self.badge:
                self.badge.set_state(reason, "warn")


class SearchInput(QLineEdit):
    def __init__(self, placeholder: str = "Ara…", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)


class ProgressRow(QWidget):
    """Görev satırı: durum noktası + başlık + süre."""

    def __init__(self, title: str, group: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(10)

        self.dot = QLabel("○")
        self.dot.setFixedWidth(16)
        self.dot.setStyleSheet(f"color: {theme.MUTED}; font-size: 13px;")
        layout.addWidget(self.dot)

        self.label = QLabel(title)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.label, 1)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {theme.MUTED}; font-size: 11px;")
        layout.addWidget(self.status, 0)

    def set_running(self) -> None:
        self.dot.setText("◐")
        self.dot.setStyleSheet(f"color: {theme.ACCENT}; font-size: 13px;")
        self.status.setText("çalışıyor…")
        self.status.setStyleSheet(f"color: {theme.ACCENT}; font-size: 11px;")

    def set_done(self, seconds: float | None = None) -> None:
        self.dot.setText("●")
        self.dot.setStyleSheet(f"color: {theme.GREEN}; font-size: 13px;")
        self.status.setText(f"{seconds:.1f}s" if seconds else t("tamam"))
        self.status.setStyleSheet(f"color: {theme.GREEN}; font-size: 11px;")

    def set_skipped(self, reason: str = "atlandı") -> None:
        self.dot.setText("○")
        self.dot.setStyleSheet(f"color: {theme.AMBER}; font-size: 13px;")
        self.status.setText(reason)
        self.status.setStyleSheet(f"color: {theme.AMBER}; font-size: 11px;")

    def set_failed(self, reason: str = "hata") -> None:
        self.dot.setText("●")
        self.dot.setStyleSheet(f"color: {theme.RED}; font-size: 13px;")
        self.status.setText(reason[:60])
        self.status.setStyleSheet(f"color: {theme.RED}; font-size: 11px;")


class IconButton(QPushButton):
    def __init__(self, text: str, tooltip: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("Ghost")
        self.setToolTip(tooltip)
        self.setFixedWidth(34)


class ListCard(Card):
    """Başlık + sağda rozet + içerik alanı."""

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        header = QHBoxLayout()
        header.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(1)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")
        titles.addWidget(self.title_label)
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setObjectName("CardSubtitle")
            titles.addWidget(self.subtitle_label)
        header.addLayout(titles, 1)
        self.header = header
        self.body().addLayout(header)
