from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from PyQt5.QtCore import (
    QRectF,
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
)

from PyQt5.QtGui import (
    QColor,
    QCloseEvent,
    QFont,
    QPainter,
    QPen,
)

from PyQt5.QtWidgets import (
    QAbstractButton,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)

from workers.cum_import_worker import CumImportWorker
from workers.filter_option_worker import FilterOptionWorker
from workers.prime_import_worker import PrimeImportWorker

from ui.widgets.filter_panel import FilterPanel
from ui.tabs.sum_tab import SumTab
from workers.sum_worker import SumWorker

from ui.tabs.yield_eqp_tab import YieldEqpTab
from workers.yield_eqp_worker import YieldEqpWorker

from ui.tabs.machine_slot_yield_tab import MachineSlotYieldTab

from ui.prime_log_import_dialog import PrimeLogImportDialog

from ui.tabs.alarm_tab import AlarmTab
from ui.tabs.dashboard_tab import DashboardTab
from workers.alarm_worker import AlarmWorker

from workers.chart_preload_worker import ChartPreloadWorker
from repositories.alarm_repository import AlarmRepository
from services.auto_send_mail_scheduler_service import AutoSendMailSchedulerService
from workers.mail_preload_worker import MailPreloadWorker

from ui.tabs.database_management_tab import DatabaseManagementTab
from ui.tabs.send_mail_tab import SendMailTab

from ui.widgets.loading_dialog import LoadingDialog


class ThemeToggleButton(QAbstractButton):
    """
    Nút gạt Light/Dark hiển thị trên thanh tab.
    """

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setCheckable(True)

        self.setFixedSize(
            120,
            30,
        )

        self.setCursor(
            Qt.PointingHandCursor
        )

        self.setToolTip(
            "Chuyển Light / Dark mode"
        )

    def paintEvent(
        self,
        event,
    ) -> None:

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        dark_mode = self.isChecked()

        outer_rect = QRectF(
            self.rect().adjusted(
                1,
                1,
                -1,
                -1,
            )
        )

        painter.setPen(
            QPen(
                QColor(
                    "#64748B"
                    if dark_mode
                    else "#CBD5E1"
                ),
                2,
            )
        )

        painter.setBrush(
            QColor(
                "#151B2B"
                if dark_mode
                else "#E9EDF3"
            )
        )

        painter.drawRoundedRect(
            outer_rect,
            14,
            14,
        )

        thumb_size = 24

        thumb_x = (
            self.width()
            - thumb_size
            - 3
            if dark_mode
            else 3
        )

        thumb_rect = QRectF(
            thumb_x,
            3,
            thumb_size,
            thumb_size,
        )

        painter.setPen(
            QPen(
                QColor("#94A3B8"),
                1,
            )
        )

        painter.setBrush(
            QColor(
                "#8B96AA"
                if dark_mode
                else "#FFFFFF"
            )
        )

        painter.drawEllipse(
            thumb_rect
        )

        text_font = QFont(
            "Segoe UI",
            8,
        )

        text_font.setBold(True)

        painter.setFont(
            text_font
        )

        painter.setPen(
            QColor(
                "#AAB2C0"
                if dark_mode
                else "#7C8798"
            )
        )

        text_rect = (
            QRectF(
                3,
                1,
                88,
                28,
            )
            if dark_mode
            else QRectF(
                29,
                1,
                88,
                28,
            )
        )

        painter.drawText(
            text_rect,
            Qt.AlignCenter,
            (
                "DARK\nMODE"
                if dark_mode
                else "LIGHT\nMODE"
            ),
        )

        icon_font = QFont(
            "Segoe UI Symbol",
            13,
        )

        painter.setFont(
            icon_font
        )

        painter.setPen(
            QColor(
                "#E5E7EB"
                if dark_mode
                else "#AAB2C0"
            )
        )

        painter.drawText(
            thumb_rect,
            Qt.AlignCenter,
            (
                "☾"
                if dark_mode
                else "☀"
            ),
        )


@dataclass
class FilterCriteria:
    """
    Lưu điều kiện filter chung để các tab sử dụng sau này.
    """

    date_from: str
    date_to: str
    selected_date: str | None
    eqp: str | None
    chamber: int | None
    scrap_codes: list[str]
    tiers: list[str | None]
    models: list[str]


