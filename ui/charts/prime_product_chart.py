from __future__ import annotations

from math import ceil

from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg,
)
from matplotlib.figure import Figure
from matplotlib.ticker import (
    FuncFormatter,
    MaxNLocator,
)


class PrimeProductYieldChart(
    FigureCanvasQTAgg
):
    """Biểu đồ đường Yield PRIME theo EQP và Model."""

    MODEL_COLORS = [
        "#ED7D31",
        "#A5A5A5",
        "#4472C4",
        "#70AD47",
        "#FFC000",
        "#5B9BD5",
        "#C00000",
        "#8064A2",
        "#00B0F0",
        "#548235",
        "#BF9000",
        "#7030A0",
        "#264478",
        "#843C0C",
        "#008C95",
    ]

    def __init__(
        self,
        parent=None,
    ):
        self.figure = Figure(
            figsize=(13, 5.36),
            dpi=100,
            facecolor="white",
            edgecolor="#BFBFBF",
            linewidth=1.0,
            frameon=True,
        )

        super().__init__(self.figure)

        self.setParent(parent)

        # Kích thước chính xác theo yêu cầu.
        self.setFixedSize(
            1300,
            536,
        )

        self.setStyleSheet(
            """
            background-color: white;
            border: 1px solid #BFBFBF;
            """
        )

        self.axis = self.figure.add_subplot(111)

        self._loaded_result = None
        self._bar_containers = []
        self._annotations = []

    def show_empty_state(
        self,
        message: str,
    ) -> None:
        self.axis.clear()
        self.figure.legends.clear()

        self._loaded_result = None
        self._bar_containers.clear()
        self._annotations.clear()

        self.axis.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            transform=self.axis.transAxes,
            color="#777777",
            fontsize=11,
        )

        self.axis.set_xticks([])
        self.axis.set_yticks([])

        self.draw_idle()

    def update_chart(
            self,
            product_result,
            selected_models: list[str],
    ) -> None:
        selected_set = set(
            selected_models
        )

        visible_models = [
            model
            for model in product_result.models
            if model in selected_set
        ]

        if not product_result.rows:
            self.show_empty_state(
                "Không có dữ liệu PRIME Product."
            )
            return

        if not visible_models:
            self.show_empty_state(
                "Các Model được chọn "
                "không phát sinh dữ liệu."
            )
            return

        data_changed = (
                product_result
                is not self._loaded_result
        )

        if data_changed:
            # Date hoặc Tier đổi mới clear toàn bộ.
            self.axis.clear()
        else:
            # Chỉ đổi Model: giữ canvas và axes,
            # chỉ xóa các cột và label cũ.
            for container in self._bar_containers:
                for patch in container.patches:
                    patch.remove()

            for annotation in self._annotations:
                annotation.remove()

        self.figure.legends.clear()
        self._bar_containers.clear()
        self._annotations.clear()

        rows = product_result.rows

        positions = list(
            range(len(rows))
        )

        valid_yields = []

        all_model_positions = {
            model: index
            for index, model in enumerate(
                product_result.models
            )
        }

        # Tổng chiều rộng của một nhóm cột tại một EQP.
        group_width = 0.72

        # Tự động chia chiều rộng theo số Model được chọn.
        bar_slot_width = (
                group_width
                / max(1, len(visible_models))
        )

        # Chừa một khoảng nhỏ giữa các cột.
        actual_bar_width = (
                bar_slot_width * 0.90
        )

        legend_handles = []
        legend_labels = []

        for visible_index, model in enumerate(
                visible_models
        ):
            model_bar_positions = []
            model_values = []

            for row_index, row in enumerate(rows):
                value = row.yield_by_model.get(
                    model
                )

                # Giữ nguyên logic cũ:
                # không vẽ giá trị không tồn tại hoặc bằng 0.
                if value is None or value == 0:
                    continue

                # Căn giữa toàn bộ nhóm cột quanh vị trí EQP.
                bar_position = (
                        positions[row_index]
                        - group_width / 2
                        + bar_slot_width / 2
                        + visible_index * bar_slot_width
                )

                model_bar_positions.append(
                    bar_position
                )

                model_values.append(
                    value
                )

                valid_yields.append(
                    value
                )

            if not model_values:
                continue

            color_index = (
                    all_model_positions[model]
                    % len(self.MODEL_COLORS)
            )

            bars = self.axis.bar(
                model_bar_positions,
                model_values,
                width=actual_bar_width,
                color=self.MODEL_COLORS[
                    color_index
                ],
                edgecolor="white",
                linewidth=0.4,
                label=model,
                zorder=3,
            )

            self._bar_containers.append(
                bars
            )

            legend_handles.append(
                bars
            )

            legend_labels.append(
                model
            )

            # Data label phía trên từng cột.
            for bar, value in zip(
                    bars.patches,
                    model_values,
            ):
                annotation = self.axis.annotate(
                    f"{value:.2f}%",
                    xy=(
                        bar.get_x()
                        + bar.get_width() / 2,
                        value,
                    ),
                    xytext=(
                        0,
                        5,
                    ),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="#333333",
                    annotation_clip=False,
                    zorder=4,
                )

                self._annotations.append(
                    annotation
                )

        self.axis.set_title(
            "Prime Yield Aging by Product",
            fontsize=12,
            color="#5F5F5F",
            pad=18,
        )

        self.axis.set_ylabel(
            "Yield",
            fontsize=9,
        )

        self.axis.set_xticks(
            positions
        )

        self.axis.set_xticklabels(
            [
                row.eqpid
                for row in rows
            ],
            rotation=0,
            ha="center",
            fontsize=8,
        )

        self.axis.set_xlim(
            -0.5,
            len(rows) - 0.5,
        )

        self.axis.yaxis.set_major_formatter(
            FuncFormatter(
                lambda value, _:
                f"{value:.2f}%"
            )
        )

        self.axis.yaxis.set_major_locator(
            MaxNLocator(nbins=7)
        )

        if valid_yields:
            minimum = min(
                valid_yields
            )

            maximum = max(
                valid_yields
            )

            padding = max(
                0.5,
                (maximum - minimum) * 0.12,
            )

            lower = max(
                0.0,
                minimum - padding,
            )

            upper = min(
                102.0,
                maximum + padding,
            )

            if upper - lower < 2:
                lower = max(
                    0.0,
                    lower - 1,
                )

                upper = min(
                    102.0,
                    upper + 1,
                )

            self.axis.set_ylim(
                lower,
                upper,
            )
        else:
            self.axis.set_ylim(
                0,
                100,
            )

        self.axis.grid(
            visible=True,
            axis="y",
            color="#D9D9D9",
            linewidth=0.6,
            zorder=0,
        )

        self.axis.set_axisbelow(
            True
        )

        self.axis.tick_params(
            axis="both",
            length=0,
            labelsize=8,
            colors="#555555",
        )

        for spine in self.axis.spines.values():
            spine.set_visible(True)
            spine.set_color("#BFBFBF")
            spine.set_linewidth(0.8)

        # Tối đa 15 Model trên một hàng legend.
        if legend_handles:
            legend_columns = min(
                15,
                len(legend_handles),
            )

            legend_rows = ceil(
                len(legend_handles)
                / legend_columns
            )

            self.figure.legend(
                legend_handles,
                legend_labels,
                loc="lower center",
                ncol=legend_columns,
                frameon=False,
                fontsize=8,
                handlelength=1.2,
                columnspacing=1.2,
                bbox_to_anchor=(
                    0.5,
                    0.015,
                ),
            )
        else:
            legend_rows = 1

        self.figure.subplots_adjust(
            left=0.06,
            right=0.985,
            top=0.88,
            bottom=min(
                0.32,
                0.14
                + (legend_rows - 1) * 0.045,
            ),
        )

        self._loaded_result = (
            product_result
        )

        self.draw_idle()