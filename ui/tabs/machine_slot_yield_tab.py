
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PyQt5.QtCore import (
    QThread,
    Qt,
    QObject,
    pyqtSignal,
    pyqtSlot,
)

from PyQt5.QtGui import QColor

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDialog,
    QLineEdit,
    QDoubleSpinBox,
)

from repositories.auto_import_scheduler_repository import (
    AutoImportSchedulerRepository,
)

from repositories.machine_slot_yield_repository import (
    MachineSlotYieldRepository,
    MachineSlotResult,
)

from repositories.alarm_repository import (
    AlarmRepository,
)


# ================================================================
# MACHINE SLOT HISTORY DIALOG
# ================================================================


class MachineSlotHistoryDialog(QDialog):

    def __init__(
        self,
        machine: str,
        slot: int,
        records,
        parent=None,
        *,
        date_from: str = "",
        date_to: str = "",
        fail_comment: str = "-",
    ):

        super().__init__(parent)

        def display_date(value):
            text = str(value)
            return f"{text[:4]}-{text[4:6]}-{text[6:]}" if len(text) == 8 else text

        history_range = (
            f"Test History From {display_date(date_from)} "
            f"- To {display_date(date_to)}"
        )
        self.setWindowTitle(
            f"{history_range} | {machine} | Slot {slot}"
        )

        self.resize(
            1050,
            600,
        )

        layout = QVBoxLayout(self)

        title = QLabel(
            f"<b>Machine:</b> {machine} "
            f"&nbsp;&nbsp; "
            f"<b>Slot:</b> {slot} "
            f"&nbsp;&nbsp; "
            f"<b>Total:</b> {len(records)} tests"
        )

        layout.addWidget(title)
        layout.addWidget(QLabel(history_range))

        comment_label = QLabel(f"Fail comment: {fail_comment or '-'}")
        comment_label.setTextFormat(Qt.PlainText)
        comment_label.setWordWrap(True)
        comment_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(comment_label)

        table = QTableWidget(
            0,
            8,
        )

        table.setHorizontalHeaderLabels(
            [
                "Date",
                "Time",
                "Result",
                "Part No",
                "Lot No",
                "Interface",
                "Scrap Code",
                "File",
            ]
        )

        table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        table.setAlternatingRowColors(True)

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        table.horizontalHeader().setStretchLastSection(
            True
        )

        # Mới nhất trước
        sorted_records = sorted(
            records,
            key=lambda r: (
                str(getattr(r, "date", "")),
                str(getattr(r, "time", "")),
                str(getattr(r, "file_name", "")),
            ),
            reverse=True,
        )

        for r in sorted_records:

            row = table.rowCount()

            table.insertRow(row)

            values = [
                r.date,
                r.time,
                r.result,
                r.partno,
                r.lotno,
                r.interface,
                r.scrapcode,
                r.file_name,
            ]

            for col, value in enumerate(values):

                item = QTableWidgetItem(
                    str(value)
                )

                item.setTextAlignment(
                    Qt.AlignCenter | Qt.AlignVCenter
                )

                if col == 2:

                    if str(r.result).upper() == "PASS":

                        item.setForeground(
                            QColor("#15803D")
                        )

                    else:

                        item.setForeground(
                            QColor("#DC2626")
                        )

                table.setItem(
                    row,
                    col,
                    item,
                )

        layout.addWidget(table)

        close_button = QPushButton(
            "Close"
        )

        close_button.clicked.connect(
            self.accept
        )

        layout.addWidget(
            close_button,
            0,
            Qt.AlignRight,
        )


# ================================================================
# MACHINE SLOT YIELD TAB
# ================================================================


