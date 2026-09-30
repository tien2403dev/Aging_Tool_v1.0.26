from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QLayout,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtWidgets import QHBoxLayout

class YieldEqpTab(QWidget):
    """Hiển thị PRIME và CUM theo từng EQP."""

    CHART_WIDTH = 1300
    PLACEHOLDER_HEIGHT = 90
    PRODUCT_CHART_HEIGHT = 536

    PLACEHOLDER_TEXT = (
        "Biểu đồ sẽ được tạo sau khi chọn "
        "Scrap Code và bấm Apply Filter."
    )

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self._cached_prime_result = None
        self._cached_cum_result = None

        self._cached_prime_product_result = None
        self.prime_product_chart = None

        self.prime_chart = None
        self.cum_chart = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Tạo hai khối PRIME và CUM."""

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

        self.scroll_area.setFrameShape(
            QScrollArea.NoFrame
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
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

        main_layout.setSpacing(12)

        main_layout.setAlignment(
            Qt.AlignTop | Qt.AlignLeft
        )

        self.prime_title_label = (
            self._create_title(
                "Prime Yield Aging by EQP"
            )
        )

        self.prime_table = (
            self._create_table()
        )

        (
            self.prime_chart_container,
            self.prime_chart_layout,
            self.prime_chart_placeholder,
        ) = self._create_chart_placeholder()

        self.cum_title_label = (
            self._create_title(
                "Cum Yield Aging by EQP"
            )
        )

        self.cum_table = (
            self._create_table()
        )

        (
            self.cum_chart_container,
            self.cum_chart_layout,
            self.cum_chart_placeholder,
        ) = self._create_chart_placeholder()

        main_layout.addWidget(
            self.prime_title_label
        )

        main_layout.addWidget(
            self.prime_table
        )

        main_layout.addWidget(
            self.prime_chart_container
        )
        #TABLE PRIME YIELD BY PRODUCT
        self.prime_product_title_label = (
            self._create_title(
                "Prime Yield Aging by Product"
            )
        )

        self.prime_product_table = (
            self._create_table()
        )
        (
            self.prime_product_chart_container,
            self.prime_product_chart_layout,
            self.prime_product_chart_placeholder,
        ) = self._create_chart_placeholder(
            height=self.PRODUCT_CHART_HEIGHT,
            text=(
                "Biểu đồ sẽ được tạo sau khi chọn "
                "Model và bấm Apply Filter."
            ),
        )

        product_row_layout = QHBoxLayout()

        product_row_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        product_row_layout.setSpacing(12)

        product_row_layout.addWidget(
            self.prime_product_table,
            0,
            Qt.AlignTop,
        )

        product_row_layout.addWidget(
            self.prime_product_chart_container,
            0,
            Qt.AlignTop,
        )

        product_row_layout.addStretch()

        main_layout.addWidget(
            self.prime_product_title_label
        )

        # main_layout.addWidget(
        #     self.prime_product_table
        # )
        main_layout.addLayout(
            product_row_layout
        )
        # Bảng Yield PRIME theo Model và Scrap Code.
        self.prime_model_scrap_title_label = (
            self._create_title(
                "Prime Yield Model by Scrap Code"
            )
        )

        self.prime_model_scrap_table = (
            self._create_table()
        )

        main_layout.addWidget(
            self.prime_model_scrap_title_label
        )

        main_layout.addWidget(
            self.prime_model_scrap_table
        )
        main_layout.addSpacing(18)

        main_layout.addWidget(
            self.cum_title_label
        )


        main_layout.addSpacing(18)

        main_layout.addWidget(
            self.cum_title_label
        )

        main_layout.addWidget(
            self.cum_table
        )


        main_layout.addWidget(
            self.cum_chart_container
        )

        self.scroll_area.setWidget(
            self.scroll_content
        )

        outer_layout.addWidget(
            self.scroll_area
        )

    @staticmethod
    def _create_title(
        text: str,
    ) -> QLabel:
        """Tạo title dùng chung."""

        label = QLabel(text)

        label.setFixedHeight(24)

        label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: #222222;
            """
        )

        return label

    @staticmethod
    def _create_table() -> QTableWidget:
        """Tạo bảng động không có scroll riêng."""

        table = QTableWidget()

        table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        table.setSelectionMode(
            QAbstractItemView.NoSelection
        )

        table.verticalHeader().setVisible(
            False
        )

        table.setAlternatingRowColors(
            True
        )

        table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        # table.setHorizontalScrollBarPolicy(
        #     Qt.ScrollBarAlwaysOff
        # )
        table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        table.setHorizontalScrollMode(
            QAbstractItemView.ScrollPerPixel
        )

        table.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        table.horizontalHeader().setMinimumSectionSize(
            38
        )

        table.horizontalHeader().setFixedHeight(
            28
        )

        table.verticalHeader().setDefaultSectionSize(
            28
        )

        table.setFixedSize(
            520,
            80,
        )

        table.setStyleSheet(
            """
            QTableWidget {
                gridline-color: #222222;
                border: 1px solid #222222;
                background-color: white;
                alternate-background-color: #F8FAFC;
                font-size: 12px;
            }

            QHeaderView::section {
                background-color: #E2F0D9;
                color: #000000;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #222222;
                padding: 2px 4px;
            }
            """
        )

        return table

    def _create_chart_placeholder(
            self,
            height: int = PLACEHOLDER_HEIGHT,
            text: str | None = None,
    ):
        container = QWidget()

        layout = QVBoxLayout(container)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSizeConstraint(
            QLayout.SetFixedSize
        )

        placeholder = QLabel(
            text or self.PLACEHOLDER_TEXT
        )

        placeholder.setAlignment(
            Qt.AlignCenter
        )

        placeholder.setFixedSize(
            self.CHART_WIDTH,
            height,
        )

        placeholder.setStyleSheet(
            """
            color: #777777;
            border: 1px solid #D9D9D9;
            background-color: white;
            """
        )

        layout.addWidget(placeholder)

        return (
            container,
            layout,
            placeholder,
        )

    def set_loading(
        self,
        date_from: str,
        date_to: str,
    ) -> None:
        """Cập nhật title theo khoảng ngày."""

        self.prime_title_label.setText(
            "Prime Yield Aging by EQP: "
            f"{date_from} - {date_to}"
        )
        self.prime_product_title_label.setText(
            "Prime Yield Aging by Product | "
            f"{date_from} - {date_to}"
        )

        self.cum_title_label.setText(
            "Cum Yield Aging by EQP: "
            f"{date_from} - {date_to}"
        )
        self.prime_model_scrap_title_label.setText(
            "Prime Yield Model by Scrap Code: "
            f"{date_from} - {date_to}"
        )

    def load_data(
        self,
        result,
    ) -> None:
        """Hiển thị kết quả worker."""

        self._cached_prime_result = (
            result.prime
        )

        self._cached_cum_result = (
            result.cum
        )
        self._cached_prime_product_result = (
            result.prime_product
        )

        self.set_loading(
            result.date_from,
            result.date_to,
        )

        self._load_table(
            self.prime_table,
            result.prime,
        )
        self._load_prime_product_table(
            result.prime_product
        )
        self._load_prime_product_chart(
            product_result=result.prime_product,
            selected_models=result.selected_models,
        )
        self._load_prime_model_scrap_table(
            result.prime_model_scrap
        )

        self._load_table(
            self.cum_table,
            result.cum,
        )

        self._load_chart(
            source="PRIME",
            source_result=result.prime,
            selected_scrap_codes=(
                result.selected_scrap_codes
            ),
        )

        self._load_chart(
            source="CUM",
            source_result=result.cum,
            selected_scrap_codes=(
                result.selected_scrap_codes
            ),
        )

        self.scroll_content.adjustSize()

    def update_chart_scraps(
        self,
        selected_scrap_codes: list[str],
    ) -> None:
        """
        Chỉ cập nhật chart từ cache.

        Không query database và không sửa bảng.
        """

        if self._cached_prime_result is not None:
            self._load_chart(
                source="PRIME",
                source_result=(
                    self._cached_prime_result
                ),
                selected_scrap_codes=(
                    selected_scrap_codes
                ),
            )

        if self._cached_cum_result is not None:
            self._load_chart(
                source="CUM",
                source_result=(
                    self._cached_cum_result
                ),
                selected_scrap_codes=(
                    selected_scrap_codes
                ),
            )

    def update_product_chart_models(
            self,
            selected_models: list[str],
    ) -> None:
        """
        Chỉ vẽ lại chart Product từ cache.

        Không query database và không dựng lại bảng.
        """

        if self._cached_prime_product_result is None:
            return

        self._load_prime_product_chart(
            product_result=(
                self._cached_prime_product_result
            ),
            selected_models=selected_models,
        )

    def _load_prime_product_chart(
            self,
            product_result,
            selected_models: list[str],
    ) -> None:
        available_models = set(
            product_result.models
        )

        visible_models = [
            model
            for model in selected_models
            if model in available_models
        ]

        if not product_result.rows:
            self._show_product_chart_message(
                "Không có dữ liệu PRIME Product "
                "trong khoảng ngày đã chọn."
            )
            return

        if not visible_models:
            self._show_product_chart_message(
                "Các Model được chọn "
                "không phát sinh dữ liệu."
            )
            return

        chart = (
            self._ensure_prime_product_chart()
        )

        chart.update_chart(
            product_result=product_result,
            selected_models=visible_models,
        )

    def _ensure_prime_product_chart(
            self,
    ):
        """Lazy-import Matplotlib khi cần vẽ."""

        if self.prime_product_chart is not None:
            return self.prime_product_chart

        from ui.charts.prime_product_chart import (
            PrimeProductYieldChart,
        )

        placeholder = (
            self.prime_product_chart_placeholder
        )

        layout = (
            self.prime_product_chart_layout
        )

        layout.removeWidget(placeholder)

        placeholder.hide()
        placeholder.deleteLater()

        chart = PrimeProductYieldChart(self)

        layout.addWidget(
            chart,
            0,
            Qt.AlignLeft,
        )

        self.prime_product_chart = chart
        self.prime_product_chart_placeholder = None

        return chart

    def _show_product_chart_message(
            self,
            message: str,
    ) -> None:
        if self.prime_product_chart is not None:
            self.prime_product_chart.show_empty_state(
                message
            )
        elif (
                self.prime_product_chart_placeholder
                is not None
        ):
            self.prime_product_chart_placeholder.setText(
                message
            )

    def _load_table(
        self,
        table: QTableWidget,
        result,
    ) -> None:
        """Hiển thị metric và toàn bộ Scrap PPM."""

        fixed_headers = [
            "EQP ID",
            "IN",
            "PASS",
            "FAIL",
            "Fail PPM",
            "Yield",
        ]

        # headers = [
        #     *fixed_headers,
        #     *[
        #         # f"SC_{code}"
        #         f"{code}"
        #         for code in result.scrap_codes
        #     ],
        # ]
        headers = [
            *fixed_headers,
            *result.scrap_codes,
        ]

        all_rows = [
            *result.rows,
            result.total,
        ]

        table.setUpdatesEnabled(
            False
        )

        try:
            table.clear()

            table.setColumnCount(
                len(headers)
            )

            table.setHorizontalHeaderLabels(
                headers
            )

            table.setRowCount(
                len(all_rows)
            )

            for row_index, row in enumerate(
                all_rows
            ):
                is_total = (
                    row.eqpid == "Total"
                )

                fixed_values = [
                    row.eqpid,
                    f"{row.in_qty:,}",
                    f"{row.pass_qty:,}",
                    f"{row.fail_qty:,}",
                    self._format_ppm(
                        row.fail_ppm
                    ),
                    self._format_yield(
                        row.yield_percent
                    ),
                ]

                # scrap_values = [
                #     (
                #         ""
                #         if is_total
                #         else self._format_ppm(
                #             row.scrap_ppm_by_code.get(
                #                 scrap_code,
                #                 0.0,
                #             )
                #         )
                #     )
                #     for scrap_code in (
                #         result.scrap_codes
                #     )
                # ]
                scrap_values = []

                for scrap_code in result.scrap_codes:
                    scrap_ppm = (
                        row.scrap_ppm_by_code.get(
                            scrap_code
                        )
                    )

                    if (
                        is_total
                        or scrap_ppm is None
                        or scrap_ppm == 0
                    ):
                        value = ""
                    else:
                        value = self._format_ppm(
                            scrap_ppm
                        )

                    scrap_values.append(
                        value
                    )

                values = [
                    *fixed_values,
                    *scrap_values,
                ]

                for column_index, value in enumerate(
                    values
                ):
                    item = QTableWidgetItem(
                        value
                    )

                    item.setTextAlignment(
                        Qt.AlignCenter
                    )

                    if is_total:
                        item.setBackground(
                            QColor("#FFF2CC")
                        )

                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)

                    table.setItem(
                        row_index,
                        column_index,
                        item,
                    )

            self._fit_table_to_content(
                table
            )

        finally:
            table.setUpdatesEnabled(
                True
            )
    def _load_prime_product_table(
        self,
        result,
    ) -> None:
        """
        Hiển thị ma trận Yield PRIME
        theo EQP và Model.
        """

        headers = [
            "EQP ID",
            *result.models,
        ]

        table = (
            self.prime_product_table
        )

        table.setUpdatesEnabled(
            False
        )

        try:
            table.clear()

            table.setColumnCount(
                len(headers)
            )

            table.setHorizontalHeaderLabels(
                headers
            )

            table.setRowCount(
                len(result.rows)
            )

            # Giữ chính xác chiều rộng 60px.
            table.horizontalHeader().setSectionResizeMode(
                QHeaderView.Fixed
            )

            for column_index in range(
                len(headers)
            ):
                table.setColumnWidth(
                    column_index,
                    60,
                )

            for row_index, row in enumerate(
                result.rows
            ):
                values = [
                    row.eqpid
                ]

                for model in result.models:
                    yield_percent = (
                        row.yield_by_model.get(
                            model
                        )
                    )

                    if (
                        yield_percent is None
                        or yield_percent == 0
                    ):
                        value = ""
                    else:
                        value = (
                            f"{yield_percent:.2f}%"
                        )

                    values.append(
                        value
                    )

                for column_index, value in enumerate(
                    values
                ):
                    item = QTableWidgetItem(
                        value
                    )

                    item.setTextAlignment(
                        Qt.AlignCenter
                    )

                    table.setItem(
                        row_index,
                        column_index,
                        item,
                    )

            self._fit_product_table_to_content()

        finally:
            table.setUpdatesEnabled(
                True
            )

    def _fit_product_table_to_content(
        self,
    ) -> None:
        """
        Giữ mỗi cột rộng 60px.

        Không tạo scroll dọc riêng.
        Nếu có nhiều Model thì tạo scroll ngang.
        """

        table = (
            self.prime_product_table
        )

        header = (
            table.horizontalHeader()
        )

        column_width = 60
        row_height = 28

        content_width = (
            table.frameWidth() * 2
            + table.columnCount()
            * column_width
            + 2
        )

        available_width = max(
            520,
            self.scroll_area.viewport().width()
            - 24,
        )

        visible_width = min(
            content_width,
            available_width,
        )

        table_height = (
            table.frameWidth() * 2
            + header.height()
            + table.rowCount()
            * row_height
            + 2
        )

        # Chừa chiều cao cho scrollbar ngang.
        if content_width > visible_width:
            table_height += (
                table.horizontalScrollBar()
                .sizeHint()
                .height()
            )

        table.setFixedSize(
            visible_width,
            table_height,
        )

    def _load_prime_model_scrap_table(
            self,
            result,
    ) -> None:
        """Hiển thị Yield và số lỗi theo từng Model."""

        table = self.prime_model_scrap_table

        headers = [
            "Model",
            "Input",
            "Pass",
            "Fail",
            "Yield",
            *result.scrap_codes,
        ]

        total_row_index = len(
            result.rows
        )

        table.setUpdatesEnabled(
            False
        )

        try:
            table.clear()
            table.clearSpans()

            table.setColumnCount(
                len(headers)
            )

            table.setHorizontalHeaderLabels(
                headers
            )

            # Các dòng Model và một dòng Total.
            table.setRowCount(
                total_row_index + 1
            )

            for row_index, row in enumerate(
                    result.rows
            ):
                values = [
                    row.model,
                    (
                        str(row.in_qty)
                        if row.in_qty > 0
                        else ""
                    ),
                    (
                        str(row.pass_qty)
                        if row.pass_qty > 0
                        else ""
                    ),
                    (
                        str(row.fail_qty)
                        if row.fail_qty > 0
                        else ""
                    ),
                    (
                        f"{row.yield_percent:.2f}%"
                        if (
                                row.yield_percent is not None
                                and row.yield_percent != 0
                        )
                        else ""
                    ),
                ]

                for scrap_code in result.scrap_codes:
                    scrap_qty = (
                        row.scrap_qty_by_code.get(
                            scrap_code,
                            0,
                        )
                    )

                    values.append(
                        str(scrap_qty)
                        if scrap_qty > 0
                        else ""
                    )

                for column_index, value in enumerate(
                        values
                ):
                    item = QTableWidgetItem(
                        value
                    )

                    item.setTextAlignment(
                        Qt.AlignCenter
                    )

                    table.setItem(
                        row_index,
                        column_index,
                        item,
                    )

            # Dòng Total chỉ hiển thị tổng từng mã lỗi.
            total_item = QTableWidgetItem(
                "Total"
            )

            total_item.setTextAlignment(
                Qt.AlignCenter
            )

            total_item.setBackground(
                QColor("#FFF2CC")
            )

            total_font = total_item.font()
            total_font.setBold(True)
            total_item.setFont(total_font)

            table.setItem(
                total_row_index,
                0,
                total_item,
            )

            for column_index, scrap_code in enumerate(
                    result.scrap_codes,
                    start=5,
            ):
                total_qty = (
                    result.total_scrap_qty_by_code.get(
                        scrap_code,
                        0,
                    )
                )

                item = QTableWidgetItem(
                    str(total_qty)
                    if total_qty > 0
                    else ""
                )

                item.setTextAlignment(
                    Qt.AlignCenter
                )

                item.setBackground(
                    QColor("#FFF2CC")
                )

                font = item.font()
                font.setBold(True)
                item.setFont(font)

                table.setItem(
                    total_row_index,
                    column_index,
                    item,
                )

            # Fit trước khi span để chữ Total không
            # làm rộng riêng cột Model.
            self._fit_table_to_content(
                table,
                fixed_column_count=5,
            )

            # Gộp năm cột Model → Yield
            # cho ô Total giống bảng mẫu.
            table.setSpan(
                total_row_index,
                0,
                1,
                5,
            )

        finally:
            table.setUpdatesEnabled(
                True
            )
    def _load_chart(
        self,
        source: str,
        source_result,
        selected_scrap_codes: list[str],
    ) -> None:
        """Lazy-create chart và vẽ mã lỗi được chọn."""

        available_codes = set(
            source_result.scrap_codes
        )

        visible_codes = [
            code
            for code in selected_scrap_codes
            if code in available_codes
        ]

        if not source_result.rows:
            self._show_chart_message(
                source,
                (
                    f"Không có dữ liệu {source} "
                    "trong khoảng ngày đã chọn."
                ),
            )
            return

        if not visible_codes:
            self._show_chart_message(
                source,
                (
                    "Các Scrap Code được chọn "
                    "không phát sinh dữ liệu."
                ),
            )
            return

        chart = self._ensure_chart(
            source
        )

        chart.update_chart(
            daily_result=source_result,
            selected_scrap_codes=(
                visible_codes
            ),
        )

    def _ensure_chart(
        self,
        source: str,
    ):
        """Chỉ import Matplotlib khi cần vẽ."""

        if source == "PRIME":
            if self.prime_chart is not None:
                return self.prime_chart

            layout = self.prime_chart_layout
            placeholder = (
                self.prime_chart_placeholder
            )

            chart_title = (
                "Prime Yield Aging By EQP"
            )

            empty_message = (
                "Không có dữ liệu PRIME."
            )
        else:
            if self.cum_chart is not None:
                return self.cum_chart

            layout = self.cum_chart_layout
            placeholder = (
                self.cum_chart_placeholder
            )

            chart_title = (
                "Cum Yield Aging By EQP"
            )

            empty_message = (
                "Không có dữ liệu CUM."
            )

        from ui.charts.cum_daily_chart import (
            CumDailyStackedChart,
        )

        layout.removeWidget(
            placeholder
        )

        placeholder.hide()
        placeholder.deleteLater()

        # chart = CumDailyStackedChart(
        #     self,
        #     chart_title=chart_title,
        #     empty_data_message=empty_message,
        #     x_value_attribute="eqpid",
        #     format_x_as_date=False,
        #     show_eqp_in_title=False,
        #     yield_label_suffix="%",
        # )
        chart = CumDailyStackedChart(
            self,
            chart_title=chart_title,
            empty_data_message=empty_message,
            x_value_attribute="eqpid",
            format_x_as_date=False,
            show_eqp_in_title=False,
            yield_label_suffix="%",

            # Chỉ áp dụng cho chart Yield EQP.
            chart_width=1300,
            bar_width_pixels=30,
            legend_columns=15,
            force_horizontal_x_labels=True,
        )

        layout.addWidget(
            chart,
            0,
            Qt.AlignLeft,
        )

        if source == "PRIME":
            self.prime_chart = chart
            self.prime_chart_placeholder = None
        else:
            self.cum_chart = chart
            self.cum_chart_placeholder = None

        return chart

    def _show_chart_message(
        self,
        source: str,
        message: str,
    ) -> None:
        """Hiển thị trạng thái chart."""

        if source == "PRIME":
            chart = self.prime_chart
            placeholder = (
                self.prime_chart_placeholder
            )
        else:
            chart = self.cum_chart
            placeholder = (
                self.cum_chart_placeholder
            )

        if chart is not None:
            chart.show_empty_state(
                message
            )
        elif placeholder is not None:
            placeholder.setText(
                message
            )

    def invalidate_cache(self) -> None:
        """Xóa cache sau khi import dữ liệu."""

        self._cached_prime_result = None
        self._cached_cum_result = None

        self.prime_table.setRowCount(0)
        self.prime_product_table.setRowCount(0)
        self.cum_table.setRowCount(0)
        self.prime_model_scrap_table.setRowCount(0)

        self._show_chart_message(
            "PRIME",
            self.PLACEHOLDER_TEXT,
        )

        self._show_chart_message(
            "CUM",
            self.PLACEHOLDER_TEXT,
        )
        self._cached_prime_product_result = None

        self._show_product_chart_message(
            "Biểu đồ sẽ được tạo sau khi chọn "
            "Model và bấm Apply Filter."
        )

    def show_error(
        self,
        error_message: str,
    ) -> None:
        """Hiển thị lỗi của worker."""

        self.invalidate_cache()

        self.prime_title_label.setText(
            "Prime Yield Aging by EQP | "
            f"{error_message}"
        )
        self.prime_product_title_label.setText(
            "Prime Yield Aging by Product | "
            f"{error_message}"
        )

        self.cum_title_label.setText(
            "Cum Yield Aging by EQP | "
            f"{error_message}"
        )

        self._show_chart_message(
            "PRIME",
            "Không thể tải dữ liệu.",
        )

        self._show_chart_message(
            "CUM",
            "Không thể tải dữ liệu.",
        )
        self._show_product_chart_message(
            "Không thể tải dữ liệu."
        )
        self.prime_model_scrap_title_label.setText(
            "Prime Yield Model by Scrap Code | "
            f"{error_message}"
        )

    def _fit_table_to_content(
            self,
            table: QTableWidget,
            fixed_column_count: int = 6,
    ) -> None:
        """
        Co từng cột vừa nội dung.

        Nếu tổng chiều rộng lớn hơn vùng hiển thị,
        bảng giữ chiều rộng bằng màn hình và xuất hiện
        thanh cuộn ngang riêng.
        """

        header = table.horizontalHeader()

        # Sáu cột metric cố định.
        for column_index in range(
                min(
                    fixed_column_count,
                    table.columnCount(),
                )
        ):
            table.resizeColumnToContents(
                column_index
            )

        table_font_metrics = (
            table.fontMetrics()
        )

        header_font_metrics = (
            header.fontMetrics()
        )

        # Các cột Scrap Code chỉ rộng vừa đủ nội dung.
        for column_index in range(
                fixed_column_count,
                table.columnCount(),
        ):
            header_item = (
                table.horizontalHeaderItem(
                    column_index
                )
            )

            header_text = (
                header_item.text()
                if header_item is not None
                else ""
            )

            column_width = (
                header_font_metrics.horizontalAdvance(
                    header_text
                )
                + 12
            )

            for row_index in range(
                table.rowCount()
            ):
                item = table.item(
                    row_index,
                    column_index,
                )

                if item is None:
                    continue

                text_width = (
                    table_font_metrics.horizontalAdvance(
                        item.text()
                    )
                    + 12
                )

                column_width = max(
                    column_width,
                    text_width,
                )

            table.setColumnWidth(
                column_index,
                max(
                    38,
                    column_width,
                ),
            )

        content_width = (
            table.frameWidth() * 2
            + 2
        )

        for column_index in range(
            table.columnCount()
        ):
            content_width += (
                table.columnWidth(
                    column_index
                )
            )

        available_width = max(
            520,
            self.scroll_area.viewport().width()
            - 24,
        )

        visible_width = min(
            content_width,
            available_width,
        )

        table_height = (
            table.frameWidth() * 2
            + header.height()
            + 2
        )

        for row_index in range(
            table.rowCount()
        ):
            table_height += table.rowHeight(
                row_index
            )

        # Chừa chiều cao cho horizontal scrollbar.
        if content_width > visible_width:
            table_height += (
                table.horizontalScrollBar()
                .sizeHint()
                .height()
            )

        table.setFixedSize(
            visible_width,
            table_height,
        )

    @staticmethod
    def _format_ppm(
        value: float | None,
    ) -> str:
        """PPM làm tròn, không dùng dấu phẩy."""

        if value is None:
            return "—"

        return f"{value:.0f}"

    @staticmethod
    def _format_yield(
        value: float | None,
    ) -> str:
        """Định dạng Yield."""

        if value is None:
            return "—"

        return f"{value:.2f}%"