class MainWindow(QMainWindow):
    """
    Cửa sổ chính của ứng dụng Aging Performance Monitoring.
    """

    filter_applied = pyqtSignal(object)

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        super().__init__()

        self.database_path = Path(
            database_path
        )

        # =====================================================
        # IMPORT WORKER
        # =====================================================

        self.import_thread = None
        self.import_worker = None

        # =====================================================
        # FILTER OPTION WORKER
        # =====================================================

        self.filter_option_thread = None
        self.filter_option_worker = None

        # =====================================================
        # SUM WORKER
        # =====================================================

        self.sum_thread = None
        self.sum_worker = None

        # =====================================================
        # YIELD EQP WORKER
        # =====================================================

        self.yield_eqp_thread = None
        self.yield_eqp_worker = None

        # =====================================================
        # ALARM WORKER
        # =====================================================

        self.alarm_thread = None
        self.alarm_worker = None

        # =====================================================
        # MACHINE SLOT YIELD -> ALARM
        # =====================================================

        self._pending_alarm_msy_key = None
        self._pending_alarm_msy_criteria = None

        # =====================================================
        # MACHINE SLOT YIELD RESULT CACHE
        # =====================================================

        self._machine_slot_yield_result = None
        self._machine_slot_yield_key = None

        self.loading_dialog = None

        # =====================================================
        # CHART PRELOAD
        # =====================================================

        self.chart_preload_thread = None
        self.chart_preload_worker = None

        self._chart_preload_state = "NOT_STARTED"
        self._chart_preload_error = None

        # =====================================================
        # MAIL PRELOAD
        # =====================================================

        self.mail_preload_thread = None
        self.mail_preload_worker = None

        self._mail_preload_state = "NOT_STARTED"
        self._mail_preload_error = None

        # =====================================================
        # FILTER ĐANG CHỜ
        # =====================================================

        self._pending_chart_filter_criteria = None

        self.filter_loading_dialog = None

        # =====================================================
        # CACHE
        # =====================================================

        self._last_summary_key = None
        self._last_daily_key = None
        self._last_prime_daily_key = None
        self._last_missing_dates_key = None
        self._last_scrap_key = None
        self._last_yield_eqp_model_key = None

        self._pending_sum_keys = None

        self._last_yield_eqp_data_key = None
        self._last_yield_eqp_scrap_key = None

        self._last_alarm_key = None
        self._pending_alarm_key = None

        self._reload_alarm_after_finish = False

        # Auto refresh current Search every 15 minutes.
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.setInterval(
            15 * 60 * 1000
        )
        self.auto_refresh_timer.timeout.connect(
            self._auto_refresh_current_search
        )
        self.auto_refresh_timer.start()

        self._pending_yield_eqp_keys = None

        self._latest_filter_criteria = None

        self.setWindowTitle(
            "Aging Yield Monitoring"
        )

        self.resize(
            1_100,
            650,
        )

        self._build_ui()

        # Scheduler Auto Send Mail chạy nền trong PGM.
        self.auto_send_mail_scheduler = (
            AutoSendMailSchedulerService(
                database_path=self.database_path,
                parent=self,
            )
        )
        self.auto_send_mail_scheduler.status_changed.connect(
            lambda message: print(
                f"[Auto Send Mail] {message}"
            )
        )
        self.auto_send_mail_scheduler.start()

        self._reload_filter_options()

        # Khi mở PGM, Alarm tự lấy ngày mới nhất trong DB.
        QTimer.singleShot(
            800,
            self._load_latest_alarm_on_startup,
        )

    # =========================================================
    # BUILD UI
    # =========================================================

    def _build_ui(self) -> None:

        self.central_widget = QWidget()

        self.setCentralWidget(
            self.central_widget
        )

        main_layout = QVBoxLayout(
            self.central_widget
        )

        # =====================================================
        # FILTER PANEL
        # =====================================================

        self.filter_panel = FilterPanel(
            self
        )

        self.filter_panel.import_prime_clicked.connect(
            self._choose_prime_log_folder
        )

        self.filter_panel.import_cum_clicked.connect(
            self._choose_cum_excel_file
        )

        self.filter_panel.filter_applied.connect(
            self._on_filter_applied
        )

        main_layout.addWidget(
            self.filter_panel
        )

        # =====================================================
        # TAB WIDGET
        # =====================================================

        self.tab_widget = QTabWidget()

        self.tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #D8DEE6;
                border-radius: 6px;
                background-color: #FFFFFF;
                top: -1px;
            }

            QTabBar::tab {
                min-width: 160px;
                height: 28px;
                padding-left: 0px;
                padding-right: 0px;
                margin-right: 4px;
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #D8DEE6;
                border-bottom: 2px solid transparent;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-family: "Segoe UI";
                font-size: 16px;
                font-weight: 400;
            }

            QTabBar::tab:hover {
                background-color: #E8EEF5;
                color: #1E293B;
            }

            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #1976D2;
                border-bottom: 3px solid #1976D2;
                font-weight: 500;
            }
            """
        )

        self._tab_widget_base_style = (
            self.tab_widget.styleSheet()
        )

        # =====================================================
        # SUMMARY
        # =====================================================

        self.sum_tab = SumTab(
            self
        )

        self.tab_widget.addTab(
            self.sum_tab,
            "📊 Summary",
        )

        # =====================================================
        # YIELD EQP
        # =====================================================

        self.yield_eqp_tab = YieldEqpTab(
            self
        )

        self.tab_widget.addTab(
            self.yield_eqp_tab,
            "📈 Yield EQP",
        )

        # =====================================================
        # MACHINE SLOT YIELD
        # =====================================================

        self.machine_slot_yield_tab = (
            MachineSlotYieldTab(
                database_path=self.database_path,
                parent=self,
            )
        )

        self.tab_widget.addTab(
            self.machine_slot_yield_tab,
            "🧪 Machine Slot Yield",
        )

        self.machine_slot_yield_tab.load_finished.connect(
            self._on_machine_slot_yield_load_finished
        )

        self.machine_slot_yield_tab.load_failed.connect(
            self._on_machine_slot_yield_load_failed
        )

        # =====================================================
        # ALARM
        # =====================================================

        self.alarm_tab = AlarmTab(
            database_path=self.database_path,
            parent=self,
        )

        self.tab_widget.addTab(
            self.alarm_tab,
            "🚨 Alarm",
        )

        # =====================================================
        # DASHBOARD
        # =====================================================

        self.dashboard_tab = DashboardTab(
            database_path=self.database_path,
            parent=self,
        )

        self.tab_widget.addTab(
            self.dashboard_tab,
            "📊 Dashboard",
        )

        # =====================================================
        # FILE MANAGEMENT
        # =====================================================

        self.database_management_tab = (
            DatabaseManagementTab(
                database_path=self.database_path,
                parent=self,
            )
        )

        self.tab_widget.addTab(
            self.database_management_tab,
            "🗃️ File Management",
        )

        # =====================================================
        # SEND MAIL
        # =====================================================

        self.send_mail_tab = SendMailTab(
            database_path=self.database_path,
            parent=self,
        )

        self.tab_widget.addTab(
            self.send_mail_tab,
            "📤 Send Mail",
        )

        # =====================================================
        # THEME BUTTON
        # =====================================================

        self.theme_button = ThemeToggleButton(
            self.tab_widget
        )

        self.theme_button.toggled.connect(
            self._apply_background_mode
        )

        self.theme_button.show()
        self.theme_button.raise_()

        # =====================================================
        # THEME SURFACES
        # =====================================================

        theme_surfaces = (
            self.central_widget,

            self.sum_tab,
            self.sum_tab.scroll_content,
            self.sum_tab.scroll_area.viewport(),

            self.yield_eqp_tab,
            self.yield_eqp_tab.scroll_content,
            self.yield_eqp_tab.scroll_area.viewport(),

            self.machine_slot_yield_tab,

            self.alarm_tab,
            self.dashboard_tab,
            self.database_management_tab,
        )

        self._theme_surfaces = []

        for surface in theme_surfaces:

            surface.setProperty(
                "themeSurface",
                True,
            )

            self._theme_surfaces.append(
                (
                    surface,
                    surface.styleSheet(),
                )
            )

        # =====================================================
        # THEME PANELS
        # =====================================================

        theme_panels = (
            self.filter_panel,

            self.database_management_tab.prime_panel,
            self.database_management_tab.cum_panel,
            self.database_management_tab.auto_import_panel,

            self.send_mail_tab,
            self.send_mail_tab.auto_send_mail_panel,
        )

        self._theme_panels = [
            (
                widget,
                widget.styleSheet(),
            )
            for widget in theme_panels
        ]

        # =====================================================
        # THEME LABELS
        # =====================================================

        theme_text_labels = (
            self.sum_tab.summary_title_label,
            self.sum_tab.daily_title_label,
            self.sum_tab.prime_daily_title_label,

            self.yield_eqp_tab.prime_title_label,
            self.yield_eqp_tab.cum_title_label,
            self.yield_eqp_tab.prime_product_title_label,
            self.yield_eqp_tab.prime_model_scrap_title_label,

            self.alarm_tab.title_label,
            self.alarm_tab.status_label,

            self.dashboard_tab.title_label,
            self.dashboard_tab.status_label,

            self.database_management_tab.status_label,
        )

        self._theme_text_labels = [
            (
                label,
                label.styleSheet(),
            )
            for label in theme_text_labels
        ]

        self._apply_background_mode(
            False
        )

        self.tab_widget.currentChanged.connect(
            self._on_tab_changed
        )

        main_layout.addWidget(
            self.tab_widget,
            1,
        )

        QTimer.singleShot(
            0,
            self._position_theme_button,
        )

    # =========================================================
    # THEME BUTTON POSITION
    # =========================================================

    def _position_theme_button(
        self,
    ) -> None:

        if not hasattr(
            self,
            "theme_button",
        ):
            return

        tab_bar = self.tab_widget.tabBar()

        if tab_bar.count() == 0:
            return

        send_mail_index = (
            tab_bar.count() - 1
        )

        send_mail_rect = tab_bar.tabRect(
            send_mail_index
        )

        button_x = (
            tab_bar.x()
            + send_mail_rect.right()
            + 8
        )

        button_y = (
            tab_bar.y()
            + max(
                0,
                (
                    send_mail_rect.height()
                    - self.theme_button.height()
                ) // 2,
            )
        )

        maximum_x = (
            self.tab_widget.width()
            - self.theme_button.width()
            - 4
        )

        button_x = min(
            button_x,
            maximum_x,
        )

        self.theme_button.move(
            button_x,
            button_y,
        )

        self.theme_button.raise_()

    def resizeEvent(
        self,
        event,
    ) -> None:

        super().resizeEvent(event)

        if hasattr(
            self,
            "theme_button",
        ):
            self._position_theme_button()

    # =========================================================
    # THEME
    # =========================================================

    def _apply_background_mode(
        self,
        dark_mode: bool,
    ) -> None:

        background_color = (
            "#202838"
            if dark_mode
            else "#FFFFFF"
        )

        for surface, base_style in (
            self._theme_surfaces
        ):

            surface.setStyleSheet(
                base_style
                + f"""
                QWidget[themeSurface="true"] {{
                    background-color: {background_color};
                }}
                """
            )

        if dark_mode:

            tab_theme_style = """
                QTabWidget::pane {
                    background-color: #202838;
                    border-color: #64748B;
                }

                QTabBar::tab {
                    background-color: #2D3748;
                    color: #E5E7EB;
                    border-color: #64748B;
                }

                QTabBar::tab:hover {
                    background-color: #3B475B;
                    color: #FFFFFF;
                }

                QTabBar::tab:selected {
                    background-color: #334155;
                    color: #60A5FA;
                    border-bottom: 3px solid #3B82F6;
                }
            """

        else:

            tab_theme_style = """
                QTabWidget::pane {
                    background-color: #FFFFFF;
                }
            """

        self.tab_widget.setStyleSheet(
            self._tab_widget_base_style
            + tab_theme_style
        )

        # =====================================================
        # FILTER PANEL
        # =====================================================

        filter_panel, filter_base_style = (
            self._theme_panels[0]
        )

        if dark_mode:

            filter_dark_style = """
                FilterPanel {
                    background-color: #202838;
                }

                QFrame#filterFrame {
                    background-color: #202838;
                    border-color: #64748B;
                }

                QFrame#chartFilterFrame {
                    background-color: #273244;
                    border-color: #64748B;
                }

                QFrame#filterFrame QLabel {
                    color: #F8FAFC;
                    background-color: transparent;
                }

                QFrame#chartFilterFrame QLabel {
                    color: #F8FAFC;
                    background-color: transparent;
                }

                QFrame#chartFilterFrame QLabel#chartFilterHint {
                    color: #CBD5E1;
                }

                QFrame#filterFrame QDateEdit,
                QFrame#filterFrame QComboBox,
                QFrame#filterFrame QListWidget {
                    color: #0F172A;
                    background-color: #FFFFFF;
                }

                QFrame#filterFrame QComboBox QAbstractItemView {
                    color: #0F172A;
                    background-color: #FFFFFF;
                }
            """

        else:

            filter_dark_style = ""

        filter_panel.setStyleSheet(
            filter_base_style
            + filter_dark_style
        )

        # =====================================================
        # FILE MANAGEMENT
        # =====================================================

        data_panel_dark_style = (
            """
            QFrame#dataListPanel {
                background-color: #273244;
                border-color: #64748B;
            }

            QLabel#panelTitle {
                color: #F8FAFC;
                background-color: transparent;
            }

            QFrame#dataListPanel QCheckBox {
                color: #F8FAFC;
                background-color: transparent;
            }

            QFrame#dataListPanel QTableWidget {
                color: #0F172A;
                background-color: #FFFFFF;
            }

            QFrame#dataListPanel QHeaderView::section {
                color: #0F172A;
            }
            """
            if dark_mode
            else ""
        )

        for panel_index in (
            1,
            2,
        ):

            panel, base_style = (
                self._theme_panels[
                    panel_index
                ]
            )

            panel.setStyleSheet(
                base_style
                + data_panel_dark_style
            )

        # =====================================================
        # AUTO IMPORT
        # =====================================================

        auto_import_panel, auto_import_base_style = (
            self._theme_panels[3]
        )

        if dark_mode:

            auto_import_dark_style = """
                QFrame#autoImportSchedulerPanel {
                    background-color: #273244;
                    border-color: #64748B;
                }

                QFrame#autoImportSchedulerPanel QLabel,
                QFrame#autoImportSchedulerPanel QCheckBox {
                    color: #F8FAFC;
                    background-color: transparent;
                }

                QFrame#autoImportSchedulerPanel QLineEdit,
                QFrame#autoImportSchedulerPanel QTimeEdit {
                    color: #0F172A;
                    background-color: #FFFFFF;
                }
            """

        else:

            auto_import_dark_style = ""

        auto_import_panel.setStyleSheet(
            auto_import_base_style
            + auto_import_dark_style
        )

        # =====================================================
        # SEND MAIL
        # =====================================================

        send_mail_panel, send_mail_base_style = (
            self._theme_panels[4]
        )

        if dark_mode:

            send_mail_dark_style = """
                SendMailTab {
                    background-color: #202838;
                }

                SendMailTab QGroupBox {
                    background-color: #273244;
                    color: #F8FAFC;
                    border-color: #64748B;
                }

                SendMailTab QGroupBox::title {
                    color: #F8FAFC;
                    background-color: transparent;
                }

                SendMailTab QLabel,
                SendMailTab QCheckBox {
                    color: #F8FAFC;
                    background-color: transparent;
                }

                SendMailTab QTableWidget,
                SendMailTab QComboBox,
                SendMailTab QLineEdit,
                SendMailTab QTimeEdit {
                    color: #0F172A;
                    background-color: #FFFFFF;
                }

                SendMailTab QHeaderView::section {
                    color: #0F172A;
                }
            """

        else:

            send_mail_dark_style = ""

        send_mail_panel.setStyleSheet(
            send_mail_base_style
            + send_mail_dark_style
        )

        # =====================================================
        # AUTO SEND MAIL
        # =====================================================

        auto_send_panel, auto_send_base_style = (
            self._theme_panels[5]
        )

        if dark_mode:

            auto_send_dark_style = """
                QGroupBox#autoSendMailPanel {
                    background-color: #273244;
                    color: #F8FAFC;
                    border-color: #64748B;
                }

                QGroupBox#autoSendMailPanel::title {
                    color: #F8FAFC;
                    background-color: transparent;
                }

                QGroupBox#autoSendMailPanel QLabel,
                QGroupBox#autoSendMailPanel QCheckBox {
                    color: #F8FAFC;
                    background-color: transparent;
                }

                QGroupBox#autoSendMailPanel QTimeEdit {
                    color: #0F172A;
                    background-color: #FFFFFF;
                }
            """

        else:

            auto_send_dark_style = ""

        auto_send_panel.setStyleSheet(
            auto_send_base_style
            + auto_send_dark_style
        )

        # =====================================================
        # TITLE LABEL
        # =====================================================

        for label, base_style in (
            self._theme_text_labels
        ):

            if dark_mode:

                dark_label_style, replaced_count = (
                    re.subn(
                        r"(^|\s)color\s*:\s*[^;]+;",
                        lambda match: (
                            f"{match.group(1)}"
                            "color: #F8FAFC;"
                        ),
                        base_style,
                        flags=re.MULTILINE,
                    )
                )

                if replaced_count == 0:

                    dark_label_style += """
                    QLabel {
                        color: #F8FAFC;
                    }
                    """

                label.setStyleSheet(
                    dark_label_style
                )

            else:

                label.setStyleSheet(
                    base_style
                )

        self.theme_button.update()

    # =========================================================
    # SUMMARY FILTER
    # =========================================================

    def _handle_sum_filter(
        self,
        criteria,
    ) -> None:

        tier_key = tuple(
            criteria.tiers
        )

        summary_key = (
            criteria.date_from,
            criteria.date_to,
            tier_key,
            tuple(
                sorted(
                    criteria.models
                )
            ),
        )

        daily_key = (
            criteria.date_from,
            criteria.date_to,
            criteria.eqp,
            tier_key,
            tuple(
                sorted(
                    criteria.models
                )
            ),
        )

        missing_dates_key = (
            criteria.date_from,
            criteria.date_to,
        )

        scrap_key = tuple(
            sorted(
                criteria.scrap_codes
            )
        )

        load_eqp_summary = (
            summary_key
            != self._last_summary_key
        )

        load_daily_summary = (
            daily_key
            != self._last_daily_key
        )

        load_prime_daily_summary = (
            daily_key
            != self._last_prime_daily_key
        )

        load_missing_dates = (
            missing_dates_key
            != self._last_missing_dates_key
        )

        scrap_changed = (
            scrap_key
            != self._last_scrap_key
        )

        if not any(
            (
                load_eqp_summary,
                load_daily_summary,
                load_prime_daily_summary,
                load_missing_dates,
            )
        ):

            if scrap_changed:

                self.sum_tab.update_daily_chart_scraps(
                    criteria.scrap_codes
                )

                self._last_scrap_key = (
                    scrap_key
                )

            self._close_filter_loading_dialog()

            return

        if (
            self.sum_thread is not None
            and self.sum_thread.isRunning()
        ):
            return

        self._pending_sum_keys = {
            "summary": summary_key,
            "daily": daily_key,
            "missing_dates": missing_dates_key,
            "scrap": scrap_key,
            "load_eqp_summary": load_eqp_summary,
            "load_daily_summary": load_daily_summary,
            "load_prime_daily_summary": (
                load_prime_daily_summary
            ),
            "load_missing_dates": load_missing_dates,
        }

        self._load_sum_data(
            date_from=criteria.date_from,
            date_to=criteria.date_to,
            eqpid=criteria.eqp,
            tiers=criteria.tiers,
            selected_scrap_codes=(
                criteria.scrap_codes
            ),
            load_eqp_summary=load_eqp_summary,
            load_daily_summary=load_daily_summary,
            load_prime_daily_summary=(
                load_prime_daily_summary
            ),
            load_missing_dates=load_missing_dates,
            selected_models=criteria.models,
        )

    # =========================================================
    # CHART PRELOAD
    # =========================================================

    def start_chart_preload(
        self,
    ) -> None:

        if (
            self._chart_preload_state
            != "NOT_STARTED"
        ):
            return

        self._chart_preload_state = "LOADING"
        self._chart_preload_error = None

        self.chart_preload_thread = QThread(
            self
        )

        self.chart_preload_worker = (
            ChartPreloadWorker()
        )

        self.chart_preload_worker.moveToThread(
            self.chart_preload_thread
        )

        self.chart_preload_thread.started.connect(
            self.chart_preload_worker.run
        )

        self.chart_preload_worker.succeeded.connect(
            self._on_chart_preload_succeeded
        )

        self.chart_preload_worker.failed.connect(
            self._on_chart_preload_failed
        )

        self.chart_preload_worker.succeeded.connect(
            self.chart_preload_thread.quit
        )

        self.chart_preload_worker.failed.connect(
            self.chart_preload_thread.quit
        )

        self.chart_preload_thread.finished.connect(
            self.chart_preload_worker.deleteLater
        )

        self.chart_preload_thread.finished.connect(
            self._on_chart_preload_thread_finished
        )

        self.chart_preload_thread.start()

    def _request_filter_load(
        self,
        criteria,
    ) -> None:

        if (
            self._chart_preload_state
            == "READY"
        ):

            self._load_active_tab(
                criteria
            )

            return

        if (
            self._chart_preload_state
            == "FAILED"
        ):

            self._close_filter_loading_dialog()

            QMessageBox.critical(
                self,
                "Không thể tải biểu đồ",
                self._chart_preload_error
                or "Không thể tải thư viện biểu đồ.",
            )

            return

        self._pending_chart_filter_criteria = (
            criteria
        )

        if (
            self._chart_preload_state
            == "NOT_STARTED"
        ):

            self.start_chart_preload()

    def _on_chart_preload_succeeded(
        self,
    ) -> None:

        self._chart_preload_state = "READY"
        self._chart_preload_error = None

        pending_criteria = (
            self._pending_chart_filter_criteria
        )

        self._pending_chart_filter_criteria = None

        if pending_criteria is not None:

            self._load_active_tab(
                pending_criteria
            )

    def _on_chart_preload_failed(
        self,
        error_message: str,
    ) -> None:

        had_pending_filter = (
            self._pending_chart_filter_criteria
            is not None
        )

        self._chart_preload_state = "FAILED"

        self._chart_preload_error = (
            error_message
        )

        self._pending_chart_filter_criteria = None

        self._close_filter_loading_dialog()

        if had_pending_filter:

            QMessageBox.critical(
                self,
                "Không thể tải biểu đồ",
                error_message,
            )

    def _on_chart_preload_thread_finished(
        self,
    ) -> None:

        if (
            self.chart_preload_thread
            is not None
        ):

            self.chart_preload_thread.deleteLater()

        self.chart_preload_thread = None
        self.chart_preload_worker = None

    # =========================================================
    # MAIL PRELOAD
    # =========================================================

    def start_mail_preload(
        self,
    ) -> None:

        if (
            self._mail_preload_state
            != "NOT_STARTED"
        ):
            return

        self._mail_preload_state = "LOADING"
        self._mail_preload_error = None

        self.mail_preload_thread = QThread(
            self
        )

        self.mail_preload_worker = (
            MailPreloadWorker()
        )

        self.mail_preload_worker.moveToThread(
            self.mail_preload_thread
        )

        self.mail_preload_thread.started.connect(
            self.mail_preload_worker.run
        )

        self.mail_preload_worker.succeeded.connect(
            self._on_mail_preload_succeeded
        )

        self.mail_preload_worker.failed.connect(
            self._on_mail_preload_failed
        )

        self.mail_preload_worker.succeeded.connect(
            self.mail_preload_thread.quit
        )

        self.mail_preload_worker.failed.connect(
            self.mail_preload_thread.quit
        )

        self.mail_preload_thread.finished.connect(
            self.mail_preload_worker.deleteLater
        )

        self.mail_preload_thread.finished.connect(
            self._on_mail_preload_thread_finished
        )

        self.mail_preload_thread.start()

    def _on_mail_preload_succeeded(
        self,
    ) -> None:

        self._mail_preload_state = "READY"
        self._mail_preload_error = None

    def _on_mail_preload_failed(
        self,
        error_message: str,
    ) -> None:

        self._mail_preload_state = "FAILED"

        self._mail_preload_error = (
            error_message
        )

    def _on_mail_preload_thread_finished(
        self,
    ) -> None:

        if (
            self.mail_preload_thread
            is not None
        ):

            self.mail_preload_thread.deleteLater()

        self.mail_preload_thread = None
        self.mail_preload_worker = None

    # =========================================================
    # FILTER LOADING DIALOG
    # =========================================================

    def _show_filter_loading_dialog(
        self,
    ) -> None:

        if (
            self.filter_loading_dialog
            is not None
        ):
            return

        self.filter_loading_dialog = LoadingDialog(
            parent=self,
            text="Loading...",
            title="Please Wait",
        )

        self.filter_loading_dialog.show()

    def _close_filter_loading_dialog(
        self,
    ) -> None:

        if (
            self.filter_loading_dialog
            is None
        ):
            return

        self.filter_loading_dialog.close()

        self.filter_loading_dialog.deleteLater()

        self.filter_loading_dialog = None

    # =========================================================
    # FILTER APPLIED
    # =========================================================

    def _on_filter_applied(
        self,
        criteria,
    ) -> None:

        self.filter_applied.emit(
            criteria
        )

        self._latest_filter_criteria = (
            criteria
        )

        # A new manual Search always invalidates the previous
        # result, even when From/To are unchanged.
        self._machine_slot_yield_result = None
        self._machine_slot_yield_key = None
        self._last_alarm_key = None
        self._last_summary_key = None
        self._last_daily_key = None
        self._last_prime_daily_key = None
        self._last_missing_dates_key = None
        self._last_scrap_key = None
        self._last_yield_eqp_model_key = None
        self._last_yield_eqp_data_key = None
        self._last_yield_eqp_scrap_key = None

        if hasattr(self, "dashboard_tab"):
            self.dashboard_tab.invalidate_cache()

        self._show_filter_loading_dialog()

        self._request_filter_load(
            criteria
        )

    # =========================================================
    # TAB CHANGED
    # =========================================================

    def _on_tab_changed(
        self,
        tab_index: int,
    ) -> None:

        if (
            self.tab_widget.currentWidget()
            is self.database_management_tab
        ):

            self.database_management_tab.load_if_needed()

            return

        if (
            self.tab_widget.currentWidget()
            is self.send_mail_tab
        ):

            self.send_mail_tab.load_if_needed()

            return

        if (
            self._latest_filter_criteria
            is None
        ):
            return

        self._request_filter_load(
            self._latest_filter_criteria
        )

    # =========================================================
    # LOAD ACTIVE TAB
    # =========================================================

    def _load_active_tab(
        self,
        criteria,
    ) -> None:

        current_widget = (
            self.tab_widget.currentWidget()
        )

        if (
            current_widget
            is self.database_management_tab
        ):

            self.database_management_tab.load_if_needed()

            self._close_filter_loading_dialog()

            return

        if (
            current_widget
            is self.send_mail_tab
        ):

            self.send_mail_tab.load_if_needed()

            self._close_filter_loading_dialog()

            return

        if (
            current_widget
            is self.sum_tab
        ):

            self._handle_sum_filter(
                criteria
            )

            return

        if (
            current_widget
            is self.yield_eqp_tab
        ):

            tier_key = tuple(
                criteria.tiers
            )

            data_key = (
                criteria.date_from,
                criteria.date_to,
                tier_key,
                tuple(
                    sorted(
                        criteria.models
                    )
                ),
            )

            scrap_key = tuple(
                sorted(
                    criteria.scrap_codes
                )
            )

            model_key = tuple(
                sorted(
                    criteria.models
                )
            )

            self._handle_yield_eqp_filter(
                criteria=criteria,
                data_key=data_key,
                scrap_key=scrap_key,
                model_key=model_key,
            )

            return

        # =====================================================
        # DASHBOARD
        # =====================================================

        if (
            current_widget
            is self.dashboard_tab
        ):

            self.dashboard_tab.load_data(
                date_from=criteria.date_from,
                date_to=criteria.date_to,
            )

            self._close_filter_loading_dialog()

            return

        # =====================================================
        # ALARM
        # =====================================================

        if (
            current_widget
            is self.alarm_tab
        ):

            # From/To filters persisted Alarm Date, not the source test dates.
            # Rebuilding from a shorter log range can remove valid Yield alarms.
            self._handle_alarm_filter(
                criteria
            )

            return

        # =====================================================
        # MACHINE SLOT YIELD
        # =====================================================

        if (
            current_widget
            is self.machine_slot_yield_tab
        ):

            machine_slot_key = (
                str(criteria.date_from),
                str(criteria.date_to),
            )

            if (
                self._machine_slot_yield_result is not None
                and self._machine_slot_yield_key
                == machine_slot_key
            ):
                self._close_filter_loading_dialog()
                return

            self.machine_slot_yield_tab.load_data(
                date_from=criteria.date_from,
                date_to=criteria.date_to,
            )

            return

    # =========================================================
    # MACHINE SLOT YIELD -> ALARM
    # =========================================================

    def _prepare_machine_slot_yield_for_alarm(
        self,
        criteria,
    ) -> None:
        """
        Chuẩn bị dữ liệu cho Alarm.

        Nếu Machine Slot Yield đã được load đúng khoảng
        ngày hiện tại thì sử dụng cache, KHÔNG đọc TXT lại.

        Nếu chưa có cache:

            Main Filter
                ↓
            Machine Slot Yield
                ↓
            đọc TXT
                ↓
            tính Yield / Fail / Alarm
                ↓
            sync DB
                ↓
            Alarm Worker
                ↓
            Alarm Tab
        """

        if criteria is None:
            return

        alarm_key = self._build_alarm_key(
            criteria
        )

        # =====================================================
        # 1. KIỂM TRA CACHE MACHINE SLOT YIELD
        # =====================================================

        if (
            self._machine_slot_yield_result
            is not None
            and self._machine_slot_yield_key
            == alarm_key
        ):

            self._pending_alarm_msy_key = None
            self._pending_alarm_msy_criteria = None

            self._handle_alarm_filter(
                criteria
            )

            return

        # =====================================================
        # 2. CHƯA CÓ CACHE -> YÊU CẦU MACHINE SLOT YIELD
        # =====================================================

        self._pending_alarm_msy_key = (
            alarm_key
        )

        self._pending_alarm_msy_criteria = (
            criteria
        )

        self.alarm_tab.set_loading(
            date_from=criteria.date_from,
            date_to=criteria.date_to,
        )

        self._show_filter_loading_dialog()

        self.machine_slot_yield_tab.load_data(
            date_from=criteria.date_from,
            date_to=criteria.date_to,
        )

    # =========================================================
    # MACHINE SLOT YIELD FINISHED
    # =========================================================

    def _on_machine_slot_yield_load_finished(
        self,
        result,
    ) -> None:
        """
        Machine Slot Yield hoàn tất.

        Quan trọng:
        - Luôn cache kết quả.
        - LUÔN đóng Loading Dialog khi Machine Slot Yield
          hoàn thành.
        - Nếu Alarm đang chờ thì tiếp tục sang Alarm.
        """

        result_key = (
            str(
                getattr(
                    result,
                    "date_from",
                    "",
                )
                or ""
            ),
            str(
                getattr(
                    result,
                    "date_to",
                    "",
                )
                or ""
            ),
        )

        # =====================================================
        # 1. CACHE KẾT QUẢ MACHINE SLOT YIELD
        # =====================================================

        self._last_alarm_key = None
        self.alarm_tab.machine_slot_result = result

        self._machine_slot_yield_result = (
            result
        )

        self._machine_slot_yield_key = (
            result_key
        )

        # =====================================================
        # 2. ĐÓNG PLEASE WAIT
        # =====================================================

        self._close_filter_loading_dialog()

        # =====================================================
        # 3. KHÔNG CÓ ALARM ĐANG CHỜ
        # =====================================================

        if (
            self._pending_alarm_msy_key
            is None
        ):
            return

        criteria = (
            self._pending_alarm_msy_criteria
        )

        if criteria is None:

            self._pending_alarm_msy_key = None
            self._pending_alarm_msy_criteria = None

            return

        expected_key = (
            self._pending_alarm_msy_key
        )

        # =====================================================
        # 4. KIỂM TRA ĐÚNG KHOẢNG NGÀY
        # =====================================================

        if result_key != expected_key:

            self._pending_alarm_msy_key = None
            self._pending_alarm_msy_criteria = None

            return

        # =====================================================
        # 5. KIỂM TRA FILTER MỚI NHẤT
        # =====================================================

        if (
            self._latest_filter_criteria
            is None
        ):

            self._pending_alarm_msy_key = None
            self._pending_alarm_msy_criteria = None

            return

        latest_key = (
            self._build_alarm_key(
                self._latest_filter_criteria
            )
        )

        if latest_key != expected_key:

            self._pending_alarm_msy_key = None
            self._pending_alarm_msy_criteria = None

            return

        # =====================================================
        # 6. NẾU ĐÃ CHUYỂN SANG TAB KHÁC
        # =====================================================

        if (
            self.tab_widget.currentWidget()
            is not self.alarm_tab
        ):

            self._pending_alarm_msy_key = None
            self._pending_alarm_msy_criteria = None

            return

        # =====================================================
        # 7. MACHINE SLOT YIELD ĐÃ SYNC DB
        # -> CHUYỂN SANG ALARM
        # =====================================================

        self._pending_alarm_msy_key = None
        self._pending_alarm_msy_criteria = None

        self._handle_alarm_filter(
            criteria
        )

    # =========================================================
    # MACHINE SLOT YIELD FAILED
    # =========================================================

    def _on_machine_slot_yield_load_failed(
        self,
        message: str,
    ) -> None:

        # =====================================================
        # LUÔN ĐÓNG PLEASE WAIT KHI CÓ LỖI
        # =====================================================

        self._close_filter_loading_dialog()

        # =====================================================
        # TRẢ ALARM VỀ TRẠNG THÁI EDIT
        # =====================================================

        self.alarm_tab._alarm_loading = False

        self.alarm_tab.table_model.editing_enabled = (
            not self.alarm_tab.is_saving()
        )

        if (
            self._pending_alarm_msy_key
            is None
        ):
            return

        self._pending_alarm_msy_key = None
        self._pending_alarm_msy_criteria = None

        QMessageBox.warning(
            self,
            "Machine Slot Yield",
            "Không thể chuẩn bị dữ liệu "
            "Machine Slot Yield cho TAB Alarm.\n\n"
            f"{message}",
        )

    # =========================================================
    # SUM DATA
    # =========================================================

    def _load_sum_data(
        self,
        date_from: str,
        date_to: str,
        eqpid: str | None,
        tiers: list[str | None],
        selected_scrap_codes: list[str],
        load_eqp_summary: bool,
        load_daily_summary: bool,
        load_prime_daily_summary: bool,
        load_missing_dates: bool,
        selected_models: list[str] | None = None,
    ) -> None:

        if (
            self.sum_thread is not None
            and self.sum_thread.isRunning()
        ):
            return

        self.sum_tab.set_loading(
            date_from=date_from,
            date_to=date_to,
        )

        self.sum_thread = QThread(
            self
        )

        self.sum_worker = SumWorker(
            database_path=self.database_path,
            date_from=date_from,
            date_to=date_to,
            eqpid=eqpid,
            tiers=tiers,
            selected_scrap_codes=(
                selected_scrap_codes
            ),
            load_eqp_summary=load_eqp_summary,
            load_daily_summary=load_daily_summary,
            load_prime_daily_summary=(
                load_prime_daily_summary
            ),
            load_missing_dates=load_missing_dates,
            selected_models=selected_models,
        )

        self.sum_worker.moveToThread(
            self.sum_thread
        )

        self.sum_thread.started.connect(
            self.sum_worker.run
        )

        self.sum_worker.succeeded.connect(
            self._on_sum_data_loaded
        )

        self.sum_worker.failed.connect(
            self._on_sum_data_failed
        )

        self.sum_worker.succeeded.connect(
            self.sum_thread.quit
        )

        self.sum_worker.failed.connect(
            self.sum_thread.quit
        )

        self.sum_thread.finished.connect(
            self.sum_worker.deleteLater
        )

        self.sum_thread.finished.connect(
            self._on_sum_thread_finished
        )

        self.sum_thread.start()

    def _on_sum_data_loaded(
        self,
        result,
    ) -> None:

        self.sum_tab.load_sum_data(
            result
        )

        pending = (
            self._pending_sum_keys
        )

        if pending is None:

            self._close_filter_loading_dialog()

            return

        if (
            result.eqp_summary
            is not None
        ):

            self._last_summary_key = (
                pending["summary"]
            )

        if (
            result.daily_summary
            is not None
        ):

            self._last_daily_key = (
                pending["daily"]
            )

        if (
            result.prime_daily_summary
            is not None
        ):

            self._last_prime_daily_key = (
                pending["daily"]
            )

        if (
            result.missing_cum_dates
            is not None
        ):

            self._last_missing_dates_key = (
                pending["missing_dates"]
            )

        self._last_scrap_key = (
            pending["scrap"]
        )

        self._pending_sum_keys = None

        self._close_filter_loading_dialog()

    def _on_sum_data_failed(
        self,
        error_message: str,
    ) -> None:

        pending = (
            self._pending_sum_keys
            or {}
        )

        self.sum_tab.show_error(
            error_message,
            clear_summary=pending.get(
                "load_eqp_summary",
                True,
            ),
            clear_daily=pending.get(
                "load_daily_summary",
                True,
            ),
            clear_missing_dates=pending.get(
                "load_missing_dates",
                True,
            ),
            clear_prime_daily=pending.get(
                "load_prime_daily_summary",
                True,
            ),
        )

        self._pending_sum_keys = None

        self._close_filter_loading_dialog()

    def _on_sum_thread_finished(
        self,
    ) -> None:

        if (
            self.sum_thread
            is not None
        ):

            self.sum_thread.deleteLater()

        self.sum_thread = None
        self.sum_worker = None

    # =========================================================
    # YIELD EQP
    # =========================================================

    def _handle_yield_eqp_filter(
        self,
        criteria,
        data_key: tuple,
        scrap_key: tuple,
        model_key: tuple,
    ) -> None:

        data_changed = (
            data_key
            != self._last_yield_eqp_data_key
        )

        scrap_changed = (
            scrap_key
            != self._last_yield_eqp_scrap_key
        )

        model_changed = (
            model_key
            != self._last_yield_eqp_model_key
        )

        if not data_changed:

            if scrap_changed:

                self.yield_eqp_tab.update_chart_scraps(
                    criteria.scrap_codes
                )

                self._last_yield_eqp_scrap_key = (
                    scrap_key
                )

            if model_changed:

                self.yield_eqp_tab.update_product_chart_models(
                    criteria.models
                )

                self._last_yield_eqp_model_key = (
                    model_key
                )

            self._close_filter_loading_dialog()

            return

        if (
            self.yield_eqp_thread is not None
            and self.yield_eqp_thread.isRunning()
        ):
            return

        self._pending_yield_eqp_keys = {
            "data": data_key,
            "scrap": scrap_key,
            "model": model_key,
        }

        self._load_yield_eqp_data(
            date_from=criteria.date_from,
            date_to=criteria.date_to,
            tiers=criteria.tiers,
            selected_scrap_codes=(
                criteria.scrap_codes
            ),
            selected_models=criteria.models,
        )

    def _load_yield_eqp_data(
        self,
        date_from: str,
        date_to: str,
        tiers: list[str | None],
        selected_scrap_codes: list[str],
        selected_models: list[str],
    ) -> None:

        self.yield_eqp_tab.set_loading(
            date_from=date_from,
            date_to=date_to,
        )

        self.yield_eqp_thread = QThread(
            self
        )

        self.yield_eqp_worker = YieldEqpWorker(
            database_path=self.database_path,
            date_from=date_from,
            date_to=date_to,
            tiers=tiers,
            selected_scrap_codes=(
                selected_scrap_codes
            ),
            selected_models=selected_models,
        )

        self.yield_eqp_worker.moveToThread(
            self.yield_eqp_thread
        )

        self.yield_eqp_thread.started.connect(
            self.yield_eqp_worker.run
        )

        self.yield_eqp_worker.succeeded.connect(
            self._on_yield_eqp_data_loaded
        )

        self.yield_eqp_worker.failed.connect(
            self._on_yield_eqp_data_failed
        )

        self.yield_eqp_worker.succeeded.connect(
            self.yield_eqp_thread.quit
        )

        self.yield_eqp_worker.failed.connect(
            self.yield_eqp_thread.quit
        )

        self.yield_eqp_thread.finished.connect(
            self.yield_eqp_worker.deleteLater
        )

        self.yield_eqp_thread.finished.connect(
            self._on_yield_eqp_thread_finished
        )

        self.yield_eqp_thread.start()

    def _on_yield_eqp_data_loaded(
        self,
        result,
    ) -> None:

        self.yield_eqp_tab.load_data(
            result
        )

        pending = (
            self._pending_yield_eqp_keys
        )

        if pending is not None:

            self._last_yield_eqp_data_key = (
                pending["data"]
            )

            self._last_yield_eqp_scrap_key = (
                pending["scrap"]
            )

            self._last_yield_eqp_model_key = (
                pending["model"]
            )

        self._pending_yield_eqp_keys = None

        self._close_filter_loading_dialog()

    def _on_yield_eqp_data_failed(
        self,
        error_message: str,
    ) -> None:

        self.yield_eqp_tab.show_error(
            error_message
        )

        self._pending_yield_eqp_keys = None

        self._close_filter_loading_dialog()

    def _on_yield_eqp_thread_finished(
        self,
    ) -> None:

        if (
            self.yield_eqp_thread
            is not None
        ):

            self.yield_eqp_thread.deleteLater()

        self.yield_eqp_thread = None
        self.yield_eqp_worker = None

    # =========================================================
    # ALARM
    # =========================================================

    def _handle_alarm_filter(
        self,
        criteria,
    ) -> None:
        """
        Query Alarm từ DATABASE.

        From/To chỉ giới hạn alarm_date của các Alarm đã lưu.
        Việc tạo/cập nhật Alarm được thực hiện khi đọc log ở Machine Slot Yield.
        """

        if criteria is None:
            return

        alarm_key = self._build_alarm_key(
            criteria
        )

        # =====================================================
        # ĐANG SAVE
        # =====================================================

        if self.alarm_tab.is_saving():

            self._close_filter_loading_dialog()

            QMessageBox.warning(
                self,
                "Alarm",
                "Đang lưu Alarm. Vui lòng thử lại bộ lọc sau.",
            )

            return

        if self.alarm_tab.has_unsaved_changes():

            self._close_filter_loading_dialog()

            QMessageBox.warning(
                self,
                "Alarm chưa Save",
                "Bạn đang có thay đổi chưa được lưu.\n\n"
                "Vui lòng bấm Save tại TAB Alarm trước "
                "khi đổi ngày hoặc Search lại.",
            )

            return

        # =====================================================
        # ALARM WORKER ĐANG CHẠY
        # =====================================================

        if (
            self.alarm_thread is not None
            and self.alarm_thread.isRunning()
        ):

            print(
                "Alarm worker đang chạy -> chờ worker hiện tại."
            )

            self._pending_alarm_key = alarm_key

            self._reload_alarm_after_finish = True

            return

        # =====================================================
        # CACHE ĐÃ CÓ
        # =====================================================

        if (
            self._last_alarm_key == alarm_key
            and self.alarm_tab.table_model.rowCount() > 0
        ):

            print(
                "Alarm sử dụng cache:",
                alarm_key,
            )

            self.alarm_tab._alarm_loading = False

            self.alarm_tab.table_model.editing_enabled = (
                not self.alarm_tab.is_saving()
            )

            self._close_filter_loading_dialog()

            return

        # =====================================================
        # LƯU PENDING KEY
        # =====================================================

        self._pending_alarm_key = alarm_key

        # =====================================================
        # BẮT ĐẦU LOADING
        # =====================================================

        self.alarm_tab.set_loading(
            date_from=criteria.date_from,
            date_to=criteria.date_to,
        )

        # =====================================================
        # TẠO THREAD
        # =====================================================

        self.alarm_thread = QThread(
            self
        )

        self.alarm_worker = AlarmWorker(
            database_path=self.database_path,
            date_from=criteria.date_from,
            date_to=criteria.date_to,
        )

        self.alarm_worker.moveToThread(
            self.alarm_thread
        )

        # =====================================================
        # START
        # =====================================================

        self.alarm_thread.started.connect(
            self.alarm_worker.run
        )

        # =====================================================
        # RESULT
        # =====================================================

        self.alarm_worker.succeeded.connect(
            self._on_alarm_data_loaded
        )

        self.alarm_worker.failed.connect(
            self._on_alarm_data_failed
        )

        # =====================================================
        # STOP THREAD
        # =====================================================

        self.alarm_worker.succeeded.connect(
            self.alarm_thread.quit
        )

        self.alarm_worker.failed.connect(
            self.alarm_thread.quit
        )

        # =====================================================
        # CLEANUP
        # =====================================================

        self.alarm_thread.finished.connect(
            self.alarm_worker.deleteLater
        )

        self.alarm_thread.finished.connect(
            self._on_alarm_thread_finished
        )

        # =====================================================
        # START THREAD
        # =====================================================

        self.alarm_thread.start()

    @staticmethod
    def _build_alarm_key(
        criteria,
    ) -> tuple | None:
        """
        Cache Alarm theo khoảng ngày.
        """

        if criteria is None:
            return None

        return (
            str(
                criteria.date_from
            ),
            str(
                criteria.date_to
            ),
        )

    def _on_alarm_data_loaded(
        self,
        result,
    ) -> None:

        # =====================================================
        # KIỂM TRA RESULT
        # =====================================================

        if result is None:

            self._pending_alarm_key = None
            self._reload_alarm_after_finish = False

            self.alarm_tab.show_error(
                "Alarm Worker không trả về dữ liệu."
            )

            self.alarm_tab._alarm_loading = False

            self.alarm_tab.table_model.editing_enabled = (
                not self.alarm_tab.is_saving()
            )

            self._close_filter_loading_dialog()

            return

        # =====================================================
        # RESULT KEY
        # =====================================================

        result_key = (
            str(
                getattr(
                    result,
                    "date_from",
                    "",
                )
                or ""
            ),
            str(
                getattr(
                    result,
                    "date_to",
                    "",
                )
                or ""
            ),
        )

        # =====================================================
        # LATEST FILTER KEY
        # =====================================================

        latest_key = (
            self._build_alarm_key(
                self._latest_filter_criteria
            )
        )

        print(
            "========== ALARM DATA LOADED =========="
        )

        print(
            "Alarm result key:",
            result_key,
        )

        print(
            "Alarm latest key:",
            latest_key,
        )

        # =====================================================
        # RESULT KHÔNG CÒN PHÙ HỢP FILTER HIỆN TẠI
        # =====================================================

        if result_key != latest_key:

            print(
                "Alarm result cũ -> yêu cầu reload."
            )

            self._reload_alarm_after_finish = True

            self.alarm_tab._alarm_loading = False

            self.alarm_tab.table_model.editing_enabled = (
                not self.alarm_tab.is_saving()
            )

            self._close_filter_loading_dialog()

            return

        # =====================================================
        # LOAD DATA VÀO ALARM TAB
        # =====================================================

        try:

            self.alarm_tab.load_data(
                result
            )

        except Exception as error:

            print(
                "Alarm load_data ERROR:",
                error,
            )

            self.alarm_tab._alarm_loading = False

            self.alarm_tab.table_model.editing_enabled = (
                not self.alarm_tab.is_saving()
            )

            self._pending_alarm_key = None

            self._close_filter_loading_dialog()

            QMessageBox.warning(
                self,
                "Alarm",
                "Có lỗi khi hiển thị dữ liệu Alarm:\n\n"
                f"{error}",
            )

            return

        # =====================================================
        # CACHE
        # =====================================================

        self._last_alarm_key = result_key

        self._pending_alarm_key = None

        # =====================================================
        # ĐẢM BẢO EDITING ĐƯỢC BẬT
        # =====================================================

        self.alarm_tab._alarm_loading = False

        self.alarm_tab.table_model.editing_enabled = (
            not self.alarm_tab.is_saving()
        )

        # =====================================================
        # ĐÓNG LOADING
        # =====================================================

        self._close_filter_loading_dialog()

        print(
            "Alarm loading finished."
        )

        print(
            "Alarm editing ENABLED."
        )

    def _on_alarm_data_failed(
        self,
        error_message: str,
    ) -> None:

        latest_key = (
            self._build_alarm_key(
                self._latest_filter_criteria
            )
        )

        print(
            "========== ALARM DATA FAILED =========="
        )

        print(
            "Alarm error:",
            error_message,
        )

        # =====================================================
        # LUÔN THOÁT TRẠNG THÁI LOADING
        # =====================================================

        self.alarm_tab._alarm_loading = False

        self.alarm_tab.table_model.editing_enabled = (
            not self.alarm_tab.is_saving()
        )

        # =====================================================
        # KẾT QUẢ KHÔNG CÒN PHÙ HỢP FILTER
        # =====================================================

        if (
            self._pending_alarm_key
            != latest_key
        ):

            self._reload_alarm_after_finish = True

            self._pending_alarm_key = None

            self._close_filter_loading_dialog()

            print(
                "Alarm error thuộc filter cũ -> reload."
            )

            return

        # =====================================================
        # HIỂN THỊ LỖI
        # =====================================================

        self.alarm_tab.show_error(
            error_message
        )

        # =====================================================
        # RESET STATE
        # =====================================================

        self._pending_alarm_key = None

        self._close_filter_loading_dialog()

    def _on_alarm_thread_finished(
        self,
    ) -> None:

        print(
            "========== ALARM THREAD FINISHED =========="
        )

        if (
            self.alarm_thread
            is not None
        ):

            self.alarm_thread.deleteLater()

        self.alarm_thread = None
        self.alarm_worker = None

        # =====================================================
        # LUÔN ĐẢM BẢO ALARM KHÔNG BỊ KẸT LOADING
        # =====================================================

        self.alarm_tab._alarm_loading = False

        self.alarm_tab.table_model.editing_enabled = (
            not self.alarm_tab.is_saving()
        )

        # =====================================================
        # KIỂM TRA CÓ CẦN RELOAD KHÔNG
        # =====================================================

        should_reload = (
            self._reload_alarm_after_finish
        )

        self._reload_alarm_after_finish = False

        # =====================================================
        # RELOAD FILTER MỚI NHẤT
        # =====================================================

        if (
            should_reload
            and self._latest_filter_criteria
            is not None
            and self.tab_widget.currentWidget()
            is self.alarm_tab
        ):

            print(
                "Alarm -> reload latest filter."
            )

            self._handle_alarm_filter(
                self._latest_filter_criteria
            )

    # =========================================================
    # LOAD LATEST ALARM ON STARTUP
    # =========================================================

    def _load_latest_alarm_on_startup(self) -> None:
        """Mở PGM sẽ tự hiển thị Alarm trong 30 ngày gần nhất."""

        try:
            from PyQt5.QtCore import QDate

            today = QDate.currentDate()
            date_from = today.addDays(-30)
            date_to = today

            # Giữ đúng bộ lọc mặc định 30 ngày:
            # From = hôm nay - 30 ngày, To = hôm nay.
            self.filter_panel.from_date_edit.setDate(date_from)
            self.filter_panel.to_date_edit.setDate(date_to)

            # Nếu user chưa Search lần nào, tự load Alarm.
            if self._latest_filter_criteria is None:
                criteria = FilterCriteria(
                    date_from=date_from.toString("yyyyMMdd"),
                    date_to=date_to.toString("yyyyMMdd"),
                    selected_date=None,
                    eqp=None,
                    chamber=None,
                    scrap_codes=[],
                    tiers=[],
                    models=[],
                )

                self._latest_filter_criteria = criteria
                self._handle_alarm_filter(criteria)

        except Exception as error:
            print(
                "Load 30-day Alarm on startup error:",
                error,
            )

    # =========================================================
    # AUTO REFRESH SEARCH

    # =========================================================

    def _auto_refresh_current_search(
        self,
    ) -> None:
        """
        Tự động chạy lại Search mỗi 15 phút
        với đúng From/To hiện tại.
        """

        criteria = self._latest_filter_criteria

        if criteria is None:
            return

        if self.tab_widget.currentWidget() is self.dashboard_tab:

            self.dashboard_tab.invalidate_cache()
            self.dashboard_tab.load_data(
                date_from=criteria.date_from,
                date_to=criteria.date_to,
            )

            return

        if self.tab_widget.currentWidget() is self.alarm_tab:

            self._last_alarm_key = None
            self._show_filter_loading_dialog()
            self._handle_alarm_filter(criteria)

            return

        self._show_filter_loading_dialog()

        if self.tab_widget.currentWidget() is self.machine_slot_yield_tab:
            self._machine_slot_yield_result = None
            self._machine_slot_yield_key = None

        self._request_filter_load(
            criteria
        )

    # =========================================================
    # IMPORT PRIME
    # =========================================================

    def _choose_prime_log_folder(
        self,
    ) -> None:

        dialog = PrimeLogImportDialog(
            self
        )

        if (
            dialog.exec_()
            != dialog.Accepted
        ):
            return

        self._start_prime_import(
            root_folder=dialog.selected_folder(),
            business_date=(
                dialog.selected_business_date()
            ),
        )

    # =========================================================
    # IMPORT CUM
    # =========================================================

    def _choose_cum_excel_file(
        self,
    ) -> None:

        file_path, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Chọn file CUM",
                "",
                "Excel Files (*.xlsx)",
            )
        )

        if not file_path:
            return

        self._start_cum_import(
            excel_path=Path(
                file_path
            )
        )

    # =========================================================
    # START PRIME IMPORT
    # =========================================================

    def _start_prime_import(
        self,
        root_folder: Path,
        business_date: str,
    ) -> None:

        self._set_import_buttons_enabled(
            False
        )

        self._show_loading_dialog(
            import_type="PRIME"
        )

        self.import_thread = QThread(
            self
        )

        self.import_worker = PrimeImportWorker(
            database_path=self.database_path,
            root_folder=root_folder,
            business_date=business_date,
        )

        self.import_worker.moveToThread(
            self.import_thread
        )

        self.import_thread.started.connect(
            self.import_worker.run
        )

        self.import_worker.succeeded.connect(
            self._on_prime_import_success
        )

        self.import_worker.failed.connect(
            self._on_prime_import_failed
        )

        self.import_worker.succeeded.connect(
            self.import_thread.quit
        )

        self.import_worker.failed.connect(
            self.import_thread.quit
        )

        self.import_thread.finished.connect(
            self.import_worker.deleteLater
        )

        self.import_thread.finished.connect(
            self._on_import_thread_finished
        )

        self.import_thread.start()

    # =========================================================
    # START CUM IMPORT
    # =========================================================

    def _start_cum_import(
        self,
        excel_path: Path,
    ) -> None:

        self._set_import_buttons_enabled(
            False
        )

        self._show_loading_dialog(
            import_type="CUM"
        )

        self.import_thread = QThread(
            self
        )

        self.import_worker = CumImportWorker(
            database_path=self.database_path,
            excel_path=excel_path,
        )

        self.import_worker.moveToThread(
            self.import_thread
        )

        self.import_thread.started.connect(
            self.import_worker.run
        )

        self.import_worker.succeeded.connect(
            self._on_cum_import_success
        )

        self.import_worker.failed.connect(
            self._on_cum_import_failed
        )

        self.import_worker.succeeded.connect(
            self.import_thread.quit
        )

        self.import_worker.failed.connect(
            self.import_thread.quit
        )

        self.import_thread.finished.connect(
            self.import_worker.deleteLater
        )

        self.import_thread.finished.connect(
            self._on_import_thread_finished
        )

        self.import_thread.start()

    # =========================================================
    # LOADING IMPORT
    # =========================================================

    def _show_loading_dialog(
        self,
        import_type: str,
    ) -> None:

        if (
            self.loading_dialog
            is not None
        ):
            return

        self.loading_dialog = LoadingDialog(
            parent=self,
            title="Please Wait",
            text="Loading ...",
        )

        self.loading_dialog.show()

    # =========================================================
    # PRIME IMPORT SUCCESS
    # =========================================================

    def _on_prime_import_success(
        self,
        result,
    ) -> None:

        imported_dates = ", ".join(
            result.imported_dates
        )

        QMessageBox.information(
            self,
            "Import PRIME thành công",
            "Import PRIME thành công.\n\n",
        )

        self.database_management_tab.mark_data_changed(
            "PRIME"
        )

        self._invalidate_prime_daily_cache()
        self._invalidate_alarm_cache()

        self._reload_filter_options()

    # =========================================================
    # CACHE INVALIDATE
    # =========================================================

    def _invalidate_yield_eqp_cache(
        self,
    ) -> None:

        self._last_yield_eqp_data_key = None
        self._last_yield_eqp_scrap_key = None
        self._pending_yield_eqp_keys = None
        self._last_yield_eqp_model_key = None

        self.yield_eqp_tab.invalidate_cache()

    def _invalidate_alarm_cache(
        self,
    ) -> None:

        self._last_alarm_key = None
        self._pending_alarm_key = None

        # =====================================================
        # MACHINE SLOT YIELD -> ALARM
        # =====================================================

        self._pending_alarm_msy_key = None
        self._pending_alarm_msy_criteria = None

        self._reload_alarm_after_finish = (
            False
        )

        # =====================================================
        # XÓA MACHINE SLOT YIELD RESULT CACHE
        # =====================================================

        self._machine_slot_yield_result = None
        self._machine_slot_yield_key = None

        self.alarm_tab.invalidate_cache()

    # =========================================================
    # PRIME IMPORT FAILED
    # =========================================================

    def _on_prime_import_failed(
        self,
        error_message: str,
    ) -> None:

        QMessageBox.critical(
            self,
            "Import PRIME thất bại",
            error_message,
        )

    # =========================================================
    # CUM IMPORT SUCCESS
    # =========================================================

    def _on_cum_import_success(
        self,
        result,
    ) -> None:

        imported_dates = ", ".join(
            result.imported_dates
        )

        QMessageBox.information(
            self,
            "Import CUM thành công",
            "Import CUM thành công.\n\n",
        )

        self.database_management_tab.mark_data_changed(
            "CUM"
        )

        self._invalidate_sum_cache()
        self._reload_filter_options()

    # =========================================================
    # SUM CACHE
    # =========================================================

    def _invalidate_sum_cache(
        self,
    ) -> None:

        self._last_prime_daily_key = None
        self._last_summary_key = None
        self._last_daily_key = None
        self._last_missing_dates_key = None
        self._last_scrap_key = None
        self._pending_sum_keys = None

        self.sum_tab.invalidate_cache()

        self._invalidate_yield_eqp_cache()
        self._invalidate_alarm_cache()

    # =========================================================
    # PRIME DAILY CACHE
    # =========================================================

    def _invalidate_prime_daily_cache(
        self,
    ) -> None:

        self._last_prime_daily_key = None
        self._pending_sum_keys = None

        self.sum_tab.invalidate_prime_cache()

        self._invalidate_yield_eqp_cache()

    # =========================================================
    # CUM IMPORT FAILED
    # =========================================================

    def _on_cum_import_failed(
        self,
        error_message: str,
    ) -> None:

        QMessageBox.critical(
            self,
            "Import CUM thất bại",
            error_message,
        )

    # =========================================================
    # FILTER OPTIONS
    # =========================================================

    def _reload_filter_options(
        self,
    ) -> None:

        if (
            self.filter_option_thread
            is not None
            and self.filter_option_thread.isRunning()
        ):
            return

        self.filter_option_thread = QThread(
            self
        )

        self.filter_option_worker = (
            FilterOptionWorker(
                database_path=self.database_path
            )
        )

        self.filter_option_worker.moveToThread(
            self.filter_option_thread
        )

        self.filter_option_thread.started.connect(
            self.filter_option_worker.run
        )

        self.filter_option_worker.succeeded.connect(
            self._on_filter_options_loaded
        )

        self.filter_option_worker.failed.connect(
            self._on_filter_options_failed
        )

        self.filter_option_worker.succeeded.connect(
            self.filter_option_thread.quit
        )

        self.filter_option_worker.failed.connect(
            self.filter_option_thread.quit
        )

        self.filter_option_thread.finished.connect(
            self.filter_option_worker.deleteLater
        )

        self.filter_option_thread.finished.connect(
            self._on_filter_option_thread_finished
        )

        self.filter_option_thread.start()

    def _on_filter_options_loaded(
        self,
        result,
    ) -> None:

        self.filter_panel.load_options(
            result
        )

    def _on_filter_options_failed(
        self,
        error_message: str,
    ) -> None:

        pass

    def _on_filter_option_thread_finished(
        self,
    ) -> None:

        if (
            self.filter_option_thread
            is not None
        ):

            self.filter_option_thread.deleteLater()

        self.filter_option_thread = None
        self.filter_option_worker = None

    # =========================================================
    # IMPORT BUTTON
    # =========================================================

    def _set_import_buttons_enabled(
        self,
        is_enabled: bool,
    ) -> None:

        self.filter_panel.set_import_buttons_enabled(
            is_enabled
        )

    # =========================================================
    # IMPORT THREAD FINISHED
    # =========================================================

    def _on_import_thread_finished(
        self,
    ) -> None:

        if (
            self.loading_dialog
            is not None
        ):

            self.loading_dialog.close()

            self.loading_dialog.deleteLater()

            self.loading_dialog = None

        self._set_import_buttons_enabled(
            True
        )

        if (
            self.import_thread
            is not None
        ):

            self.import_thread.deleteLater()

        self.import_thread = None
        self.import_worker = None

    # =========================================================
    # CLOSE EVENT
    # =========================================================

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        """
        Ngăn đóng app khi đang import,
        tải option hoặc đang chạy worker.
        """

        is_import_running = (
            self.import_thread is not None
            and self.import_thread.isRunning()
        )

        is_filter_loading = (
            self.filter_option_thread
            is not None
            and self.filter_option_thread.isRunning()
        )

        is_chart_preload_loading = (
            self.chart_preload_thread
            is not None
            and self.chart_preload_thread.isRunning()
        )

        is_mail_preload_loading = (
            self.mail_preload_thread
            is not None
            and self.mail_preload_thread.isRunning()
        )

        is_sum_loading = (
            self.sum_thread is not None
            and self.sum_thread.isRunning()
        )

        is_yield_eqp_loading = (
            self.yield_eqp_thread is not None
            and self.yield_eqp_thread.isRunning()
        )

        is_alarm_loading = (
            self.alarm_thread is not None
            and self.alarm_thread.isRunning()
        )

        is_database_management_loading = (
            self.database_management_tab.is_busy()
        )

        is_mail_login_loading = (
            self.send_mail_tab.is_busy()
        )

        # Machine Slot Yield có thread riêng bên trong tab.
        is_machine_slot_yield_loading = False

        try:

            msy_thread = getattr(
                self.machine_slot_yield_tab,
                "thread",
                None,
            )

            is_machine_slot_yield_loading = (
                msy_thread is not None
                and msy_thread.isRunning()
            )

        except RuntimeError:

            is_machine_slot_yield_loading = False

        if (
            is_import_running
            or is_filter_loading
            or is_chart_preload_loading
            or is_mail_preload_loading
            or is_sum_loading
            or is_yield_eqp_loading
            or is_alarm_loading
            or is_machine_slot_yield_loading
            or self.alarm_tab.is_saving()
            or is_database_management_loading
            or is_mail_login_loading
        ):

            QMessageBox.warning(
                self,
                "Tác vụ đang chạy",
                "Không thể đóng ứng dụng khi tác vụ đang chạy.",
            )

            event.ignore()

            return

        event.accept()