class MachineSlotYieldTab(QWidget):

    """
    Machine Slot Yield

    From Date / To Date được quản lý tập trung
    tại MainWindow.FilterPanel.

    MainWindow gọi:

        load_data(
            date_from,
            date_to,
        )

    Trong tab này chỉ còn:

        - Log Folder
        - Target 15
        - Target 30
        - Machine
        - Slot
        - Chỉ hiện Alarm
        - Export Excel

    Không có Date Picker hoặc Search riêng.

    Alarm:

        - FAIL 2 lần liên tiếp trong 5 ngày gần nhất.
        - Không phân biệt cùng Model hay khác Model.
        - Last 15/30 Yield vẫn hiển thị để tham khảo,
          không còn là điều kiện tạo Alarm.

    Sau khi Machine Slot Yield load và calculate xong,
    kết quả Alarm sẽ được đồng bộ vào SQLite.

    TAB Alarm không cần đọc TXT lại.
    """

    # ------------------------------------------------------------
    # SIGNAL
    #
    # load_finished:
    #   Machine Slot Yield đã:
    #       1. đọc TXT
    #       2. calculate
    #       3. render
    #       4. sync Alarm vào DB
    #
    #   MainWindow dùng signal này để biết lúc nào có thể
    #   chạy AlarmWorker.
    #
    # load_failed:
    #   Chuẩn bị dữ liệu Machine Slot Yield thất bại.
    # ------------------------------------------------------------

    load_finished = pyqtSignal(object)

    load_failed = pyqtSignal(str)

    HEADERS = [
        "No",
        "Machine",
        "Slot",
        "Total Test",
        "PASS",
        "FAIL",
        "YEILD",
        "Fail comment",
        "Lần 1",
        "Lần 2",
        "Lần 3",
        "Lần 4",
        "Lần 5",
        "Lần 6",
        "Lần 7",
        "Lần 8",
        "Lần 9",
        "Lần 10",
    ]

    DAILY_HEADERS = [
        "Machine",
        "Date",
        "Slot",
        "Test",
        "Pass",
        "Fail",
        "Yield",
    ]

    def __init__(
        self,
        database_path,
        parent=None,
    ):

        super().__init__(parent)

        self.database_path = Path(
            database_path
        )

        # --------------------------------------------------------
        # MACHINE SLOT YIELD REPOSITORY
        # --------------------------------------------------------

        self.repository = (
            MachineSlotYieldRepository(
                self.database_path.parent
                / "machine_slot_targets.json"
            )
        )

        # --------------------------------------------------------
        # ALARM REPOSITORY
        # --------------------------------------------------------

        self.alarm_repository = (
            AlarmRepository(
                self.database_path
            )
        )

        self.thread = None

        self.worker = None

        self.current_result: (
            MachineSlotResult | None
        ) = None

        self._all_slot_rows = []

        self.current_date_from = None
        self.current_date_to = None

        self._build_ui()

        self._load_log_folder()

        self._load_targets_to_ui()

        self.export_button.setEnabled(False)

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):

        root = QVBoxLayout(self)

        root.setContentsMargins(
            10,
            10,
            10,
            10,
        )

        root.setSpacing(8)

        # --------------------------------------------------------
        # TITLE
        # --------------------------------------------------------

        title = QLabel(
            "Machine Slot Yield"
        )

        title.setStyleSheet(
            "font-size: 16px; "
            "font-weight: bold;"
        )

        root.addWidget(title)

        # --------------------------------------------------------
        # LOG FOLDER
        # --------------------------------------------------------

        folder_layout = QHBoxLayout()

        folder_layout.setSpacing(8)

        folder_layout.addWidget(
            QLabel("<b>Log Folder:</b>")
        )

        self.folder_edit = QLineEdit()

        self.folder_edit.setReadOnly(True)

        self.folder_edit.setMinimumWidth(450)

        self.folder_edit.setToolTip(
            "Log Folder riêng của Machine Slot Yield"
        )

        folder_layout.addWidget(
            self.folder_edit,
            1,
        )

        self.select_folder_button = QPushButton(
            "📁 Select"
        )

        self.select_folder_button.clicked.connect(
            self._select_folder
        )

        folder_layout.addWidget(
            self.select_folder_button
        )

        self.save_folder_button = QPushButton(
            "💾 Save Folder"
        )

        self.save_folder_button.clicked.connect(
            self._save_log_folder
        )

        folder_layout.addWidget(
            self.save_folder_button
        )

        root.addLayout(
            folder_layout
        )

        # --------------------------------------------------------
        # TARGET
        # --------------------------------------------------------

        target_layout = QHBoxLayout()

        target_layout.setSpacing(8)

        target_layout.addWidget(
            QLabel("<b>Target 15:</b>")
        )

        self.target15_spin = QDoubleSpinBox()

        self.target15_spin.setRange(
            0.0,
            100.0,
        )

        self.target15_spin.setDecimals(2)

        self.target15_spin.setSuffix(" %")

        self.target15_spin.setSingleStep(0.5)

        self.target15_spin.setMinimumWidth(100)

        target_layout.addWidget(
            self.target15_spin
        )

        target_layout.addWidget(
            QLabel("<b>Target 30:</b>")
        )

        self.target30_spin = QDoubleSpinBox()

        self.target30_spin.setRange(
            0.0,
            100.0,
        )

        self.target30_spin.setDecimals(2)

        self.target30_spin.setSuffix(" %")

        self.target30_spin.setSingleStep(0.5)

        self.target30_spin.setMinimumWidth(100)

        target_layout.addWidget(
            self.target30_spin
        )

        for attribute, label in (("target15_model_spin", "Target 15 cùng Model:"),
                                 ("target30_model_spin", "Target 30 cùng Model:")):
            target_layout.addWidget(QLabel(f"<b>{label}</b>"))
            spin = QDoubleSpinBox()
            spin.setRange(0, 100)
            spin.setDecimals(2)
            spin.setSuffix(" %")
            spin.setSingleStep(0.5)
            spin.setMinimumWidth(100)
            setattr(self, attribute, spin)
            target_layout.addWidget(spin)

        self.save_target_button = QPushButton(
            "💾 Save Target"
        )

        self.save_target_button.clicked.connect(
            self._save_targets
        )

        target_layout.addWidget(
            self.save_target_button
        )

        target_layout.addStretch()

        root.addLayout(
            target_layout
        )

        # --------------------------------------------------------
        # MACHINE / SLOT / ALARM / EXPORT
        # --------------------------------------------------------

        filter_layout = QHBoxLayout()

        filter_layout.setSpacing(8)

        filter_layout.addWidget(
            QLabel("Machine:")
        )

        self.machine_combo = QComboBox()

        self.machine_combo.addItem("ALL")

        self.machine_combo.setMinimumWidth(150)

        filter_layout.addWidget(
            self.machine_combo
        )

        filter_layout.addWidget(
            QLabel("Slot:")
        )

        self.slot_combo = QComboBox()

        self.slot_combo.addItem("ALL")

        self.slot_combo.setMinimumWidth(100)

        filter_layout.addWidget(
            self.slot_combo
        )

        self.alarm_only_check = QCheckBox(
            "🔴 Chỉ hiện Alarm"
        )

        self.alarm_only_check.setToolTip(
            "Chỉ hiển thị những dòng đang Alarm"
        )

        filter_layout.addWidget(
            self.alarm_only_check
        )

        # --------------------------------------------------------
        # EXPORT
        # --------------------------------------------------------

        self.export_button = QPushButton(
            "📊 Export Excel"
        )

        self.export_button.setEnabled(False)

        self.export_button.setToolTip(
            "Export Machine Slot Yield ra Excel"
        )

        self.export_button.clicked.connect(
            self._export_excel
        )

        filter_layout.addWidget(
            self.export_button
        )

        filter_layout.addStretch()

        root.addLayout(
            filter_layout
        )

        # --------------------------------------------------------
        # SHARED DATE STATUS
        # --------------------------------------------------------

        self.date_range_label = QLabel(
            "Khoảng ngày: Chưa chọn"
        )

        self.date_range_label.setStyleSheet(
            "color: #2563EB; "
            "font-weight: bold;"
        )

        root.addWidget(
            self.date_range_label
        )

        # --------------------------------------------------------
        # STATUS
        # --------------------------------------------------------

        self.status_label = QLabel(
            "Chọn khoảng ngày tại FilterPanel "
            "ở MainWindow rồi bấm Search."
        )

        self.status_label.setStyleSheet(
            "color: #64748B;"
        )

        root.addWidget(
            self.status_label
        )

        self.summary_label = QLabel("")

        root.addWidget(
            self.summary_label
        )

        # --------------------------------------------------------
        # SUMMARY
        # --------------------------------------------------------

        root.addWidget(
            QLabel(
                "<b>Machine / Slot Summary</b>"
            )
        )

        self.summary_table = QTableWidget(
            0,
            len(self.HEADERS),
        )

        self.summary_table.verticalHeader().setVisible(
            False
        )

        self.summary_table.setHorizontalHeaderLabels(
            self.HEADERS
        )

        self.summary_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.summary_table.setAlternatingRowColors(True)

        self.summary_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.summary_table.setWordWrap(False)
        self.summary_table.setTextElideMode(Qt.ElideRight)

        self.summary_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        header = self.summary_table.horizontalHeader()

        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #1E3A5F;
                color: white;
                font-weight: bold;
                font-size: 10pt;
                border: 1px solid #CBD5E1;
                padding: 6px;
            }

            QHeaderView::section:hover {
                background-color: #274C77;
            }
        """)

        header.setDefaultAlignment(
            Qt.AlignCenter
        )

        self.summary_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #CBD5E1;
                border: 1px solid #94A3B8;
                selection-background-color: #BFDBFE;
                selection-color: #1E293B;
            }

            QTableWidget::item {
                padding: 4px;
            }
        """)

        header.setFixedHeight(38)

        self.summary_table.setColumnWidth(0, 50)
        self.summary_table.setColumnWidth(1, 120)
        self.summary_table.setColumnWidth(2, 60)
        self.summary_table.setColumnWidth(3, 80)
        self.summary_table.setColumnWidth(4, 65)
        self.summary_table.setColumnWidth(5, 65)
        self.summary_table.setColumnWidth(6, 75)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.summary_table.setColumnWidth(7, 180)

        for col in range(8, 18):

            self.summary_table.setColumnWidth(
                col,
                75,
            )

        self.summary_table.verticalHeader().setDefaultSectionSize(
            46
        )

        self.summary_table.verticalHeader().setSectionResizeMode(
            QHeaderView.Fixed
        )

        self.summary_table.horizontalHeader().setStretchLastSection(
            False
        )

        self.summary_table.cellClicked.connect(self._show_fail_comment)

        self.summary_table.cellDoubleClicked.connect(
            self._summary_double_click
        )

        root.addWidget(
            self.summary_table,
            4,
        )

        # --------------------------------------------------------
        # DAILY
        # --------------------------------------------------------

        root.addWidget(
            QLabel(
                "<b>Daily Machine / Slot</b>"
            )
        )

        self.daily_table = QTableWidget(
            0,
            len(self.DAILY_HEADERS),
        )

        self.daily_table.setHorizontalHeaderLabels(
            self.DAILY_HEADERS
        )

        self.daily_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.daily_table.setAlternatingRowColors(True)

        self.daily_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        root.addWidget(
            self.daily_table,
            2,
        )

        # --------------------------------------------------------
        # FILTER SIGNAL
        # --------------------------------------------------------

        self.machine_combo.currentIndexChanged.connect(
            self._machine_filter_changed
        )

        self.slot_combo.currentIndexChanged.connect(
            self._apply_slot_filters
        )

        self.alarm_only_check.stateChanged.connect(
            self._apply_slot_filters
        )

    # ============================================================
    # PUBLIC LOAD DATA
    # ============================================================

    def load_data(
        self,
        date_from: str,
        date_to: str,
    ):

        date_from = self._normalize_shared_date(
            date_from
        )

        date_to = self._normalize_shared_date(
            date_to
        )

        if not date_from or not date_to:

            self._clear_result()

            message = (
                "Chưa có khoảng ngày hợp lệ."
            )

            self.status_label.setText(
                message
            )

            self.load_failed.emit(
                message
            )

            return

        # --------------------------------------------------------
        # FROM <= TO
        # --------------------------------------------------------

        if date_from > date_to:

            self._clear_result()

            message = (
                "Ngày From không được lớn hơn ngày To."
            )

            self.status_label.setText(
                message
            )

            self.load_failed.emit(
                message
            )

            return

        # --------------------------------------------------------
        # LOG FOLDER
        # --------------------------------------------------------

        log_folder = (
            self.folder_edit.text().strip()
        )

        if not log_folder:

            self._clear_result()

            message = (
                "Chưa có Log Folder."
            )

            self.status_label.setText(
                message
            )

            self.load_failed.emit(
                message
            )

            return

        folder = Path(log_folder)

        if not folder.is_dir():

            self._clear_result()

            message = (
                f"Log Folder không tồn tại:\n{folder}"
            )

            self.status_label.setText(
                message
            )

            self.load_failed.emit(
                message
            )

            return

        # --------------------------------------------------------
        # SAVE DATE
        # --------------------------------------------------------

        self.current_date_from = date_from
        self.current_date_to = date_to

        self.date_range_label.setText(
            "Khoảng ngày: "
            f"{self._format_date_range(date_from)}"
            "  →  "
            f"{self._format_date_range(date_to)}"
        )

        # --------------------------------------------------------
        # MACHINE
        # --------------------------------------------------------

        machine = self.machine_combo.currentText()

        if machine == "ALL":

            machine = None

        # --------------------------------------------------------
        # CHECK WORKER
        # --------------------------------------------------------

        if self.thread is not None:

            try:

                if self.thread.isRunning():

                    self.status_label.setText(
                        "Machine Slot Yield đang tải dữ liệu..."
                    )

                    return

            except RuntimeError:

                self.thread = None
                self.worker = None

        # --------------------------------------------------------
        # BUSY
        # --------------------------------------------------------

        self._set_busy(True)

        self.status_label.setText(
            "Đang đọc Log Folder "
            "theo khoảng ngày chung..."
        )

        # --------------------------------------------------------
        # THREAD
        # --------------------------------------------------------

        self.thread = QThread(self)

        self.worker = _MachineSlotWorker(
            self.repository,
            log_folder,
            date_from,
            date_to,
            machine,
            None,
            self.database_path,
            (self.target15_spin.value(), self.target30_spin.value(),
             self.target15_model_spin.value(), self.target30_model_spin.value()),
        )

        self.worker.moveToThread(
            self.thread
        )

        self.thread.started.connect(
            self.worker.run
        )

        self.worker.succeeded.connect(
            self._search_succeeded
        )

        self.worker.failed.connect(
            self._search_failed
        )

        self.worker.succeeded.connect(
            self.thread.quit
        )

        self.worker.failed.connect(
            self.thread.quit
        )

        self.thread.finished.connect(
            self._thread_finished
        )

        self.thread.start()

    # ============================================================
    # NORMALIZE SHARED DATE
    # ============================================================

    @staticmethod
    def _normalize_shared_date(value):

        text = str(value or "").strip()

        if not text:
            return ""

        if (
            len(text) == 10
            and text[4] == "-"
            and text[7] == "-"
        ):

            parts = text.split("-")

            if (
                len(parts) == 3
                and all(
                    part.isdigit()
                    for part in parts
                )
                and len(parts[0]) == 4
                and len(parts[1]) == 2
                and len(parts[2]) == 2
            ):

                return (
                    parts[0]
                    + parts[1]
                    + parts[2]
                )

        if (
            len(text) == 10
            and text[4] == "/"
            and text[7] == "/"
        ):

            parts = text.split("/")

            if (
                len(parts) == 3
                and all(
                    part.isdigit()
                    for part in parts
                )
                and len(parts[0]) == 4
                and len(parts[1]) == 2
                and len(parts[2]) == 2
            ):

                return (
                    parts[0]
                    + parts[1]
                    + parts[2]
                )

        if (
            len(text) == 8
            and text.isdigit()
        ):

            return text

        return ""

    # ============================================================
    # CLEAR RESULT
    # ============================================================

    def _clear_result(self):

        self.current_result = None

        self._all_slot_rows = []

        self.summary_table.setRowCount(0)

        self.daily_table.setRowCount(0)

        self.summary_label.setText("")

        self.export_button.setEnabled(False)

    # ============================================================
    # FORMAT SHARED DATE
    # ============================================================

    @staticmethod
    def _format_date_range(value):

        text = str(value or "").strip()

        if (
            len(text) == 8
            and text.isdigit()
        ):

            return (
                f"{text[0:4]}-"
                f"{text[4:6]}-"
                f"{text[6:8]}"
            )

        return text

    # ============================================================
    # MACHINE FILTER CHANGED
    # ============================================================

    def _machine_filter_changed(self):

        self._update_slot_combo_for_machine()

        self._apply_slot_filters()

    # ============================================================
    # TARGET
    # ============================================================

    def _load_targets_to_ui(self):
        for spin, value in zip((self.target15_spin, self.target30_spin,
                                self.target15_model_spin, self.target30_model_spin),
                               self.repository.load_all_targets()):
            spin.setValue(value)

    def _save_targets(self):
        try:
            self.repository.save_targets(self.target15_spin.value(), self.target30_spin.value(),
                                         self.target15_model_spin.value(), self.target30_model_spin.value())
            self.status_label.setText("Đã lưu 4 Target. Đang cập nhật Alarm theo log mới nhất.")
            if self.current_date_from and self.current_date_to:
                self.load_data(self.current_date_from, self.current_date_to)
        except Exception as error:
            QMessageBox.warning(self, "Lỗi lưu Target", str(error))

    # ============================================================
    # LOG FOLDER
    # ============================================================

    def _load_log_folder(self):

        try:

            saved_folder = (
                self.repository.load_log_folder()
            )

            if saved_folder:

                self.folder_edit.setText(
                    saved_folder
                )

                self._load_machines()

                self.status_label.setText(
                    "Đang sử dụng Log Folder riêng "
                    "đã lưu cho Machine Slot Yield."
                )

                return

            config = (
                AutoImportSchedulerRepository(
                    self.database_path
                ).get_config()
            )

            if config.log_folder:

                self.folder_edit.setText(
                    config.log_folder
                )

                self._load_machines()

                self.status_label.setText(
                    "Đang sử dụng Log Folder "
                    "từ File Management."
                )

        except Exception as error:

            self.status_label.setText(
                f"Không tải được Log Folder: {error}"
            )

    def _select_folder(self):

        current_folder = (
            self.folder_edit.text().strip()
        )

        if not current_folder:

            current_folder = str(Path.home())

        selected = (
            QFileDialog.getExistingDirectory(
                self,
                "Chọn Log Folder",
                current_folder,
            )
        )

        if not selected:
            return

        self.folder_edit.setText(selected)

        self._load_machines()

        self.status_label.setText(
            "Đã chọn Log Folder mới. "
            "Bấm '💾 Save Folder' để lưu."
        )

    def _save_log_folder(self):

        log_folder = (
            self.folder_edit.text().strip()
        )

        if not log_folder:

            QMessageBox.warning(
                self,
                "Thiếu Log Folder",
                "Vui lòng chọn Log Folder trước.",
            )

            return

        folder = Path(log_folder)

        if not folder.exists():

            QMessageBox.warning(
                self,
                "Log Folder không tồn tại",
                f"Không tìm thấy:\n{folder}",
            )

            return

        if not folder.is_dir():

            QMessageBox.warning(
                self,
                "Đường dẫn không hợp lệ",
                f"Đây không phải Folder:\n{folder}",
            )

            return

        try:

            self.repository.save_log_folder(
                folder
            )

            self._load_machines()

            self.status_label.setText(
                "Đã lưu Log Folder riêng cho "
                "Machine Slot Yield."
            )

            QMessageBox.information(
                self,
                "Đã lưu",
                "Đã lưu Log Folder thành công.\n\n"
                f"{folder}",
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Lỗi lưu Log Folder",
                str(error),
            )

    def _load_machines(self):

        self.machine_combo.blockSignals(True)

        current = (
            self.machine_combo.currentText()
        )

        self.machine_combo.clear()

        self.machine_combo.addItem("ALL")

        log_folder = (
            self.folder_edit.text().strip()
        )

        if log_folder:

            try:

                machines = (
                    self.repository.list_machines(
                        log_folder
                    )
                )

                for machine in machines:

                    self.machine_combo.addItem(
                        machine
                    )

            except Exception as error:

                self.status_label.setText(
                    f"Không đọc được Machine: {error}"
                )

        index = (
            self.machine_combo.findText(
                current
            )
        )

        if index >= 0:

            self.machine_combo.setCurrentIndex(
                index
            )

        self.machine_combo.blockSignals(False)

        self._update_slot_combo_for_machine()

    # ============================================================
    # BUSY
    # ============================================================

    def _set_busy(self, busy):

        for spin in (self.target15_spin, self.target30_spin,
                     self.target15_model_spin, self.target30_model_spin):
            spin.setEnabled(not busy)

        self.select_folder_button.setEnabled(
            not busy
        )

        self.save_folder_button.setEnabled(
            not busy
        )

        self.save_target_button.setEnabled(
            not busy
        )

        self.machine_combo.setEnabled(
            not busy
        )

        self.slot_combo.setEnabled(
            not busy
        )

        self.alarm_only_check.setEnabled(
            not busy
        )

        self.export_button.setEnabled(
            (
                not busy
                and self.current_result is not None
                and bool(
                    self.current_result.records
                )
            )
        )

    # ============================================================
    # SEARCH RESULT
    # ============================================================

    def _search_succeeded(self, result):

        self.current_result = result

        # --------------------------------------------------------
        # BUILD MACHINE SLOT YIELD
        # --------------------------------------------------------

        self._rebuild_slot_rows()

        self._update_filter_combos()

        self._apply_slot_filters()

        self._render_daily(result)

        # Log parsing and database synchronisation have both completed in
        # the worker; only UI rendering runs on the main thread.

        # --------------------------------------------------------
        # FINISH
        # --------------------------------------------------------

        self._set_busy(False)

        has_data = bool(
            result.records
        )

        self.export_button.setEnabled(
            has_data
        )

        if has_data:

            self.status_label.setText(
                "Đã đọc và tổng hợp dữ liệu thành công. "
                "Machine Slot Yield Alarm đã được cập nhật."
            )

        else:

            self.status_label.setText(
                "Không có dữ liệu trong khoảng ngày đã chọn."
            )

        # --------------------------------------------------------
        # QUAN TRỌNG
        #
        # Chỉ emit SAU KHI:
        #
        # TXT -> calculate -> render -> sync DB
        #
        # MainWindow nhận signal này rồi mới load Alarm.
        # --------------------------------------------------------

        self.load_finished.emit(
            result
        )

    def _search_failed(self, message):

        self._clear_result()

        self._set_busy(False)

        self.status_label.setText(
            f"Lỗi: {message}"
        )

        # MainWindow có thể dùng signal này
        # để dừng quá trình chuẩn bị Alarm.
        self.load_failed.emit(
            str(message)
        )

    def _thread_finished(self):

        if self.thread is not None:

            try:

                self.thread.deleteLater()

            except RuntimeError:

                pass

        self.thread = None

        self.worker = None

    # ============================================================
    # BUILD SLOT ROWS
    # ============================================================

    def _rebuild_slot_rows(self):

        self._all_slot_rows = []

        if self.current_result is None:
            return

        records = list(
            self.current_result.records
        )

        target_15 = (
            self.target15_spin.value()
        )

        target_30 = (
            self.target30_spin.value()
        )

        grouped = {}

        for record in records:

            try:

                machine = str(
                    record.machine
                ).strip()

                slot = int(
                    record.slot
                )

            except (
                ValueError,
                TypeError,
            ):

                continue

            result_text = str(
                getattr(
                    record,
                    "result",
                    "",
                )
            ).strip().upper()

            if result_text not in (
                "PASS",
                "FAIL",
            ):

                continue

            key = (
                machine,
                slot,
            )

            grouped.setdefault(
                key,
                [],
            ).append(record)

        for (
            machine,
            slot,
        ), slot_records in grouped.items():

            slot_records.sort(
                key=self._record_sort_key,
                reverse=True,
            )

            total_test = len(
                slot_records
            )

            pass_count = sum(
                1
                for r in slot_records
                if str(
                    r.result
                ).strip().upper()
                == "PASS"
            )

            fail_count = sum(
                1
                for r in slot_records
                if str(
                    r.result
                ).strip().upper()
                == "FAIL"
            )

            total_yield = (
                pass_count
                / total_test
                * 100
                if total_test
                else None
            )

            # ----------------------------------------------------
            # LAST 15
            # ----------------------------------------------------

            latest_15 = slot_records[:15]

            pass_15 = sum(
                1
                for r in latest_15
                if str(
                    r.result
                ).strip().upper()
                == "PASS"
            )

            count_15 = len(
                latest_15
            )

            yield_15 = (
                pass_15
                / count_15
                * 100
                if count_15 == 15
                else None
            )

            # ----------------------------------------------------
            # LAST 30
            # ----------------------------------------------------

            latest_30 = slot_records[:30]

            pass_30 = sum(
                1
                for r in latest_30
                if str(
                    r.result
                ).strip().upper()
                == "PASS"
            )

            count_30 = len(
                latest_30
            )

            yield_30 = (
                pass_30
                / count_30
                * 100
                if count_30 == 30
                else None
            )

            # ----------------------------------------------------
            # Shared rules: the UI and persisted Alarm use the same evidence.
            events = [event for (day, event_machine, event_slot), day_events
                      in self.current_result.alarm_events.items()
                      if event_machine == machine and event_slot == slot
                      for event in day_events]
            fail_two_consecutive = any(e['rule'] == 'consecutive' for e in events)
            same_model_fail = any(e['rule'] == 'consecutive' and 'cùng Model' in e['reason'] for e in events)
            alarm_15 = any(e['rule'] == 'yield15' for e in events)
            alarm_30 = any(e['rule'] == 'yield30' for e in events)
            # Filter/count current log violations, not retained database history.
            alarm = bool(events)
            comments = list(dict.fromkeys(
                str(event.get("reason", "")).strip() for event in events
                if str(event.get("reason", "")).strip()
            ))
            fail_comment = " | ".join(comments) if comments else "-"

            # ----------------------------------------------------
            # LAST 10
            # ----------------------------------------------------

            latest_tests = []

            for record in slot_records[:10]:

                latest_tests.append(
                    {
                        "result": str(
                            record.result
                        ).strip().upper(),

                        "date": str(
                            record.date
                        ),

                        "time": str(
                            record.time or ""
                        ),

                        "partno": str(
                            getattr(
                                record,
                                "partno",
                                "",
                            )
                            or ""
                        ),

                        "lotno": str(
                            getattr(
                                record,
                                "lotno",
                                "",
                            )
                            or ""
                        ),
                    }
                )

            self._all_slot_rows.append(
                {
                    "machine": machine,
                    "slot": slot,
                    "total_test": total_test,
                    "pass_count": pass_count,
                    "fail_count": fail_count,
                    "yield": total_yield,
                    "fail_comment": fail_comment,
                    "yield_15": yield_15,
                    "yield_30": yield_30,

                    "fail_two_consecutive":
                        fail_two_consecutive,

                    "same_model_fail":
                        same_model_fail,

                    "alarm_15":
                        alarm_15,

                    "alarm_30":
                        alarm_30,

                    "alarm":
                        alarm,

                    "latest_tests":
                        latest_tests,

                    "records":
                        slot_records,
                }
            )

        self._all_slot_rows.sort(
            key=lambda x: (
                str(
                    x["machine"]
                ).casefold(),
                x["slot"],
            )
        )

    # ============================================================
    # RECORD SORT
    # ============================================================

    @staticmethod
    def _record_sort_key(record):

        data_date = str(
            getattr(
                record,
                "date",
                "",
            )
        )

        data_time = str(
            getattr(
                record,
                "time",
                "",
            )
        )

        file_name = str(
            getattr(
                record,
                "file_name",
                "",
            )
        )

        file_path = str(
            getattr(
                record,
                "file_path",
                "",
            )
        )

        return (
            data_date,
            data_time,
            file_name,
            file_path,
            int(getattr(record, "line_number", 0) or 0),
        )

    @staticmethod
    def _result_is_pass(record):
        return str(
            getattr(record, "result", "") or ""
        ).strip().upper() == "PASS"

    @staticmethod
    def _result_is_fail(record):
        return (
            str(
                getattr(
                    record,
                    "result",
                    "",
                )
            )
            .strip()
            .upper()
            == "FAIL"
        )

    # ============================================================
    # FILTER COMBO
    # ============================================================

    def _update_filter_combos(self):

        current_machine = (
            self.machine_combo.currentText()
        )

        machines = sorted(
            {
                row["machine"]
                for row in self._all_slot_rows
            },
            key=str.casefold,
        )

        self.machine_combo.blockSignals(True)

        self.machine_combo.clear()

        self.machine_combo.addItem("ALL")

        self.machine_combo.addItems(
            machines
        )

        index = (
            self.machine_combo.findText(
                current_machine
            )
        )

        if index >= 0:

            self.machine_combo.setCurrentIndex(
                index
            )

        else:

            self.machine_combo.setCurrentIndex(0)

        self.machine_combo.blockSignals(False)

        self._update_slot_combo_for_machine()

    def _update_slot_combo_for_machine(self):

        current_slot = (
            self.slot_combo.currentText()
        )

        machine = (
            self.machine_combo.currentText()
        )

        slots = sorted(
            {
                row["slot"]
                for row in self._all_slot_rows
                if (
                    machine == "ALL"
                    or row["machine"] == machine
                )
            }
        )

        self.slot_combo.blockSignals(True)

        self.slot_combo.clear()

        self.slot_combo.addItem("ALL")

        for slot in slots:

            self.slot_combo.addItem(
                str(slot)
            )

        index = (
            self.slot_combo.findText(
                current_slot
            )
        )

        if index >= 0:

            self.slot_combo.setCurrentIndex(
                index
            )

        else:

            self.slot_combo.setCurrentIndex(0)

        self.slot_combo.blockSignals(False)

    # ============================================================
    # APPLY FILTER
    # ============================================================

    def _apply_slot_filters(self):

        machine = (
            self.machine_combo.currentText()
        )

        slot_text = (
            self.slot_combo.currentText()
        )

        alarm_only = (
            self.alarm_only_check.isChecked()
        )

        filtered = []

        for row in self._all_slot_rows:

            if (
                machine != "ALL"
                and row["machine"] != machine
            ):

                continue

            if slot_text != "ALL":

                try:

                    selected_slot = int(
                        slot_text
                    )

                except ValueError:

                    continue

                if (
                    row["slot"]
                    != selected_slot
                ):

                    continue

            if (
                alarm_only
                and not row["alarm"]
            ):

                continue

            filtered.append(row)

        self._render_slot_table(
            filtered
        )

    # ============================================================
    # RENDER SLOT TABLE
    # ============================================================

    def _render_slot_table(
        self,
        rows,
    ):

        self.summary_table.setRowCount(0)

        for index, row_data in enumerate(
            rows,
            start=1,
        ):

            row = (
                self.summary_table.rowCount()
            )

            self.summary_table.insertRow(row)

            values = [
                index,
                row_data["machine"],
                row_data["slot"],
                row_data["total_test"],
                row_data["pass_count"],
                row_data["fail_count"],
                self._fmt_pct(
                    row_data["yield"]
                ),
                row_data.get("fail_comment", "-"),
            ]

            latest_tests = (
                row_data["latest_tests"]
            )

            for i in range(10):

                if i < len(latest_tests):

                    test = latest_tests[i]

                    date_text = (
                        self._format_test_date(
                            test["date"]
                        )
                    )

                    cell_text = (
                        f"{test['result']}\n"
                        f"{date_text}"
                    )

                else:

                    cell_text = "-"

                values.append(
                    cell_text
                )

            for col, value in enumerate(values):

                item = QTableWidgetItem(
                    str(value)
                )

                item.setTextAlignment(
                    Qt.AlignCenter
                    | Qt.AlignVCenter
                )

                if col == 7:
                    item.setToolTip(str(value))

                if col >= 8:

                    test_index = col - 8

                    if (
                        test_index
                        < len(latest_tests)
                    ):

                        result_text = (
                            latest_tests[
                                test_index
                            ]["result"]
                        )

                        if result_text == "PASS":

                            item.setForeground(
                                QColor("#15803D")
                            )

                        elif result_text == "FAIL":

                            item.setForeground(
                                QColor("#DC2626")
                            )

                self.summary_table.setItem(
                    row,
                    col,
                    item,
                )

            if row_data["alarm"]:

                for col in range(
                    len(self.HEADERS)
                ):

                    item = (
                        self.summary_table.item(
                            row,
                            col,
                        )
                    )

                    if item is None:
                        continue

                    item.setBackground(
                        QColor("#FECACA")
                    )

                    item.setForeground(
                        QColor("#991B1B")
                    )

                for col in range(8, 18):

                    item = (
                        self.summary_table.item(
                            row,
                            col,
                        )
                    )

                    if item is None:
                        continue

                    text = item.text()

                    if text.startswith("PASS"):

                        item.setForeground(
                            QColor("#15803D")
                        )

                    elif text.startswith("FAIL"):

                        item.setForeground(
                            QColor("#DC2626")
                        )

            else:

                for col in range(8, 18):

                    item = (
                        self.summary_table.item(
                            row,
                            col,
                        )
                    )

                    if item is None:
                        continue

                    text = item.text()

                    if text.startswith("FAIL"):

                        item.setBackground(
                            QColor("#FEE2E2")
                        )

                        item.setForeground(
                            QColor("#B91C1C")
                        )

            self.summary_table.setRowHeight(row, 44)

        alarm_count = sum(
            1
            for row in rows
            if row["alarm"]
        )

        fail_count = sum(
            1
            for row in rows
            if row["fail_count"] > 0
        )

        self.summary_label.setText(
            f"Hiển thị: {len(rows)} Slot | "
            f"Slot có FAIL: {fail_count} | "
            f"ALARM: {alarm_count}"
        )

    # ============================================================
    # FORMAT DATE
    # ============================================================

    @staticmethod
    def _format_test_date(value):

        text = str(
            value or ""
        ).strip()

        if not text:
            return ""

        if (
            len(text) == 8
            and text.isdigit()
        ):

            return (
                f"{text[0:4]}-"
                f"{text[4:6]}-"
                f"{text[6:8]}"
            )

        return (
            text
            .replace("-", "")
            .replace("/", "")
        )

    # ============================================================
    # DAILY
    # ============================================================

    def _render_daily(self, result):

        self.daily_table.setRowCount(0)

        target_15 = (
            self.target15_spin.value()
        )

        for d in result.daily:

            row = (
                self.daily_table.rowCount()
            )

            self.daily_table.insertRow(row)

            values = [
                d.machine,
                d.date,
                d.slot,
                d.test_count,
                d.pass_count,
                d.fail_count,
                self._fmt_pct(
                    d.yield_percent
                ),
            ]

            for col, value in enumerate(values):

                item = QTableWidgetItem(
                    str(value)
                )

                item.setTextAlignment(
                    Qt.AlignCenter
                    | Qt.AlignVCenter
                )

                if (
                    col == 6
                    and d.yield_percent is not None
                    and d.yield_percent < target_15
                ):

                    item.setBackground(
                        QColor("#FECACA")
                    )

                    item.setForeground(
                        QColor("#991B1B")
                    )

                self.daily_table.setItem(
                    row,
                    col,
                    item,
                )

    # ============================================================
    # SUMMARY DOUBLE CLICK
    # ============================================================

    def _show_fail_comment(self, row, column):
        if column == 7:
            # Open the same test history dialog used by the rest of the row.
            self._summary_double_click(row, 0)

    def _summary_double_click(
        self,
        row,
        column,
    ):

        if column == 7:
            return

        machine_item = (
            self.summary_table.item(
                row,
                1,
            )
        )

        slot_item = (
            self.summary_table.item(
                row,
                2,
            )
        )

        if (
            not machine_item
            or not slot_item
        ):

            return

        machine = machine_item.text()

        try:

            slot = int(
                slot_item.text()
            )

        except ValueError:

            return

        if self.current_result is None:
            return

        records = []

        for r in self.current_result.records:

            try:

                record_machine = str(
                    r.machine
                )

                record_slot = int(
                    r.slot
                )

            except (
                ValueError,
                TypeError,
            ):

                continue

            if (
                record_machine == machine
                and record_slot == slot
            ):

                records.append(r)

        comment_item = self.summary_table.item(row, 7)
        fail_comment = comment_item.text() if comment_item is not None else "-"

        dialog = MachineSlotHistoryDialog(
            machine,
            slot,
            records,
            self,
            date_from=self.current_result.date_from,
            date_to=self.current_result.date_to,
            fail_comment=fail_comment,
        )

        dialog.exec_()

    # ============================================================
    # FORMAT
    # ============================================================

    @staticmethod
    def _fmt_pct(value):

        if value is None:
            return "-"

        return f"{value:.2f}%"

    # ============================================================
    # EXPORT EXCEL
    # ============================================================

    def _export_excel(self):

        if self.current_result is None:

            QMessageBox.warning(
                self,
                "Chưa có dữ liệu",
                "Vui lòng chọn From Date / To Date "
                "ở FilterPanel và bấm Search trước.",
            )

            return

        if not self.current_result.records:

            QMessageBox.warning(
                self,
                "Không có dữ liệu",
                "Không có dữ liệu để Export.",
            )

            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Machine Slot Yield",
            "Machine_Slot_Yield.xlsx",
            "Excel Files (*.xlsx)",
        )

        if not path:
            return

        try:

            from openpyxl import Workbook

            from openpyxl.styles import (
                Font,
                Alignment,
                PatternFill,
            )

            wb = Workbook()

            # ====================================================
            # SLOT SUMMARY
            # ====================================================

            ws = wb.active

            ws.title = "Slot Summary"

            ws.append(
                self.HEADERS
                + [
                    "Last 15 Yield",
                    "Target 15",
                    "Last 30 Yield",
                    "Target 30",
                    "Fail 2 Consecutive",
                    "Same Model Fail",
                    "Alarm 15",
                    "Alarm 30",
                    "ALARM",
                ]
            )

            for no, row_data in enumerate(
                self._all_slot_rows,
                start=1,
            ):

                values = [
                    no,
                    row_data["machine"],
                    row_data["slot"],
                    row_data["total_test"],
                    row_data["pass_count"],
                    row_data["fail_count"],
                    self._fmt_pct(
                        row_data["yield"]
                    ),
                    row_data.get("fail_comment", "-"),
                ]

                latest_tests = (
                    row_data["latest_tests"]
                )

                for i in range(10):

                    if i < len(latest_tests):

                        test = latest_tests[i]

                        values.append(
                            f"{test['result']}\n"
                            f"{self._format_test_date(test['date'])}"
                        )

                    else:

                        values.append("-")

                values.extend(
                    [
                        self._fmt_pct(
                            row_data["yield_15"]
                        ),
                        self.target15_spin.value(),
                        self._fmt_pct(
                            row_data["yield_30"]
                        ),
                        self.target30_spin.value(),

                        "YES"
                        if row_data[
                            "fail_two_consecutive"
                        ]
                        else "NO",

                        "YES"
                        if row_data[
                            "same_model_fail"
                        ]
                        else "NO",

                        "YES"
                        if row_data["alarm_15"]
                        else "NO",

                        "YES"
                        if row_data["alarm_30"]
                        else "NO",

                        "ALARM"
                        if row_data["alarm"]
                        else "PASS",
                    ]
                )

                ws.append(values)

                excel_row = ws.max_row

                for col in range(
                    8,
                    19,
                ):

                    ws.cell(
                        excel_row,
                        col,
                    ).alignment = Alignment(
                        horizontal="center",
                        vertical="center",
                        wrap_text=True,
                    )

                if row_data["alarm"]:

                    for cell in ws[excel_row]:

                        cell.fill = PatternFill(
                            fill_type="solid",
                            fgColor="FECACA",
                        )

            # ====================================================
            # DAILY
            # ====================================================

            ws2 = wb.create_sheet("Daily")

            ws2.append(
                self.DAILY_HEADERS
            )

            for d in self.current_result.daily:

                ws2.append(
                    [
                        d.machine,
                        d.date,
                        d.slot,
                        d.test_count,
                        d.pass_count,
                        d.fail_count,
                        d.yield_percent,
                    ]
                )

            # ====================================================
            # TEST HISTORY
            # ====================================================

            ws3 = wb.create_sheet(
                "Test History"
            )

            ws3.append(
                [
                    "Machine",
                    "Date",
                    "Time",
                    "Slot",
                    "Result",
                    "Part No",
                    "Lot No",
                    "Interface",
                    "Scrap Code",
                    "File",
                ]
            )

            for r in self.current_result.records:

                ws3.append(
                    [
                        r.machine,
                        r.date,
                        r.time,
                        r.slot,
                        r.result,
                        r.partno,
                        r.lotno,
                        r.interface,
                        r.scrapcode,
                        r.file_name,
                    ]
                )

            # ====================================================
            # FORMAT EXCEL
            # ====================================================

            for wsx in wb.worksheets:

                wsx.freeze_panes = "A2"

                wsx.auto_filter.ref = (
                    wsx.dimensions
                )

                for cell in wsx[1]:

                    cell.font = Font(
                        bold=True
                    )

                    cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center",
                        wrap_text=True,
                    )

                for column_cells in wsx.columns:

                    max_length = 0

                    for cell in column_cells:

                        value_length = len(
                            str(
                                cell.value
                                or ""
                            )
                        )

                        if value_length > max_length:

                            max_length = value_length

                    length = min(
                        max_length + 2,
                        35,
                    )

                    wsx.column_dimensions[
                        column_cells[0].column_letter
                    ].width = length

            # ====================================================
            # SAVE
            # ====================================================

            wb.save(path)

            QMessageBox.information(
                self,
                "Export thành công",
                f"Đã xuất Excel:\n{path}",
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Export thất bại",
                str(error),
            )


# ================================================================
# WORKER
# ================================================================


class _MachineSlotWorker(QObject):

    succeeded = pyqtSignal(object)

    failed = pyqtSignal(str)

    def __init__(
        self,
        repository,
        log_folder,
        date_from,
        date_to,
        machine,
        last_days,
        database_path,
        targets,
    ):

        super().__init__()

        self.repository = repository

        self.log_folder = log_folder

        self.date_from = date_from

        self.date_to = date_to

        self.machine = machine

        self.last_days = last_days

        self.database_path = database_path

        self.targets = targets

    @pyqtSlot()
    def run(self):

        try:

            result = self.repository.load(
                log_root=self.log_folder,
                date_from=self.date_from,
                date_to=self.date_to,
                machine=self.machine,
                last_days=self.last_days,
            )

            AlarmRepository(self.database_path).sync_machine_slot_yield_result(
                result=result,
                date_from=result.date_from,
                date_to=result.date_to,
                target_15=self.targets[0],
                target_30=self.targets[1],
                target_15_model=self.targets[2],
                target_30_model=self.targets[3],
            )

            self.succeeded.emit(
                result
            )

        except Exception as error:

            self.failed.emit(
                str(error)
            )
