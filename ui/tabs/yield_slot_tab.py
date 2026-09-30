
from __future__ import annotations

from PyQt5.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTableView,
    QVBoxLayout,
    QWidget,
)


# ============================================================
# COMMON TABLE VIEW
# ============================================================

class YieldSlotTableView(QTableView):
    """
    QTableView không tự scroll dọc.

    Khi lăn chuột theo chiều dọc trên bảng,
    chuyển thao tác scroll sang QScrollArea của tab.
    """

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self._outer_scroll_area = None

    def set_outer_scroll_area(
        self,
        scroll_area: QScrollArea,
    ) -> None:
        self._outer_scroll_area = scroll_area

    def wheelEvent(
        self,
        event,
    ) -> None:

        vertical_delta = (
            event.pixelDelta().y()
            or event.angleDelta().y()
        )

        horizontal_delta = (
            event.pixelDelta().x()
            or event.angleDelta().x()
        )

        is_horizontal_scroll = (
            abs(horizontal_delta)
            > abs(vertical_delta)
            or bool(
                event.modifiers()
                & Qt.ShiftModifier
            )
        )

        if (
            self._outer_scroll_area is not None
            and vertical_delta != 0
            and not is_horizontal_scroll
        ):

            scroll_bar = (
                self._outer_scroll_area
                .verticalScrollBar()
            )

            scroll_bar.setValue(
                scroll_bar.value()
                - vertical_delta
            )

            event.accept()
            return

        super().wheelEvent(event)


# ============================================================
# DAILY TABLE MODEL
# ============================================================

class YieldSlotTableModel(
    QAbstractTableModel
):
    """Model cho bảng Daily Yield."""

    FIXED_HEADERS = [
        "Date",
        "In",
        "Pass",
        "Fail",
        "Yield",
    ]

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self._result = None
        self._headers: list[str] = []

    def set_result(
        self,
        result,
    ) -> None:

        self.beginResetModel()

        self._result = result

        self._headers = [
            *self.FIXED_HEADERS,
            *[
                str(slot_no)
                for slot_no in result.slots
            ],
        ]

        self.endResetModel()

    def clear(self) -> None:

        self.beginResetModel()

        self._result = None
        self._headers = []

        self.endResetModel()

    def rowCount(
        self,
        parent=QModelIndex(),
    ) -> int:

        if (
            parent.isValid()
            or self._result is None
        ):
            return 0

        return len(
            self._result.rows
        )

    def columnCount(
        self,
        parent=QModelIndex(),
    ) -> int:

        if parent.isValid():
            return 0

        return len(
            self._headers
        )

    def data(
        self,
        index,
        role=Qt.DisplayRole,
    ):

        if (
            not index.isValid()
            or self._result is None
        ):
            return None

        row = self._result.rows[
            index.row()
        ]

        column = index.column()

        if role == Qt.TextAlignmentRole:

            return int(
                Qt.AlignCenter
            )

        if (
            role == Qt.BackgroundRole
            and column >= 5
        ):

            slot_no = self._result.slots[
                column - 5
            ]

            if (
                row.fail_qty_by_slot.get(
                    slot_no,
                    0,
                )
                > 0
            ):

                return QColor(
                    "#F9A8D4"
                )

        if role != Qt.DisplayRole:
            return None

        if column == 0:
            return row.date

        if column == 1:
            return str(
                row.in_qty
            )

        if column == 2:
            return str(
                row.pass_qty
            )

        if column == 3:
            return str(
                row.fail_qty
            )

        if column == 4:

            if row.yield_percent is None:
                return "—"

            return (
                f"{row.yield_percent:.2f}%"
            )

        slot_no = self._result.slots[
            column - 5
        ]

        fail_qty = (
            row.fail_qty_by_slot.get(
                slot_no,
                0,
            )
        )

        return (
            str(fail_qty)
            if fail_qty > 0
            else ""
        )

    def headerData(
        self,
        section,
        orientation,
        role=Qt.DisplayRole,
    ):

        if (
            role == Qt.DisplayRole
            and orientation == Qt.Horizontal
            and 0 <= section < len(self._headers)
        ):

            return self._headers[
                section
            ]

        if role == Qt.TextAlignmentRole:

            return int(
                Qt.AlignCenter
            )

        return None


# ============================================================
# SCRAP TABLE MODEL
# ============================================================

