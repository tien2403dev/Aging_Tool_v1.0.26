from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot,
)


class FilterOptionWorker(QObject):
    """
    Đọc option filter trong QThread để không block UI.
    """

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        """Lưu đường dẫn database cần đọc option filter."""

        super().__init__()

        self.database_path = Path(database_path)

    @pyqtSlot()
    def run(self) -> None:
        """Đọc cache filter và gửi kết quả về UI thread."""

        try:
            # Chỉ import repository khi worker thực sự chạy.
            from repositories.filter_option_repository import (
                FilterOptionRepository,
            )

            repository = FilterOptionRepository(
                database_path=self.database_path
            )

            result = repository.load_options()

            self.succeeded.emit(result)

        except Exception as error:
            error_message = str(error).strip()

            if not error_message:
                error_message = (
                    "Không thể tải dữ liệu bộ lọc."
                )

            self.failed.emit(error_message)