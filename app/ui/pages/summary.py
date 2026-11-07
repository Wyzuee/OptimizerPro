"""Özet ve uygulama: tüm seçimleri gösterir, kuyruğu çalıştırır."""
from __future__ import annotations

import threading
from collections import OrderedDict

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from ...core.i18n import t, tn
from ...core import logger, ps
from ...core.tasks import (
    STATUS_DONE, STATUS_FAILED, STATUS_SKIPPED, Task, TaskContext, TaskEngine,
)
from .. import theme
from ..widgets import Badge, Card, Hint, ProgressRow, SectionTitle, TitleLabel
from .base import BasePage


class ApplyWorker(QThread):
    task_started = Signal(int)
    task_finished = Signal(int, object)
    progress = Signal(float)
    log = Signal(str)
    finished_all = Signal(object, object)

    def __init__(self, tasks: list[Task], ctx: TaskContext):
        super().__init__()
        self.tasks = tasks
        self.ctx = ctx

    def run(self) -> None:
        engine = TaskEngine(self.tasks, self.ctx)

        def on_start(index, task):
            self.task_started.emit(index)

        def on_finish(index, result):
            self.task_finished.emit(index, result)

        def on_progress(fraction):
            self.progress.emit(fraction)

        results = engine.run(on_task_start=on_start, on_task_finish=on_finish, on_progress=on_progress)
        self.finished_all.emit(engine.summary(), dict(self.ctx.results))


