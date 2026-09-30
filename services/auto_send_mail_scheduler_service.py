from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QObject, QThreadPool, QTimer, pyqtSignal

from repositories.auto_send_mail_scheduler_repository import AutoSendMailSchedulerRepository
from workers.auto_send_mail_hourly_worker import AutoSendMailHourlyWorker


class AutoSendMailSchedulerService(QObject):
    """
    Tự động kiểm tra Alarm theo thời gian thực trong PGM.

    Khi Enable Auto Send Mail = ON:
        - kiểm tra mỗi 5 phút;
        - cập nhật Machine Slot Yield Alarm;
        - gửi ngay các Alarm mới chưa từng gửi;
        - không phụ thuộc Send Time;
        - Mail History / mail_slot_send_history chống gửi lặp.
    """

    status_changed = pyqtSignal(str)
    CHECK_INTERVAL_MS = 5 * 60 * 1000

    def __init__(self, database_path: str | Path, parent=None):
        super().__init__(parent)
        self.database_path = Path(database_path)
        self.repository = AutoSendMailSchedulerRepository(self.database_path)
        self._timer = QTimer(self)
        self._timer.setInterval(self.CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self._check_schedule)
        self._running = False
        self._worker = None

    def start(self) -> None:
        if self._timer.isActive():
            return
        self._timer.start()
        self._check_schedule()

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()

    def _check_schedule(self) -> None:
        if self._running:
            return

        try:
            config = self.repository.get_config()
        except Exception as error:
            self.status_changed.emit(f"Không đọc được Auto Send Mail: {error}")
            return

        if not config.enabled:
            return

        self._running = True
        self.status_changed.emit("Auto Send Mail: kiểm tra Alarm mới...")

        try:
            worker = AutoSendMailHourlyWorker(self.database_path)
            self._worker = worker
            worker.signals.succeeded.connect(self._on_succeeded)
            worker.signals.skipped.connect(self._on_skipped)
            worker.signals.failed.connect(self._on_failed)
            worker.signals.finished.connect(self._on_finished)
            QThreadPool.globalInstance().start(worker)
        except BaseException as error:
            self._running = False
            self._worker = None
            self.status_changed.emit(
                f"Auto Send Mail khởi động lỗi: {type(error).__name__}: {error}"
            )

    def _on_succeeded(self, result) -> None:
        self.status_changed.emit(
            "Auto Send Mail thành công | "
            f"Số Alarm: {getattr(result, 'sent_slot_count', 0)}"
        )

    def _on_skipped(self, message: str) -> None:
        self.status_changed.emit(f"Auto Send Mail: {message}")

    def _on_failed(self, message: str) -> None:
        self.status_changed.emit(f"Auto Send Mail lỗi: {message}")

    def _on_finished(self) -> None:
        self._running = False
        self._worker = None
