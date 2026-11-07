"""Görev motoru: adımların ürettiği işleri sırayla, izole ve iptal edilebilir çalıştırır."""
from __future__ import annotations

import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Callable

from . import logger, ps

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"


@dataclass
class TaskContext:
    dry_run: bool = False
    cancel_event: threading.Event = field(default_factory=threading.Event)
    on_progress: Callable[[str, float], None] | None = None
    on_log: Callable[[str], None] | None = None
    results: dict = field(default_factory=dict)

    def log(self, message: str) -> None:
        logger.info(message)
        if self.on_log:
            try:
                self.on_log(message)
            except Exception:
                pass

    def warn(self, message: str) -> None:
        logger.warn(message)
        if self.on_log:
            try:
                self.on_log("⚠ " + message)
            except Exception:
                pass

    def progress(self, key: str, fraction: float) -> None:
        if self.on_progress:
            try:
                self.on_progress(key, max(0.0, min(1.0, fraction)))
            except Exception:
                pass

    def check_cancel(self) -> None:
        if self.cancel_event.is_set():
            raise ps.Cancelled("Kullanıcı iptal etti")

    def add(self, key: str, value) -> None:
        self.results[key] = self.results.get(key, 0) + value if isinstance(value, (int, float)) else value


@dataclass
class Task:
    key: str
    group: str
    title: str
    fn: Callable[[TaskContext], None]
    weight: float = 1.0
    optional: bool = False


@dataclass
class TaskResult:
    task: Task
    status: str
    message: str = ""
    detail: str = ""
    started: float = 0.0
    duration: float = 0.0


class TaskEngine:
    """Görevleri sırayla çalıştırır; hata bir sonrakini durdurmaz."""

    def __init__(self, tasks: list[Task], context: TaskContext | None = None):
        self.tasks = tasks
        self.ctx = context or TaskContext()
        self.results: list[TaskResult] = []
        self._index = 0

    # ---------------------------------------------------------------- public
    def run(self, on_task_start=None, on_task_finish=None, on_progress=None) -> list[TaskResult]:
        total_weight = sum(t.weight for t in self.tasks) or 1.0
        done_weight = 0.0

        for index, task in enumerate(self.tasks):
            if self.ctx.cancel_event.is_set():
                self.results.append(TaskResult(task, STATUS_SKIPPED, "İptal edildi"))
                continue

            self._index = index
            if on_task_start:
                on_task_start(index, task)
            started = time.time()
            result: TaskResult
            try:
                self.ctx.log(f"▶ {task.title}")
                task.fn(self.ctx)
                result = TaskResult(task, STATUS_DONE)
            except ps.Cancelled:
                result = TaskResult(task, STATUS_SKIPPED, "İptal edildi")
            except Exception as exc:  # noqa: BLE001
                detail = traceback.format_exc(limit=4)
                logger.error(f"Görev başarısız '{task.title}': {exc}\n{detail}")
                result = TaskResult(task, STATUS_FAILED, str(exc), detail)
            result.started = started
            result.duration = time.time() - started
            self.results.append(result)

            done_weight += task.weight
            if on_progress:
                on_progress(done_weight / total_weight)
            if on_task_finish:
                on_task_finish(index, result)

        return self.results

    # -------------------------------------------------------------- summary
    def summary(self) -> dict:
        counts = {STATUS_DONE: 0, STATUS_SKIPPED: 0, STATUS_FAILED: 0}
        for r in self.results:
            counts[r.status] = counts.get(r.status, 0) + 1
        return {
            "total": len(self.results),
            "done": counts.get(STATUS_DONE, 0),
            "skipped": counts.get(STATUS_SKIPPED, 0),
            "failed": counts.get(STATUS_FAILED, 0),
            "results": self.results,
        }
