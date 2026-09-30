from __future__ import annotations

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)


class SumTab(QWidget):
    """
    Tab Sum. Hiện chỉ chứa khối CUM theo EQPID.
    """

    EMPTY_DAILY_WIDTH = 520
    EMPTY_DAILY_HEIGHT = 80

    DAILY_CHART_PLACEHOLDER_TEXT = (
        "Biểu đồ Daily sẽ được tạo sau khi chọn "
        "EQP, Scrap Code và bấm Apply Filter"
    )

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)
        self._cached_daily_result = None
        self._cached_prime_daily_result = None
        self._build_ui()

    def _build_ui(
        self,
    ) -> None:
        """Tạo bảng CUM bên trái và biểu đồ bên phải."""

        outer_layout = QVBoxLayout(self)

        outer_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.scroll_area = QScrollArea(self)

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.scroll_area.setFrameShape(
            QScrollArea.NoFrame
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

        main_layout.setSpacing(0)

        self.scroll_area.setWidget(
            self.scroll_content
        )

        outer_layout.addWidget(
            self.scroll_area
        )

        content_layout = QHBoxLayout()

        content_layout.setSpacing(28)
        content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        today = QDate.currentDate().toString(
            "yyyyMMdd"
        )

        self.summary_title_label = QLabel(
            "Cum Yield Aging summary: "
            # f"{today} - {today}"
        )

        self.summary_title_label.setFixedHeight(24)

        self.summary_title_label.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        self.summary_title_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: #222222;
            """
        )

        #CUM SUMMARY TABLE
        self.summary_table = QTableWidget()
        self.summary_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.summary_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.summary_table.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        self.summary_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        self.summary_table.horizontalHeader().setStretchLastSection(
            False
        )

        self.summary_table.horizontalHeader().setDefaultSectionSize(
            82
        )

        self.summary_table.verticalHeader().setDefaultSectionSize(
            28
        )

        self.summary_table.horizontalHeader().setFixedHeight(
            28
        )

        self.summary_table.setStyleSheet(
            """
            QTableWidget {
                gridline-color: #222222;
                border: 1px solid #222222;
                font-size: 13px;
            }

            QHeaderView::section {
                background-color: #E2F0D9;
                color: #000000;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #222222;
                padding: 4px;
            }
            """
        )
        self.summary_table.setColumnCount(6)

        self.summary_table.setHorizontalHeaderLabels(
            [
                "EQPID",
                "In Qty",
                "Out Qty",
                "Fail Qty",
                "Fail PPM",
                "Yield",
            ]
        )

        self.summary_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.summary_table.setSelectionMode(
            QAbstractItemView.NoSelection
        )

        self.summary_table.setAlternatingRowColors(True)

        self.summary_table.verticalHeader().setVisible(
            False
        )

        self.summary_table.horizontalHeader().setStretchLastSection(
            True
        )

        self.summary_table.setMinimumWidth(520)
        self.summary_table.setMinimumHeight(330)

        #CUM SUMMARY CHART
        self.chart = None

        self.chart_container = QWidget()

        self.chart_layout = QVBoxLayout(
            self.chart_container
        )

        self.chart_layout.setContentsMargins(
            0,
            30,
            0,
            0,
        )

        self.chart_placeholder_label = QLabel(
            "Biểu đồ sẽ được tạo khi bấm Apply Filter."
        )

        self.chart_placeholder_label.setAlignment(
            Qt.AlignCenter
        )

        self.chart_placeholder_label.setStyleSheet(
            "color: #777777;"
        )

        self.chart_layout.addWidget(
            self.chart_placeholder_label
        )

        #CUM DAILY TALE BY EQP
        self.daily_title_label = QLabel(
            "Cum Yield Aging Daily | "
            "Vui lòng chọn EQP"
        )

        self.daily_title_label.setFixedHeight(24)

        self.daily_title_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: #222222;
            """
        )

        self.cum_warning_label = QLabel()
        self.cum_warning_label.setWordWrap(True)
        self.cum_warning_label.setStyleSheet(
            """
            color: #C2410C;

            border-radius: 4px;
            padding: 6px 8px;
            font-size: 12px;
            font-weight: 400;
            """
        )
        self.cum_warning_label.hide()

        self.daily_table = QTableWidget()

        self.daily_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.daily_table.setSelectionMode(
            QAbstractItemView.NoSelection
        )

        self.daily_table.verticalHeader().setVisible(
            False
        )

        self.daily_table.setAlternatingRowColors(
            True
        )

        self.daily_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.daily_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.daily_table.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        self.daily_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        self.daily_table.horizontalHeader().setFixedHeight(
            24
        )

        self.daily_table.verticalHeader().setDefaultSectionSize(
            24
        )

        self.daily_table.setStyleSheet(
            """
            QTableWidget {
                gridline-color: #D9D9D9;
                border: 1px solid #BFBFBF;
                background-color: white;
                alternate-background-color: #F8FAFC;
                font-size: 12px;
            }

            QHeaderView::section {
                background-color: #E2F0D9;
                color: #000000;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #BFBFBF;
                padding: 4px 8px;
            }
            """
        )
        self.daily_table.setRowCount(0)
        self.daily_table.setColumnCount(0)

        self.daily_table.setFixedSize(
            self.EMPTY_DAILY_WIDTH,
            self.EMPTY_DAILY_HEIGHT,
        )
        # CUM DAILY CHART BY EQP
        self.daily_chart = None

        self.daily_chart_container = QWidget()

        self.daily_chart_layout = QVBoxLayout(
            self.daily_chart_container
        )

        self.daily_chart_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.daily_chart_layout.setSizeConstraint(
            QLayout.SetFixedSize
        )

        self.daily_chart_placeholder_label = QLabel(
            self.DAILY_CHART_PLACEHOLDER_TEXT
        )

        self.daily_chart_placeholder_label.setAlignment(
            Qt.AlignCenter
        )

        self.daily_chart_placeholder_label.setFixedSize(
            self.EMPTY_DAILY_WIDTH,
            self.EMPTY_DAILY_HEIGHT,
        )

        self.daily_chart_placeholder_label.setStyleSheet(
            """
            color: #777777;
            border: 1px solid #D9D9D9;
            background-color: white;
            """
        )

        self.daily_chart_layout.addWidget(
            self.daily_chart_placeholder_label
        )

        # PRIME DAILY TABLE BY EQP
        self.prime_daily_title_label = QLabel(
            "Prime Yield Aging Daily | "
            "Vui lòng chọn EQP"
        )

        self.prime_daily_title_label.setFixedHeight(24)

        self.prime_daily_title_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: #222222;
            """
        )

        self.prime_daily_table = (
            self._create_empty_daily_table()
        )

        # PRIME DAILY CHART BY EQP
        self.prime_daily_chart = None
        self.prime_daily_chart_container = QWidget()

        self.prime_daily_chart_layout = QVBoxLayout(
            self.prime_daily_chart_container
        )

        self.prime_daily_chart_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.prime_daily_chart_layout.setSizeConstraint(
            QLayout.SetFixedSize
        )

        self.prime_daily_chart_placeholder_label = QLabel(
            self.DAILY_CHART_PLACEHOLDER_TEXT
        )

        self.prime_daily_chart_placeholder_label.setAlignment(
            Qt.AlignCenter
        )

        self.prime_daily_chart_placeholder_label.setFixedSize(
            self.EMPTY_DAILY_WIDTH,
            self.EMPTY_DAILY_HEIGHT,
        )

        self.prime_daily_chart_placeholder_label.setStyleSheet(
            """
            color: #777777;
            border: 1px solid #D9D9D9;
            background-color: white;
            """
        )

        self.prime_daily_chart_layout.addWidget(
            self.prime_daily_chart_placeholder_label
        )

        table_layout = QVBoxLayout()

        table_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        table_layout.setSpacing(6)

        table_layout.setAlignment(
            Qt.AlignTop
        )

        table_layout.setSizeConstraint(
            QLayout.SetFixedSize
        )

        table_layout.addWidget(
            self.summary_title_label
        )

        table_layout.addWidget(
            self.summary_table
        )

        table_container = QWidget()

        table_container.setLayout(
            table_layout
        )
        table_container.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        content_layout.addWidget(
            table_container,
            0,
            Qt.AlignTop,
        )

        content_layout.addWidget(
            self.chart_container,
            0,
            Qt.AlignTop,
        )

        content_layout.addStretch(1)
        #ADD TABLE, CHART SUMMARY
        main_layout.addLayout(
            content_layout
        )

        main_layout.addSpacing(12)

        main_layout.addWidget(
            self.daily_title_label,
            0,
            Qt.AlignLeft,
        )

        main_layout.addWidget(
            self.cum_warning_label
        )

        main_layout.addWidget(
            self.daily_table,
            0,
            Qt.AlignLeft,
        )

        main_layout.addSpacing(12)

        main_layout.addWidget(
            self.daily_chart_container,
            0,
            Qt.AlignLeft,
        )
        main_layout.addSpacing(20)

        main_layout.addWidget(
            self.prime_daily_title_label,
            0,
            Qt.AlignLeft,
        )

        main_layout.addWidget(
            self.prime_daily_table,
            0,
            Qt.AlignLeft,
        )

        main_layout.addSpacing(12)

        main_layout.addWidget(
            self.prime_daily_chart_container,
            0,
            Qt.AlignLeft,
        )

        main_layout.addStretch()

    def set_loading(
            self,
            date_from: str,
            date_to: str,
    ) -> None:
        """
        Cập nhật tiêu đề theo khoảng ngày đang được tải.

        date_from và date_to đã có định dạng yyyyMMdd.
        """

        self.summary_title_label.setText(
            "Cum Yield Aging summary: "
            f"{date_from} - {date_to}"
        )

    def load_sum_data(
            self,
            result,
    ) -> None:
        """Chỉ cập nhật phần worker vừa tải lại."""

        if result.eqp_summary is not None:
            self._load_summary_table(
                rows=result.eqp_summary.rows,
                total=result.eqp_summary.total,
            )

            self._ensure_chart()

            self.chart.update_chart(
                result.eqp_summary.rows
            )

        if result.missing_cum_dates is not None:
            self._show_missing_cum_warning(
                result.missing_cum_dates
            )

        if result.daily_summary is not None:
            self._cached_daily_result = (
                result.daily_summary
            )

            self._load_daily_table(
                result.daily_summary
            )

            self._load_daily_chart(
                daily_result=(
                    result.daily_summary
                ),
                selected_scrap_codes=(
                    result.selected_scrap_codes
                ),
            )
        if result.prime_daily_summary is not None:
            self._cached_prime_daily_result = (
                result.prime_daily_summary
            )

            self._load_prime_daily_table(
                result.prime_daily_summary
            )

            self._load_prime_daily_chart(
                daily_result=(
                    result.prime_daily_summary
                ),
                selected_scrap_codes=(
                    result.selected_scrap_codes
                ),
            )

    def update_daily_chart_scraps(
            self,
            selected_scrap_codes: list[str],
    ) -> None:
        """
        Chỉ vẽ lại chart Daily.

        Không query database và không dựng lại bảng.
        """
        if self._cached_daily_result is not None:
            self._load_daily_chart(
                daily_result=(
                    self._cached_daily_result
                ),
                selected_scrap_codes=(
                    selected_scrap_codes
                ),
            )

        if self._cached_prime_daily_result is not None:
            self._load_prime_daily_chart(
                daily_result=(
                    self._cached_prime_daily_result
                ),
                selected_scrap_codes=(
                    selected_scrap_codes
                ),
            )

    def invalidate_cache(
            self,
    ) -> None:
        """Xóa cache khi CUM được import lại."""

        self._cached_daily_result = None
        self._cached_prime_daily_result = None

    def invalidate_prime_cache(
            self,
    ) -> None:
        """Xóa riêng cache Prime Daily."""

        self._cached_prime_daily_result = None

    def show_error(
            self,
            error_message: str,
            clear_summary: bool = True,
            clear_daily: bool = True,
            clear_missing_dates: bool = True,
            clear_prime_daily: bool = True,
    ) -> None:
        """Chỉ xóa phần vừa query bị lỗi."""

        if clear_summary:
            self.summary_table.setRowCount(0)

            if self.chart is not None:
                self.chart.show_empty_state(
                    "Không thể tải dữ liệu."
                )

        if clear_missing_dates:
            self.cum_warning_label.hide()

        if clear_daily:
            self._cached_daily_result = None
            self.daily_table.setRowCount(0)

            self.daily_title_label.setText(
                "Cum Yield Aging Daily | "
                "Không thể tải dữ liệu"
            )

            if self.daily_chart is not None:
                self.daily_chart.show_empty_state(
                    "Không thể tải dữ liệu Daily."
                )
            else:
                self.daily_chart_placeholder_label.setText(
                    "Không thể tải dữ liệu Daily."
                )
        if clear_prime_daily:
            self._cached_prime_daily_result = None
            self.prime_daily_table.setRowCount(0)

            self.prime_daily_title_label.setText(
                "Prime Yield Aging Daily | "
                "Không thể tải dữ liệu"
            )

            if self.prime_daily_chart is not None:
                self.prime_daily_chart.show_empty_state(
                    "Không thể tải dữ liệu Prime Daily."
                )
            else:
                self.prime_daily_chart_placeholder_label.setText(
                    "Không thể tải dữ liệu Prime Daily."
                )

    def _show_missing_cum_warning(
            self,
            missing_dates: list[str],
    ) -> None:
        """
        Hiện các ngày thiếu CUM trên cùng một dòng,
        phân cách bằng dấu phẩy.
        """

        if not missing_dates:
            self.cum_warning_label.clear()
            self.cum_warning_label.hide()
            return

        dates_text = ", ".join(
            missing_dates
        )

        self.cum_warning_label.setText(
            "Warning: Dữ liệu Cum ngày "
            f"{dates_text} chưa được update"
        )

        self.cum_warning_label.show()

    def _load_summary_table(
        self,
        rows,
        total,
    ) -> None:
        """Đổ các dòng EQPID và dòng Total vào QTableWidget."""
        self.summary_table.setUpdatesEnabled(
            False
        )
        all_rows = [
            *rows,
            total,
        ]

        self.summary_table.setRowCount(
            len(all_rows)
        )

        for row_index, row in enumerate(all_rows):
            is_total_row = row.eqpid == "Total"

            values = [
                row.eqpid,
                f"{row.in_qty:,}",
                f"{row.out_qty:,}",
                f"{row.fail_qty:,}",
                self._format_ppm(row.fail_ppm),
                self._format_yield(
                    row.yield_percent
                ),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)

                if column_index == 0:
                    item.setTextAlignment(
                        Qt.AlignLeft
                        | Qt.AlignVCenter
                    )
                else:
                    item.setTextAlignment(
                        Qt.AlignRight
                        | Qt.AlignVCenter
                    )

                if is_total_row:
                    item.setBackground(
                        Qt.lightGray
                    )

                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                self.summary_table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        self._fit_table_to_content()
        self.summary_table.setUpdatesEnabled(
            True
        )

    @staticmethod
    def _format_ppm(
        value: float | None,
    ) -> str:
        """Định dạng Fail PPM để hiển thị trên bảng."""

        if value is None:
            return "—"

        return f"{value:,.0f}"

    @staticmethod
    def _format_yield(
        value: float | None,
    ) -> str:
        """Định dạng Yield phần trăm để hiển thị trên bảng."""

        if value is None:
            return "—"

        return f"{value:.2f}%"

    def _ensure_chart(
            self,
    ) -> None:
        """
        Chỉ import Matplotlib và tạo biểu đồ
        khi người dùng Apply Filter lần đầu.
        """

        if self.chart is not None:
            return

        from ui.charts.cum_eqp_chart import (
            CumEqpChart,
        )

        self.chart_layout.removeWidget(
            self.chart_placeholder_label
        )

        self.chart_placeholder_label.hide()
        self.chart_placeholder_label.deleteLater()
        self.chart_placeholder_label = None

        self.chart = CumEqpChart(self)

        self.chart_layout.addWidget(
            self.chart,
            0,
            Qt.AlignTop,
        )

    def _ensure_daily_chart(
            self,
    ) -> bool:
        """
        Chỉ import Matplotlib và tạo chart Daily
        sau khi người dùng bấm Apply Filter.
        """

        if self.daily_chart is not None:
            return False

        from ui.charts.cum_daily_chart import (
            CumDailyStackedChart,
        )

        self.daily_chart_layout.removeWidget(
            self.daily_chart_placeholder_label
        )

        self.daily_chart_placeholder_label.hide()
        self.daily_chart_placeholder_label.deleteLater()
        self.daily_chart_placeholder_label = None

        self.daily_chart = CumDailyStackedChart(
            self
        )

        self.daily_chart_layout.addWidget(
            self.daily_chart,
            0,
            Qt.AlignLeft,
        )
        return True

    def _load_daily_chart(
            self,
            daily_result,
            selected_scrap_codes: list[str],
    ) -> None:
        """
        Vẽ chart bằng các Scrap Code đang được tick.

        Bảng Daily vẫn giữ toàn bộ mã lỗi.
        """
        if not daily_result.eqpid:
            self._show_daily_chart_message(
                self.DAILY_CHART_PLACEHOLDER_TEXT
            )
            return

        if not selected_scrap_codes:
            self._show_daily_chart_message(
                self.DAILY_CHART_PLACEHOLDER_TEXT
            )
            return

        available_codes = set(
            daily_result.scrap_codes
        )

        has_available_code = any(
            code in available_codes
            for code in selected_scrap_codes
        )

        if not has_available_code:
            self._show_daily_chart_message(
                "Các Scrap Code được chọn "
                "không phát sinh dữ liệu."
            )
            return

        chart_was_created = (
            self._ensure_daily_chart()
        )

        self.daily_chart.update_chart(
            daily_result=daily_result,
            selected_scrap_codes=(
                selected_scrap_codes
            ),
        )

        # Chart có kích thước cố định.
        # Chỉ adjust layout khi tạo lần đầu.
        if chart_was_created:
            self.scroll_content.adjustSize()

    def _show_daily_chart_message(
            self,
            message: str,
    ) -> None:
        """Hiển thị trạng thái của chart Daily."""

        if self.daily_chart is not None:
            self.daily_chart.show_empty_state(
                message
            )

            return

        self.daily_chart_placeholder_label.setText(
            message
        )

    def _fit_table_to_content(
            self,
    ) -> None:
        """
        Co bảng đúng bằng số dòng và độ rộng cột.
        Không xuất hiện thanh cuộn.
        """

        self.summary_table.resizeColumnsToContents()

        table_width = (
                self.summary_table.frameWidth() * 2
        )

        for column_index in range(
                self.summary_table.columnCount()
        ):
            table_width += self.summary_table.columnWidth(
                column_index
            )

        table_height = (
                self.summary_table.frameWidth() * 2
                + self.summary_table.horizontalHeader().height()
        )

        for row_index in range(
                self.summary_table.rowCount()
        ):
            table_height += self.summary_table.rowHeight(
                row_index
            )

        self.summary_table.setFixedWidth(
            table_width + 2
        )

        self.summary_table.setFixedHeight(
            table_height + 2
        )

    # @staticmethod
    # def _format_date(
    #         value: str,
    # ) -> str:
    #     """Chuyển YYYYMMDD thành YYYY-MM-DD để hiển thị."""
    #
    #     if len(value) != 8:
    #         return value
    #
    #     return (
    #         f"{value[:4]}-"
    #         f"{value[4:6]}-"
    #         f"{value[6:]}"
    #     )
    def _load_daily_table(
            self,
            result,
    ) -> None:
        """Hiển thị hiệu suất từng ngày của EQP được chọn."""

        # if not result.eqpid:
        #     self.daily_title_label.setText(
        #         "Cum Yield Aging Daily | "
        #         "Chọn EQP"
        #     )
        #     self.daily_table.setUpdatesEnabled(
        #         False
        #     )
        #     self.daily_table.clear()
        #     self.daily_table.setRowCount(0)
        #     self.daily_table.setColumnCount(0)
        #     self.daily_table.setFixedSize(
        #         520,
        #         80,
        #     )
        #
        #     self.scroll_content.adjustSize()
        #     return
        if not result.eqpid:
            self._cached_daily_result = None

            self.daily_title_label.setText(
                "Cum Yield Aging Daily | "
                "Chọn EQP"
            )

            self.daily_table.setUpdatesEnabled(False)

            try:
                self.daily_table.clear()
                self.daily_table.setRowCount(0)
                self.daily_table.setColumnCount(0)

                self.daily_table.setFixedSize(
                    self.EMPTY_DAILY_WIDTH,
                    self.EMPTY_DAILY_HEIGHT,
                )
            finally:
                # Bắt buộc phải bật lại để Qt xóa
                # dữ liệu cũ đang hiển thị trên màn hình.
                self.daily_table.setUpdatesEnabled(True)

            self.daily_table.viewport().update()
            self.scroll_content.adjustSize()
            return

        self.daily_title_label.setText(
            "Cum Yield Aging Daily | "
            f"EQP: {result.eqpid}"
        )

        fixed_headers = [
            "Date",
            "In Qty",
            "Pass",
            "Fail Qty",
            "Fail PPM",
            "Yield",
        ]

        headers = [
            *fixed_headers,
            *result.scrap_codes,
        ]

        self.daily_table.clear()

        self.daily_table.setColumnCount(
            len(headers)
        )

        self.daily_table.setHorizontalHeaderLabels(
            headers
        )

        self.daily_table.setRowCount(
            len(result.rows)
        )

        for row_index, row in enumerate(
                result.rows
        ):
            fixed_values = [
                row.date,
                f"{row.in_qty:,}",
                f"{row.out_qty:,}",
                f"{row.fail_qty:,}",
                self._format_daily_ppm(
                    row.fail_ppm
                ),
                self._format_daily_yield(
                    row.yield_percent
                ),
            ]

            for column_index, value in enumerate(
                    fixed_values
            ):
                self._set_daily_item(
                    row_index=row_index,
                    column_index=column_index,
                    value=value,
                )

            for code_offset, scrap_code in enumerate(
                    result.scrap_codes
            ):
                scrap_ppm = row.scrap_ppm_by_code.get(
                    scrap_code
                )

                value = (
                    ""
                    if scrap_ppm is None
                    else self._format_daily_ppm(
                        scrap_ppm
                    )
                )

                self._set_daily_item(
                    row_index=row_index,
                    column_index=(
                            len(fixed_headers)
                            + code_offset
                    ),
                    value=value,
                )

        self._fit_daily_table_to_content()
        self.daily_table.setUpdatesEnabled(
            True
        )

    def _set_daily_item(
            self,
            row_index: int,
            column_index: int,
            value: str,
            table: QTableWidget | None = None,
    ) -> None:
        """Tạo ô và căn giữa toàn bộ dữ liệu bảng Daily."""

        target_table = (
            table
            if table is not None
            else self.daily_table
        )

        item = QTableWidgetItem(value)

        item.setTextAlignment(
            Qt.AlignCenter
        )

        target_table.setItem(
            row_index,
            column_index,
            item,
        )

    def _fit_daily_table_to_content(
            self,
            table: QTableWidget | None = None,
    ) -> None:
        """
        Co bảng vừa đủ toàn bộ cột và dòng.

        Nếu không truyền table thì mặc định
        sử dụng bảng Cum Daily.
        """

        target_table = (
            table
            if table is not None
            else self.daily_table
        )

        target_table.resizeColumnsToContents()

        for row_index in range(
                target_table.rowCount()
        ):
            target_table.setRowHeight(
                row_index,
                24,
            )

        table_width = (
                target_table.frameWidth() * 2
        )

        for column_index in range(
                target_table.columnCount()
        ):
            table_width += (
                target_table.columnWidth(
                    column_index
                )
            )

        table_height = (
                target_table.frameWidth() * 2
                + target_table.horizontalHeader().height()
        )

        for row_index in range(
                target_table.rowCount()
        ):
            table_height += (
                target_table.rowHeight(
                    row_index
                )
            )

        target_table.setFixedSize(
            table_width + 2,
            table_height + 2,
        )

        self.scroll_content.adjustSize()

    @staticmethod
    def _format_daily_ppm(
            value: float | None,
    ) -> str:
        """
        Làm tròn PPM và không sử dụng
        dấu phẩy phân cách hàng nghìn.
        """

        if value is None:
            return ""

        return f"{value:.0f}"

    @staticmethod
    def _format_daily_yield(
            value: float | None,
    ) -> str:
        """Định dạng Yield; không có dữ liệu thì để trống."""

        if value is None:
            return ""

        return f"{value:.2f}%"

    def _create_empty_daily_table(
            self,
    ) -> QTableWidget:
        """Tạo bảng Daily rỗng có giao diện giống CUM Daily."""

        table = QTableWidget()

        table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        table.setSelectionMode(
            QAbstractItemView.NoSelection
        )

        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)

        table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        table.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        table.horizontalHeader().setFixedHeight(24)
        table.verticalHeader().setDefaultSectionSize(24)

        table.setStyleSheet(
            """
            QTableWidget {
                gridline-color: #D9D9D9;
                border: 1px solid #BFBFBF;
                background-color: white;
                alternate-background-color: #F8FAFC;
                font-size: 12px;
            }

            QHeaderView::section {
                background-color: #E2F0D9;
                color: #000000;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #BFBFBF;
                padding: 4px 8px;
            }
            """
        )

        table.setRowCount(0)
        table.setColumnCount(0)

        table.setFixedSize(
            self.EMPTY_DAILY_WIDTH,
            self.EMPTY_DAILY_HEIGHT,
        )

        return table

    def _load_prime_daily_table(
            self,
            result,
    ) -> None:
        """Hiển thị hiệu suất PRIME từng ngày của EQP."""

        if not result.eqpid:
            self._cached_prime_daily_result = None

            self.prime_daily_title_label.setText(
                "Prime Yield Aging Daily | "
                "Chọn EQP"
            )

            self.prime_daily_table.setUpdatesEnabled(
                False
            )

            try:
                self.prime_daily_table.clear()
                self.prime_daily_table.setRowCount(0)
                self.prime_daily_table.setColumnCount(0)

                self.prime_daily_table.setFixedSize(
                    self.EMPTY_DAILY_WIDTH,
                    self.EMPTY_DAILY_HEIGHT,
                )
            finally:
                self.prime_daily_table.setUpdatesEnabled(
                    True
                )

            self.prime_daily_table.viewport().update()
            self.scroll_content.adjustSize()
            return

        self.prime_daily_title_label.setText(
            "Prime Yield Aging Daily | "
            f"EQP: {result.eqpid}"
        )

        fixed_headers = [
            "Date",
            "In Qty",
            "Pass",
            "Fail Qty",
            "Fail PPM",
            "Yield",
        ]

        headers = [
            *fixed_headers,
            *result.scrap_codes,
        ]

        self.prime_daily_table.setUpdatesEnabled(
            False
        )

        try:
            self.prime_daily_table.clear()

            self.prime_daily_table.setColumnCount(
                len(headers)
            )

            self.prime_daily_table.setHorizontalHeaderLabels(
                headers
            )

            self.prime_daily_table.setRowCount(
                len(result.rows)
            )

            for row_index, row in enumerate(
                    result.rows
            ):
                fixed_values = [
                    row.date,
                    f"{row.in_qty:,}",
                    f"{row.out_qty:,}",
                    f"{row.fail_qty:,}",
                    self._format_daily_ppm(
                        row.fail_ppm
                    ),
                    self._format_daily_yield(
                        row.yield_percent
                    ),
                ]

                for column_index, value in enumerate(
                        fixed_values
                ):
                    self._set_daily_item(
                        row_index=row_index,
                        column_index=column_index,
                        value=value,
                        table=self.prime_daily_table,
                    )

                for code_offset, scrap_code in enumerate(
                        result.scrap_codes
                ):
                    scrap_ppm = (
                        row.scrap_ppm_by_code.get(
                            scrap_code
                        )
                    )

                    value = (
                        ""
                        if scrap_ppm is None
                        else self._format_daily_ppm(
                            scrap_ppm
                        )
                    )

                    self._set_daily_item(
                        row_index=row_index,
                        column_index=(
                                len(fixed_headers)
                                + code_offset
                        ),
                        value=value,
                        table=self.prime_daily_table,
                    )

            self._fit_daily_table_to_content(
                table=self.prime_daily_table
            )

        finally:
            self.prime_daily_table.setUpdatesEnabled(
                True
            )

    def _ensure_prime_daily_chart(
            self,
    ) -> bool:
        """Tạo chart Prime Daily khi cần hiển thị."""

        if self.prime_daily_chart is not None:
            return False

        from ui.charts.cum_daily_chart import (
            CumDailyStackedChart,
        )

        self.prime_daily_chart_layout.removeWidget(
            self.prime_daily_chart_placeholder_label
        )

        self.prime_daily_chart_placeholder_label.hide()
        self.prime_daily_chart_placeholder_label.deleteLater()
        self.prime_daily_chart_placeholder_label = None

        self.prime_daily_chart = CumDailyStackedChart(
            self,
            chart_title="Prime Yield Aging Daily",
            empty_data_message=(
                "Không có dữ liệu PRIME Daily."
            ),
        )

        self.prime_daily_chart_layout.addWidget(
            self.prime_daily_chart,
            0,
            Qt.AlignLeft,
        )

        return True

    def _load_prime_daily_chart(
            self,
            daily_result,
            selected_scrap_codes: list[str],
    ) -> None:
        """Vẽ chart Prime theo Scrap Code được chọn."""

        if not daily_result.eqpid:
            self._show_prime_daily_chart_message(
                self.DAILY_CHART_PLACEHOLDER_TEXT
            )
            return

        if not selected_scrap_codes:
            self._show_prime_daily_chart_message(
                self.DAILY_CHART_PLACEHOLDER_TEXT
            )
            return

        available_codes = set(
            daily_result.scrap_codes
        )

        has_available_code = any(
            code in available_codes
            for code in selected_scrap_codes
        )

        if not has_available_code:
            self._show_prime_daily_chart_message(
                "Các Scrap Code được chọn "
                "không phát sinh dữ liệu."
            )
            return

        chart_was_created = (
            self._ensure_prime_daily_chart()
        )

        self.prime_daily_chart.update_chart(
            daily_result=daily_result,
            selected_scrap_codes=(
                selected_scrap_codes
            ),
        )

        if chart_was_created:
            self.scroll_content.adjustSize()

    def _show_prime_daily_chart_message(
            self,
            message: str,
    ) -> None:
        """Hiển thị trạng thái chart Prime Daily."""

        if self.prime_daily_chart is not None:
            self.prime_daily_chart.show_empty_state(
                message
            )
            return

        self.prime_daily_chart_placeholder_label.setText(
            message
        )
