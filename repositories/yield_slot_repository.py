from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Union

from database.connection import create_connection
from repositories.data_filter import build_data_filter


# ============================================================
# DAILY YIELD
# ============================================================

@dataclass
class YieldSlotDayRow:
    """Một dòng PRIME theo ngày và 120 slot của chamber."""

    date: str
    in_qty: int
    pass_qty: int
    fail_qty: int
    yield_percent: float | None
    fail_qty_by_slot: dict[int, int]


@dataclass
class YieldSlotResult:
    """Kết quả tổng hợp của tab Yield Slot."""

    date_from: str
    date_to: str
    eqp: str
    chamber: int
    slots: list[int]
    rows: list[YieldSlotDayRow]


# ============================================================
# SCRAP
# ============================================================

@dataclass
class YieldSlotScrapRow:
    """Một dòng tổng hợp PRIME của một Slot."""

    slot: int
    in_qty: int
    pass_qty: int
    fail_qty: int
    yield_percent: float | None
    scrap_qty_by_code: dict[str, int]


@dataclass
class YieldSlotScrapResult:
    """Kết quả bảng PRIME Yield Slot theo Scrapcode."""

    date_from: str
    date_to: str
    eqp: str
    chamber: int
    scrap_codes: list[str]
    rows: list[YieldSlotScrapRow]


# ============================================================
# MACHINE SLOT YIELD
# ============================================================

@dataclass
class MachineSlotTest:
    """
    Một lần test gần nhất của Slot.

    result:
        PASS hoặc FAIL

    date:
        Ngày test.

    time:
        Thời gian test.
    """

    result: str
    date: str
    time: str


@dataclass
class MachineSlotYieldRow:
    """
    Kết quả Yield của một Slot.

    Bao gồm:

    - Tổng toàn bộ test trong khoảng lọc.
    - Last 15.
    - Last 30.
    - 10 lần test gần nhất.
    - Kiểm tra FAIL 2 lần liên tục.
    - Trạng thái ALARM tổng thể.
    """

    slot: int

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    total_test: int
    total_pass: int
    total_fail: int
    total_yield: float | None

    # --------------------------------------------------------
    # LAST 15
    # --------------------------------------------------------

    test_count_15: int
    pass_count_15: int
    fail_count_15: int
    yield_15: float | None
    status_15: str

    # --------------------------------------------------------
    # LAST 30
    # --------------------------------------------------------

    test_count_30: int
    pass_count_30: int
    fail_count_30: int
    yield_30: float | None
    status_30: str

    # --------------------------------------------------------
    # LAST 10 TEST
    # --------------------------------------------------------

    latest_tests: list[MachineSlotTest]

    # --------------------------------------------------------
    # FAIL 2 LẦN LIÊN TỤC
    # --------------------------------------------------------

    fail_two_consecutive: bool

    # --------------------------------------------------------
    # OVERALL
    # --------------------------------------------------------

    status: str


# ============================================================
# PAGE RESULT
# ============================================================

@dataclass
class YieldSlotPageResult:
    """Toàn bộ dữ liệu cần hiển thị trong tab Yield Slot."""

    daily: YieldSlotResult
    scrap: YieldSlotScrapResult

    # Machine Slot Yield
    machine_yield: list[MachineSlotYieldRow]

    # Target
    target_15: float
    target_30: float


# ============================================================
# REPOSITORY
# ============================================================

