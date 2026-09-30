# from __future__ import annotations
#
# from pathlib import Path
#
# from PyQt5.QtCore import (
#     QDate,
#     QSettings,
#     Qt,
# )
# from PyQt5.QtWidgets import (
#     QDateEdit,
#     QDialog,
#     QFileDialog,
#     QLabel,
#     QPushButton,
#     QVBoxLayout,
# )
#
#
# class PrimeLogImportDialog(QDialog):
#     """Chọn ngày import và folder Get_Result_History."""
#
#     SETTINGS_KEY = "prime_log_root_folder"
#
#     def __init__(
#         self,
#         parent=None,
#     ):
#         super().__init__(parent)
#
#         self._selected_folder: Path | None = None
#
#         self._settings = QSettings(
#             "AgingTool",
#             "AgingMonitoring",
#         )
#
#         self.setWindowTitle(
#             "Import Log"
#         )
#
#         self.setModal(True)
#
#         self.setFixedSize(
#             290,
#             230,
#         )
#
#         self._build_ui()
#
#     def _build_ui(
#         self,
#     ) -> None:
#         """Tạo giao diện chọn ngày và folder."""
#
#         layout = QVBoxLayout(self)
#
#         layout.setContentsMargins(
#             56,
#             28,
#             56,
#             28,
#         )
#
#         layout.setSpacing(14)
#
#         title_label = QLabel(
#             "Chọn ngày cần lấy log"
#         )
#
#         title_label.setAlignment(
#             Qt.AlignCenter
#         )
#
#         title_label.setStyleSheet(
#             """
#             font-size: 13px;
#             font-weight: 600;
#             color: #111827;
#             """
#         )
#
#         self.date_edit = QDateEdit()
#
#         self.date_edit.setCalendarPopup(
#             True
#         )
#
#         self.date_edit.setDisplayFormat(
#             "yyyy-MM-dd"
#         )
#
#         self.date_edit.setDate(
#             QDate.currentDate()
#         )
#
#         self.date_edit.setFixedHeight(32)
#
#         select_button = QPushButton(
#             "Select Folder"
#         )
#
#         select_button.setFixedHeight(32)
#
#         select_button.setStyleSheet(
#             """
#             QPushButton {
#                 color: white;
#                 background-color: #1976D2;
#                 border: none;
#                 border-radius: 5px;
#                 font-size: 12px;
#             }
#
#             QPushButton:hover {
#                 background-color: #42A5F5;
#             }
#
#             QPushButton:pressed {
#                 background-color: #0D47A1;
#             }
#             """
#         )
#
#         cancel_button = QPushButton(
#             "Cancel"
#         )
#
#         cancel_button.setFixedHeight(32)
#
#         cancel_button.setStyleSheet(
#             """
#             QPushButton {
#                 color: white;
#                 background-color: #D9343A;
#                 border: none;
#                 border-radius: 5px;
#                 font-size: 12px;
#             }
#
#             QPushButton:hover {
#                 background-color: #E05257;
#             }
#
#             QPushButton:pressed {
#                 background-color: #B91C1C;
#             }
#             """
#         )
#
#         layout.addWidget(
#             title_label
#         )
#
#         layout.addWidget(
#             self.date_edit
#         )
#
#         layout.addWidget(
#             select_button
#         )
#
#         layout.addWidget(
#             cancel_button
#         )
#
#         select_button.clicked.connect(
#             self._choose_root_folder
#         )
#
#         cancel_button.clicked.connect(
#             self.reject
#         )
#
#     def _choose_root_folder(
#         self,
#     ) -> None:
#         """Mở hộp thoại chọn Get_Result_History."""
#
#         initial_folder = self._settings.value(
#             self.SETTINGS_KEY,
#             "",
#             type=str,
#         )
#
#         folder_path = (
#             QFileDialog.getExistingDirectory(
#                 self,
#                 "Chọn folder Get_Result_History",
#                 initial_folder,
#                 QFileDialog.ShowDirsOnly,
#             )
#         )
#
#         if not folder_path:
#             return
#
#         self._selected_folder = Path(
#             folder_path
#         )
#
#         # Lần sau tự mở lại folder vừa chọn.
#         self._settings.setValue(
#             self.SETTINGS_KEY,
#             folder_path,
#         )
#
#         self.accept()
#
#     def selected_business_date(
#         self,
#     ) -> str:
#         """Trả ngày theo định dạng database YYYYMMDD."""
#
#         return self.date_edit.date().toString(
#             "yyyyMMdd"
#         )
#
#     def selected_folder(
#         self,
#     ) -> Path:
#         """Trả folder người dùng đã chọn."""
#
#         if self._selected_folder is None:
#             raise RuntimeError(
#                 "Chưa chọn folder log."
#             )
#
#         return self._selected_folder


