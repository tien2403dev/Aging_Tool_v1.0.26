from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from database.connection import create_connection


@dataclass
class FilterOptionResult:
    eqps: list[str]
    chambers: list[int]
    scrap_codes: list[str]
    tiers: list[str | None]
    models: list[str]


class FilterOptionRepository:
    """
    Đọc các lựa chọn filter từ bảng cache nhỏ.
    """

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        """Lưu đường dẫn database để tạo connection khi cần."""

        self.database_path = Path(database_path)

    def load_options(
        self,
    ) -> FilterOptionResult:
        """Đọc EQP, Chamber và Scrap code từ cache filter."""

        connection = create_connection(
            self.database_path
        )

        try:
            eqps = self._load_eqps(connection)

            chambers = self._load_chambers(connection)

            scrap_codes = self._load_scrap_codes(
                connection
            )

            tiers = self._load_tiers(connection)

            models = self._load_models(
                connection
            )

            return FilterOptionResult(
                eqps=eqps,
                chambers=chambers,
                scrap_codes=scrap_codes,
                tiers=tiers,
                models=models,
            )

        finally:
            connection.close()

    @staticmethod
    def _load_eqps(
        connection,
    ) -> list[str]:
        """Đọc danh sách EQP đang còn dữ liệu PRIME."""

        rows = connection.execute(
            """
            SELECT eqp
            FROM filter_eqp_option
            WHERE row_count > 0
            ORDER BY eqp
            """
        ).fetchall()

        return [
            row["eqp"]
            for row in rows
        ]

    @staticmethod
    def _load_chambers(
        connection,
    ) -> list[int]:
        """Đọc danh sách Chamber đang còn dữ liệu PRIME."""

        rows = connection.execute(
            """
            SELECT chamber
            FROM filter_chamber_option
            WHERE row_count > 0
            ORDER BY chamber
            """
        ).fetchall()

        return [
            row["chamber"]
            for row in rows
        ]

    @staticmethod
    def _load_scrap_codes(
        connection,
    ) -> list[str]:
        """Đọc Scrap code còn xuất hiện ở PRIME hoặc CUM."""

        rows = connection.execute(
            """
            SELECT scrap_code
            FROM filter_scrap_code_option
            WHERE prime_row_count > 0
               OR cum_row_count > 0
            ORDER BY
                CAST(scrap_code AS INTEGER),
                scrap_code
            """
        ).fetchall()

        return [
            row["scrap_code"]
            for row in rows
        ]

    @staticmethod
    def _load_tiers(
            connection,
    ) -> list[str]:
        """Chỉ đọc các Tier khác NULL từ CUM và PRIME."""

        rows = connection.execute(
            """
            SELECT TIER
            FROM (
                SELECT TIER
                FROM cum_data
                WHERE TIER IS NOT NULL
                GROUP BY TIER

                UNION

                SELECT TIER
                FROM prime_data
                WHERE TIER IS NOT NULL
                GROUP BY TIER
            )
            ORDER BY TIER
            """
        ).fetchall()

        return [
            str(row["TIER"])
            for row in rows
        ]

    @staticmethod
    def _load_models(
            connection,
    ) -> list[str]:
        """Đọc Model PRIME từ bảng cache nhỏ."""

        rows = connection.execute(
            """
            SELECT model
            FROM filter_model_option
            WHERE row_count > 0
            ORDER BY model
            """
        ).fetchall()

        return [
            row["model"]
            for row in rows
        ]
