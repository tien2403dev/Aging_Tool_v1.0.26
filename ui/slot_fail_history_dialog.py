from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt5.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QThread,
    Qt,
)
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
)

from workers.alarm_history_worker import (
    AlarmHistoryWorker,
)


class SlotFailHistoryTableModel(
    QAbstractTableModel
):
    """Model nhẹ cho bảng lịch sử FAIL."""

    HEADERS = [
        "DATE",
        "TIME",
        "MODEL",
        "LOTID",
        "SCRAP",
        "FAIL QTY",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []

    def rowCount(
        self,
        parent=QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0

        return len(self.rows)

    def columnCount(
        self,
        parent=QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0

        return len(self.HEADERS)

    def data(
        self,
        index,
        role=Qt.DisplayRole,
    ):
        if not index.isValid():
            return None

        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignCenter)

        if role != Qt.DisplayRole:
            return None

        row = self.rows[index.row()]

        values = (
            row.date,
            row.time,
            row.model,
            row.lotid,
            row.scrap,
            row.fail_qty,
        )

        return values[index.column()]

    def headerData(
        self,
        section,
        orientation,
        role=Qt.DisplayRole,
    ):
        if (
            role == Qt.DisplayRole
            and orientation == Qt.Horizontal
        ):
            return self.HEADERS[section]

        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignCenter)

        return None

    def set_rows(self, rows) -> None:
        self.beginResetModel()
        self.rows = list(rows)
        self.endResetModel()


class SlotFailHistoryDialog(QDialog):
    """Hiển thị lịch sử FAIL của một Slot."""

    def __init__(
        self,
        database_path: Union[str, Path],
        eqp: str,
        chamber: int,
        slot: int,
        parent=None,
    ):
        super().__init__(parent)

        self.database_path = Path(
            database_path
        )

        self.eqp = eqp
        self.chamber = chamber
        self.slot = slot

        self.history_thread = None
        self.history_worker = None

        self.setWindowTitle(
            "Slot Fail History: "
            f"EQP: {eqp} "
            f"CHAMBER: {chamber} "
            f"SLOT: {slot}"
        )

        self.resize(850, 520)

        self._build_ui()
        self._load_history()

    def _build_ui(self) -> None:
        """Tạo giao diện dialog."""

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        layout.setSpacing(10)

        self.status_label = QLabel(
            "Đang tải lịch sử FAIL..."
        )

        self.table_model = (
            SlotFailHistoryTableModel(self)
        )

        self.table = QTableView(self)

        self.table.setModel(
            self.table_model
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )

        self.table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.table.verticalHeader().setVisible(
            False
        )

        self.table.verticalHeader().setDefaultSectionSize(
            28
        )

        self.table.horizontalHeader().setFixedHeight(
            32
        )

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Fixed
        )

        widths = (
            105,
            90,
            100,
            190,
            120,
            85,
        )

        for column, width in enumerate(widths):
            self.table.setColumnWidth(
                column,
                width,
            )

        self.table.horizontalHeader().setStretchLastSection(
            True
        )

        self.table.setStyleSheet(
            """
            QTableView {
                gridline-color: #CBD5E1;
                border: 1px solid #94A3B8;
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                font-size: 12px;
            }

            QHeaderView::section {
                color: #1E293B;
                background-color: #E2E8F0;
                border: none;
                border-right: 1px solid #CBD5E1;
                border-bottom: 1px solid #94A3B8;
                font-weight: 600;
            }
            """
        )

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Close
        )

        # Tránh đóng dialog khi QThread còn chạy.
        self.button_box.setEnabled(False)

        self.button_box.rejected.connect(
            self.reject
        )

        layout.addWidget(
            self.status_label
        )

        layout.addWidget(
            self.table,
            1,
        )

        layout.addWidget(
            self.button_box
        )

    def _load_history(self) -> None:
        """Khởi chạy worker tải lịch sử."""

        self.history_thread = QThread(self)

        self.history_worker = (
            AlarmHistoryWorker(
                database_path=self.database_path,
                eqp=self.eqp,
                chamber=self.chamber,
                slot=self.slot,
            )
        )

        self.history_worker.moveToThread(
            self.history_thread
        )

        self.history_thread.started.connect(
            self.history_worker.run
        )

        self.history_worker.succeeded.connect(
            self._on_history_loaded
        )

        self.history_worker.failed.connect(
            self._on_history_failed
        )

        self.history_worker.succeeded.connect(
            self.history_thread.quit
        )

        self.history_worker.failed.connect(
            self.history_thread.quit
        )

        self.history_thread.finished.connect(
            self.history_worker.deleteLater
        )

        self.history_thread.finished.connect(
            self._on_history_thread_finished
        )

        self.history_thread.start()

    def _on_history_loaded(
        self,
        result,
    ) -> None:
        """Hiển thị lịch sử FAIL."""

        self.table_model.set_rows(
            result.rows
        )

        if result.rows:
            self.status_label.setText(
                "Tổng số dòng FAIL: "
                f"{len(result.rows):,}"
            )
        else:
            self.status_label.setText(
                "Không có lịch sử FAIL phù hợp."
            )

    def _on_history_failed(
        self,
        error_message: str,
    ) -> None:
        """Hiển thị lỗi query."""

        self.table_model.set_rows([])

        self.status_label.setText(
            "Không thể tải lịch sử FAIL: "
            f"{error_message}"
        )

    def _on_history_thread_finished(
        self,
    ) -> None:
        """Dọn worker và QThread."""

        if self.history_thread is not None:
            self.history_thread.deleteLater()

        self.history_thread = None
        self.history_worker = None

        self.button_box.setEnabled(True)

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        """Không đóng dialog khi worker còn chạy."""

        if (
            self.history_thread is not None
            and self.history_thread.isRunning()
        ):
            self.status_label.setText(
                "Đang tải dữ liệu, vui lòng chờ..."
            )

            event.ignore()
            return

        event.accept()