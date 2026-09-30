from __future__ import annotations

import sqlite3

from datetime import datetime
from typing import Iterable


class ImportStatusRepository:
    """Ghi thời điểm import gần nhất theo loại dữ liệu và DATE."""

    @staticmethod
    def upsert_dates(
        connection: sqlite3.Connection,
        data_type: str,
        business_dates: Iterable[str],
    ) -> None:
        """
        Ghi một load time chung cho toàn bộ ngày trong một lần import.

        Hàm nhận connection từ transaction import hiện tại để dữ liệu
        và metadata luôn commit hoặc rollback cùng nhau.
        """

        normalized_type = data_type.strip().upper()

        if normalized_type not in {"PRIME", "CUM"}:
            raise ValueError(
                "Loại dữ liệu import không hợp lệ."
            )

        normalized_dates = sorted(
            {
                str(value).strip()
                for value in business_dates
                if str(value).strip()
            }
        )

        if not normalized_dates:
            return

        load_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        connection.executemany(
            """
            INSERT INTO data_import_status (
                data_type,
                data_date,
                load_time
            )
            VALUES (?, ?, ?)
            ON CONFLICT (data_type, data_date)
            DO UPDATE SET
                load_time = excluded.load_time
            """,
            (
                (
                    normalized_type,
                    business_date,
                    load_time,
                )
                for business_date in normalized_dates
            ),
        )