class SummaryPage(BasePage):
    step_id = "summary"
    title = "Özet ve uygula"
    subtitle = "Seçimlerinizi gözden geçirin. Uygula dediğinizde tüm işlemler sırayla çalışır."

    run_completed = Signal(object, object)

    def __init__(self, session, parent=None):
        super().__init__(session, parent)
        self.tasks: list[Task] = []
        self.task_checks: list[QCheckBox] = []
        self.rows: list[ProgressRow] = []
        self.worker: ApplyWorker | None = None
        self.ctx: TaskContext | None = None
        self.groups_card: QWidget | None = None
        self._build()

    def _build(self) -> None:
        stats = Card()
        row = QHBoxLayout()
        row.setSpacing(10)
        self.task_count = Badge(t("0 işlem"), "info")
        self.group_count = Badge(t("0 grup"), "muted")
        row.addWidget(self.task_count)
        row.addWidget(self.group_count)
        row.addStretch(1)

        self.apply_btn = QPushButton("Uygula")
        self.apply_btn.setObjectName("Primary")
        self.apply_btn.clicked.connect(self.start_apply)
        row.addWidget(self.apply_btn)

        self.cancel_btn = QPushButton("İptal")
        self.cancel_btn.setObjectName("DangerBtn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel)
        row.addWidget(self.cancel_btn)
        stats.add_layout(row)

        self.dry_badge = Badge(t("deneme modu — değişiklik uygulanmaz"), "warn")
        self.dry_badge.setVisible(bool(self.session.get("dry_run")))
        stats.add(self.dry_badge)
        self.add(stats)

        self.progress_card = Card()
        self.progress_card.add(TitleLabel("İlerleme", 13))
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress_card.add(self.progress)
        self.progress_label = QLabel("hazır")
        self.progress_label.setObjectName("Hint")
        self.progress_card.add(self.progress_label)
        self.add(self.progress_card)

        self.plan_card = Card()
        self.plan_card.add(SectionTitle("YAPILACAKLAR"))
        self.plan_box = QVBoxLayout()
        self.plan_box.setSpacing(2)
        self.plan_card.add_layout(self.plan_box)
        self.add(self.plan_card)

        self.empty_label = QLabel("")
        self.empty_label.setObjectName("Hint")
        self.add(self.empty_label)
        self.add_stretch()

    # ---------------------------------------------------------------- plan
    def set_plan(self, tasks: list[Task]) -> None:
        self.tasks = tasks
        self._fill_plan()

    def _fill_plan(self) -> None:
        while self.plan_box.count():
            item = self.plan_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.task_checks = []
        self.rows = []

        if not self.tasks:
            self.empty_label.setText(
                "Hiçbir adımda işlem seçilmedi. Bu adımı atlayabilir veya geri dönüp seçim yapabilirsiniz."
            )
            self.task_count.setText("0 işlem")
            self.group_count.setText("0 grup")
            self.apply_btn.setEnabled(False)
            return

        self.empty_label.setText("")
        self.apply_btn.setEnabled(True)

        groups: OrderedDict[str, list[tuple[int, Task]]] = OrderedDict()
        for index, task in enumerate(self.tasks):
            groups.setdefault(task.group, []).append((index, task))

        for group, entries in groups.items():
            header = QLabel(group.upper())
            header.setObjectName("SectionTitle")
            header.setContentsMargins(2, 8, 0, 2)
            self.plan_box.addWidget(header)
            for index, task in entries:
                row = QWidget()
                layout = QHBoxLayout(row)
                layout.setContentsMargins(0, 2, 0, 2)
                layout.setSpacing(8)
                checkbox = QCheckBox()
                checkbox.setChecked(True)
                layout.addWidget(checkbox)
                progress_row = ProgressRow(task.title)
                layout.addWidget(progress_row, 1)
                self.plan_box.addWidget(row)
                self.task_checks.append(checkbox)
                self.rows.append(progress_row)

        self.task_count.setText(t("{count} işlem", count=len(self.tasks)))
        self.group_count.setText(t("{count} grup", count=len(groups)))
        self.progress.setValue(0)
        self.progress_label.setText("hazır")

    def selected_tasks(self) -> list[Task]:
        return [task for task, checkbox in zip(self.tasks, self.task_checks) if checkbox.isChecked()]

    # --------------------------------------------------------------- apply
    def start_apply(self) -> None:
        tasks = self.selected_tasks()
        if not tasks:
            return
        self.tasks_to_run = tasks
        self._index_map = {id(task): index for index, task in enumerate(tasks)}

        # Satırları yeniden kur (yalnızca seçilenler)
        while self.plan_box.count():
            item = self.plan_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.rows = []
        self.task_checks = []
        groups: OrderedDict[str, list[Task]] = OrderedDict()
        for task in tasks:
            groups.setdefault(task.group, []).append(task)
        for group, entries in groups.items():
            header = QLabel(group.upper())
            header.setObjectName("SectionTitle")
            header.setContentsMargins(2, 8, 0, 2)
            self.plan_box.addWidget(header)
            for task in entries:
                row = ProgressRow(task.title)
                self.plan_box.addWidget(row)
                self.rows.append(row)

        self.apply_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setValue(0)
        self.progress_label.setText("başlıyor…")

        self.ctx = TaskContext(dry_run=bool(self.session.get("dry_run")))
        self.worker = ApplyWorker(tasks, self.ctx)
        self.worker.task_started.connect(self._on_task_started)
        self.worker.task_finished.connect(self._on_task_finished)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(lambda _: None)
        self.worker.finished_all.connect(self._on_finished)
        self.session.begin_run()
        self.worker.start()

    def _on_task_started(self, index: int) -> None:
        if 0 <= index < len(self.rows):
            self.rows[index].set_running()
            self.progress_label.setText(t("çalışıyor: {title}", title=self.rows[index]._title))

    def _on_task_finished(self, index: int, result) -> None:
        if not (0 <= index < len(self.rows)):
            return
        row = self.rows[index]
        if result.status == STATUS_DONE:
            row.set_done(result.duration)
        elif result.status == STATUS_SKIPPED:
            row.set_skipped(result.message or "atlandı")
        else:
            row.set_failed(result.message or "hata")

    def _on_progress(self, fraction: float) -> None:
        self.progress.setValue(int(fraction * 1000))
        self.progress_label.setText(f"%{fraction * 100:.0f}")

    def _on_finished(self, summary: dict, stats: dict) -> None:
        self.apply_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress.setValue(1000)
        self.progress_label.setText(
            f"tamamlandı · {summary['done']} başarılı, {summary['skipped']} atlandı, {summary['failed']} hata"
        )
        status = "partial" if summary.get("failed") else "completed"
        self.session.finish_run(status, {
            "summary": {k: summary[k] for k in ("total", "done", "skipped", "failed")},
            "stats": stats,
            "items": [
                {
                    "title": r.task.title,
                    "group": r.task.group,
                    "status": r.status,
                    "message": r.message,
                    "duration": round(r.duration, 2),
                }
                for r in summary["results"]
            ],
        })
        self.run_completed.emit(summary, stats)

    def cancel(self) -> None:
        if self.ctx:
            self.ctx.cancel_event.set()
            ps.cancel_all()
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("iptal ediliyor…")

    def plan(self) -> list[Task]:
        return []

    def collect(self) -> None:
        pass
