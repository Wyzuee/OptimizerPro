"""Reklamları kapat (OFGB yerel uygulaması)."""
from __future__ import annotations

import sys
import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...core.i18n import t
from ...core import logger
from ...core.elevation import is_admin
from ...core.tasks import Task
from ...modules import ofgb
from .. import theme
from ..widgets import Badge, Card, Hint, SectionTitle, TitleLabel
from .base import BasePage


class AdsPage(BasePage):
    step_id = "ads"
    title = "Reklamları kapat"
    subtitle = "Windows'un her yerindeki reklam, öneri ve tanıtımları kapatır (OFGB v0.4 anahtarları)."

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        try:
            self.build_number = sys.getwindowsversion().build
        except Exception:
            self.build_number = 0
        self.admin = is_admin()
        self.toggles = ofgb.load_toggles()
        self.rows: dict[str, QCheckBox] = {}
        self._build()
        self._restore()

    def _build(self) -> None:
        header = Card()
        row = QHBoxLayout()
        row.setSpacing(10)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(TitleLabel("Tüm reklam ve önerileri kapat", 13))
        texts.addWidget(Hint("12 ayarın tamamını tek tıkla kapatır. İstediğinizi geri açabilirsiniz."))
        row.addLayout(texts, 1)

        self.all_btn = QPushButton("Tümünü kapat")
        self.all_btn.setObjectName("Primary")
        self.all_btn.clicked.connect(self._select_all)
        row.addWidget(self.all_btn)

        self.ofgb_btn = QPushButton("Orijinal OFGB arayüzü")
        self.ofgb_btn.setObjectName("Ghost")
        self.ofgb_btn.setToolTip("Resmi OFGB uygulamasını indirip açar (.NET 8 gerekir).")
        self.ofgb_btn.clicked.connect(self._launch_original)
        row.addWidget(self.ofgb_btn)
        header.add_layout(row)

        self.status = QLabel("")
        self.status.setObjectName("Hint")
        self.status.setWordWrap(True)
        header.add(self.status)
        self.add(header)

        categories: dict[str, list[ofgb.Toggle]] = {}
        for toggle in self.toggles:
            categories.setdefault(toggle.category, []).append(toggle)

        for category, toggles in categories.items():
            card = Card()
            card.add(SectionTitle(category.upper()))
            for toggle in toggles:
                row = QHBoxLayout()
                row.setSpacing(10)
                checkbox = QCheckBox()
                row.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignTop)

                texts = QVBoxLayout()
                texts.setSpacing(1)
                title_row = QHBoxLayout()
                title_row.setSpacing(8)
                title_label = TitleLabel(toggle.title, 12.5)
                title_row.addWidget(title_label, 1)
                supported, reason = ofgb.supported(toggle, self.build_number, self.admin)
                if not supported:
                    title_row.addWidget(Badge(reason, "warn"))
                texts.addLayout(title_row)
                if toggle.description:
                    texts.addWidget(Hint(toggle.description))
                row.addLayout(texts, 1)

                if supported:
                    self.rows[toggle.id] = checkbox
                    try:
                        checkbox.setChecked(toggle.current_state())
                    except Exception:
                        pass
                else:
                    checkbox.setEnabled(False)

                holder = QWidget()
                holder.setLayout(row)
                card.add(holder)
            self.add(card)

        self.add(Hint(
            "Bu ayarlar HKCU altında saklanır ve yönetici izni gerektirmez. "
            "Değişiklikler geri alma kaydına eklenir."
        ))
        self.add_stretch()

    def _select_all(self) -> None:
        all_checked = all(cb.isChecked() for cb in self.rows.values()) if self.rows else False
        for checkbox in self.rows.values():
            checkbox.setChecked(not all_checked)
        self.all_btn.setText("Tümünü aç" if not all_checked else "Tümünü kapat")

    def _launch_original(self) -> None:
        self.ofgb_btn.setEnabled(False)
        self.status.setText("OFGB hazırlanıyor…")

        def work():
            try:
                path = ofgb.ensure_ofgb_exe(on_log=lambda msg: self.status.setText(msg))
                import subprocess
                subprocess.Popen([path])
                logger.info(f"OFGB başlatıldı: {path}")
                self.status.setText("OFGB açıldı. İşiniz bitince bu pencereyi kapatabilirsiniz.")
            except Exception as exc:  # noqa: BLE001
                logger.warn(f"OFGB başlatılamadı: {exc}")
                self.status.setText(t("OFGB açılamadı: {exc}", exc=exc))
            finally:
                self.ofgb_btn.setEnabled(True)

        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------------- state
    def _restore(self) -> None:
        saved = self.session.get("ofgb") or {}
        if saved:
            for toggle_id, value in saved.items():
                checkbox = self.rows.get(toggle_id)
                if checkbox:
                    checkbox.setChecked(bool(value))

    def collect(self) -> None:
        self.session.set("ofgb", {tid: cb.isChecked() for tid, cb in self.rows.items() if cb.isChecked()})

    def plan(self) -> list[Task]:
        selected = [tid for tid, cb in self.rows.items() if cb.isChecked()]
        if not selected:
            return []

        def run(ctx):
            ok, fail = ofgb.apply_selection(selected, ctx.dry_run)
            ctx.log(f"Reklam ayarları: {ok} uygulandı, {fail} başarısız")
            ctx.add("ads_applied", ok)
            if fail and not ok:
                raise RuntimeError(f"{fail} anahtar yazılamadı")

        return [Task(
            key="ofgb:apply",
            group="Reklamlar",
            title=f"{len(selected)} reklam ayarını kapat",
            fn=run,
        )]

    def summary(self) -> str:
        count = sum(1 for cb in self.rows.values() if cb.isChecked())
        return f"{count} ayar" if count else "seçim yok"