class YieldSlotScrapTableModel(
    QAbstractTableModel
):
    """Model bảng Slot theo Scrapcode."""

    FIXED_HEADERS = [
        "Slot",
        "In",
        "Pass",
        "Fail",
        "Yield",
    ]

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self._result = None
        self._headers: list[str] = []

    def set_result(
        self,
        result,
    ) -> None:

        self.beginResetModel()

        self._result = result

        self._headers = [
            *self.FIXED_HEADERS,
            *result.scrap_codes,
        ]

        self.endResetModel()

    def clear(self) -> None:

        self.beginResetModel()

        self._result = None
        self._headers = []

        self.endResetModel()

    def rowCount(
        self,
        parent=QModelIndex(),
    ) -> int:

        if (
            parent.isValid()
            or self._result is None
        ):
            return 0

        return len(
            self._result.rows
        )

    def columnCount(
        self,
        parent=QModelIndex(),
    ) -> int:

        if parent.isValid():
            return 0

        return len(
            self._headers
        )

    def data(
        self,
        index,
        role=Qt.DisplayRole,
    ):

        if (
            not index.isValid()
            or self._result is None
        ):
            return None

        row = self._result.rows[
            index.row()
        ]

        column = index.column()

        if role == Qt.TextAlignmentRole:

            return int(
                Qt.AlignCenter
            )

        if (
            role == Qt.BackgroundRole
            and column >= 5
        ):

            scrap_code = (
                self._result.scrap_codes[
                    column - 5
                ]
            )

            scrap_qty = (
                row.scrap_qty_by_code.get(
                    scrap_code,
                    0,
                )
            )

            if scrap_qty > 0:

                return QColor(
                    "#F9A8D4"
                )

        if role != Qt.DisplayRole:
            return None

        if column == 0:
            return str(
                row.slot
            )

        if column == 1:
            return str(
                row.in_qty
            )

        if column == 2:
            return str(
                row.pass_qty
            )

        if column == 3:
            return str(
                row.fail_qty
            )

        if column == 4:

            if row.yield_percent is None:
                return "—"

            return (
                f"{row.yield_percent:.2f}%"
            )

        scrap_code = (
            self._result.scrap_codes[
                column - 5
            ]
        )

        scrap_qty = (
            row.scrap_qty_by_code.get(
                scrap_code,
                0,
            )
        )

        return (
            str(scrap_qty)
            if scrap_qty > 0
            else ""
        )

    def headerData(
        self,
        section,
        orientation,
        role=Qt.DisplayRole,
    ):

        if (
            role == Qt.DisplayRole
            and orientation == Qt.Horizontal
            and 0 <= section < len(self._headers)
        ):

            return self._headers[
                section
            ]

        if role == Qt.TextAlignmentRole:

            return int(
                Qt.AlignCenter
            )

        return None


# ============================================================
# MACHINE SLOT YIELD TABLE MODEL
# ============================================================

