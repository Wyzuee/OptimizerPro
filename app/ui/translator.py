"""Widget ağacındaki statik metinleri aktif dile çevirir.

Sayfa oluşturulduktan sonra bir kez çağrılır. Dinamik olarak sonradan
yazılan metinler için koddaki `t()` çağrıları kullanılır.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractButton, QComboBox, QGroupBox, QLabel, QLineEdit, QTabWidget,
    QTableWidget, QTreeWidget, QWidget,
)

from ..core import i18n

_visited: set[int] = set()


def _tr(text: str) -> str:
    if not text:
        return text
    translated = i18n.t(text)
    return translated if translated != text else text


def apply(root: QWidget) -> int:
    """Ağaçtaki tüm statik metinleri çevirir. Değiştirilen öğe sayısını döner."""
    if i18n.current() == "tr":
        return 0
    changed = 0
    for widget in root.findChildren(QWidget):
        changed += _apply_widget(widget)
    changed += _apply_widget(root)
    return changed


def _apply_widget(widget: QWidget) -> int:
    changed = 0
    name = widget.objectName()

    # Kimlik amaçlı / özel biçimli metinleri koru
    if name in {"StepButton", "LogoTitle", "LogoSubtitle", "StatValue", "Badge", "LogView"}:
        if name == "StepButton":
            changed += _translate_step_button(widget)
        return changed

    if isinstance(widget, QLabel):
        text = widget.text()
        if text and _should_translate(text):
            new = _tr(text)
            if new != text:
                widget.setText(new)
                changed += 1

    if isinstance(widget, QAbstractButton):
        text = widget.text()
        if text and _should_translate(text):
            new = _tr(text)
            if new != text:
                widget.setText(new)
                changed += 1

    if isinstance(widget, QGroupBox):
        title = widget.title()
        if title:
            new = _tr(title)
            if new != title:
                widget.setTitle(new)
                changed += 1

    if isinstance(widget, QLineEdit):
        placeholder = widget.placeholderText()
        if placeholder:
            new = _tr(placeholder)
            if new != placeholder:
                widget.setPlaceholderText(new)
                changed += 1

    if isinstance(widget, QComboBox):
        for index in range(widget.count()):
            item = widget.itemText(index)
            new = _tr(item)
            if new != item:
                widget.setItemText(index, new)
                changed += 1

    if isinstance(widget, QTabWidget):
        for index in range(widget.count()):
            label = widget.tabText(index)
            new = _tr(label)
            if new != label:
                widget.setTabText(index, new)
                changed += 1

    if isinstance(widget, (QTreeWidget, QTableWidget)):
        changed += _translate_headers(widget)

    tip = widget.toolTip()
    if tip:
        new = _tr(tip)
        if new != tip:
            widget.setToolTip(new)
            changed += 1
    return changed


def _translate_step_button(widget: QWidget) -> int:
    """'3   Başlangıç ve boot' -> '3   Startup & boot'"""
    text = getattr(widget, "text", lambda: "")()
    if not text or "   " not in text:
        return 0
    prefix, _, label = text.partition("   ")
    new_label = _tr(label)
    if new_label == label:
        return 0
    widget.setText(f"{prefix}   {new_label}")
    return 1


def _translate_headers(widget) -> int:
    if isinstance(widget, QTreeWidget):
        count = widget.columnCount()
    else:
        count = widget.columnCount()
    changed = 0
    for index in range(count):
        if isinstance(widget, QTreeWidget):
            item = widget.headerItem()
            current = item.text(index) if item else ""
        else:
            current = widget.horizontalHeaderItem(index).text() if widget.horizontalHeaderItem(index) else ""
        if not current:
            continue
        new = _tr(current)
        if new == current:
            continue
        if isinstance(widget, QTreeWidget):
            widget.headerItem().setText(index, new)
        else:
            from PySide6.QtWidgets import QTableWidgetItem
            widget.setHorizontalHeaderItem(index, QTableWidgetItem(new))
        changed += 1
    return changed


def _should_translate(text: str) -> bool:
    """Yol, sayı, sembol, uzantı gibi metinleri atla."""
    if len(text) < 2:
        return False
    if text.startswith(("http", "HKCU", "HKLM", "C:\\", "%", "{", "<")):
        return False
    if text[0] in "◆✓◐●○✕!•→←·" and len(text) <= 3:
        return False
    if all(c in "0123456789 .,:/%-+=*()[]<>|\\_@" for c in text):
        return False
    return True
