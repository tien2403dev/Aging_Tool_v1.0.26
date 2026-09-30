from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot,
)


class YieldSlotWorker(QObject):
    """Chạy truy vấn Yield Slot ngoài UI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        database_path: Union[str, Path],
        date_from: str,
        date_to: str,
        eqp: str,
        chamber: int,
        tiers: list[str | None],
        selected_models: list[str] | None = None,
    ):
        super().__init__()

        self.database_path = Path(
            database_path
        )

        self.date_from = date_from
        self.date_to = date_to
        self.eqp = eqp
        self.chamber = chamber
        self.tiers = list(tiers)
        self.selected_models = list(
            selected_models or []
        )

    @pyqtSlot()
    def run(self) -> None:
        """Tải dữ liệu tổng hợp rồi trả về UI."""

        try:
            from repositories.yield_slot_repository import (
                YieldSlotRepository,
            )

            repository = YieldSlotRepository(
                self.database_path
            )

            result = (
                repository.get_yield_slot_page(
                    date_from=self.date_from,
                    date_to=self.date_to,
                    eqp=self.eqp,
                    chamber=self.chamber,
                    tiers=self.tiers,
                    selected_models=self.selected_models,
                )
            )

            self.succeeded.emit(result)

        except Exception as error:
            error_message = str(error).strip()

            self.failed.emit(
                error_message
                or (
                    "Không thể tải dữ liệu "
                    "tab Yield Slot."
                )
            )