class MachineSlotYieldTableModel(
    QAbstractTableModel
):
    """
    Bảng:

    No
    Machine
    Slot
    Total Test
    PASS
    FAIL
    YEILD
    Lần 1 ... Lần 10
    """

    HEADERS = [
        "No",
        "Machine",
        "Slot",
        "Total Test",
        "PASS",
        "FAIL",
        "YEILD",
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

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self._rows = []
        self._machine = ""
        self._target_15 = 95.0
        self._target_30 = 95.0

        self._machine_filter = ""
        self._slot_filter = ""
        self._result_filter = "ALL"

    # --------------------------------------------------------
    # SET DATA
    # --------------------------------------------------------

    def set_result(
        self,
        rows,
        machine: str,
        target_15: float,
        target_30: float,
    ) -> None:

        self.beginResetModel()

        self._rows = list(rows)
        self._machine = (
            machine or ""
        )

        self._target_15 = float(
            target_15
        )

        self._target_30 = float(
            target_30
        )

        self.endResetModel()

    def clear(self) -> None:

        self.beginResetModel()

        self._rows = []

        self.endResetModel()

    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    def set_filters(
        self,
        machine: str = "",
        slot: str = "",
        result: str = "ALL",
    ) -> None:

        self.beginResetModel()

        self._machine_filter = (
            machine.strip().lower()
        )

        self._slot_filter = (
            slot.strip().lower()
        )

        self._result_filter = (
            result
        )

        self.endResetModel()

    def _filtered_rows(self):

        result = []

        for row in self._rows:

            machine_text = (
                self._machine.lower()
            )

            if (
                self._machine_filter
                and self._machine_filter
                not in machine_text
            ):
                continue

            slot_text = str(
                row.slot
            )

            if (
                self._slot_filter
                and self._slot_filter
                not in slot_text
            ):
                continue

            if (
                self._result_filter
                == "PASS"
                and row.status != "PASS"
            ):
                continue

            if (
                self._result_filter
                == "FAIL"
                and not self._row_has_fail(
                    row
                )
            ):
                continue

            if (
                self._result_filter
                == "ALARM"
                and row.status != "ALARM"
            ):
                continue

            result.append(row)

        return result

    @staticmethod
    def _row_has_fail(
        row,
    ) -> bool:

        if row.total_fail > 0:
            return True

        for test in row.latest_tests:

            if test.result == "FAIL":
                return True

        return False

    # --------------------------------------------------------
    # ROW / COLUMN
    # --------------------------------------------------------

    def rowCount(
        self,
        parent=QModelIndex(),
    ) -> int:

        if parent.isValid():
            return 0

        return len(
            self._filtered_rows()
        )

    def columnCount(
        self,
        parent=QModelIndex(),
    ) -> int:

        if parent.isValid():
            return 0

        return len(
            self.HEADERS
        )

    # --------------------------------------------------------
    # CELL
    # --------------------------------------------------------

    def data(
        self,
        index,
        role=Qt.DisplayRole,
    ):

        if not index.isValid():
            return None

        rows = self._filtered_rows()

        if index.row() >= len(rows):
            return None

        row = rows[
            index.row()
        ]

        column = index.column()

        # ----------------------------------------------
        # ALIGN
        # ----------------------------------------------

        if role == Qt.TextAlignmentRole:

            return int(
                Qt.AlignCenter
            )

        # ----------------------------------------------
        # ALARM ROW
        # ----------------------------------------------

        if role == Qt.BackgroundRole:

            if row.status == "ALARM":

                return QColor(
                    "#FCA5A5"
                )

            return None

        if role == Qt.ForegroundRole:

            if row.status == "ALARM":

                return QColor(
                    "#7F1D1D"
                )

            return None

        # ----------------------------------------------
        # DISPLAY
        # ----------------------------------------------

        if role != Qt.DisplayRole:
            return None

        # No
        if column == 0:

            return str(
                index.row() + 1
            )

        # Machine
        if column == 1:

            return self._machine

        # Slot
        if column == 2:

            return str(
                row.slot
            )

        # Total Test
        if column == 3:

            return str(
                row.total_test
            )

        # PASS
        if column == 4:

            return str(
                row.total_pass
            )

        # FAIL
        if column == 5:

            return str(
                row.total_fail
            )

        # YEILD
        if column == 6:

            if row.total_yield is None:
                return "—"

            return (
                f"{row.total_yield:.2f}%"
            )

        # Lần 1 -> Lần 10
        test_index = (
            column - 7
        )

        if (
            test_index
            < len(row.latest_tests)
        ):

            test = (
                row.latest_tests[
                    test_index
                ]
            )

            date_text = (
                test.date
            )

            return (
                f"{test.result}\n"
                f"{date_text}"
            )

        return ""

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    def headerData(
        self,
        section,
        orientation,
        role=Qt.DisplayRole,
    ):

        if (
            role == Qt.DisplayRole
            and orientation == Qt.Horizontal
            and 0 <= section
            < len(self.HEADERS)
        ):

            return self.HEADERS[
                section
            ]

        if role == Qt.TextAlignmentRole:

            return int(
                Qt.AlignCenter
            )

        return None


# ============================================================
# MAIN TAB
# ============================================================

class YieldSlotTab(QWidget):
    """
    Tab Yield Slot.

    Gồm:

    1. Daily Prime Yield by Slot
    2. Prime Yield Slot by Scrapcode
    3. Machine / Slot Summary
    """

    # Signal để MainWindow lưu Target xuống DB.
    target_save_requested = pyqtSignal(
        float,
        float,
    )

    FIXED_COLUMN_COUNT = 5

    ROW_HEIGHT = 24
    HEADER_HEIGHT = 30

    SLOT_COLUMN_WIDTH = 30

    MAX_TABLE_HEIGHT = 500

    FIXED_COLUMN_WIDTHS = [
        60,
        60,
        60,
        60,
        60,
    ]

    SCRAP_COLUMN_WIDTH = 44

    SCRAP_FIXED_COLUMN_WIDTHS = [
        60,
        60,
        60,
        60,
        60,
    ]

    MACHINE_YIELD_COLUMN_WIDTHS = [
        45,   # No
        100,  # Machine
        55,   # Slot
        80,   # Total Test
        60,   # PASS
        60,   # FAIL
        75,   # YEILD
        82,   # Lần 1
        82,   # Lần 2
        82,   # Lần 3
        82,   # Lần 4
        82,   # Lần 5
        82,   # Lần 6
        82,   # Lần 7
        82,   # Lần 8
        82,   # Lần 9
        82,   # Lần 10
    ]

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self._machine_yield_result = []
        self._current_machine = ""

        self._build_ui()

    # ========================================================
    # BUILD UI
    # ========================================================

    def _build_ui(self) -> None:

        outer_layout = QVBoxLayout(
            self
        )

        outer_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.scroll_area = QScrollArea(
            self
        )

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setFrameShape(
            QScrollArea.NoFrame
        )

        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.scroll_content = QWidget()

        main_layout = QVBoxLayout(
            self.scroll_content
        )

        main_layout.setContentsMargins(
            10,
            10,
            10,
            10,
        )

        main_layout.setSpacing(6)

        main_layout.setSizeConstraint(
            QLayout.SetMinimumSize
        )

        # ====================================================
        # DAILY
        # ====================================================

        self.title_label = QLabel(
            "Daily Prime Yield by Slot | "
            "EQP:- & Chamber: -"
        )

        self.title_label.setFixedHeight(
            24
        )

        self.title_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: #222222;
            """
        )

        self.status_label = QLabel(
            "Vui lòng chọn EQP, Chamber "
            "và bấm Apply Filter."
        )

        self.status_label.setStyleSheet(
            """
            color: #64748B;
            font-size: 12px;
            """
        )

        self.table_model = (
            YieldSlotTableModel(self)
        )

        self.fixed_table = (
            self._create_table_view()
        )

        self.fixed_table.setModel(
            self.table_model
        )

        self.fixed_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.fixed_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.fixed_table.setFocusPolicy(
            Qt.NoFocus
        )

        self.slot_table = (
            self._create_table_view()
        )

        self.slot_table.setModel(
            self.table_model
        )

        self.slot_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.slot_table.setHorizontalScrollMode(
            QAbstractItemView.ScrollPerPixel
        )

        self.slot_table.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.table = self.slot_table

        self.fixed_table.verticalScrollBar().valueChanged.connect(
            self.slot_table.verticalScrollBar().setValue
        )

        self.slot_table.verticalScrollBar().valueChanged.connect(
            self.fixed_table.verticalScrollBar().setValue
        )

        self.table_container = QWidget()

        table_layout = QHBoxLayout(
            self.table_container
        )

        table_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        table_layout.setSpacing(0)

        self.fixed_table_container = QWidget()

        fixed_layout = QVBoxLayout(
            self.fixed_table_container
        )

        fixed_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        fixed_layout.setSpacing(0)

        fixed_layout.addWidget(
            self.fixed_table
        )

        self.fixed_bottom_spacer = QWidget()

        self.fixed_bottom_spacer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        fixed_layout.addWidget(
            self.fixed_bottom_spacer
        )

        table_layout.addWidget(
            self.fixed_table_container
        )

        table_layout.addWidget(
            self.slot_table,
            1,
        )

        # ====================================================
        # SCRAP
        # ====================================================

        self._build_scrap_table_section()

        # ====================================================
        # MACHINE SLOT SUMMARY
        # ====================================================

        self._build_machine_slot_yield_section()

        # ====================================================
        # ADD TO MAIN
        # ====================================================

        main_layout.addWidget(
            self.title_label
        )

        main_layout.addWidget(
            self.status_label
        )

        main_layout.addWidget(
            self.table_container
        )

        main_layout.addSpacing(
            18
        )

        main_layout.addWidget(
            self.scrap_title_label
        )

        main_layout.addWidget(
            self.scrap_status_label
        )

        main_layout.addWidget(
            self.scrap_table_container
        )

        main_layout.addSpacing(
            18
        )

        main_layout.addWidget(
            self.machine_yield_title_label
        )

        main_layout.addWidget(
            self.machine_yield_target_widget
        )

        main_layout.addWidget(
            self.machine_yield_filter_widget
        )

        main_layout.addWidget(
            self.machine_yield_status_label
        )

        main_layout.addWidget(
            self.machine_yield_table
        )

        main_layout.addStretch()

        self.scroll_area.setWidget(
            self.scroll_content
        )

        outer_layout.addWidget(
            self.scroll_area
        )

        self._update_table_height(
            row_count=0
        )

        self._update_scrap_table_height(
            row_count=0
        )

    # ========================================================
    # MACHINE SLOT YIELD SECTION
    # ========================================================

    def _build_machine_slot_yield_section(
        self,
    ) -> None:

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        self.machine_yield_title_label = QLabel(
            "Machine / Slot Summary"
        )

        self.machine_yield_title_label.setFixedHeight(
            26
        )

        self.machine_yield_title_label.setStyleSheet(
            """
            font-size: 15px;
            font-weight: bold;
            color: #222222;
            """
        )

        # ----------------------------------------------------
        # TARGET
        # ----------------------------------------------------

        self.machine_yield_target_widget = QWidget()

        target_layout = QHBoxLayout(
            self.machine_yield_target_widget
        )

        target_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        target_layout.setSpacing(
            8
        )

        target_title = QLabel(
            "Target:"
        )

        target_title.setStyleSheet(
            """
            font-weight: bold;
            color: #334155;
            """
        )

        target_layout.addWidget(
            target_title
        )

        target_15_label = QLabel(
            "Last 15:"
        )

        target_layout.addWidget(
            target_15_label
        )

        self.target_15_spin = (
            QDoubleSpinBox()
        )

        self.target_15_spin.setRange(
            0.0,
            100.0
        )

        self.target_15_spin.setDecimals(
            2
        )

        self.target_15_spin.setSingleStep(
            0.5
        )

        self.target_15_spin.setSuffix(
            " %"
        )

        self.target_15_spin.setFixedWidth(
            95
        )

        self.target_15_spin.setValue(
            95.0
        )

        target_layout.addWidget(
            self.target_15_spin
        )

        target_30_label = QLabel(
            "Last 30:"
        )

        target_layout.addWidget(
            target_30_label
        )

        self.target_30_spin = (
            QDoubleSpinBox()
        )

        self.target_30_spin.setRange(
            0.0,
            100.0
        )

        self.target_30_spin.setDecimals(
            2
        )

        self.target_30_spin.setSingleStep(
            0.5
        )

        self.target_30_spin.setSuffix(
            " %"
        )

        self.target_30_spin.setFixedWidth(
            95
        )

        self.target_30_spin.setValue(
            95.0
        )

        target_layout.addWidget(
            self.target_30_spin
        )

        self.save_target_button = (
            QPushButton(
                "Save Target"
            )
        )

        self.save_target_button.setFixedHeight(
            28
        )

        self.save_target_button.clicked.connect(
            self._save_machine_yield_target
        )

        target_layout.addWidget(
            self.save_target_button
        )

        target_layout.addStretch()

        self.machine_yield_target_widget.setStyleSheet(
            """
            QWidget {
                background-color: #F8FAFC;
            }

            QLabel {
                color: #334155;
            }

            QDoubleSpinBox {
                padding: 3px;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background: white;
            }

            QPushButton {
                padding: 4px 12px;
                border: 1px solid #94A3B8;
                border-radius: 4px;
                background: #E2E8F0;
                font-weight: bold;
            }

            QPushButton:hover {
                background: #CBD5E1;
            }
            """
        )

        # ----------------------------------------------------
        # FILTER
        # ----------------------------------------------------

        self.machine_yield_filter_widget = QWidget()

        filter_layout = QHBoxLayout(
            self.machine_yield_filter_widget
        )

        filter_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        filter_layout.setSpacing(
            8
        )

        filter_layout.addWidget(
            QLabel("Machine:")
        )

        self.machine_filter_edit = (
            QLineEdit()
        )

        self.machine_filter_edit.setPlaceholderText(
            "Machine"
        )

        self.machine_filter_edit.setFixedWidth(
            130
        )

        self.machine_filter_edit.textChanged.connect(
            self._apply_machine_yield_filter
        )

        filter_layout.addWidget(
            self.machine_filter_edit
        )

        filter_layout.addWidget(
            QLabel("Slot:")
        )

        self.slot_filter_edit = (
            QLineEdit()
        )

        self.slot_filter_edit.setPlaceholderText(
            "Slot"
        )

        self.slot_filter_edit.setFixedWidth(
            90
        )

        self.slot_filter_edit.textChanged.connect(
            self._apply_machine_yield_filter
        )

        filter_layout.addWidget(
            self.slot_filter_edit
        )

        filter_layout.addWidget(
            QLabel("Result:")
        )

        self.result_filter_combo = (
            QComboBox()
        )

        self.result_filter_combo.addItems(
            [
                "ALL",
                "PASS",
                "FAIL",
                "ALARM",
            ]
        )

        self.result_filter_combo.setFixedWidth(
            100
        )

        self.result_filter_combo.currentTextChanged.connect(
            self._apply_machine_yield_filter
        )

        filter_layout.addWidget(
            self.result_filter_combo
        )

        self.clear_machine_filter_button = (
            QPushButton(
                "Clear Filter"
            )
        )

        self.clear_machine_filter_button.clicked.connect(
            self._clear_machine_yield_filter
        )

        filter_layout.addWidget(
            self.clear_machine_filter_button
        )

        filter_layout.addStretch()

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        self.machine_yield_status_label = QLabel(
            ""
        )

        self.machine_yield_status_label.setStyleSheet(
            """
            color: #64748B;
            font-size: 12px;
            """
        )

        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        self.machine_yield_table = (
            self._create_table_view()
        )

        self.machine_yield_table.setModel(
            MachineSlotYieldTableModel(
                self
            )
        )

        self.machine_yield_model = (
            self.machine_yield_table.model()
        )

        self.machine_yield_table.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.machine_yield_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.machine_yield_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.machine_yield_table.setHorizontalScrollMode(
            QAbstractItemView.ScrollPerPixel
        )

        self.machine_yield_table.setWordWrap(
            True
        )

        self.machine_yield_table.verticalHeader().setDefaultSectionSize(
            38
        )

        self.machine_yield_table.horizontalHeader().setFixedHeight(
            32
        )

        self.machine_yield_table.setStyleSheet(
            """
            QTableView {
                gridline-color: #94A3B8;
                border: 1px solid #64748B;
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                font-size: 12px;
            }

            QHeaderView::section {
                background-color: #D9EAF7;
                color: #0F172A;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #94A3B8;
                padding: 2px;
            }
            """
        )

        self._configure_machine_yield_columns()

        self.machine_yield_table.setFixedHeight(
            430
        )

    # ========================================================
    # SAVE TARGET
    # ========================================================

    def _save_machine_yield_target(
        self,
    ) -> None:

        target_15 = (
            self.target_15_spin.value()
        )

        target_30 = (
            self.target_30_spin.value()
        )

        self.target_save_requested.emit(
            target_15,
            target_30,
        )

        self._machine_yield_status(
            "Target đã được gửi để lưu."
        )

    # ========================================================
    # MACHINE FILTER
    # ========================================================

    def _apply_machine_yield_filter(
        self,
    ) -> None:

        self.machine_yield_model.set_filters(
            machine=self.machine_filter_edit.text(),
            slot=self.slot_filter_edit.text(),
            result=self.result_filter_combo.currentText(),
        )

        self._update_machine_yield_status()

    def _clear_machine_yield_filter(
        self,
    ) -> None:

        self.machine_filter_edit.clear()
        self.slot_filter_edit.clear()

        self.result_filter_combo.setCurrentText(
            "ALL"
        )

        self._apply_machine_yield_filter()

    # ========================================================
    # MACHINE TABLE
    # ========================================================

    def _configure_machine_yield_columns(
        self,
    ) -> None:

        header = (
            self.machine_yield_table
            .horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView.Fixed
        )

        for column, width in enumerate(
            self.MACHINE_YIELD_COLUMN_WIDTHS
        ):

            self.machine_yield_table.setColumnWidth(
                column,
                width,
            )

    def _update_machine_yield_status(
        self,
    ) -> None:

        visible_count = (
            self.machine_yield_model.rowCount()
        )

        total_count = len(
            self._machine_yield_result
        )

        if total_count == 0:

            self.machine_yield_status_label.setText(
                "Không có dữ liệu Machine / Slot."
            )

            return

        self.machine_yield_status_label.setText(
            f"Hiển thị {visible_count}/{total_count} Slot"
        )

    def _machine_yield_status(
        self,
        message: str,
    ) -> None:

        self.machine_yield_status_label.setText(
            message
        )

    # ========================================================
    # COMMON TABLE
    # ========================================================

    def _create_table_view(
        self,
    ) -> YieldSlotTableView:

        table = YieldSlotTableView(
            self
        )

        table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        table.setSelectionMode(
            QAbstractItemView.NoSelection
        )

        table.setAlternatingRowColors(
            True
        )

        table.setSortingEnabled(
            False
        )

        table.verticalHeader().setVisible(
            False
        )

        table.verticalHeader().setSectionResizeMode(
            QHeaderView.Fixed
        )

        table.verticalHeader().setMinimumSectionSize(
            self.ROW_HEIGHT
        )

        table.verticalHeader().setDefaultSectionSize(
            self.ROW_HEIGHT
        )

        table.horizontalHeader().setFixedHeight(
            self.HEADER_HEIGHT
        )

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Fixed
        )

        table.horizontalHeader().setMinimumSectionSize(
            1
        )

        table.horizontalHeader().setDefaultSectionSize(
            self.SLOT_COLUMN_WIDTH
        )

        table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        table.setVerticalScrollMode(
            QAbstractItemView.ScrollPerItem
        )

        table.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        table.setStyleSheet(
            """
            QTableView {
                gridline-color: #CBD5E1;
                border: 1px solid #94A3B8;
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                font-size: 12px;
            }

            QHeaderView::section {
                background-color: #D9EAF7;
                color: #0F172A;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #94A3B8;
                padding: 0px;
            }
            """
        )

        return table

    # ========================================================
    # SCRAP SECTION
    # ========================================================

    def _build_scrap_table_section(
        self,
    ) -> None:

        self.scrap_title_label = QLabel(
            "Prime yield Slot by Scrapcode | "
            "EQP: - & chamber: -"
        )

        self.scrap_title_label.setFixedHeight(
            24
        )

        self.scrap_title_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: #222222;
            """
        )

        self.scrap_status_label = QLabel(
            "Vui lòng chọn EQP, Chamber "
            "và bấm Apply Filter."
        )

        self.scrap_status_label.setStyleSheet(
            """
            color: #64748B;
            font-size: 12px;
            """
        )

        self.scrap_table_model = (
            YieldSlotScrapTableModel(self)
        )

        self.scrap_fixed_table = (
            self._create_table_view()
        )

        self.scrap_fixed_table.setModel(
            self.scrap_table_model
        )

        self.scrap_fixed_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.scrap_fixed_table.setFocusPolicy(
            Qt.NoFocus
        )

        self.scrap_fixed_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.scrap_table = (
            self._create_table_view()
        )

        self.scrap_table.setModel(
            self.scrap_table_model
        )

        self.scrap_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.scrap_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.scrap_table.setHorizontalScrollMode(
            QAbstractItemView.ScrollPerPixel
        )

        self.scrap_table.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.scrap_fixed_table.verticalScrollBar().valueChanged.connect(
            self.scrap_table.verticalScrollBar().setValue
        )

        self.scrap_table.verticalScrollBar().valueChanged.connect(
            self.scrap_fixed_table.verticalScrollBar().setValue
        )

        self.scrap_table_container = QWidget()

        scrap_table_layout = QHBoxLayout(
            self.scrap_table_container
        )

        scrap_table_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        scrap_table_layout.setSpacing(
            0
        )

        self.scrap_fixed_table_container = QWidget()

        scrap_fixed_layout = QVBoxLayout(
            self.scrap_fixed_table_container
        )

        scrap_fixed_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        scrap_fixed_layout.setSpacing(
            0
        )

        scrap_fixed_layout.addWidget(
            self.scrap_fixed_table
        )

        self.scrap_fixed_bottom_spacer = QWidget()

        self.scrap_fixed_bottom_spacer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        scrap_fixed_layout.addWidget(
            self.scrap_fixed_bottom_spacer
        )

        scrap_table_layout.addWidget(
            self.scrap_fixed_table_container
        )

        scrap_table_layout.addWidget(
            self.scrap_table,
            1,
        )

    # ========================================================
    # COLUMN CONFIG
    # ========================================================

    def _needs_horizontal_scrollbar(
        self,
        table: QTableView,
    ) -> bool:

        total_width = 0

        model = table.model()

        if model is None:
            return False

        for column in range(
            model.columnCount()
        ):

            if not table.isColumnHidden(
                column
            ):

                total_width += (
                    table.columnWidth(
                        column
                    )
                )

        return (
            total_width
            > table.viewport().width()
        )

    def _configure_table_columns(
        self,
        total_columns: int,
    ) -> None:

        self.fixed_table.setUpdatesEnabled(
            False
        )

        self.slot_table.setUpdatesEnabled(
            False
        )

        try:

            for column in range(
                total_columns
            ):

                is_fixed_column = (
                    column
                    < self.FIXED_COLUMN_COUNT
                )

                self.fixed_table.setColumnHidden(
                    column,
                    not is_fixed_column,
                )

                self.slot_table.setColumnHidden(
                    column,
                    is_fixed_column,
                )

            for column, width in enumerate(
                self.FIXED_COLUMN_WIDTHS
            ):

                self.fixed_table.setColumnWidth(
                    column,
                    width,
                )

            for column in range(
                self.FIXED_COLUMN_COUNT,
                total_columns,
            ):

                self.slot_table.setColumnWidth(
                    column,
                    self.SLOT_COLUMN_WIDTH,
                )

            fixed_table_width = (
                sum(
                    self.FIXED_COLUMN_WIDTHS
                )
                + (
                    self.fixed_table.frameWidth()
                    * 2
                )
            )

            self.fixed_table.setFixedWidth(
                fixed_table_width
            )

            self.fixed_table.horizontalHeader().setOffset(
                0
            )

            self.slot_table.horizontalHeader().setOffset(
                0
            )

            self.slot_table.horizontalScrollBar().setValue(
                0
            )

        finally:

            self.fixed_table.setUpdatesEnabled(
                True
            )

            self.slot_table.setUpdatesEnabled(
                True
            )

    def _configure_scrap_table_columns(
        self,
        total_columns: int,
    ) -> None:

        self.scrap_fixed_table.setUpdatesEnabled(
            False
        )

        self.scrap_table.setUpdatesEnabled(
            False
        )

        try:

            for column in range(
                total_columns
            ):

                is_fixed_column = (
                    column
                    < self.FIXED_COLUMN_COUNT
                )

                self.scrap_fixed_table.setColumnHidden(
                    column,
                    not is_fixed_column,
                )

                self.scrap_table.setColumnHidden(
                    column,
                    is_fixed_column,
                )

            for column, width in enumerate(
                self.SCRAP_FIXED_COLUMN_WIDTHS
            ):

                self.scrap_fixed_table.setColumnWidth(
                    column,
                    width,
                )

            for column in range(
                self.FIXED_COLUMN_COUNT,
                total_columns,
            ):

                self.scrap_table.setColumnWidth(
                    column,
                    self.SCRAP_COLUMN_WIDTH,
                )

            fixed_table_width = (
                sum(
                    self.SCRAP_FIXED_COLUMN_WIDTHS
                )
                + (
                    self.scrap_fixed_table.frameWidth()
                    * 2
                )
            )

            self.scrap_fixed_table.setFixedWidth(
                fixed_table_width
            )

            self.scrap_fixed_table.horizontalHeader().setOffset(
                0
            )

            self.scrap_table.horizontalHeader().setOffset(
                0
            )

            self.scrap_table.horizontalScrollBar().setValue(
                0
            )

        finally:

            self.scrap_fixed_table.setUpdatesEnabled(
                True
            )

            self.scrap_table.setUpdatesEnabled(
                True
            )

    # ========================================================
    # HEIGHT
    # ========================================================

    def _update_table_height(
        self,
        row_count: int,
    ) -> None:

        header_height = (
            self.slot_table
            .horizontalHeader()
            .height()
        )

        needs_horizontal_scroll = (
            self._needs_horizontal_scrollbar(
                self.slot_table
            )
        )

        scrollbar_height = (
            self.slot_table
            .style()
            .pixelMetric(
                QStyle.PM_ScrollBarExtent
            )
            if needs_horizontal_scroll
            else 0
        )

        frame_height = (
            self.slot_table.frameWidth()
            * 2
        )

        rows_height = (
            row_count
            * self.ROW_HEIGHT
        )

        desired_height = (
            header_height
            + rows_height
            + scrollbar_height
            + frame_height
            + 2
        )

        desired_height = max(
            desired_height,
            80,
        )

        table_height = min(
            desired_height,
            self.MAX_TABLE_HEIGHT,
        )

        self.slot_table.setFixedHeight(
            table_height
        )

        fixed_height = max(
            table_height
            - scrollbar_height,
            1,
        )

        self.fixed_table.setFixedHeight(
            fixed_height
        )

        self.fixed_bottom_spacer.setFixedHeight(
            scrollbar_height
        )

        self.fixed_bottom_spacer.setVisible(
            needs_horizontal_scroll
        )

        self.fixed_table_container.setFixedHeight(
            table_height
        )

        self.table_container.setFixedHeight(
            table_height
        )

    def _update_scrap_table_height(
        self,
        row_count: int,
    ) -> None:

        header_height = (
            self.scrap_table
            .horizontalHeader()
            .height()
        )

        needs_horizontal_scroll = (
            self._needs_horizontal_scrollbar(
                self.scrap_table
            )
        )

        scrollbar_height = (
            self.scrap_table
            .style()
            .pixelMetric(
                QStyle.PM_ScrollBarExtent
            )
            if needs_horizontal_scroll
            else 0
        )

        frame_height = (
            self.scrap_table.frameWidth()
            * 2
        )

        rows_height = (
            row_count
            * self.ROW_HEIGHT
        )

        desired_height = (
            header_height
            + rows_height
            + scrollbar_height
            + frame_height
            + 2
        )

        desired_height = max(
            desired_height,
            80,
        )

        table_height = min(
            desired_height,
            self.MAX_TABLE_HEIGHT,
        )

        self.scrap_table.setFixedHeight(
            table_height
        )

        fixed_height = max(
            table_height
            - scrollbar_height,
            1,
        )

        self.scrap_fixed_table.setFixedHeight(
            fixed_height
        )

        self.scrap_fixed_bottom_spacer.setFixedHeight(
            scrollbar_height
        )

        self.scrap_fixed_bottom_spacer.setVisible(
            needs_horizontal_scroll
        )

        self.scrap_fixed_table_container.setFixedHeight(
            table_height
        )

        self.scrap_table_container.setFixedHeight(
            table_height
        )

    # ========================================================
    # LOAD DATA
    # ========================================================

    def load_data(
        self,
        page_result,
    ) -> None:

        daily_result = (
            page_result.daily
        )

        scrap_result = (
            page_result.scrap
        )

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        self._set_title(
            daily_result.eqp,
            daily_result.chamber,
            daily_result.date_from,
            daily_result.date_to,
        )

        # ----------------------------------------------------
        # DAILY
        # ----------------------------------------------------

        self.table_model.set_result(
            daily_result
        )

        self._configure_table_columns(
            self.table_model.columnCount()
        )

        self._update_table_height(
            row_count=len(
                daily_result.rows
            )
        )

        # ----------------------------------------------------
        # SCRAP
        # ----------------------------------------------------

        self.scrap_table_model.set_result(
            scrap_result
        )

        self._configure_scrap_table_columns(
            self.scrap_table_model.columnCount()
        )

        self._update_scrap_table_height(
            row_count=len(
                scrap_result.rows
            )
        )

        # ----------------------------------------------------
        # MACHINE SLOT YIELD
        # ----------------------------------------------------

        self._current_machine = (
            daily_result.eqp
        )

        self._machine_yield_result = list(
            page_result.machine_yield
        )

        target_15 = float(
            page_result.target_15
        )

        target_30 = float(
            page_result.target_30
        )

        self.target_15_spin.setValue(
            target_15
        )

        self.target_30_spin.setValue(
            target_30
        )

        self.machine_yield_model.set_result(
            rows=self._machine_yield_result,
            machine=self._current_machine,
            target_15=target_15,
            target_30=target_30,
        )

        self._configure_machine_yield_columns()

        self._update_machine_yield_status()

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        self.status_label.clear()
        self.status_label.hide()

        self.scrap_status_label.clear()
        self.scrap_status_label.hide()

    # ========================================================
    # SELECTION REQUIRED
    # ========================================================

    def show_selection_required(
        self,
        eqp: str | None,
        chamber: int | None,
    ) -> None:

        self._set_title(
            eqp,
            chamber,
        )

        self.table_model.clear()

        self.scrap_table_model.clear()

        self.machine_yield_model.clear()

        self._machine_yield_result = []

        self._update_table_height(
            row_count=0
        )

        self._update_scrap_table_height(
            row_count=0
        )

        self.status_label.setText(
            "Vui lòng chọn EQP, Chamber "
            "và bấm Apply Filter."
        )

        self.status_label.show()

        self.scrap_status_label.setText(
            "Vui lòng chọn EQP, Chamber "
            "và bấm Apply Filter."
        )

        self.scrap_status_label.show()

        self._update_machine_yield_status()

    # ========================================================
    # LOADING
    # ========================================================

    def set_loading(
        self,
        eqp: str,
        chamber: int,
    ) -> None:

        self._set_title(
            eqp,
            chamber,
        )

        self.status_label.setText(
            "Đang tải dữ liệu..."
        )

        self.status_label.show()

        self.scrap_status_label.setText(
            "Đang tải dữ liệu..."
        )

        self.scrap_status_label.show()

        self.machine_yield_status_label.setText(
            "Đang tải Machine / Slot Yield..."
        )

    # ========================================================
    # ERROR
    # ========================================================

    def show_error(
        self,
        error_message: str,
    ) -> None:

        self.table_model.clear()

        self.scrap_table_model.clear()

        self.machine_yield_model.clear()

        self._machine_yield_result = []

        self._update_table_height(
            row_count=0
        )

        self._update_scrap_table_height(
            row_count=0
        )

        self.status_label.setText(
            "Không thể tải dữ liệu: "
            f"{error_message}"
        )

        self.status_label.show()

        self.scrap_status_label.setText(
            "Không thể tải dữ liệu: "
            f"{error_message}"
        )

        self.scrap_status_label.show()

        self.machine_yield_status_label.setText(
            "Không thể tải Machine / Slot Yield: "
            f"{error_message}"
        )

    # ========================================================
    # INVALIDATE CACHE
    # ========================================================

    def invalidate_cache(
        self,
    ) -> None:

        self.table_model.clear()

        self.scrap_table_model.clear()

        self.machine_yield_model.clear()

        self._machine_yield_result = []

        self._update_table_height(
            row_count=0
        )

        self._update_scrap_table_height(
            row_count=0
        )

        self.status_label.setText(
            "Dữ liệu đã thay đổi. "
            "Vui lòng bấm Apply Filter."
        )

        self.status_label.show()

        self.scrap_status_label.setText(
            "Dữ liệu đã thay đổi. "
            "Vui lòng bấm Apply Filter."
        )

        self.scrap_status_label.show()

        self.machine_yield_status_label.setText(
            "Dữ liệu đã thay đổi. "
            "Vui lòng bấm Apply Filter."
        )

    # ========================================================
    # TITLE
    # ========================================================

    def _set_title(
        self,
        eqp: str | None,
        chamber: int | None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> None:

        eqp_text = (
            eqp
            or "Chọn EQP"
        )

        chamber_text = (
            str(chamber)
            if chamber is not None
            else "Chọn Chamber"
        )

        date_range_text = (
            f"{date_from} - {date_to}"
            if date_from and date_to
            else ""
        )

        self.title_label.setText(
            "Daily Prime Yield by Slot | "
            f"EQP: {eqp_text} "
            f"& Chamber: {chamber_text}"
        )

        self.scrap_title_label.setText(
            "Prime Yield Slot by Scrap Code "
            f"{date_range_text} | "
            f"EQP: {eqp_text} "
            f"& Chamber: {chamber_text}"
        )

        self.machine_yield_title_label.setText(
            "Machine / Slot Summary | "
            f"Machine: {eqp_text} "
            f"& Chamber: {chamber_text}"
        )