from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import (
    QDate,
    QSettings,
    Qt,
)
from PyQt5.QtWidgets import (
    QDateEdit,
    QDialog,
    QFileDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class PrimeLogImportDialog(QDialog):
    """Chọn ngày import và folder gốc chứa log của tất cả máy."""

    SETTINGS_KEY = "prime_log_root_folder"

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self._selected_folder: Path | None = None

        self._settings = QSettings(
            "AgingTool",
            "AgingMonitoring",
        )

        self.setWindowTitle(
            "Import Log"
        )

        self.setModal(True)

        self.setFixedSize(
            290,
            230,
        )

        self._build_ui()

    def _build_ui(
        self,
    ) -> None:
        """Tạo giao diện chọn ngày và folder."""

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            56,
            28,
            56,
            28,
        )

        layout.setSpacing(14)

        title_label = QLabel(
            "Chọn ngày cần lấy log"
        )

        title_label.setAlignment(
            Qt.AlignCenter
        )

        title_label.setStyleSheet(
            """
            font-size: 13px;
            font-weight: 600;
            color: #111827;
            """
        )

        self.date_edit = QDateEdit()

        self.date_edit.setCalendarPopup(
            True
        )

        self.date_edit.setDisplayFormat(
            "yyyy-MM-dd"
        )

        self.date_edit.setDate(
            QDate.currentDate().addDays(-1)
        )

        self.date_edit.setFixedHeight(32)

        select_button = QPushButton(
            "Select Folder"
        )

        select_button.setFixedHeight(32)

        select_button.setStyleSheet(
            """
            QPushButton {
                color: white;
                background-color: #1976D2;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }

            QPushButton:hover {
                background-color: #42A5F5;
            }

            QPushButton:pressed {
                background-color: #0D47A1;
            }
            """
        )

        cancel_button = QPushButton(
            "Cancel"
        )

        cancel_button.setFixedHeight(32)

        cancel_button.setStyleSheet(
            """
            QPushButton {
                color: white;
                background-color: #D9343A;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }

            QPushButton:hover {
                background-color: #E05257;
            }

            QPushButton:pressed {
                background-color: #B91C1C;
            }
            """
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            self.date_edit
        )

        layout.addWidget(
            select_button
        )

        layout.addWidget(
            cancel_button
        )

        select_button.clicked.connect(
            self._choose_root_folder
        )

        cancel_button.clicked.connect(
            self.reject
        )

    def _choose_root_folder(
        self,
    ) -> None:
        """Mở hộp thoại chọn folder gốc chứa log của tất cả máy."""

        initial_folder = self._settings.value(
            self.SETTINGS_KEY,
            "",
            type=str,
        )

        folder_path = (
            QFileDialog.getExistingDirectory(
                self,
                "Chọn folder chứa log của tất cả máy",
                initial_folder,
                QFileDialog.ShowDirsOnly,
            )
        )

        if not folder_path:
            return

        self._selected_folder = Path(
            folder_path
        )

        # Lần sau tự mở lại folder vừa chọn.
        self._settings.setValue(
            self.SETTINGS_KEY,
            folder_path,
        )

        self.accept()

    def selected_business_date(
        self,
    ) -> str:
        """Trả ngày theo định dạng database YYYYMMDD."""

        return self.date_edit.date().toString(
            "yyyyMMdd"
        )

    def selected_folder(
        self,
    ) -> Path:
        """Trả folder người dùng đã chọn."""

        if self._selected_folder is None:
            raise RuntimeError(
                "Chưa chọn folder log."
            )

        return self._selected_folder
