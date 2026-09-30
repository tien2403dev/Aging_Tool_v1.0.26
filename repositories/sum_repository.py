from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Union

from database.connection import create_connection
from repositories.data_filter import build_data_filter

@dataclass
class CumEqpSummaryRow:
    """Một dòng thống kê CUM theo EQPID."""

    eqpid: str
    in_qty: int
    out_qty: int
    fail_qty: int
    fail_ppm: float | None
    yield_percent: float | None


@dataclass
class CumEqpSummaryResult:
    """Kết quả bảng CUM theo EQPID, gồm cả dòng Total."""

    rows: list[CumEqpSummaryRow]
    total: CumEqpSummaryRow

@dataclass
class CumDailyRow:
    """Một dòng thống kê CUM của EQP theo ngày."""

    date: str
    in_qty: int
    out_qty: int
    fail_qty: int
    fail_ppm: float | None
    yield_percent: float | None
    scrap_ppm_by_code: dict[str, float]


@dataclass
class CumDailyResult:
    """Kết quả thống kê từng ngày của một EQP."""

    eqpid: str | None
    scrap_codes: list[str]
    rows: list[CumDailyRow]

@dataclass
class PrimeDailyRow:
    """Một dòng thống kê PRIME của EQP theo ngày."""

    date: str
    in_qty: int
    out_qty: int
    fail_qty: int
    fail_ppm: float | None
    yield_percent: float | None
    scrap_ppm_by_code: dict[str, float]


@dataclass
class PrimeDailyResult:
    """Kết quả thống kê PRIME từng ngày của một EQP."""

    eqpid: str | None
    scrap_codes: list[str]
    rows: list[PrimeDailyRow]

@dataclass
class SumResult:
    """
    Kết quả từng phần của Tab Sum.

    Giá trị None nghĩa là phần đó không cần
    query và không cần cập nhật lại giao diện.
    """

    eqp_summary: CumEqpSummaryResult | None
    daily_summary: CumDailyResult | None
    prime_daily_summary: PrimeDailyResult | None
    missing_cum_dates: list[str] | None
    selected_scrap_codes: list[str]
