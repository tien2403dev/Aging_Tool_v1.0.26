from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot,
)


class CumImportWorker(QObject):
    """
    Chạy Import CUM trong QThread.

    CumImportService và openpyxl chỉ được import
    khi user thực sự bấm Import CUM.
    """

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        database_path: Union[str, Path],
        excel_path: Union[str, Path],
    ):
        super().__init__()

        self.database_path = Path(database_path)
        self.excel_path = Path(excel_path)

    @pyqtSlot()
    def run(self) -> None:
        try:
            # Lazy import để app khởi động nhanh.
            from services.cum_import_service import (
                CumImportService,
            )

            service = CumImportService(
                database_path=self.database_path
            )

            result = service.import_file(
                excel_path=self.excel_path
            )

            self.succeeded.emit(result)

        except Exception as error:
            error_message = str(error).strip()

            if not error_message:
                error_message = (
                    "Import CUM thất bại do lỗi không xác định."
                )

            self.failed.emit(error_message)