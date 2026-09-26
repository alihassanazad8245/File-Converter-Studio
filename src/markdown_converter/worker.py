"""Background conversion worker.

Wraps :mod:`.engine` in a ``QThread`` so PDF/DOCX generation (which can take
a noticeable moment on larger documents) never blocks the UI thread. This is
the only module that imports both Qt and the engine - keeping the engine
itself Qt-free means it stays trivially unit-testable.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from .engine import ConversionRequest, convert_batch
from .models import ConversionResult


class ConversionWorker(QObject):
    """Runs one or more conversion requests on a background thread."""

    progress = Signal(int, int, str)  # index, total, current_source_path
    finished = Signal(list)  # list[ConversionResult]
    failed = Signal(str)  # unexpected error message

    def __init__(self, requests: list[ConversionRequest], on_collision: str = "replace") -> None:
        super().__init__()
        self.requests = requests
        self.on_collision = on_collision

    def run(self) -> None:
        try:
            results: list[ConversionResult] = convert_batch(
                self.requests, on_collision=self.on_collision,
                progress_callback=lambda i, t, p: self.progress.emit(i, t, p),
            )
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001 - surface any unexpected failure to the UI
            self.failed.emit(str(exc))


class CallableWorker(QObject):
    """Runs one arbitrary zero-argument callable on a background thread.

    Used by the PDF and Image tool panels, whose actions (merge, compress,
    convert, ...) don't share the batch-conversion engine's signature but
    still deserve the same "never freeze the UI" treatment.
    """

    succeeded = Signal(object)  # whatever the callable returned
    failed = Signal(str)

    def __init__(self, func) -> None:
        super().__init__()
        self._func = func

    def run(self) -> None:
        try:
            result = self._func()
            self.succeeded.emit(result)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self.failed.emit(str(exc))


def run_callable_in_background(func, on_succeeded, on_failed) -> tuple[QThread, "CallableWorker"]:
    """Run ``func()`` on a background thread; returns ``(thread, worker)`` -
    the caller must keep both alive until a signal fires."""
    thread = QThread()
    worker = CallableWorker(func)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.succeeded.connect(on_succeeded)
    worker.failed.connect(on_failed)
    worker.succeeded.connect(thread.quit)
    worker.failed.connect(thread.quit)
    worker.succeeded.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread, worker


def run_conversion_in_background(
    requests: list[ConversionRequest], on_collision: str,
    on_progress, on_finished, on_failed,
) -> tuple[QThread, ConversionWorker]:
    """Start a conversion on a background thread and wire up its signals.

    Returns ``(thread, worker)`` - the caller must keep both alive (e.g. as
    attributes on the main window) until ``finished``/``failed`` fires, or
    Qt will garbage-collect the thread mid-run.
    """
    thread = QThread()
    worker = ConversionWorker(requests, on_collision)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.progress.connect(on_progress)
    worker.finished.connect(on_finished)
    worker.failed.connect(on_failed)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread, worker
