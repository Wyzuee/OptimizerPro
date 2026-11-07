"""Başlangıç öğeleri ve boot (msconfig) ayarları."""
from __future__ import annotations

import threading

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QSpinBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ...core.tasks import Task
from ...modules import bootcfg, startup as startup_mod
from ...core.i18n import t
from .. import theme
from ..widgets import Badge, Card, Hint, SectionTitle, TitleLabel
from .base import BasePage


class StartupPage(BasePage):
    step_id = "startup"
    title = "Başlangıç ve boot"
    subtitle = "Açılışta kendiliğinden çalışan uygulamaları kapatın; boot ayarlarını yönetin."

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.items: list[startup_mod.StartupItem] = []
        self.baseline: dict[str, bool] = {}
        self.boot_info: dict = {}
        self._build()
        self._load_boot()

    def _build(self) -> None:
        from PySide6.QtWidgets import QTabWidget
        self.tabs = QTabWidget()
        self.add(self.tabs)

        # ---------------------------------------------------- başlangıç
        start_tab = QWidget()
        start_layout = QVBoxLayout(start_tab)
        start_layout.setContentsMargins(14, 14, 14, 14)
        start_layout.setSpacing(10)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.reload_btn = QPushButton("Yenile")
        self.reload_btn.setObjectName("Ghost")
        self.reload_btn.clicked.connect(self.load_startup)
        bar.addWidget(self.reload_btn)

        self.disable_all_btn = QPushButton("Önerilenleri kapat")
        self.disable_all_btn.setObjectName("Ghost")
        self.disable_all_btn.clicked.connect(self._disable_recommended)
        bar.addWidget(self.disable_all_btn)
        bar.addStretch(1)
        self.count_badge = Badge(t("yükleniyor…"), "muted")
        bar.addWidget(self.count_badge)
        start_layout.addLayout(bar)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["", "Ad", "Konum", "Komut"])
        self.tree.setColumnWidth(0, 44)
        self.tree.setColumnWidth(1, 220)
        self.tree.setColumnWidth(2, 150)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setIndentation(4)
        self.tree.itemChanged.connect(self._on_item_changed)
        start_layout.addWidget(self.tree, 1)

        start_layout.addWidget(Hint(
            "Kapatma işlemi kayıt defterindeki onay bayrağını değiştirir; komut silinmez, "
            "Görev Yöneticisi > Başlangıç sekmesinde tekrar açılabilir."
        ))
        self.tabs.addTab(start_tab, "Başlangıç Uygulamaları")

        # --------------------------------------------------------- boot
        boot_tab = QWidget()
        boot_layout = QVBoxLayout(boot_tab)
        boot_layout.setContentsMargins(14, 14, 14, 14)
        boot_layout.setSpacing(12)

        timeout_card = Card()
        timeout_card.add(TitleLabel("Önyükleme menüsü bekleme süresi", 13))
        timeout_card.add(Hint("Çift işletim sistemi yoksa 0-5 saniye yeterlidir."))
        row = QHBoxLayout()
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(0, 120)
        self.timeout_spin.setSuffix(" saniye")
        self.timeout_spin.setValue(5)
        row.addWidget(self.timeout_spin)
        row.addStretch(1)
        timeout_card.add_layout(row)
        boot_layout.addWidget(timeout_card)

        cpu_card = Card()
        cpu_card.add(TitleLabel("İşlemci sayısı (gelişmiş)", 13))
        cpu_card.add(Hint(
            "msconfig > Önyükleme > Gelişmiş seçenekleri karşılığıdır (bcdedit numproc). "
            "Çoğu sistemde hiçbir kazanç sağlamaz ve çekirdek sayısını sınırlamak performansı DÜŞÜREBİLİR. "
            "Varsayılan olarak devre dışı bırakılmıştır."
        ))
        self.cpu_enable = QCheckBox("Bu ayarı etkinleştir (riskli)")
        self.cpu_enable.stateChanged.connect(self._toggle_cpu)
        cpu_card.add(self.cpu_enable)

        cpu_row = QHBoxLayout()
        self.cpu_spin = QSpinBox()
        self.cpu_spin.setRange(1, 256)
        self.cpu_spin.setEnabled(False)
        cpu_row.addWidget(QLabel("Kullanılacak işlemci:"))
        cpu_row.addWidget(self.cpu_spin)
        self.cpu_info = QLabel("")
        self.cpu_info.setObjectName("Hint")
        cpu_row.addWidget(self.cpu_info, 1)
        cpu_card.add_layout(cpu_row)
        boot_layout.addWidget(cpu_card)

        state_card = Card()
        state_card.add(SectionTitle("MEVCUT BOOT DURUMU"))
        self.boot_state = QLabel("okunuyor…")
        self.boot_state.setObjectName("Hint")
        self.boot_state.setWordWrap(True)
        state_card.add(self.boot_state)
        boot_layout.addWidget(state_card)

        boot_layout.addStretch(1)
        self.tabs.addTab(boot_tab, "Boot (msconfig)")

    # -------------------------------------------------------------- startup
    def on_show(self) -> None:
        if not self.items:
            self.load_startup()

    def load_startup(self) -> None:
        self.reload_btn.setEnabled(False)
        try:
            self.items = startup_mod.list_items(include_disabled=True)
        except Exception:
            self.items = []
        self._fill_tree()
        self.reload_btn.setEnabled(True)

    def _fill_tree(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        self.baseline = {item.key: item.enabled for item in self.items}
        for item in self.items:
            node = QTreeWidgetItem(["", item.name, item.location, item.short_command])
            node.setFlags(node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            node.setCheckState(0, Qt.CheckState.Checked if item.enabled else Qt.CheckState.Unchecked)
            node.setData(1, Qt.ItemDataRole.UserRole, item.key)
            node.setSizeHint(0, QSize(0, 32))
            if item.kind == "folder":
                node.setToolTip(2, "Startup klasörü")
            self.tree.addTopLevelItem(node)
        self.tree.blockSignals(False)

        enabled = sum(1 for i in self.items if i.enabled)
        self.count_badge.set_state(f"{enabled} açık / {len(self.items)} toplam", "info")

    def _on_item_changed(self, node: QTreeWidgetItem, column: int) -> None:
        if column != 0:
            return
        key = node.data(1, Qt.ItemDataRole.UserRole)
        item = next((i for i in self.items if i.key == key), None)
        if not item:
            return
        item.enabled = node.checkState(0) == Qt.CheckState.Checked
        enabled = sum(1 for i in self.items if i.enabled)
        self.count_badge.set_state(f"{enabled} açık / {len(self.items)} toplam", "info")

    def _disable_recommended(self) -> None:
        """Yayıncısı bilinmeyen / kullanıcı klasörü dışındaki girişleri kapatmayı önerir."""
        suspicious_keywords = ("update", "helper", "launcher", "updater", "agent", "adobe", "java", "quicktime")
        count = 0
        for index in range(self.tree.topLevelItemCount()):
            node = self.tree.topLevelItem(index)
            text = (node.text(1) + " " + node.text(3)).lower()
            if any(word in text for word in suspicious_keywords):
                if node.checkState(0) == Qt.CheckState.Checked:
                    node.setCheckState(0, Qt.CheckState.Unchecked)
                    count += 1
        if count == 0:
            QMessageBox.information(self, "Başlangıç", "Kapatılacak öneri bulunamadı.")

    # ----------------------------------------------------------------- boot
    def _load_boot(self) -> None:
        def work():
            info = bootcfg.current_entry()
            cores, threads = bootcfg.cpu_counts()
            self.boot_info = info
            self.boot_info["cores"] = cores
            self.boot_info["threads"] = threads

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        # Basit bekleyiş: kısa süreli iş olduğu için doğrudan da çalıştırılabilir
        thread.join(timeout=15)
        self._apply_boot_info()

    def _apply_boot_info(self) -> None:
        info = self.boot_info or {}
        self.timeout_spin.setValue(int(info.get("timeout") or 5))
        threads = int(info.get("threads") or 1)
        self.cpu_spin.setMaximum(max(1, threads))
        self.cpu_spin.setValue(int(info.get("numproc") or threads))
        self.cpu_info.setText(t("Sistemde {cores} çekirdek / {threads} iş parçacığı var", cores=info.get("cores", "?"), threads=threads))
        numproc = int(info.get("numproc") or 0)
        self.boot_state.setText(
            f"Giriş: {info.get('description') or '(varsayılan)'}\n"
            f"Timeout: {info.get('timeout')} sn\n"
            f"numproc: {numproc or 'ayarlı değil (tüm çekirdekler)'}\n"
            f"Safe boot: {info.get('safeboot') or 'kapalı'}"
        )
        if numproc:
            self.cpu_enable.setChecked(True)

    def _toggle_cpu(self) -> None:
        enabled = self.cpu_enable.isChecked()
        self.cpu_spin.setEnabled(enabled)
        if enabled:
            reply = QMessageBox.warning(
                self, "İşlemci sayısı",
                "İşlemci sayısını sınırlamak performansı düşürebilir ve bazı sistemlerde açılış sorunlarına yol açabilir.\n\n"
                "Devam etmek istiyor musunuz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.cpu_enable.setChecked(False)
                self.cpu_spin.setEnabled(False)

    # ---------------------------------------------------------------- state
    def collect(self) -> None:
        changes = {i.key: i.enabled for i in self.items}
        self.session.set("startup", changes)
        self.session.set("boot", {
            "enabled": self.cpu_enable.isChecked(),
            "numproc": self.cpu_spin.value() if self.cpu_enable.isChecked() else 0,
            "timeout": self.timeout_spin.value(),
        })

    def plan(self) -> list[Task]:
        tasks: list[Task] = []
        current = {i.key: i.enabled for i in self.items}
        changed = [i for i in self.items if current.get(i.key) != self.baseline.get(i.key)]

        for item in changed:
            want = current[item.key]

            def make(item=item, want=want):
                def run(ctx):
                    ok = startup_mod.set_enabled(item, want, ctx.dry_run)
                    if not ok:
                        raise RuntimeError("başlangıç durumu değiştirilemedi")
                    ctx.add("startup_changed", 1)
                return run

            tasks.append(Task(
                key=f"startup:{item.key}",
                group="Başlangıç",
                title=f"{item.name} → {'aç' if want else 'kapat'}",
                fn=make(),
            ))

        boot_state = self.session.get("boot") or {}
        if boot_state.get("enabled"):
            numproc = int(boot_state.get("numproc") or 0)

            def run_numproc(ctx):
                if not bootcfg.set_numproc(numproc, ctx.dry_run):
                    raise RuntimeError("numproc ayarlanamadı")
                ctx.add("boot_changed", 1)

            tasks.append(Task(
                key="boot:numproc",
                group="Boot",
                title=f"İşlemci sayısı: {numproc}",
                fn=run_numproc,
            ))
        return tasks

    def summary(self) -> str:
        tasks = self.plan()
        return f"{len(tasks)} değişiklik" if tasks else "değişiklik yok"
