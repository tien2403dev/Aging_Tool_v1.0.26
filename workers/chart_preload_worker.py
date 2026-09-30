from __future__ import annotations

import importlib

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot,
)


class ChartPreloadWorker(QObject):
    """
    Import trước Matplotlib và các module chart
    sau khi giao diện chính đã hiển thị.

    Worker chỉ import module, không tạo QWidget,
    FigureCanvas hoặc đối tượng biểu đồ.
    """

    succeeded = pyqtSignal()
    failed = pyqtSignal(str)

    @pyqtSlot()
    def run(self) -> None:
        """Import các module chart bên ngoài UI thread."""

        try:
            importlib.import_module(
                "ui.charts.cum_eqp_chart"
            )

            importlib.import_module(
                "ui.charts.cum_daily_chart"
            )

            importlib.import_module(
                "ui.charts.prime_product_chart"
            )

            self.succeeded.emit()

        except Exception as error:
            error_message = str(error).strip()

            self.failed.emit(
                error_message
                or "Không thể tải thư viện biểu đồ."
            )