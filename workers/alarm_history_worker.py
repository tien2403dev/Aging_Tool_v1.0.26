from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot,
)


class AlarmHistoryWorker(QObject):
    """Query lịch sử FAIL của Slot ngoài UI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        database_path: Union[str, Path],
        eqp: str,
        chamber: int,
        slot: int,
    ):
        super().__init__()

        self.database_path = Path(
            database_path
        )

        self.eqp = eqp
        self.chamber = chamber
        self.slot = slot

    @pyqtSlot()
    def run(self) -> None:
        """Tải lịch sử FAIL và trả về dialog."""

        try:
            from repositories.alarm_repository import (
                AlarmRepository,
            )

            repository = AlarmRepository(
                self.database_path
            )

            result = (
                repository.get_slot_fail_history(
                    eqp=self.eqp,
                    chamber=self.chamber,
                    slot=self.slot,
                )
            )

            self.succeeded.emit(result)

        except Exception as error:
            self.failed.emit(
                str(error).strip()
                or (
                    "Không thể tải lịch sử "
                    "FAIL của Slot."
                )
            )