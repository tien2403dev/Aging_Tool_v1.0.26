from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot,
)


class YieldEqpWorker(QObject):
    """Chạy truy vấn Yield EQP ngoài UI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
            self,
            database_path: Union[str, Path],
            date_from: str,
            date_to: str,
            tiers: list[str | None],
            selected_scrap_codes: list[str],
            selected_models: list[str],
    ):
        super().__init__()

        self.database_path = Path(
            database_path
        )

        self.date_from = date_from
        self.date_to = date_to
        self.tiers = list(tiers)

        self.selected_scrap_codes = list(
            selected_scrap_codes
        )
        self.selected_models = list(
            selected_models
        )

    @pyqtSlot()
    def run(self) -> None:
        """Tải PRIME và CUM rồi trả kết quả về UI."""

        try:
            from repositories.yield_eqp_repository import (
                YieldEqpRepository,
            )

            repository = YieldEqpRepository(
                self.database_path
            )

            result = repository.get_yield_eqp_data(
                date_from=self.date_from,
                date_to=self.date_to,
                tiers=self.tiers,
                selected_scrap_codes=(
                    self.selected_scrap_codes
                ),
                selected_models=(
                    self.selected_models
                ),
            )

            self.succeeded.emit(result)

        except Exception as error:
            error_message = str(error).strip()

            self.failed.emit(
                error_message
                or (
                    "Không thể tải dữ liệu "
                    "tab Yield EQP."
                )
            )