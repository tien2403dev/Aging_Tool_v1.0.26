from __future__ import annotations

from pathlib import Path
from typing import Union

from database.connection import create_connection


class DashboardRepository:
    """Tổng hợp hiện trạng cải tiến Machine Slot Yield Alarm theo ngày."""

    def __init__(self, database_path: Union[str, Path]):
        self.database_path = Path(database_path)

    def get_daily(
        self,
        date_from: str,
        date_to: str,
    ) -> list[dict]:
        connection = create_connection(
            self.database_path,
            busy_timeout_ms=5_000,
        )
        try:
            rows = connection.execute(
                """
                SELECT
                    alarm_date,
                    COUNT(*) AS total_alarm,
                    SUM(
                        CASE WHEN status = 'Chưa tiến hành'
                        THEN 1 ELSE 0 END
                    ) AS not_started,
                    SUM(
                        CASE WHEN status = 'Đang tiến hành'
                        THEN 1 ELSE 0 END
                    ) AS in_progress,
                    SUM(
                        CASE WHEN status = 'Đã hoàn thành'
                        THEN 1 ELSE 0 END
                    ) AS completed,
                    SUM(
                        CASE WHEN quick_check_result = 'PASS'
                        THEN 1 ELSE 0 END
                    ) AS quick_pass,
                    SUM(
                        CASE WHEN cal_check_result = 'PASS'
                        THEN 1 ELSE 0 END
                    ) AS cal_pass,
                    SUM(
                        CASE WHEN monitor_day1 = 'PASS'
                        THEN 1 ELSE 0 END
                    ) AS monitor1_pass,
                    SUM(
                        CASE WHEN monitor_day2 = 'PASS'
                        THEN 1 ELSE 0 END
                    ) AS monitor2_pass,
                    SUM(
                        CASE WHEN monitor_day3 = 'PASS'
                        THEN 1 ELSE 0 END
                    ) AS monitor3_pass
                FROM machine_slot_yield_alarm
                WHERE alarm_date BETWEEN ? AND ?
                GROUP BY alarm_date
                ORDER BY alarm_date DESC
                """,
                (date_from, date_to),
            ).fetchall()
        finally:
            connection.close()

        return [dict(row) for row in rows]

    def get_totals(
        self,
        date_from: str,
        date_to: str,
    ) -> dict:
        connection = create_connection(
            self.database_path,
            busy_timeout_ms=5_000,
        )
        try:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_alarm,
                    SUM(CASE WHEN status = 'Chưa tiến hành' THEN 1 ELSE 0 END) AS not_started,
                    SUM(CASE WHEN status = 'Đang tiến hành' THEN 1 ELSE 0 END) AS in_progress,
                    SUM(CASE WHEN status = 'Đã hoàn thành' THEN 1 ELSE 0 END) AS completed,
                    SUM(CASE WHEN quick_check_result = 'PASS' THEN 1 ELSE 0 END) AS quick_pass,
                    SUM(CASE WHEN cal_check_result = 'PASS' THEN 1 ELSE 0 END) AS cal_pass,
                    SUM(CASE WHEN monitor_day1 = 'PASS' THEN 1 ELSE 0 END) AS monitor1_pass,
                    SUM(CASE WHEN monitor_day2 = 'PASS' THEN 1 ELSE 0 END) AS monitor2_pass,
                    SUM(CASE WHEN monitor_day3 = 'PASS' THEN 1 ELSE 0 END) AS monitor3_pass
                FROM machine_slot_yield_alarm
                WHERE alarm_date BETWEEN ? AND ?
                """,
                (date_from, date_to),
            ).fetchone()
        finally:
            connection.close()

        return dict(row) if row is not None else {}
    def get_daily_trend(self, date_from: str, date_to: str) -> list[dict]:
        """Dữ liệu biểu đồ Dashboard theo từng ngày."""
        connection = create_connection(self.database_path, busy_timeout_ms=5_000)
        try:
            rows = connection.execute(
                """
                WITH machine_days AS (
                    SELECT alarm_date, COUNT(*) AS machine_alarm_count
                    FROM machine_slot_yield_alarm
                    WHERE alarm_date BETWEEN ? AND ?
                    GROUP BY alarm_date
                ),
                slot_days AS (
                    SELECT alarm_date, COUNT(*) AS slot_fail_count
                    FROM slot_fail_alarm
                    WHERE alarm_date BETWEEN ? AND ?
                    GROUP BY alarm_date
                ),
                all_days AS (
                    SELECT alarm_date FROM machine_days
                    UNION
                    SELECT alarm_date FROM slot_days
                )
                SELECT
                    all_days.alarm_date,
                    COALESCE(machine_days.machine_alarm_count, 0) AS machine_alarm_count,
                    COALESCE(slot_days.slot_fail_count, 0) AS slot_fail_count,
                    (
                        COALESCE(machine_days.machine_alarm_count, 0)
                        + COALESCE(slot_days.slot_fail_count, 0)
                    ) AS total_alarm_count
                FROM all_days
                LEFT JOIN machine_days
                    ON machine_days.alarm_date = all_days.alarm_date
                LEFT JOIN slot_days
                    ON slot_days.alarm_date = all_days.alarm_date
                ORDER BY all_days.alarm_date ASC
                """,
                (date_from, date_to, date_from, date_to),
            ).fetchall()
        finally:
            connection.close()
        return [dict(row) for row in rows]

    def get_status_distribution(self, date_from: str, date_to: str) -> list[dict]:
        """Phân bố trạng thái Action để vẽ biểu đồ."""
        connection = create_connection(self.database_path, busy_timeout_ms=5_000)
        try:
            rows = connection.execute(
                """
                SELECT status, COUNT(*) AS total
                FROM machine_slot_yield_alarm
                WHERE alarm_date BETWEEN ? AND ?
                GROUP BY status
                ORDER BY total DESC
                """,
                (date_from, date_to),
            ).fetchall()
        finally:
            connection.close()
        return [dict(row) for row in rows]

