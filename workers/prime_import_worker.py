from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot,
)


class PrimeImportWorker(QObject):
    """
    Chạy Import PRIME trong QThread.

    Không import openpyxl hoặc PrimeImportService tại lúc app khởi động.
    Các phần này chỉ được import trong run().
    """

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)


    def __init__(
            self,
            database_path: Union[str, Path],
            root_folder: Union[str, Path],
            business_date: str,
    ):
        super().__init__()

        self.database_path = Path(
            database_path
        )

        self.root_folder = Path(
            root_folder
        )

        self.business_date = business_date

    @pyqtSlot()
    def run(self) -> None:
        """
        Hàm này chạy trong worker thread, không block UI thread.
        """

        try:
            # Lazy import:
            # Service và openpyxl chỉ load khi user bấm Import.
            from services.prime_import_service import (
                PrimeImportService,
            )


            service = PrimeImportService(
                database_path=self.database_path
            )

            result = service.import_folder(
                root_folder=self.root_folder,
                business_date=self.business_date,
            )

            self.succeeded.emit(
                result
            )

        except Exception as error:
            error_message = str(error).strip()

            if not error_message:
                error_message = (
                    "Import PRIME thất bại do lỗi không xác định."
                )

            self.failed.emit(error_message)