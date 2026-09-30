from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot,
)


class AlarmWorker(QObject):
    """Query bảng Slot Fail Alarm ngoài UI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
            self,
            database_path: Union[str, Path],
            date_from: str,
            date_to: str,
            # selected_models: list[str],
    ):
        super().__init__()

        self.database_path = Path(
            database_path
        )

        self.date_from = date_from
        self.date_to = date_to

        # self.selected_models = list(
        #     selected_models
        # )

    @pyqtSlot()
    def run(self) -> None:
        """Chạy query và trả DTO nhỏ về UI."""

        try:
            from repositories.alarm_repository import (
                AlarmRepository,
            )

            repository = AlarmRepository(
                self.database_path
            )

            result = repository.get_alarm_rows(
                date_from=self.date_from,
                date_to=self.date_to,
                # selected_models=self.selected_models,
            )

            self.succeeded.emit(result)

        except Exception as error:
            self.failed.emit(
                str(error).strip()
                or "Không thể tải dữ liệu Alarm."
            )