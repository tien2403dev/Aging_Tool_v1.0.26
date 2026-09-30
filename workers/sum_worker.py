from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot,
)


class SumWorker(QObject):
    """
    Chạy truy vấn Tab Sum trong QThread để UI không bị treo.
    """

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
            self,
            database_path: Union[str, Path],
            date_from: str,
            date_to: str,
            eqpid: str | None,
            tiers: list[str | None],
            selected_scrap_codes: list[str],
            load_eqp_summary: bool,
            load_daily_summary: bool,
            load_prime_daily_summary: bool,
            load_missing_dates: bool,
            selected_models: list[str] | None = None,
    ):
        super().__init__()

        self.database_path = Path(database_path)
        self.date_from = date_from
        self.date_to = date_to
        self.eqpid = eqpid
        self.tiers = tiers

        self.selected_scrap_codes = (
            selected_scrap_codes
        )

        self.load_eqp_summary = (
            load_eqp_summary
        )

        self.load_daily_summary = (
            load_daily_summary
        )
        self.load_prime_daily_summary = (
            load_prime_daily_summary
        )

        self.load_missing_dates = (
            load_missing_dates
        )
        self.selected_models = list(
            selected_models or []
        )

    @pyqtSlot()
    def run(self) -> None:
        """Lấy dữ liệu tổng hợp CUM theo EQPID."""

        try:
            from repositories.sum_repository import (
                SumRepository,
            )

            repository = SumRepository(
                database_path=self.database_path
            )

            result = repository.get_sum_data(
                date_from=self.date_from,
                date_to=self.date_to,
                eqpid=self.eqpid,
                tiers=self.tiers,
                selected_models=self.selected_models,
                selected_scrap_codes=(
                    self.selected_scrap_codes
                ),
                load_eqp_summary=(
                    self.load_eqp_summary
                ),
                load_daily_summary=(
                    self.load_daily_summary
                ),
                load_prime_daily_summary=(
                    self.load_prime_daily_summary
                ),
                load_missing_dates=(
                    self.load_missing_dates
                ),
            )

            self.succeeded.emit(result)

        except Exception as error:
            error_message = str(error).strip()

            if not error_message:
                error_message = (
                    "Không thể tải dữ liệu Tab Sum."
                )

            self.failed.emit(error_message)
