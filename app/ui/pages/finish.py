"""Kurulum tamamlandı ekranı ve rapor."""
from __future__ import annotations

import os
import subprocess
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from ...core.i18n import t
from ...core import logger, logger as log_mod, ps, undo
from ...core.download import human_size
from ...core.paths import reports_dir
from ...core.restore import restore_all
from ...core.state import SESSION
from .. import theme
from ..widgets import Badge, Card, Hint, SectionTitle, StatCard, TitleLabel
from .base import BasePage


class FinishPage(BasePage):
    step_id = "finish"
    title = "Kurulum tamamlandı"
    subtitle = "Tüm seçili işlemler tamamlandı. Aşağıda özet ve atlananlar listelenir."

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.summary: dict = {}
        self.stats: dict = {}
        self._build()

    def _build(self) -> None:
        hero = Card()
        hero.setMinimumHeight(120)
        row = QHBoxLayout()
        row.setSpacing(16)
        row.setContentsMargins(4, 4, 4, 4)

        self.hero_icon = QLabel("✓")
        self.hero_icon.setFixedWidth(64)
        self.hero_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_icon.setStyleSheet(
            f"font-size: 42px; color: {theme.GREEN}; background: {theme.GREEN_SOFT}; border-radius: 32px;"
        )
        row.addWidget(self.hero_icon)

        texts = QVBoxLayout()
        texts.setSpacing(4)
        self.hero_title = QLabel("Kurulum tamamlandı")
        self.hero_title.setStyleSheet("font-size: 26px; font-weight: 700;")
        texts.addWidget(self.hero_title)
        self.hero_sub = QLabel("")
        self.hero_sub.setObjectName("PageSubtitle")
        self.hero_sub.setWordWrap(True)
        texts.addWidget(self.hero_sub)
        row.addLayout(texts, 1)

        self.state_badge = Badge(t("tamamlandı"), "ok")
        row.addWidget(self.state_badge, 0, Qt.AlignmentFlag.AlignTop)
        hero.add_layout(row)
        self.add(hero)

        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(12)
        self.add_layout(self.stats_grid)

        self.issues_card = Card()
        self.issues_card.add(SectionTitle("ATLANAN VEYA HATA VEREN İŞLEMLER"))
        self.issues_box = QVBoxLayout()
        self.issues_box.setSpacing(4)
        self.issues_card.add_layout(self.issues_box)
        self.add(self.issues_card)

        actions = Card()
        actions.add(TitleLabel("Sırada ne var?", 13))
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self.restart_btn = QPushButton("Şimdi yeniden başlat")
        self.restart_btn.setObjectName("Primary")
        self.restart_btn.clicked.connect(self._restart)
        row2.addWidget(self.restart_btn)

        self.later_btn = QPushButton("Sonra")
        self.later_btn.setObjectName("Ghost")
        self.later_btn.clicked.connect(self._later)
        row2.addWidget(self.later_btn)

        self.report_btn = QPushButton("Raporu kaydet")
        self.report_btn.setObjectName("Ghost")
        self.report_btn.clicked.connect(self._save_report)
        row2.addWidget(self.report_btn)

        self.log_btn = QPushButton("Günlüğü aç")
        self.log_btn.setObjectName("Ghost")
        self.log_btn.clicked.connect(self._open_log)
        row2.addWidget(self.log_btn)

        self.undo_btn = QPushButton("Değişiklikleri geri al")
        self.undo_btn.setObjectName("DangerBtn")
        self.undo_btn.clicked.connect(self._undo)
        row2.addWidget(self.undo_btn)

        self.exit_btn = QPushButton("Çık")
        self.exit_btn.setObjectName("Ghost")
        self.exit_btn.clicked.connect(self._exit)
        row2.addWidget(self.exit_btn)
        row2.addStretch(1)
        actions.add_layout(row2)
        actions.add(Hint("Yeniden başlatma, kapatılan başlangıç öğeleri ve bazı ayarların etkinleşmesi için önerilir."))
        self.add(actions)
        self.add_stretch()

    # --------------------------------------------------------------- render
    def show_results(self, summary: dict, stats: dict) -> None:
        self.summary = summary or {}
        self.stats = stats or {}
        total = int(self.summary.get("total") or 0)
        done = int(self.summary.get("done") or 0)
        skipped = int(self.summary.get("skipped") or 0)
        failed = int(self.summary.get("failed") or 0)

        if total == 0:
            self.step_title_reset("Yapılacak işlem yok", "Hiçbir adımda işlem seçilmedi.", "muted", "•")
        elif failed:
            self.step_title_reset(
                "Kurulum tamamlandı (bazı işlemler atlandı)",
                f"{done} işlem başarılı, {failed} işlem hata verdi, {skipped} işlem atlandı.",
                "warn", "!",
            )
        else:
            self.step_title_reset(
                "Kurulum tamamlandı",
                f"{done} işlem başarıyla uygulandı" + (f", {skipped} işlem atlandı." if skipped else "."),
                "ok", "✓",
            )

        self._fill_stats(done, skipped, failed)
        self._fill_issues()

    def step_title_reset(self, title: str, subtitle: str, tone: str, glyph: str) -> None:
        self.hero_title.setText(title)
        self.hero_sub.setText(subtitle)
        self.state_badge.set_state({"ok": "tamamlandı", "warn": "kısmi", "muted": "boş"}.get(tone, ""), tone)
        colors = {"ok": (theme.GREEN, theme.GREEN_SOFT), "warn": (theme.AMBER, theme.AMBER_SOFT),
                  "muted": (theme.MUTED, "#16222F")}
        color, bg = colors.get(tone, (theme.GREEN, theme.GREEN_SOFT))
        self.hero_icon.setText(glyph)
        self.hero_icon.setStyleSheet(
            f"font-size: 42px; font-weight: 700; color: {color}; background: {bg}; border-radius: 32px;"
        )

    def _fill_stats(self, done: int, skipped: int, failed: int) -> None:
        while self.stats_grid.count():
            item = self.stats_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = self.stats or {}
        cleanup_bytes = int(stats.get("cleanup_bytes") or 0)
        installed = int(stats.get("programs_installed") or 0) + int(stats.get("dev_apps") or 0)
        ads = int(stats.get("ads_applied") or 0)
        tweaks = int(stats.get("tweaks_applied") or 0)
        startup_changed = int(stats.get("startup_changed") or 0)
        apps_removed = int(stats.get("appx_removed") or 0)
        files = int(stats.get("files_deleted") or 0) + int(stats.get("files_moved") or 0)

        cards = [
            (human_size(cleanup_bytes), "Kazanılan disk alanı", "ok"),
            (str(installed), "Kurulan program", "info"),
            (str(ads + tweaks), "Uygulanan ayar", "info"),
            (str(apps_removed), "Kaldırılan Windows uygulaması", "warn"),
            (str(startup_changed), "Başlangıç değişikliği", "muted"),
            (str(files), "Düzenlenen dosya", "muted"),
        ]
        for index, (value, label, tone) in enumerate(cards):
            self.stats_grid.addWidget(StatCard(value, label, tone), index // 3, index % 3)

    def _fill_issues(self) -> None:
        while self.issues_box.count():
            item = self.issues_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = self.summary.get("results") or []
        problems = [r for r in items if getattr(r, "status", "") in ("failed", "skipped")]
        if not problems:
            self.issues_card.setVisible(False)
            return
        self.issues_card.setVisible(True)
        for result in problems[:40]:
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 1, 0, 1)
            layout.setSpacing(8)
            tone = "err" if result.status == "failed" else "warn"
            layout.addWidget(Badge("hata" if tone == "err" else "atlandı", tone))
            label = QLabel(result.task.title)
            label.setWordWrap(True)
            layout.addWidget(label, 1)
            if result.message:
                msg = QLabel(result.message[:80])
                msg.setObjectName("Hint")
                layout.addWidget(msg, 0)
            self.issues_box.addWidget(row)

    # --------------------------------------------------------------- actions
    def _restart(self) -> None:
        reply = QMessageBox.question(
            self, "Yeniden başlat",
            "Bilgisayar 10 saniye içinde yeniden başlatılacak. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if bool(self.session.get("read_only")):
            QMessageBox.warning(
                self, "Yönetici izni gerekli",
                "Yeniden başlatma için yönetici izni gerekir. Optimizer Pro'yu "
                "yönetici olarak çalıştırın.",
            )
            return

        result = subprocess.run(
            ["shutdown", "/r", "/t", "10", "/c", "Optimizer Pro"],
            capture_output=True, text=True,
            creationflags=0x08000000, timeout=30,
        )
        if result.returncode == 0:
            self.hero_sub.setText("Bilgisayar 10 saniye içinde yeniden başlatılacak…")
            logger.info("Yeniden başlatma planlandı (10 sn)")
        else:
            detail = (result.stderr or result.stdout or "").strip()[:200]
            logger.warn(f"Yeniden başlatma başarısız: {detail}")
            QMessageBox.warning(
                self, "Yeniden başlatma başarısız",
                f"Windows yeniden başlatmayı reddetti.\n\n{detail}\n\n"
                "Programı yönetici olarak çalıştırdığınızdan emin olun.",
            )

    def _later(self) -> None:
        self.hero_sub.setText("Değişikliklerin bir kısmı yeniden başlatmadan sonra etkin olur.")

    def _open_log(self) -> None:
        path = log_mod.current_log_path()
        try:
            os.startfile(path)
        except Exception:
            QMessageBox.information(self, "Günlük", path)

    def _save_report(self) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        md_path = reports_dir() / f"{stamp}_rapor.md"
        html_path = reports_dir() / f"{stamp}_rapor.html"
        stats = self.stats or {}
        items = self.summary.get("results") or []

        lines = [
            f"# Optimizer Pro raporu — {stamp}",
            "",
            f"- Toplam işlem: {self.summary.get('total', 0)}",
            f"- Başarılı: {self.summary.get('done', 0)}",
            f"- Atlanan: {self.summary.get('skipped', 0)}",
            f"- Hata: {self.summary.get('failed', 0)}",
            f"- Kazanılan alan: {human_size(int(stats.get('cleanup_bytes') or 0))}",
            "",
            "## İşlemler",
            "",
            "| Durum | Grup | İşlem | Süre | Not |",
            "| --- | --- | --- | --- | --- |",
        ]
        for result in items:
            status = {"done": "✔", "skipped": "○", "failed": "✕"}.get(result.status, "?")
            lines.append(
                f"| {status} | {result.task.group} | {result.task.title} | {result.duration:.1f}s | {result.message or ''} |"
            )
        md_path.write_text("\n".join(lines), encoding="utf-8")

        rows = "".join(
            f"<tr><td>{r.task.group}</td><td>{r.task.title}</td>"
            f"<td>{'✔' if r.status == 'done' else ('○' if r.status == 'skipped' else '✕')}</td>"
            f"<td>{r.duration:.1f}s</td><td>{r.message or ''}</td></tr>"
            for r in items
        )
        html = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<title>Optimizer Pro raporu</title>
<style>body{{font-family:Segoe UI,sans-serif;background:#0A1018;color:#E8F1F8;padding:32px}}
h1{{color:#22D3EE}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #213548;padding:6px 10px;font-size:13px}}
th{{background:#131F2E;text-align:left}}</style></head><body>
<h1>Optimizer Pro raporu</h1><p>{stamp}</p>
<p>Toplam {self.summary.get('total', 0)} işlem · {self.summary.get('done', 0)} başarılı ·
{self.summary.get('skipped', 0)} atlandı · {self.summary.get('failed', 0)} hata</p>
<table><tr><th>Grup</th><th>İşlem</th><th>Durum</th><th>Süre</th><th>Not</th></tr>{rows}</table>
</body></html>"""
        html_path.write_text(html, encoding="utf-8")

        logger.info(f"Rapor kaydedildi: {md_path}")
        QMessageBox.information(self, "Rapor", f"Rapor kaydedildi:\n{md_path}\n{html_path}")

    def _undo(self) -> None:
        count = undo.count()
        if count == 0:
            QMessageBox.information(self, "Geri al", "Geri alınacak kayıt bulunamadı.")
            return
        reply = QMessageBox.question(
            self, "Geri al",
            f"{count} kayıt geri alınacak (registry değerleri, taşınan dosyalar, güç planı).\n"
            "Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        ok, fail, messages = restore_all(dry_run=bool(self.session.get("dry_run")))
        QMessageBox.information(self, "Geri al", f"{ok} kayıt geri alındı, {fail} başarısız.\n")
        if fail:
            logger.warn("; ".join(messages[:10]))

    def _exit(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()

    def on_show(self) -> None:
        report = SESSION.get("last_run") or {}
        if not self.summary and report.get("report"):
            stored = report["report"]
            self.stats = stored.get("stats") or {}
            items = stored.get("items") or []

            class _R:
                def __init__(self, row):
                    self.status = row.get("status")
                    self.message = row.get("message")
                    self.duration = row.get("duration", 0)
                    self.task = type("T", (), {"title": row.get("title"), "group": row.get("group")})()

            self.summary = {
                "total": stored.get("summary", {}).get("total", len(items)),
                "done": stored.get("summary", {}).get("done", 0),
                "skipped": stored.get("summary", {}).get("skipped", 0),
                "failed": stored.get("summary", {}).get("failed", 0),
                "results": [_R(row) for row in items],
            }
            self.show_results(self.summary, self.stats)
