from __future__ import annotations

import traceback

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal

from repositories.alarm_repository import AlarmRepository


class AlarmTrackingSaveSignals(QObject):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)
    finished = pyqtSignal()


class AlarmTrackingSaveWorker(QRunnable):
    """Lưu toàn bộ thay đổi Alarm bằng một transaction."""

    def __init__(self, database_path, changes):
        super().__init__()
        self.database_path = database_path
        self.changes = list(changes or [])
        self.signals = AlarmTrackingSaveSignals()
        self.setAutoDelete(False)

    def run(self) -> None:
        try:
            result = AlarmRepository(
                self.database_path
            ).save_tracking_changes(
                self.changes
            )

            try:
                self.signals.succeeded.emit(result)
            except BaseException:
                pass

        except BaseException as error:
            try:
                traceback.print_exc()
            except BaseException:
                pass

            message = (
                str(error).strip()
                or type(error).__name__
            )

            try:
                self.signals.failed.emit(
                    f"Không thể lưu Alarm.\n\n"
                    f"{type(error).__name__}: {message}"
                )
            except BaseException:
                pass

        finally:
            try:
                self.signals.finished.emit()
            except BaseException:
                pass
