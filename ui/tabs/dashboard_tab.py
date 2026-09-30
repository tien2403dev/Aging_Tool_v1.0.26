from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PyQt5.QtWidgets import (
    QGridLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from repositories.dashboard_repository import DashboardRepository


class DashboardTab(QWidget):
    """Dashboard theo dõi hiện trạng cải tiến Alarm hàng ngày."""

    def __init__(
        self,
        database_path: Union[str, Path],
        parent=None,
    ):
        super().__init__(parent)
        self.database_path = Path(database_path)
        self.repository = DashboardRepository(self.database_path)
        self._cache_key = None
        self._figures = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.title_label = QLabel("Dashboard")
        self.title_label.setStyleSheet(
            "color:#1E293B;font-size:16px;font-weight:600;"
        )

        self.status_label = QLabel(
            "Chọn From, To và bấm Search."
        )
        self.status_label.setStyleSheet(
            "color:#64748B;font-size:12px;"
        )

        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)

        self.cards = {}
        card_layout = QGridLayout()
        card_layout.setSpacing(8)

        card_names = (
            ("total", "Total Alarm"),
            ("not_started", "Chưa tiến hành"),
            ("in_progress", "Đang tiến hành"),
            ("completed", "Đã hoàn thành"),
            ("quick_pass", "Quick Check PASS"),
            ("cal_pass", "CAL Check PASS"),
            ("monitor1_pass", "Monitor Day 1 PASS"),
            ("monitor2_pass", "Monitor Day 2 PASS"),
            ("monitor3_pass", "Monitor Day 3 PASS"),
            ("action_effectiveness", "Action Effectiveness"),
            ("open_action", "Open Action"),
        )

        for i, (key, title) in enumerate(card_names):
            card = QWidget()
            card.setStyleSheet(
                """
                QWidget {
                    background:#F8FAFC;
                    border:1px solid #CBD5E1;
                    border-radius:8px;
                }
                QLabel {
                    border:none;
                    background:transparent;
                }
                """
            )
            v = QVBoxLayout(card)
            v.setContentsMargins(12, 8, 12, 8)
            lbl = QLabel(title)
            lbl.setStyleSheet(
                "font-size:12px;color:#64748B;border:none;"
            )
            value = QLabel("0")
            value.setStyleSheet(
                "font-size:22px;font-weight:700;color:#0F172A;border:none;"
            )
            value.setAlignment(Qt.AlignCenter)
            v.addWidget(lbl)
            v.addWidget(value)
            self.cards[key] = value
            card_layout.addWidget(card, i // 5, i % 5)

        layout.addLayout(card_layout)

        # --------------------------------------------------------
        # BIỂU ĐỒ BÁO CÁO
        # --------------------------------------------------------
        chart_row = QGridLayout()
        chart_row.setSpacing(8)

        self.alarm_trend_canvas = FigureCanvasQTAgg(Figure(figsize=(7, 2.8)))
        self.action_trend_canvas = FigureCanvasQTAgg(Figure(figsize=(7, 2.8)))
        self.status_canvas = FigureCanvasQTAgg(Figure(figsize=(7, 2.8)))

        chart_row.addWidget(self.alarm_trend_canvas, 0, 0)
        chart_row.addWidget(self.action_trend_canvas, 0, 1)
        chart_row.addWidget(self.status_canvas, 1, 0, 1, 2)
        layout.addLayout(chart_row)

        self.table = QTableWidget(0, 13)
        self.table.setHorizontalHeaderLabels(
            [
                "Date",
                "Số lần phát sinh",
                "Chưa tiến hành",
                "Đang tiến hành",
                "Đã hoàn thành",
                "Action Effectiveness",
                "Open Action",
                "Quick PASS",
                "CAL PASS",
                "Monitor D1 PASS",
                "Monitor D2 PASS",
                "Monitor D3 PASS",
                "Action Report",
            ]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

    @staticmethod
    def _clear_canvas(canvas):
        canvas.figure.clear()
        canvas.figure.subplots_adjust(left=0.10, right=0.97, top=0.84, bottom=0.22)

    def _draw_charts(self, daily, trend, status_distribution):
        # Alarm phát sinh theo ngày
        canvas = self.alarm_trend_canvas
        self._clear_canvas(canvas)
        ax = canvas.figure.add_subplot(111)
        dates = [str(x.get("alarm_date", "")) for x in trend]
        values = [int(x.get("total_alarm_count") or 0) for x in trend]
        ax.plot(dates, values, marker="o")
        ax.set_title("Alarm phát sinh theo ngày")
        ax.set_ylabel("Số lần")
        ax.grid(True, alpha=0.25)
        ax.tick_params(axis="x", rotation=45)
        canvas.draw_idle()

        # Action Effectiveness theo ngày
        canvas = self.action_trend_canvas
        self._clear_canvas(canvas)
        ax = canvas.figure.add_subplot(111)
        dates2 = [str(x.get("alarm_date", "")) for x in daily]
        eff = []
        for x in daily:
            total = int(x.get("total_alarm") or 0)
            completed = int(x.get("completed") or 0)
            eff.append(completed / total * 100.0 if total else 0.0)
        ax.plot(dates2, eff, marker="o")
        ax.set_title("Action Effectiveness theo ngày")
        ax.set_ylabel("%")
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.25)
        ax.tick_params(axis="x", rotation=45)
        canvas.draw_idle()

        # Phân bố trạng thái Action
        canvas = self.status_canvas
        self._clear_canvas(canvas)
        ax = canvas.figure.add_subplot(111)
        labels = [str(x.get("status") or "Không xác định") for x in status_distribution]
        vals = [int(x.get("total") or 0) for x in status_distribution]
        if vals:
            ax.bar(labels, vals)
            ax.set_title("Phân bố trạng thái Action")
            ax.set_ylabel("Số Alarm")
            ax.tick_params(axis="x", rotation=20)
            for idx, val in enumerate(vals):
                ax.text(idx, val, str(val), ha="center", va="bottom")
        else:
            ax.text(0.5, 0.5, "Không có dữ liệu", ha="center", va="center")
            ax.set_title("Phân bố trạng thái Action")
            ax.set_axis_off()
        canvas.draw_idle()

    def load_data(self, date_from: str, date_to: str):
        key = (str(date_from), str(date_to))

        if self._cache_key == key and self.table.rowCount() > 0:
            return

        self._cache_key = key
        self.title_label.setText(
            f"Dashboard | {date_from} - {date_to}"
        )

        try:
            totals = self.repository.get_totals(date_from, date_to)
            daily = self.repository.get_daily(date_from, date_to)
            trend = self.repository.get_daily_trend(date_from, date_to)
            status_distribution = self.repository.get_status_distribution(date_from, date_to)
            self._draw_charts(daily, trend, status_distribution)

            total_alarm = int(
                totals.get("total_alarm") or 0
            )
            completed = int(
                totals.get("completed") or 0
            )
            open_action = max(
                total_alarm - completed,
                0,
            )
            effectiveness = (
                completed / total_alarm * 100.0
                if total_alarm
                else 0.0
            )

            for key_name, label in self.cards.items():
                if key_name == "action_effectiveness":
                    label.setText(
                        f"{effectiveness:.1f}%"
                    )
                elif key_name == "open_action":
                    label.setText(
                        f"{open_action:,}"
                    )
                else:
                    label.setText(
                        f"{int(totals.get(key_name) or 0):,}"
                    )

            self.table.setRowCount(0)

            for data in daily:
                row = self.table.rowCount()
                self.table.insertRow(row)

                daily_total = int(
                    data.get("total_alarm") or 0
                )
                daily_completed = int(
                    data.get("completed") or 0
                )
                daily_open = max(
                    daily_total - daily_completed,
                    0,
                )
                daily_effectiveness = (
                    daily_completed / daily_total * 100.0
                    if daily_total
                    else 0.0
                )

                values = [
                    data.get("alarm_date", ""),
                    daily_total,
                    data.get("not_started", 0),
                    data.get("in_progress", 0),
                    daily_completed,
                    f"{daily_effectiveness:.1f}%",
                    daily_open,
                    data.get("quick_pass", 0),
                    data.get("cal_pass", 0),
                    data.get("monitor1_pass", 0),
                    data.get("monitor2_pass", 0),
                    data.get("monitor3_pass", 0),
                    (
                        "Đạt 100%"
                        if daily_effectiveness >= 100.0
                        else "Đang xử lý"
                        if daily_effectiveness > 0
                        else "Chưa Action"
                    ),
                ]

                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value or ""))
                    item.setTextAlignment(
                        Qt.AlignCenter | Qt.AlignVCenter
                    )

                    if col == 4 and int(value or 0) > 0:
                        item.setBackground(QColor("#DCFCE7"))

                    if col == 5 and daily_total > 0:
                        item.setBackground(QColor("#DCFCE7"))

                    self.table.setItem(row, col, item)

            self.status_label.setText(
                f"Tổng {total_alarm:,} Alarm "
                f"| Action Effectiveness: {effectiveness:.1f}% "
                f"| {len(daily):,} ngày có Alarm"
            )

        except Exception as error:
            self._cache_key = None
            self.status_label.setText(
                f"Không thể tải Dashboard: {error}"
            )

    def invalidate_cache(self):
        self._cache_key = None
