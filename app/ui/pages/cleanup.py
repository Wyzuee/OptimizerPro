"""Temizlik sayfası: hedef grupları, ölçüm, seçim."""
from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from ...core.download import human_size
from ...core.tasks import Task
from ...modules import cleanup as cleanup_mod
from ...core.i18n import t
from .. import theme
from ..widgets import Badge, Card, Hint, SectionTitle, TitleLabel
from .base import BasePage


class CleanupPage(BasePage):
    step_id = "cleanup"
    title = "Disk temizliği"
    subtitle = "Geçici dosyalar, güncelleme kalıntıları ve çöp kutusu. Her grup ayrı ayrı seçilir."

    measured = Signal(dict)

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.targets = cleanup_mod.load_targets()
        self.rows: dict[str, tuple[QCheckBox, Badge]] = {}
        self.sizes: dict[str, int] = {}
        self.total_label = None
        self.measured.connect(self._on_measured)
        self._build()
        self._restore()

    def _build(self) -> None:
        top = Card()
        row = QHBoxLayout()
        row.setSpacing(12)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(TitleLabel("Seçili grupların toplam boyutu", 13))
        self.total_label = QLabel("ölçüm bekleniyor…")
        self.total_label.setStyleSheet(f"color: {theme.ACCENT}; font-size: 12px;")
        texts.addWidget(self.total_label)
        row.addLayout(texts, 1)

        self.measure_btn = QPushButton("Boyutları ölç")
        self.measure_btn.setObjectName("Ghost")
        self.measure_btn.clicked.connect(self.measure)
        row.addWidget(self.measure_btn)

        select_all = QPushButton("Güvenli olanları seç")
        select_all.setObjectName("Ghost")
        select_all.clicked.connect(self._select_safe)
        row.addWidget(select_all)
        top.add_layout(row)
        self.add(top)

        current_group = None
        group_card = None
        for target in self.targets:
            if target.group != current_group:
                if group_card:
                    self.add(group_card)
                current_group = target.group
                group_card = Card()
                group_card.add(SectionTitle(target.group.upper()))

            line = QHBoxLayout()
            line.setContentsMargins(0, 4, 0, 4)
            line.setSpacing(10)
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(lambda _: self._update_total())
            line.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignTop)

            texts = QVBoxLayout()
            texts.setSpacing(1)
            title_label = QLabel(target.name)
            title_label.setObjectName("CardTitle")
            title_label.setWordWrap(False)
            title_row = QHBoxLayout()
            title_row.setSpacing(8)
            title_row.addWidget(title_label)
            if target.warning:
                title_row.addWidget(Badge(t("dikkat"), "warn"))
            title_row.addStretch(1)
            texts.addLayout(title_row)
            if target.description:
                desc = QLabel(target.description)
                desc.setObjectName("CardSubtitle")
                desc.setWordWrap(True)
                texts.addWidget(desc)
            line.addLayout(texts, 1)

            badge = Badge("—", "muted")
            line.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)

            from PySide6.QtWidgets import QWidget
            wrapper = QWidget()
            wrapper.setLayout(line)
            wrapper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            group_card.add(wrapper)
            self.rows[target.id] = (checkbox, badge)

        if group_card:
            self.add(group_card)

        info = Card()
        info.add(Hint("Prefetch ve küçük resim önbelleği Windows tarafından yeniden oluşturulur; "
                      "kalıcı performans kaybı olmaz. Kilitli dosyalar atlanır ve raporda gösterilir."))
        self.add(info)
        self.add_stretch()

    # ------------------------------------------------------------- actions
    def _select_safe(self) -> None:
        for target in self.targets:
            checkbox, _ = self.rows[target.id]
            checkbox.setChecked(target.risk == "low")

    def _update_total(self) -> None:
        total = 0
        for target_id, (checkbox, _) in self.rows.items():
            if checkbox.isChecked():
                total += self.sizes.get(target_id, 0)
        if self.measure_btn.text() == "Boyutları ölç":
            self.total_label.setText("ölçüm bekleniyor…")
        else:
            self.total_label.setText(t("{size} temizlenecek", size=human_size(total)))

    def measure(self) -> None:
        self.measure_btn.setEnabled(False)
        self.measure_btn.setText("ölçülüyor…")

        def work():
            for target in self.targets:
                size = cleanup_mod.measure(target)
                self.sizes[target.id] = size
                self.measured.emit(dict(self.sizes))

        thread = threading.Thread(target=work, daemon=True)
        thread.start()

    def _on_measured(self, sizes: dict) -> None:
        self.sizes = sizes
        for target_id, (_, badge) in self.rows.items():
            size = sizes.get(target_id)
            if size is None:
                continue
            if target_id == "dism_cleanup":
                badge.set_state(t("yalnızca DISM"), "info")
            else:
                badge.set_state(human_size(size) if size else "0 B", "ok" if size else "muted")
        if len(sizes) >= len(self.targets):
            self.measure_btn.setEnabled(True)
            self.measure_btn.setText("Boyutları ölç")
            self._update_total()

    # -------------------------------------------------------------- state
    def _restore(self) -> None:
        selected = set(self.session.get("cleanup") or [])
        for target_id, (checkbox, _) in self.rows.items():
            checkbox.setChecked(target_id in selected)

    def collect(self) -> None:
        selected = [tid for tid, (checkbox, _) in self.rows.items() if checkbox.isChecked()]
        self.session.set("cleanup", selected)

    def plan(self) -> list[Task]:
        selected = [tid for tid, (checkbox, _) in self.rows.items() if checkbox.isChecked()]
        tasks = []
        lookup = {t.id: t for t in self.targets}
        for target_id in selected:
            target = lookup.get(target_id)
            if not target:
                continue

            def make(target=target):
                def run(ctx):
                    ok, message = cleanup_mod.clean(target, ctx.dry_run, on_log=ctx.log)
                    if not ok:
                        raise RuntimeError(message)
                    ctx.add("cleanup_count", 1)
                    ctx.add("cleanup_bytes", self.sizes.get(target.id, 0))
                return run

            tasks.append(Task(
                key=f"cleanup:{target.id}",
                group="Temizlik",
                title=target.name,
                fn=make(),
                weight=3 if target.kind == "dism" else 1,
            ))
        return tasks

    def summary(self) -> str:
        selected = [tid for tid, (c, _) in self.rows.items() if c.isChecked()]
        if not selected:
            return "seçim yok"
        total = sum(self.sizes.get(t, 0) for t in selected)
        return f"{len(selected)} grup · {human_size(total)}"
