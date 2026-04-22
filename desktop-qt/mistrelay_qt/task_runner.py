from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class Worker(QRunnable):
    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self._fn = fn
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # pragma: no cover - UI thread relay
            self.signals.failed.emit(str(exc))
        else:  # pragma: no cover - UI thread relay
            self.signals.finished.emit(result)


class TaskRunner(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._workers: set[Worker] = set()

    def submit(
        self,
        fn: Callable[[], Any],
        *,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        worker = Worker(fn)
        self._workers.add(worker)

        def cleanup() -> None:
            self._workers.discard(worker)

        def success(result: Any) -> None:
            cleanup()
            if on_success:
                on_success(result)

        def failed(message: str) -> None:
            cleanup()
            if on_error:
                on_error(message)

        worker.signals.finished.connect(success)
        worker.signals.failed.connect(failed)
        self._pool.start(worker)