class YieldSlotRepository:
    """Truy vấn PRIME đã tổng hợp cho tab Yield Slot."""

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        self.database_path = Path(
            database_path
        )

    # ========================================================
    # MAIN PAGE
    # ========================================================

    def get_yield_slot_page(
        self,
        date_from: str,
        date_to: str,
        eqp: str,
        chamber: int,
        tiers: list[str | None],
        selected_models: list[str] | None = None,
    ) -> YieldSlotPageResult:
        """
        Tải đồng thời:

        1. Daily Yield
        2. Slot by Scrapcode
        3. Machine Slot Yield 15/30 test
        """

        if not eqp:
            raise ValueError(
                "Vui lòng chọn EQP."
            )

        if chamber not in (1, 2):
            raise ValueError(
                "Vui lòng chọn Chamber 1 hoặc Chamber 2."
            )

        dates = self._build_date_range(
            date_from,
            date_to,
        )

        slots = list(
            range(1, 121)
            if chamber == 1
            else range(121, 241)
        )

        tier_sql, tier_params = build_data_filter(
            column_name="TIER",
            tiers=tiers,
            selected_models=selected_models,
        )

        connection = create_connection(
            self.database_path
        )

        try:
            grouped_rows = connection.execute(
                f"""
                SELECT
                    DATE AS data_date,
                    Slot AS slot_no,

                    CASE
                        WHEN RESULT = 'FAIL'
                         AND NULLIF(
                             TRIM(SCRAPCODE),
                             ''
                         ) IS NOT NULL
                        THEN TRIM(SCRAPCODE)
                        ELSE NULL
                    END AS scrap_code,

                    COUNT(*) AS in_qty,

                    SUM(
                        CASE
                            WHEN RESULT = 'PASS'
                            THEN 1
                            ELSE 0
                        END
                    ) AS pass_qty,

                    SUM(
                        CASE
                            WHEN RESULT = 'FAIL'
                            THEN 1
                            ELSE 0
                        END
                    ) AS fail_qty

                FROM prime_data

                WHERE EQP = ?
                  AND Chamber = ?
                  AND DATE BETWEEN ? AND ?
                  {tier_sql}

                GROUP BY
                    DATE,
                    Slot,
                    scrap_code

                ORDER BY
                    DATE,
                    Slot,
                    scrap_code
                """,
                [
                    eqp,
                    chamber,
                    date_from,
                    date_to,
                    *tier_params,
                ],
            ).fetchall()

        finally:
            connection.close()

        # ====================================================
        # DAILY
        # ====================================================

        by_date = {
            data_date: {
                "in_qty": 0,
                "pass_qty": 0,
                "fail_qty": 0,
                "fail_qty_by_slot": {},
            }
            for data_date in dates
        }

        # ====================================================
        # SLOT SCRAP
        # ====================================================

        by_slot = {
            slot_no: {
                "in_qty": 0,
                "pass_qty": 0,
                "fail_qty": 0,
                "scrap_qty_by_code": {},
            }
            for slot_no in slots
        }

        scrap_code_set: set[str] = set()

        for grouped_row in grouped_rows:

            data_date = str(
                grouped_row["data_date"]
            )

            slot_no = int(
                grouped_row["slot_no"]
            )

            scrap_code = (
                str(grouped_row["scrap_code"])
                if grouped_row["scrap_code"]
                is not None
                else None
            )

            in_qty = int(
                grouped_row["in_qty"] or 0
            )

            pass_qty = int(
                grouped_row["pass_qty"] or 0
            )

            fail_qty = int(
                grouped_row["fail_qty"] or 0
            )

            # ----------------------------------------------
            # DAILY
            # ----------------------------------------------

            day_summary = by_date[data_date]

            day_summary["in_qty"] += in_qty
            day_summary["pass_qty"] += pass_qty
            day_summary["fail_qty"] += fail_qty

            if fail_qty > 0:

                current_slot_fail = (
                    day_summary[
                        "fail_qty_by_slot"
                    ].get(slot_no, 0)
                )

                day_summary[
                    "fail_qty_by_slot"
                ][slot_no] = (
                    current_slot_fail
                    + fail_qty
                )

            # ----------------------------------------------
            # SLOT
            # ----------------------------------------------

            slot_summary = by_slot[slot_no]

            slot_summary["in_qty"] += in_qty
            slot_summary["pass_qty"] += pass_qty
            slot_summary["fail_qty"] += fail_qty

            if (
                scrap_code is not None
                and fail_qty > 0
            ):

                scrap_code_set.add(
                    scrap_code
                )

                current_scrap_qty = (
                    slot_summary[
                        "scrap_qty_by_code"
                    ].get(scrap_code, 0)
                )

                slot_summary[
                    "scrap_qty_by_code"
                ][scrap_code] = (
                    current_scrap_qty
                    + fail_qty
                )

        # ====================================================
        # DAILY ROWS
        # ====================================================

        daily_rows = []

        for data_date in dates:

            day_summary = by_date[
                data_date
            ]

            in_qty = int(
                day_summary["in_qty"]
            )

            pass_qty = int(
                day_summary["pass_qty"]
            )

            yield_percent = (
                pass_qty / in_qty * 100
                if in_qty > 0
                else None
            )

            daily_rows.append(
                YieldSlotDayRow(
                    date=data_date,
                    in_qty=in_qty,
                    pass_qty=pass_qty,
                    fail_qty=int(
                        day_summary["fail_qty"]
                    ),
                    yield_percent=yield_percent,
                    fail_qty_by_slot=dict(
                        day_summary[
                            "fail_qty_by_slot"
                        ]
                    ),
                )
            )

        # ====================================================
        # SCRAP CODE SORT
        # ====================================================

        def scrap_sort_key(
            scrap_code: str,
        ) -> tuple:

            if scrap_code.isdigit():
                return (
                    0,
                    int(scrap_code),
                )

            return (
                1,
                scrap_code.casefold(),
            )

        scrap_codes = sorted(
            scrap_code_set,
            key=scrap_sort_key,
        )

        # ====================================================
        # SCRAP ROWS
        # ====================================================

        scrap_rows = []

        for slot_no in slots:

            slot_summary = by_slot[
                slot_no
            ]

            in_qty = int(
                slot_summary["in_qty"]
            )

            pass_qty = int(
                slot_summary["pass_qty"]
            )

            yield_percent = (
                pass_qty / in_qty * 100
                if in_qty > 0
                else None
            )

            scrap_rows.append(
                YieldSlotScrapRow(
                    slot=slot_no,
                    in_qty=in_qty,
                    pass_qty=pass_qty,
                    fail_qty=int(
                        slot_summary["fail_qty"]
                    ),
                    yield_percent=yield_percent,
                    scrap_qty_by_code=dict(
                        slot_summary[
                            "scrap_qty_by_code"
                        ]
                    ),
                )
            )

        # ====================================================
        # MACHINE SLOT YIELD
        # ====================================================

        machine_yield = (
            self._get_machine_slot_yield(
                date_from=date_from,
                date_to=date_to,
                eqp=eqp,
                chamber=chamber,
                tiers=tiers,
                selected_models=selected_models,
            )
        )

        # ====================================================
        # TARGET
        # ====================================================

        target_15, target_30 = (
            self.get_machine_slot_yield_target()
        )

        # ====================================================
        # RESULTS
        # ====================================================

        daily_result = YieldSlotResult(
            date_from=date_from,
            date_to=date_to,
            eqp=eqp,
            chamber=chamber,
            slots=slots,
            rows=daily_rows,
        )

        scrap_result = YieldSlotScrapResult(
            date_from=date_from,
            date_to=date_to,
            eqp=eqp,
            chamber=chamber,
            scrap_codes=scrap_codes,
            rows=scrap_rows,
        )

        return YieldSlotPageResult(
            daily=daily_result,
            scrap=scrap_result,
            machine_yield=machine_yield,
            target_15=target_15,
            target_30=target_30,
        )

    # ========================================================
    # MACHINE SLOT YIELD
    # ========================================================

    def _get_machine_slot_yield(
        self,
        date_from: str,
        date_to: str,
        eqp: str,
        chamber: int,
        tiers: list[str | None],
        selected_models: list[str] | None = None,
    ) -> list[MachineSlotYieldRow]:
        """
        Lấy dữ liệu Machine Slot Yield.

        Với mỗi Slot:

        - Tổng toàn bộ test trong khoảng Date From -> Date To.
        - Last 15 test gần nhất.
        - Last 30 test gần nhất.
        - 10 test gần nhất kèm ngày/giờ.
        - Kiểm tra FAIL 2 lần liên tục.
        - Kiểm tra Yield Last 15 theo Target.
        - Kiểm tra Yield Last 30 theo Target.

        Thứ tự test mới nhất:

            DATE DESC
            TIME DESC
            id DESC
        """

        slots = list(
            range(1, 121)
            if chamber == 1
            else range(121, 241)
        )

        tier_sql, tier_params = build_data_filter(
            column_name="TIER",
            tiers=tiers,
            selected_models=selected_models,
        )

        target_15, target_30 = (
            self.get_machine_slot_yield_target()
        )

        connection = create_connection(
            self.database_path
        )

        try:

            rows = connection.execute(
                f"""
                SELECT
                    id,
                    DATE AS data_date,
                    TIME AS data_time,
                    Slot AS slot_no,
                    RESULT

                FROM prime_data

                WHERE EQP = ?
                  AND Chamber = ?
                  AND DATE BETWEEN ? AND ?
                  {tier_sql}

                ORDER BY
                    Slot,
                    DATE DESC,
                    TIME DESC,
                    id DESC
                """,
                [
                    eqp,
                    chamber,
                    date_from,
                    date_to,
                    *tier_params,
                ],
            ).fetchall()

        finally:

            connection.close()

        # ====================================================
        # GOM DỮ LIỆU THEO SLOT
        # ====================================================

        slot_results: dict[
            int,
            list[MachineSlotTest]
        ] = {
            slot: []
            for slot in slots
        }

        for row in rows:

            slot = int(
                row["slot_no"]
            )

            if slot not in slot_results:
                continue

            result = str(
                row["RESULT"]
            ).strip().upper()

            # Chỉ tính PASS / FAIL
            if result not in (
                "PASS",
                "FAIL",
            ):
                continue

            data_date = str(
                row["data_date"]
            )

            data_time = str(
                row["data_time"]
                or ""
            )

            slot_results[
                slot
            ].append(
                MachineSlotTest(
                    result=result,
                    date=data_date,
                    time=data_time,
                )
            )

        # ====================================================
        # CALCULATE
        # ====================================================

        result_rows = []

        for slot in slots:

            tests = slot_results[
                slot
            ]

            # ------------------------------------------------
            # TOTAL
            # ------------------------------------------------

            total_test = len(
                tests
            )

            total_pass = sum(
                1
                for test in tests
                if test.result == "PASS"
            )

            total_fail = sum(
                1
                for test in tests
                if test.result == "FAIL"
            )

            total_yield = (
                total_pass
                / total_test
                * 100
                if total_test > 0
                else None
            )

            # ------------------------------------------------
            # LAST 15
            # ------------------------------------------------

            latest_15 = tests[:15]

            pass_15 = sum(
                1
                for test in latest_15
                if test.result == "PASS"
            )

            fail_15 = sum(
                1
                for test in latest_15
                if test.result == "FAIL"
            )

            count_15 = len(
                latest_15
            )

            yield_15 = (
                pass_15
                / count_15
                * 100
                if count_15 > 0
                else None
            )

            if yield_15 is None:

                status_15 = "N/A"

            elif yield_15 < target_15:

                status_15 = (
                    "Hiệu suất không đạt"
                )

            else:

                status_15 = "PASS"

            # ------------------------------------------------
            # LAST 30
            # ------------------------------------------------

            latest_30 = tests[:30]

            pass_30 = sum(
                1
                for test in latest_30
                if test.result == "PASS"
            )

            fail_30 = sum(
                1
                for test in latest_30
                if test.result == "FAIL"
            )

            count_30 = len(
                latest_30
            )

            yield_30 = (
                pass_30
                / count_30
                * 100
                if count_30 > 0
                else None
            )

            if yield_30 is None:

                status_30 = "N/A"

            elif yield_30 < target_30:

                status_30 = (
                    "Hiệu suất không đạt"
                )

            else:

                status_30 = "PASS"

            # ------------------------------------------------
            # 10 TEST GẦN NHẤT
            # ------------------------------------------------

            latest_10 = tests[:10]

            # ------------------------------------------------
            # FAIL 2 LẦN LIÊN TỤC
            #
            # tests[0] = lần mới nhất
            # tests[1] = lần ngay trước đó
            # ------------------------------------------------

            fail_two_consecutive = (
                len(tests) >= 2
                and tests[0].result == "FAIL"
                and tests[1].result == "FAIL"
            )

            # ------------------------------------------------
            # OVERALL ALARM
            #
            # Đỏ cả hàng nếu:
            #
            # 1. FAIL 2 lần liên tục
            #
            # OR
            #
            # 2. Last 15 < Target 15
            #
            # OR
            #
            # 3. Last 30 < Target 30
            # ------------------------------------------------

            alarm_condition = (
                fail_two_consecutive
                or (
                    status_15
                    == "Hiệu suất không đạt"
                )
                or (
                    status_30
                    == "Hiệu suất không đạt"
                )
            )

            if alarm_condition:

                overall_status = "ALARM"

            elif (
                status_15 == "N/A"
                and status_30 == "N/A"
            ):

                overall_status = "N/A"

            else:

                overall_status = "PASS"

            # ------------------------------------------------
            # APPEND
            # ------------------------------------------------

            result_rows.append(
                MachineSlotYieldRow(

                    slot=slot,

                    # TOTAL
                    total_test=total_test,
                    total_pass=total_pass,
                    total_fail=total_fail,
                    total_yield=total_yield,

                    # LAST 15
                    test_count_15=count_15,
                    pass_count_15=pass_15,
                    fail_count_15=fail_15,
                    yield_15=yield_15,
                    status_15=status_15,

                    # LAST 30
                    test_count_30=count_30,
                    pass_count_30=pass_30,
                    fail_count_30=fail_30,
                    yield_30=yield_30,
                    status_30=status_30,

                    # LAST 10
                    latest_tests=latest_10,

                    # FAIL 2 CONTINUOUS
                    fail_two_consecutive=(
                        fail_two_consecutive
                    ),

                    # OVERALL
                    status=overall_status,
                )
            )

        return result_rows

    # ========================================================
    # TARGET - GET
    # ========================================================

    def get_machine_slot_yield_target(
        self,
    ) -> tuple[float, float]:
        """
        Lấy Target Last 15 và Last 30.

        Returns:
            (
                target_15,
                target_30,
            )
        """

        connection = create_connection(
            self.database_path
        )

        try:

            row = connection.execute(
                """
                SELECT
                    target_15,
                    target_30

                FROM machine_slot_yield_target

                WHERE id = 1
                """
            ).fetchone()

        finally:

            connection.close()

        if row is None:

            return (
                95.0,
                95.0,
            )

        return (
            float(row["target_15"]),
            float(row["target_30"]),
        )

    # ========================================================
    # TARGET - SAVE
    # ========================================================

    def save_machine_slot_yield_target(
        self,
        target_15: float,
        target_30: float,
    ) -> None:
        """
        Lưu Target Last 15 / Last 30.
        """

        target_15 = float(
            target_15
        )

        target_30 = float(
            target_30
        )

        if not 0 <= target_15 <= 100:

            raise ValueError(
                "Target 15 phải nằm "
                "trong khoảng 0-100%."
            )

        if not 0 <= target_30 <= 100:

            raise ValueError(
                "Target 30 phải nằm "
                "trong khoảng 0-100%."
            )

        connection = create_connection(
            self.database_path
        )

        try:

            connection.execute(
                """
                INSERT INTO machine_slot_yield_target (
                    id,
                    target_15,
                    target_30,
                    updated_at
                )

                VALUES (
                    1,
                    ?,
                    ?,
                    ?
                )

                ON CONFLICT(id)
                DO UPDATE SET
                    target_15 =
                        excluded.target_15,

                    target_30 =
                        excluded.target_30,

                    updated_at =
                        excluded.updated_at
                """,
                (
                    target_15,
                    target_30,
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                ),
            )

            connection.commit()

        except Exception:

            connection.rollback()
            raise

        finally:

            connection.close()

    # ========================================================
    # DATE RANGE
    # ========================================================

    @staticmethod
    def _build_date_range(
        date_from: str,
        date_to: str,
    ) -> list[str]:
        """Tạo đủ mọi ngày trong khoảng lọc."""

        try:

            start_date = datetime.strptime(
                date_from,
                "%Y%m%d",
            ).date()

            end_date = datetime.strptime(
                date_to,
                "%Y%m%d",
            ).date()

        except ValueError as error:

            raise ValueError(
                "Ngày lọc phải có định dạng yyyyMMdd."
            ) from error

        if start_date > end_date:

            raise ValueError(
                "Date From không được lớn hơn Date To."
            )

        day_count = (
            end_date - start_date
        ).days + 1

        return [
            (
                start_date
                + timedelta(
                    days=offset
                )
            ).strftime(
                "%Y%m%d"
            )
            for offset in range(
                day_count
            )
        ]

    # ========================================================
    # LEGACY TIER FILTER
    # ========================================================

    @staticmethod
    def _build_tier_filter(
        column_name: str,
        tiers: list[str | None],
    ) -> tuple[str, list[str]]:
        """
        Tạo điều kiện SQL chỉ cho Tier khác NULL.

        Giữ lại để tương thích với code cũ.
        """

        normal_tiers = [
            str(tier)
            for tier in tiers
            if tier is not None
        ]

        if not normal_tiers:

            return (
                "AND 0 = 1",
                [],
            )

        placeholders = ", ".join(
            "?"
            for _ in normal_tiers
        )

        return (
            f"AND {column_name} "
            f"IN ({placeholders})",
            normal_tiers,
        )