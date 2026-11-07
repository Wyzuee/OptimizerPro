"""Klasik Optimizer terminali: gömülü konsolda eski aracı çalıştırır."""
from __future__ import annotations

import os
import subprocess
import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from ...core.i18n import t
from ...core import logger
from ...core.paths import tools_dir
from ...core.tasks import Task
from .. import theme
from ..widgets import Badge, Card, Hint, LogView, TitleLabel
from .base import BasePage

_CREATE_NO_WINDOW = 0x08000000


class TerminalPage(BasePage):
    step_id = "terminal"
    title = "Klasik terminal"
    subtitle = "Önceki Optimizer aracını bu panelde çalıştırın. E/H sorularını aşağıdaki alandan yanıtlayın."

    stream = Signal(str)
    finished = Signal(int)

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.process: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None
        self._build()
        self.stream.connect(self.log.append_text)
        self.finished.connect(self._on_finished)

    def _build(self) -> None:
        card = Card()
        row = QHBoxLayout()
        row.setSpacing(10)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(TitleLabel("Optimizer.exe (klasik sürüm)", 13))
        texts.addWidget(Hint("Bu araç konsol tabanlıdır. Çıktısı aşağıda canlı olarak görünür."))
        row.addLayout(texts, 1)

        self.status_badge = Badge(t("hazır"), "muted")
        row.addWidget(self.status_badge)

        self.start_btn = QPushButton("Başlat")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(self.start_process)
        row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Durdur")
        self.stop_btn.setObjectName("DangerBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_process)
        row.addWidget(self.stop_btn)

        self.clear_btn = QPushButton("Temizle")
        self.clear_btn.setObjectName("Ghost")
        self.clear_btn.clicked.connect(lambda: self.log.clear())
        row.addWidget(self.clear_btn)
        card.add_layout(row)

        exe = tools_dir() / "Optimizer.exe"
        self.path_label = QLabel(f"Araç yolu: {exe}" + ("" if exe.exists() else "  (bulunamadı!)"))
        self.path_label.setObjectName("Hint" if exe.exists() else "Danger")
        card.add(self.path_label)
        self.add(card)

        self.log = LogView()
        self.log.setMinimumHeight(360)
        self.add(self.log)

        input_card = Card()
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Yanıt yazıp Enter'a basın (ör. E, H, 1,7,19)…")
        self.input.returnPressed.connect(self.send_input)
        row2.addWidget(self.input, 1)

        for label, value in (("E (Evet)", "E"), ("H (Hayır)", "H"), ("ESC", "\x1b")):
            btn = QPushButton(label)
            btn.setObjectName("Ghost")
            btn.clicked.connect(lambda _=False, v=value: self._send(v))
            row2.addWidget(btn)

        self.send_btn = QPushButton("Gönder")
        self.send_btn.clicked.connect(self.send_input)
        row2.addWidget(self.send_btn)
        input_card.add_layout(row2)

        input_card.add(Hint(
            "Not: Bu araç kendi konsolunda ESC ile durdurulabiliyordu. Gömülü modda ESC çalışmaz; "
            "bunun yerine yukarıdaki 'Durdur' düğmesini kullanın."
        ))
        self.add(input_card)
        self.add_stretch()

    # -------------------------------------------------------------- process
    def start_process(self) -> None:
        if self.process and self.process.poll() is None:
            return
        exe = tools_dir() / "Optimizer.exe"
        if not exe.exists():
            self.log.append_line(f"[hata] Araç bulunamadı: {exe}")
            self.status_badge.set_state(t("bulunamadı"), "err")
            return

        if bool(self.session.get("dry_run")):
            self.log.append_line("[dry-run] Optimizer.exe çalıştırılmadı.")
            return

        from ...core.elevation import is_admin
        if not is_admin():
            self.log.append_line(
                "[hata] Bu araç yönetici izni ister. Optimizer Pro'yu yönetici olarak yeniden başlatın."
            )
            self.status_badge.set_state(t("yönetici gerekli"), "err")
            return

        try:
            self.process = subprocess.Popen(
                [str(exe)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(exe.parent),
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
                creationflags=_CREATE_NO_WINDOW,
                bufsize=0,
            )
        except Exception as exc:  # noqa: BLE001
            self.log.append_line(f"[hata] Başlatılamadı: {exc}")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_badge.set_state(t("çalışıyor"), "info")
        logger.info("Klasik Optimizer başlatıldı")
        self._reader = threading.Thread(target=self._read_output, daemon=True)
        self._reader.start()

    def _read_output(self) -> None:
        import codecs
        assert self.process and self.process.stdout
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        while True:
            chunk = self.process.stdout.read(256)
            if not chunk:
                break
            text = decoder.decode(chunk)
            if text:
                self.stream.emit(text)
        final = decoder.decode(b"", True)
        if final:
            self.stream.emit(final)
        self.finished.emit(self.process.returncode or 0)

    def _on_finished(self, code: int) -> None:
        self.log.append_line("\n" + t("[süreç bitti · çıkış kodu {code}]", code=code))
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_badge.set_state(t("bitti"), "muted")
        logger.info(f"Klasik Optimizer kapandı (kod {code})")

    def stop_process(self) -> None:
        if not self.process or self.process.poll() is not None:
            return
        try:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.process.pid)],
                           capture_output=True, creationflags=_CREATE_NO_WINDOW, timeout=15)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass
        self.log.append_line("\n" + t("[durduruldu]"))

    def _send(self, text: str) -> None:
        if not self.process or self.process.poll() is not None or not self.process.stdin:
            self.log.append_line("[uyarı] Çalışan süreç yok.")
            return
        try:
            self.process.stdin.write((text + "\r\n").encode("utf-8"))
            self.process.stdin.flush()
            self.log.append_line(f"> {text if text != chr(27) else 'ESC'}")
        except Exception as exc:  # noqa: BLE001
            self.log.append_line(f"[hata] Gönderilemedi: {exc}")

    def send_input(self) -> None:
        text = self.input.text()
        self.input.clear()
        if text:
            self._send(text)

    # ---------------------------------------------------------------- plan
    def plan(self) -> list[Task]:
        return []