class SumRepository:
    """
    Chỉ chứa các truy vấn dữ liệu cho Tab Sum.
    """

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        self.database_path = Path(database_path)

    def get_cum_eqp_summary(
        self,
        date_from: str,
        date_to: str,
        tiers: list[str | None],
        connection=None,
        selected_models: list[str] | None = None,
    ) -> CumEqpSummaryResult:
        """
        Tổng hợp CUM theo EQPID trong khoảng ngày được chọn.

        Chỉ dùng Date From và Date To.
        Fail Qty được tính bằng In - Out.
        """

        close_connection = connection is None

        if connection is None:
            connection = create_connection(
                self.database_path
            )

        try:
            tier_sql, tier_params = build_data_filter(
                column_name="TIER",
                tiers=tiers,
                selected_models=selected_models,
            )

            cursor = connection.execute(
                f"""
                SELECT
                    EQPID,
                    SUM(INQTY) AS in_qty,
                    SUM(OUTQTY) AS out_qty
                FROM cum_data
                WHERE DATE BETWEEN ? AND ?
                  {tier_sql}
                GROUP BY EQPID
                ORDER BY EQPID
                """,
                [
                    date_from,
                    date_to,
                    *tier_params,
                ],
            )

            rows = [
                self._build_summary_row(
                    eqpid=row["EQPID"],
                    in_qty=row["in_qty"],
                    out_qty=row["out_qty"],
                )
                for row in cursor.fetchall()
            ]

            total_in_qty = sum(
                row.in_qty
                for row in rows
            )

            total_out_qty = sum(
                row.out_qty
                for row in rows
            )

            total = self._build_summary_row(
                eqpid="Total",
                in_qty=total_in_qty,
                out_qty=total_out_qty,
            )

            return CumEqpSummaryResult(
                rows=rows,
                total=total,
            )


        finally:

            if close_connection:
                connection.close()

    def get_sum_data(
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
    ) -> SumResult:
        """
        Chỉ query những phần bị ảnh hưởng bởi bộ lọc.

        Một SQLite connection được dùng chung cho
        toàn bộ query trong cùng một lượt Apply.
        """

        connection = create_connection(
            self.database_path
        )

        try:
            eqp_summary = (
                self.get_cum_eqp_summary(
                    date_from=date_from,
                    date_to=date_to,
                    tiers=tiers,
                    connection=connection,
                    selected_models=selected_models,
                )
                if load_eqp_summary
                else None
            )

            daily_summary = (
                self.get_cum_daily_summary(
                    date_from=date_from,
                    date_to=date_to,
                    eqpid=eqpid,
                    tiers=tiers,
                    connection=connection,
                    selected_models=selected_models,
                )
                if load_daily_summary
                else None
            )
            prime_daily_summary = (
                self.get_prime_daily_summary(
                    date_from=date_from,
                    date_to=date_to,
                    eqpid=eqpid,
                    tiers=tiers,
                    connection=connection,
                    selected_models=selected_models,
                )
                if load_prime_daily_summary
                else None
            )

            missing_cum_dates = (
                self.get_missing_cum_dates(
                    date_from=date_from,
                    date_to=date_to,
                    connection=connection,
                )
                if load_missing_dates
                else None
            )

        finally:
            connection.close()

        return SumResult(
            eqp_summary=eqp_summary,
            daily_summary=daily_summary,
            prime_daily_summary=prime_daily_summary,
            missing_cum_dates=missing_cum_dates,
            selected_scrap_codes=list(
                selected_scrap_codes
            ),
        )

    def get_cum_daily_summary(
        self,
        date_from: str,
        date_to: str,
        eqpid: str | None,
        tiers: list[str | None],
        connection=None,
        selected_models: list[str] | None = None,
    ) -> CumDailyResult:
        """
        Tổng hợp hiệu suất từng ngày của một EQP.

        In/Out lấy từ cum_data.
        Fail = In - Out.
        Mã lỗi lấy từ cum_scrap_detail.
        """

        if not eqpid:
            return CumDailyResult(
                eqpid=None,
                scrap_codes=[],
                rows=[],
            )

        close_connection = connection is None

        if connection is None:
            connection = create_connection(
                self.database_path
            )

        try:
            tier_sql, tier_params = build_data_filter(
                column_name="TIER",
                tiers=tiers,
                selected_models=selected_models,
            )

            quantity_cursor = connection.execute(
                f"""
                SELECT
                    DATE,
                    SUM(INQTY) AS in_qty,
                    SUM(OUTQTY) AS out_qty
                FROM cum_data
                WHERE DATE BETWEEN ? AND ?
                  AND EQPID = ?
                  {tier_sql}
                GROUP BY DATE
                ORDER BY DATE
                """,
                [
                    date_from,
                    date_to,
                    eqpid,
                    *tier_params,
                ],
            )

            quantity_by_date = {
                row["DATE"]: (
                    int(row["in_qty"] or 0),
                    int(row["out_qty"] or 0),
                )
                for row in quantity_cursor.fetchall()
            }

            detail_tier_sql, detail_tier_params = (
                build_data_filter(
                    column_name="data.TIER",
                    tiers=tiers,
                    selected_models=selected_models,
                )
            )

            scrap_cursor = connection.execute(
                f"""
                SELECT
                    data.DATE,
                    detail.scrap_code,
                    SUM(detail.qty) AS scrap_qty
                FROM cum_data AS data
                INNER JOIN cum_scrap_detail AS detail
                    ON detail.cum_data_id = data.id
                WHERE data.DATE BETWEEN ? AND ?
                  AND data.EQPID = ?
                  {detail_tier_sql}
                GROUP BY
                    data.DATE,
                    detail.scrap_code
                ORDER BY
                    detail.scrap_code,
                    data.DATE
                """,
                [
                    date_from,
                    date_to,
                    eqpid,
                    *detail_tier_params,
                ],
            )

            scrap_qty_by_date: dict[
                str,
                dict[str, int],
            ] = {}

            scrap_codes = set()

            for row in scrap_cursor.fetchall():
                date = row["DATE"]
                scrap_code = row["scrap_code"]
                scrap_qty = int(
                    row["scrap_qty"] or 0
                )

                scrap_codes.add(scrap_code)

                scrap_qty_by_date.setdefault(
                    date,
                    {},
                )[scrap_code] = scrap_qty

            rows = []

            for date in self._iter_dates(
                    date_from=date_from,
                    date_to=date_to,
            ):
                in_qty, out_qty = quantity_by_date.get(
                    date,
                    (0, 0),
                )

                fail_qty = in_qty - out_qty

                if in_qty > 0:
                    fail_ppm = (
                                       fail_qty / in_qty
                               ) * 1_000_000

                    yield_percent = (
                                            out_qty / in_qty
                                    ) * 100
                else:
                    fail_ppm = None
                    yield_percent = None

                scrap_ppm_by_code = {}

                for scrap_code, scrap_qty in (
                        scrap_qty_by_date.get(
                            date,
                            {},
                        ).items()
                ):
                    if in_qty > 0:
                        scrap_ppm_by_code[scrap_code] = (
                                                                scrap_qty / in_qty
                                                        ) * 1_000_000

                rows.append(
                    CumDailyRow(
                        date=date,
                        in_qty=in_qty,
                        out_qty=out_qty,
                        fail_qty=fail_qty,
                        fail_ppm=fail_ppm,
                        yield_percent=yield_percent,
                        scrap_ppm_by_code=(
                            scrap_ppm_by_code
                        ),
                    )
                )

            return CumDailyResult(
                eqpid=eqpid,
                scrap_codes=sorted(scrap_codes),
                rows=rows,
            )


        finally:

            if close_connection:
                connection.close()

    def get_prime_daily_summary(
        self,
        date_from: str,
        date_to: str,
        eqpid: str | None,
        tiers: list[str | None],
        connection=None,
        selected_models: list[str] | None = None,
    ) -> PrimeDailyResult:
        """
        Tổng hợp In, Pass, Fail và Scrap PPM
        từ bảng prime_data theo từng ngày.
        """

        if not eqpid:
            return PrimeDailyResult(
                eqpid=None,
                scrap_codes=[],
                rows=[],
            )

        close_connection = connection is None

        if connection is None:
            connection = create_connection(
                self.database_path
            )

        try:
            tier_sql, tier_params = build_data_filter(
                column_name="TIER",
                tiers=tiers,
                selected_models=selected_models,
            )

            quantity_cursor = connection.execute(
                f"""
                SELECT
                    DATE,
                    SUM(QTY) AS in_qty,
                    SUM(
                        CASE
                            WHEN RESULT = 'PASS'
                            THEN QTY
                            ELSE 0
                        END
                    ) AS pass_qty
                FROM prime_data
                WHERE DATE BETWEEN ? AND ?
                  AND EQP = ?
                  {tier_sql}
                GROUP BY DATE
                ORDER BY DATE
                """,
                [
                    date_from,
                    date_to,
                    eqpid,
                    *tier_params,
                ],
            )

            quantity_by_date = {
                row["DATE"]: (
                    int(row["in_qty"] or 0),
                    int(row["pass_qty"] or 0),
                )
                for row in quantity_cursor.fetchall()
            }

            scrap_tier_sql, scrap_tier_params = (
                build_data_filter(
                    column_name="TIER",
                    tiers=tiers,
                    selected_models=selected_models,
                )
            )

            scrap_cursor = connection.execute(
                f"""
                SELECT
                    DATE,
                    SCRAPCODE AS scrap_code,
                    SUM(QTY) AS scrap_qty
                FROM prime_data
                WHERE DATE BETWEEN ? AND ?
                  AND EQP = ?
                  AND RESULT = 'FAIL'
                  AND COALESCE(SCRAPCODE, '') <> ''
                  {scrap_tier_sql}
                GROUP BY
                    DATE,
                    SCRAPCODE
                ORDER BY
                    SCRAPCODE,
                    DATE
                """,
                [
                    date_from,
                    date_to,
                    eqpid,
                    *scrap_tier_params,
                ],
            )

            scrap_qty_by_date: dict[
                str,
                dict[str, int],
            ] = {}

            scrap_codes = set()

            for row in scrap_cursor.fetchall():
                date = row["DATE"]
                scrap_code = row["scrap_code"]

                scrap_qty = int(
                    row["scrap_qty"] or 0
                )

                scrap_codes.add(scrap_code)

                scrap_qty_by_date.setdefault(
                    date,
                    {},
                )[scrap_code] = scrap_qty

            rows = []

            for date in self._iter_dates(
                    date_from=date_from,
                    date_to=date_to,
            ):
                in_qty, pass_qty = (
                    quantity_by_date.get(
                        date,
                        (0, 0),
                    )
                )

                fail_qty = in_qty - pass_qty

                if in_qty > 0:
                    fail_ppm = (
                                       fail_qty / in_qty
                               ) * 1_000_000

                    yield_percent = (
                                            pass_qty / in_qty
                                    ) * 100
                else:
                    fail_ppm = None
                    yield_percent = None

                scrap_ppm_by_code = {
                    scrap_code: (
                                        scrap_qty / in_qty
                                ) * 1_000_000
                    for scrap_code, scrap_qty in (
                        scrap_qty_by_date.get(
                            date,
                            {},
                        ).items()
                    )
                    if in_qty > 0
                }

                rows.append(
                    PrimeDailyRow(
                        date=date,
                        in_qty=in_qty,
                        out_qty=pass_qty,
                        fail_qty=fail_qty,
                        fail_ppm=fail_ppm,
                        yield_percent=yield_percent,
                        scrap_ppm_by_code=(
                            scrap_ppm_by_code
                        ),
                    )
                )

            return PrimeDailyResult(
                eqpid=eqpid,
                scrap_codes=sorted(
                    scrap_codes
                ),
                rows=rows,
            )

        finally:
            if close_connection:
                connection.close()
    def get_missing_cum_dates(
            self,
            date_from: str,
            date_to: str,
            connection=None,
    ) -> list[str]:
        """Trả về các ngày trong khoảng lọc chưa có dòng nào ở CUM."""

        close_connection = connection is None

        if connection is None:
            connection = create_connection(
                self.database_path
            )

        try:
            rows = connection.execute(
                """
                SELECT DISTINCT DATE
                FROM cum_data
                WHERE DATE BETWEEN ? AND ?
                """,
                (date_from, date_to),
            ).fetchall()

            available_dates = {
                row["DATE"]
                for row in rows
            }

            return [
                date
                for date in self._iter_dates(date_from, date_to)
                if date not in available_dates
            ]


        finally:

            if close_connection:
                connection.close()

    @staticmethod
    def _build_tier_filter(
            column_name: str,
            tiers: list[str | None],
    ) -> tuple[str, list[str]]:
        """Tạo điều kiện SQL chỉ cho Tier khác NULL."""

        normal_tiers = [
            str(tier)
            for tier in tiers
            if tier is not None
        ]

        # Không chọn Tier nào thì không trả dữ liệu.
        if not normal_tiers:
            return "AND 0 = 1", []

        placeholders = ", ".join(
            "?"
            for _ in normal_tiers
        )

        return (
            f"AND {column_name} IN ({placeholders})",
            normal_tiers,
        )

    @staticmethod
    def _iter_dates(
            date_from: str,
            date_to: str,
    ) -> list[str]:
        """Tạo đầy đủ danh sách ngày trong khoảng đã chọn."""

        start_date = datetime.strptime(
            date_from,
            "%Y%m%d",
        ).date()

        end_date = datetime.strptime(
            date_to,
            "%Y%m%d",
        ).date()

        dates = []
        current_date = start_date

        while current_date <= end_date:
            dates.append(
                current_date.strftime("%Y%m%d")
            )

            current_date += timedelta(days=1)

        return dates

    @staticmethod
    def _build_summary_row(
        eqpid: str,
        in_qty: int,
        out_qty: int,
    ) -> CumEqpSummaryRow:
        """Tính Fail Qty, Fail PPM và Yield từ tổng In/Out."""

        fail_qty = in_qty - out_qty

        if in_qty <= 0:
            fail_ppm = None
            yield_percent = None
        else:
            fail_ppm = (
                fail_qty / in_qty
            ) * 1_000_000

            yield_percent = (
                out_qty / in_qty
            ) * 100

        return CumEqpSummaryRow(
            eqpid=eqpid,
            in_qty=in_qty,
            out_qty=out_qty,
            fail_qty=fail_qty,
            fail_ppm=fail_ppm,
            yield_percent=yield_percent,
        )
