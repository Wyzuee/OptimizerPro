"""Tema: renk paleti ve QSS."""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget

# ------------------------------------------------------------------ palet
BG = "#0A1018"
BG_ALT = "#0E1724"
SURFACE = "#131F2E"
SURFACE_HI = "#192939"
SURFACE_ACTIVE = "#1E3348"
BORDER = "#213548"
BORDER_HI = "#2C4A64"
TEXT = "#E8F1F8"
TEXT_DIM = "#B9CCDC"
MUTED = "#8199B1"
ACCENT = "#22D3EE"
ACCENT_DEEP = "#0E7490"
ACCENT_SOFT = "#0F2E3A"
GREEN = "#34D399"
GREEN_SOFT = "#0C2E26"
AMBER = "#FBBF24"
AMBER_SOFT = "#33280A"
RED = "#F87171"
RED_SOFT = "#3A1717"
PURPLE = "#A78BFA"

RADIUS = 12


QSS = f"""
* {{
    font-family: "Segoe UI Variable Display", "Segoe UI", "Noto Sans", sans-serif;
    outline: none;
}}
QWidget {{
    color: {TEXT};
    background: transparent;
}}
QMainWindow, #Root {{
    background: {BG};
}}

/* ---------------------------------------------------------- sidebar */
#Sidebar {{
    background: {BG_ALT};
    border-right: 1px solid {BORDER};
}}
#LogoTitle {{
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.2px;
}}
#LogoSubtitle {{
    color: {MUTED};
    font-size: 11px;
}}
#SidebarVersion {{
    color: {MUTED};
    font-size: 11px;
}}

/* ---------------------------------------------------------- header */
#Header {{
    background: {BG};
    border-bottom: 1px solid {BORDER};
}}
#PageTitle {{
    font-size: 22px;
    font-weight: 700;
}}
#PageSubtitle {{
    color: {MUTED};
    font-size: 12.5px;
}}

/* ---------------------------------------------------------- content */
#ContentStack {{
    background: {BG};
}}
#ScrollArea {{
    background: transparent;
    border: none;
}}
#ScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ---------------------------------------------------------- cards */
#Card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
}}
#Card:hover {{
    border-color: {BORDER_HI};
}}
#CardSelected {{
    background: {SURFACE_HI};
    border: 1px solid {ACCENT};
    border-radius: {RADIUS}px;
}}
#CardTitle {{
    font-size: 13.5px;
    font-weight: 600;
}}
#CardSubtitle {{
    color: {MUTED};
    font-size: 11.5px;
}}
#SectionTitle {{
    font-size: 12px;
    font-weight: 700;
    color: {TEXT_DIM};
    letter-spacing: 0.6px;
}}
#Hint {{
    color: {MUTED};
    font-size: 11.5px;
}}
#Danger {{
    color: {RED};
    font-size: 11.5px;
}}
#Warn {{
    color: {AMBER};
    font-size: 11.5px;
}}
#Good {{
    color: {GREEN};
    font-size: 11.5px;
}}

/* ---------------------------------------------------------- buttons */
QPushButton {{
    background: {SURFACE_HI};
    color: {TEXT};
    border: 1px solid {BORDER_HI};
    border-radius: 9px;
    padding: 9px 18px;
    font-size: 12.5px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {SURFACE_ACTIVE};
    border-color: {ACCENT_DEEP};
}}
QPushButton:pressed {{
    background: {ACCENT_SOFT};
}}
QPushButton:disabled {{
    color: #55677A;
    background: #111B27;
    border-color: #1B2A38;
}}
QPushButton#Primary {{
    background: {ACCENT};
    color: #04141A;
    border: 1px solid {ACCENT};
    font-weight: 700;
}}
QPushButton#Primary:hover {{
    background: #4BDFF3;
    border-color: #4BDFF3;
}}
QPushButton#Primary:disabled {{
    background: #1C3B45;
    color: #5C7A85;
    border-color: #1C3B45;
}}
QPushButton#Ghost {{
    background: transparent;
    border: 1px solid {BORDER};
    color: {TEXT_DIM};
}}
QPushButton#Ghost:hover {{
    border-color: {BORDER_HI};
    color: {TEXT};
}}
QPushButton#DangerBtn {{
    background: transparent;
    border: 1px solid #4A2222;
    color: {RED};
}}
QPushButton#DangerBtn:hover {{
    background: {RED_SOFT};
}}
QPushButton#Link {{
    background: transparent;
    border: none;
    color: {ACCENT};
    padding: 2px 4px;
    font-weight: 500;
    text-align: left;
}}
QPushButton#Link:hover {{
    color: #6FE7F7;
    text-decoration: underline;
}}
QPushButton#StepButton {{
    background: transparent;
    border: none;
    border-radius: 9px;
    padding: 8px 10px;
    text-align: left;
    color: {MUTED};
    font-weight: 500;
    font-size: 12px;
}}
QPushButton#StepButton:hover {{
    background: {SURFACE};
    color: {TEXT};
}}
QPushButton#StepButton[current="true"] {{
    background: {ACCENT_SOFT};
    color: {ACCENT};
    border-left: 3px solid {ACCENT};
    font-weight: 700;
}}
QPushButton#StepButton[done="true"] {{
    color: {TEXT_DIM};
}}
QPushButton#LangButton {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 4px;
    color: {MUTED};
    font-size: 11.5px;
    font-weight: 600;
}}
QPushButton#LangButton:hover {{
    border-color: {BORDER_HI};
    color: {TEXT};
}}
QPushButton#LangButton:checked {{
    background: {ACCENT_SOFT};
    border-color: {ACCENT};
    color: {ACCENT};
}}

/* ---------------------------------------------------------- inputs */
QLineEdit {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 8px 12px;
    color: {TEXT};
    selection-background-color: {ACCENT_DEEP};
    font-size: 12.5px;
}}
QLineEdit:focus {{
    border-color: {ACCENT_DEEP};
}}
QComboBox {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 7px 10px;
    min-height: 18px;
    font-size: 12.5px;
}}
QComboBox:hover {{ border-color: {BORDER_HI}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDER_HI};
    selection-background-color: {ACCENT_SOFT};
    selection-color: {ACCENT};
    padding: 4px;
}}

QSpinBox {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 6px 8px;
    font-size: 12.5px;
}}
QSpinBox:focus {{ border-color: {ACCENT_DEEP}; }}

QCheckBox {{
    spacing: 9px;
    font-size: 12.5px;
    color: {TEXT};
}}
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1.5px solid {BORDER_HI};
    background: {BG_ALT};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT_DEEP};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url("@CHECK@");
}}
QCheckBox::indicator:disabled {{
    background: #101A24;
    border-color: #1B2A38;
}}
QCheckBox:disabled {{
    color: #55677A;
}}

QProgressBar {{
    background: {BG_ALT};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 4px;
}}

/* ---------------------------------------------------------- tables */
QTableWidget, QTreeWidget, QListWidget {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    gridline-color: {BORDER};
    alternate-background-color: {BG_ALT};
    font-size: 12px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT};
}}
QTableWidget::item, QTreeWidget::item {{
    padding: 4px 6px;
    border: none;
}}
/* Qt tablolarında onay kutusu göstergesini sabitle (yazı altına kaymasın) */
QTreeView::indicator, QTreeWidget::indicator, QTableView::indicator, QTableWidget::indicator {{
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1.5px solid {BORDER_HI};
    background: {BG_ALT};
}}
QTreeView::indicator:hover, QTreeWidget::indicator:hover,
QTableView::indicator:hover, QTableWidget::indicator:hover {{
    border-color: {ACCENT_DEEP};
}}
QTreeView::indicator:checked, QTreeWidget::indicator:checked,
QTableView::indicator:checked, QTableWidget::indicator:checked {{
    background: {ACCENT};
    border: 1.5px solid {ACCENT};
    image: url("@CHECK@");
}}
QTreeView::indicator:indeterminate, QTreeWidget::indicator:indeterminate {{
    background: {ACCENT_DEEP};
    border: 1.5px solid {ACCENT_DEEP};
}}
QTreeView::indicator:disabled, QTreeWidget::indicator:disabled {{
    background: #101A24;
    border-color: #1B2A38;
}}
QHeaderView::section {{
    background: {BG_ALT};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.4px;
}}

/* ---------------------------------------------------------- scroll */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #24384C;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #32506B;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #24384C;
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---------------------------------------------------------- misc */
#Footer {{
    background: {BG_ALT};
    border-top: 1px solid {BORDER};
}}
#LogPanel {{
    background: #060C13;
    border-top: 1px solid {BORDER};
}}
QPlainTextEdit#LogView {{
    background: #060C13;
    border: none;
    color: #9FB6CB;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 11px;
    selection-background-color: {ACCENT_DEEP};
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    background: {SURFACE};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 8px 16px;
    border: none;
    font-size: 12px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover {{
    color: {TEXT};
}}
QToolTip {{
    background: {SURFACE_HI};
    color: {TEXT};
    border: 1px solid {BORDER_HI};
    padding: 6px;
    border-radius: 6px;
}}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {MUTED};
    font-size: 11px;
    letter-spacing: 0.4px;
}}
QSplitter::handle {{
    background: {BORDER};
}}
#Divider {{
    background: {BORDER};
    max-height: 1px;
    min-height: 1px;
}}
#Badge {{
    border-radius: 9px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 700;
}}
#Badge[tone="ok"] {{ background: {GREEN_SOFT}; color: {GREEN}; }}
#Badge[tone="warn"] {{ background: {AMBER_SOFT}; color: {AMBER}; }}
#Badge[tone="err"] {{ background: {RED_SOFT}; color: {RED}; }}
#Badge[tone="info"] {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}
#Badge[tone="muted"] {{ background: #16222F; color: {MUTED}; }}
"""


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(BG_ALT))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(SURFACE_HI))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT_DEEP))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(SURFACE_HI))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    app.setPalette(palette)
    font = QFont("Segoe UI Variable Display", 10)
    if not QFont(font).exactMatch():
        font = QFont("Segoe UI", 10)
    app.setFont(font)
    from ..core.paths import asset
    check = asset("check.png")
    check_url = str(check).replace("\\", "/") if check.exists() else ""
    qss = QSS.replace("@CHECK@", check_url)
    app.setStyleSheet(qss)


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
