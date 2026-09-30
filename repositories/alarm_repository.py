from __future__ import annotations

import sqlite3

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Union

from database.connection import create_connection


@dataclass(frozen=True)
class SlotFailAlarmRow:
    """Một dòng hiển thị trong bảng Slot Fail Alarm."""

    alarm_date: str
    eqp: str
    chamber: int
    slot: int
    start_datetime: str
    end_datetime: str
    fail_qty: int
    scrap_codes: str
    models: str
    lotids: str
    status: str = "Chưa tiến hành"
    date_complete: str = ""
    engineer: str = ""


@dataclass(frozen=True)
class SlotFailAlarmResult:
    """Kết quả query của tab Alarm."""

    date_from: str
    date_to: str
    rows: list[SlotFailAlarmRow]


@dataclass(frozen=True)
class SlotFailHistoryRow:
    """Một dòng FAIL trong lịch sử của một slot."""

    date: str
    time: str
    model: str
    lotid: str
    scrap: str
    fail_qty: int


@dataclass(frozen=True)
class SlotFailHistoryResult:
    """Kết quả lịch sử FAIL của một slot."""

    eqp: str
    chamber: int
    slot: int
    rows: list[SlotFailHistoryRow]


@dataclass(frozen=True)
class AlarmRow:
    """Một dòng Machine Slot Yield Alarm hiển thị trên TAB Alarm."""

    alarm_type: str
    alarm_date: str
    eqp: str
    machine: str
    chamber: int | str
    slot: int
    start_datetime: str
    end_datetime: str
    fail_qty: int | str
    scrap_codes: str
    models: str
    lotids: str
    yield_15: float | str | None = None
    target_15: float | str | None = None
    yield_30: float | str | None = None
    target_30: float | str | None = None
    yield_15_model: float | None = None
    yield_30_model: float | None = None
    total_test: int = 0
    pass_count: int = 0
    fail_count: int = 0
    yield_percent: float | str | None = None
    reason: str = ""
    status: str = "Chưa tiến hành"
    date_complete: str = ""
    quick_check_result: str = ""
    cal_check_result: str = ""
    engineer_action: str = ""
    monitor_day1: str = ""
    monitor_day2: str = ""
    monitor_day3: str = ""
    comment: str = ""
    engineer: str = ""


@dataclass(frozen=True)
class AlarmResult:
    """Kết quả query Alarm từ database."""

    date_from: str
    date_to: str
    rows: list[AlarmRow]


MACHINE_SLOT_YIELD_ALARM_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS machine_slot_yield_alarm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alarm_date TEXT NOT NULL,
    machine TEXT NOT NULL,
    slot INTEGER NOT NULL,
    start_datetime TEXT NOT NULL DEFAULT '',
    end_datetime TEXT NOT NULL DEFAULT '',
    yield_15 REAL,
    target_15 REAL NOT NULL DEFAULT 0,
    yield_30 REAL,
    target_30 REAL NOT NULL DEFAULT 0,
    total_test INTEGER NOT NULL DEFAULT 0,
    pass_count INTEGER NOT NULL DEFAULT 0,
    fail_count INTEGER NOT NULL DEFAULT 0,
    yield_percent REAL,
    reason TEXT NOT NULL DEFAULT '',
    scrap_codes TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Chưa tiến hành',
    date_complete TEXT NOT NULL DEFAULT '',
    quick_check_result TEXT NOT NULL DEFAULT '',
    cal_check_result TEXT NOT NULL DEFAULT '',
    engineer_action TEXT NOT NULL DEFAULT '',
    monitor_day1 TEXT NOT NULL DEFAULT '',
    monitor_day2 TEXT NOT NULL DEFAULT '',
    monitor_day3 TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    engineer TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (alarm_date, machine, slot)
)
"""



class AlarmRepository:
    """Tạo và truy vấn Slot Fail Alarm từ prime_data."""

    FAIL_THRESHOLD = 2
    INSERT_BATCH_SIZE = 1_000
    DATE_BATCH_SIZE = 500

    def __init__(
            self,
            database_path: Union[str, Path] | None = None,
    ):
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else None
        )

    # ============================================================
    # SLOT FAIL ALARM
    # ============================================================

    @staticmethod
    def prepare_affected_slots_for_prime_replace(
            connection: sqlite3.Connection,
    ) -> None:
        """
        Lưu các slot bị tác động bởi dữ liệu PRIME cũ và staging.
        """

        AlarmRepository._reset_affected_slot_table(
            connection
        )

        connection.execute(
            """
            INSERT OR IGNORE INTO temp_alarm_affected_slot (
                eqp,
                chamber,
                slot
            )
            SELECT DISTINCT
                prime.EQP,
                prime.Chamber,
                prime.Slot
            FROM prime_data AS prime
            INNER JOIN temp_prime_delete_ids AS deleted
                ON deleted.id = prime.id
            """
        )

        connection.execute(
            """
            INSERT OR IGNORE INTO temp_alarm_affected_slot (
                eqp,
                chamber,
                slot
            )
            SELECT DISTINCT
                stage.EQP,
                stage.Chamber,
                stage.Slot
            FROM staging_prime.staging_prime_data AS stage
            """
        )

    @staticmethod
    def prepare_affected_slots_for_dates(
            connection: sqlite3.Connection,
            business_dates: Iterable[str],
    ) -> None:
        """Lưu các slot có PRIME thuộc những ngày vừa đổi Tier."""

        dates = sorted(set(business_dates))

        AlarmRepository._reset_affected_slot_table(
            connection
        )

        if not dates:
            return

        for start_index in range(
                0,
                len(dates),
                AlarmRepository.DATE_BATCH_SIZE,
        ):
            date_batch = dates[
                start_index:
                start_index
                + AlarmRepository.DATE_BATCH_SIZE
            ]

            placeholders = ", ".join(
                "?" for _ in date_batch
            )

            connection.execute(
                f"""
                INSERT OR IGNORE INTO temp_alarm_affected_slot (
                    eqp,
                    chamber,
                    slot
                )
                SELECT DISTINCT
                    EQP,
                    Chamber,
                    Slot
                FROM prime_data
                WHERE DATE IN ({placeholders})
                """,
                date_batch,
            )

    @staticmethod
    def _reset_affected_slot_table(
            connection: sqlite3.Connection,
    ) -> None:
        """Tạo lại bảng TEMP chứa khóa slot cần tính alarm."""

        connection.execute(
            """
            DROP TABLE IF EXISTS temp_alarm_affected_slot
            """
        )

        connection.execute(
            """
            CREATE TEMP TABLE temp_alarm_affected_slot (
                eqp TEXT NOT NULL,
                chamber INTEGER NOT NULL,
                slot INTEGER NOT NULL,

                PRIMARY KEY (
                    eqp,
                    chamber,
                    slot
                )
            ) WITHOUT ROWID
            """
        )

    def rebuild_affected_slots(
            self,
            connection: sqlite3.Connection,
            affected_dates: Iterable[str] | None = None,
    ) -> int:

        target_dates: list[str] | None

        if affected_dates is None:
            target_dates = None
            target_date_set = None

        else:
            target_dates = sorted(
                {
                    str(date)
                    for date in affected_dates
                    if str(date).strip()
                }
            )

            if not target_dates:
                return 0

            target_date_set = set(
                target_dates
            )

        if target_dates is None:

            cursor = connection.execute(
                """
                SELECT
                    prime.id,
                    prime.DATE,
                    prime.TIME,
                    prime.RESULT,
                    prime.SCRAPCODE,
                    prime.MODEL,
                    prime.LOTNO,
                    prime.QTY,
                    prime.EQP,
                    prime.Chamber,
                    prime.Slot

                FROM temp_alarm_affected_slot AS affected

                CROSS JOIN prime_data AS prime
                    INDEXED BY idx_prime_alarm_event_order

                    ON prime.EQP = affected.eqp
                   AND prime.Chamber = affected.chamber
                   AND prime.Slot = affected.slot

                ORDER BY
                    affected.eqp,
                    affected.chamber,
                    affected.slot,
                    prime.DATE,
                    prime.TIME,
                    prime.id
                """
            )

        else:

            minimum_date = target_dates[0]
            maximum_date = target_dates[-1]

            cursor = connection.execute(
                """
                WITH affected_with_last_pass AS (
                    SELECT
                        affected.eqp,
                        affected.chamber,
                        affected.slot,

                        (
                            SELECT previous.id

                            FROM prime_data AS previous
                                INDEXED BY
                                    idx_prime_alarm_event_order

                            WHERE previous.EQP =
                                    affected.eqp
                              AND previous.Chamber =
                                    affected.chamber
                              AND previous.Slot =
                                    affected.slot

                              AND previous.RESULT = 'PASS'
                              AND previous.DATE < ?

                            ORDER BY
                                previous.DATE DESC,
                                previous.TIME DESC,
                                previous.id DESC

                            LIMIT 1
                        ) AS last_pass_id

                    FROM temp_alarm_affected_slot AS affected
                ),

                affected_boundary AS (
                    SELECT
                        affected.eqp,
                        affected.chamber,
                        affected.slot,
                        affected.last_pass_id,

                        boundary.DATE AS boundary_date,
                        boundary.TIME AS boundary_time,
                        boundary.id AS boundary_id

                    FROM affected_with_last_pass AS affected

                    LEFT JOIN prime_data AS boundary
                        ON boundary.id =
                            affected.last_pass_id
                )

                SELECT
                    prime.id,
                    prime.DATE,
                    prime.TIME,
                    prime.RESULT,
                    prime.SCRAPCODE,
                    prime.MODEL,
                    prime.LOTNO,
                    prime.QTY,
                    prime.EQP,
                    prime.Chamber,
                    prime.Slot

                FROM affected_boundary AS affected

                CROSS JOIN prime_data AS prime
                    INDEXED BY idx_prime_alarm_event_order

                    ON prime.EQP = affected.eqp
                   AND prime.Chamber = affected.chamber
                   AND prime.Slot = affected.slot

                WHERE prime.DATE <= ?

                  AND (
                        prime.DATE >= ?

                        OR affected.last_pass_id IS NULL

                        OR prime.DATE >
                            affected.boundary_date

                        OR (
                            prime.DATE =
                                affected.boundary_date
                            AND prime.TIME >
                                affected.boundary_time
                        )

                        OR (
                            prime.DATE =
                                affected.boundary_date
                            AND prime.TIME =
                                affected.boundary_time
                            AND prime.id >
                                affected.boundary_id
                        )
                  )

                ORDER BY
                    affected.eqp,
                    affected.chamber,
                    affected.slot,
                    prime.DATE,
                    prime.TIME,
                    prime.id
                """,
                (
                    minimum_date,
                    maximum_date,
                    minimum_date,
                ),
            )

        current_slot = None
        slot_events: list[sqlite3.Row] = []

        insert_rows: list[tuple] = []
        inserted_count = 0

        for row in cursor:

            slot_key = (
                str(row["EQP"]),
                int(row["Chamber"]),
                int(row["Slot"]),
            )

            if (
                    current_slot is not None
                    and slot_key != current_slot
            ):

                insert_rows.extend(
                    self._build_slot_alarms(
                        events=slot_events,
                        target_dates=target_date_set,
                    )
                )

                inserted_count += (
                    self._flush_insert_rows(
                        connection=connection,
                        insert_rows=insert_rows,
                        force=False,
                    )
                )

                slot_events = []

            current_slot = slot_key
            slot_events.append(row)

        if slot_events:

            insert_rows.extend(
                self._build_slot_alarms(
                    events=slot_events,
                    target_dates=target_date_set,
                )
            )

        inserted_count += self._flush_insert_rows(
            connection=connection,
            insert_rows=insert_rows,
            force=True,
        )

        return inserted_count

    def _flush_insert_rows(
            self,
            connection: sqlite3.Connection,
            insert_rows: list[tuple],
            force: bool,
    ) -> int:

        if not insert_rows:
            return 0

        if (
                not force
                and len(insert_rows)
                < self.INSERT_BATCH_SIZE
        ):
            return 0

        connection.executemany(
            """
            INSERT INTO slot_fail_alarm (
                alarm_date,
                eqp,
                chamber,
                slot,
                start_prime_id,
                end_prime_id,
                start_datetime,
                end_datetime,
                fail_qty,
                scrap_codes,
                models,
                lotids
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (alarm_date, eqp, chamber, slot) DO UPDATE SET
                start_prime_id = excluded.start_prime_id,
                end_prime_id = excluded.end_prime_id,
                start_datetime = excluded.start_datetime,
                end_datetime = excluded.end_datetime,
                fail_qty = excluded.fail_qty,
                scrap_codes = excluded.scrap_codes,
                models = excluded.models,
                lotids = excluded.lotids
            """,
            insert_rows,
        )

        inserted_count = len(insert_rows)
        insert_rows.clear()

        return inserted_count

    @staticmethod
    def _build_slot_alarms(
            events: list[sqlite3.Row],
            target_dates: set[str] | None = None,
    ) -> list[tuple]:

        if not events:
            return []

        threshold = (
            AlarmRepository.FAIL_THRESHOLD
        )

        daily_fail_indexes: dict[
            tuple[str, str],
            list[int],
        ] = {}

        consecutive_indexes_by_date: dict[
            str,
            set[int],
        ] = {}

        run_fail_indexes_by_model: dict[
            str,
            list[int],
        ] = {}

        for index, event in enumerate(events):

            result = str(
                event["RESULT"] or ""
            ).strip().upper()

            event_model = str(
                event["MODEL"] or ""
            ).strip()

            if not event_model:
                run_fail_indexes_by_model.clear()
                continue

            if result != "FAIL":
                run_fail_indexes_by_model.clear()
                continue

            model_run_indexes = (
                run_fail_indexes_by_model.setdefault(
                    event_model,
                    [],
                )
            )

            model_run_indexes.append(index)

            event_date = str(
                event["DATE"]
            )

            if (
                    target_dates is not None
                    and event_date not in target_dates
            ):
                continue

            daily_fail_indexes.setdefault(
                (event_date, event_model),
                [],
            ).append(index)

            if len(model_run_indexes) >= threshold:

                consecutive_indexes_by_date.setdefault(
                    event_date,
                    set(),
                ).update(
                    model_run_indexes
                )

        candidate_indexes_by_date: dict[
            str,
            set[int],
        ] = {}

        for (
                (alarm_date, _model),
                fail_indexes,
        ) in daily_fail_indexes.items():

            if len(fail_indexes) < threshold:
                continue

            candidate_indexes_by_date.setdefault(
                alarm_date,
                set(),
            ).update(
                fail_indexes
            )

        for (
                alarm_date,
                fail_indexes,
        ) in consecutive_indexes_by_date.items():

            candidate_indexes_by_date.setdefault(
                alarm_date,
                set(),
            ).update(
                fail_indexes
            )

        alarm_rows: list[tuple] = []

        for alarm_date in sorted(
                candidate_indexes_by_date
        ):

            candidate_indexes = (
                candidate_indexes_by_date[
                    alarm_date
                ]
            )

            if not candidate_indexes:
                continue

            ordered_indexes = sorted(
                candidate_indexes
            )

            group = [
                events[index]
                for index in ordered_indexes
            ]

            group = [
                row
                for row in group
                if (
                    str(
                        row["RESULT"] or ""
                    ).strip().upper()
                    == "FAIL"
                )
            ]

            if len(group) < threshold:
                continue

            start_event = group[0]
            end_event = group[-1]

            alarm_rows.append(
                (
                    alarm_date,
                    str(end_event["EQP"]),
                    int(end_event["Chamber"]),
                    int(end_event["Slot"]),
                    int(start_event["id"]),
                    int(end_event["id"]),
                    (
                        f'{start_event["DATE"]} '
                        f'{start_event["TIME"]}'
                    ),
                    (
                        f'{end_event["DATE"]} '
                        f'{end_event["TIME"]}'
                    ),
                    sum(
                        int(row["QTY"] or 0)
                        for row in group
                    ),
                    AlarmRepository._join_unique(
                        row["SCRAPCODE"]
                        for row in group
                    ),
                    AlarmRepository._join_unique(
                        row["MODEL"]
                        for row in group
                    ),
                    AlarmRepository._join_unique(
                        row["LOTNO"]
                        for row in group
                    ),
                )
            )

        return alarm_rows

    @staticmethod
    def _join_unique(
            values: Iterable[object],
    ) -> str:

        seen: set[str] = set()
        result: list[str] = []

        for value in values:

            normalized = str(
                value or ""
            ).strip()

            if (
                    not normalized
                    or normalized in seen
            ):
                continue

            seen.add(normalized)
            result.append(normalized)

        return ", ".join(result)

    # ============================================================
    # MACHINE SLOT YIELD ALARM
    # ============================================================

    @staticmethod
    def _machine_alarm_datetime(record) -> str:

        date_value = str(
            getattr(record, "date", "") or ""
        )

        time_value = str(
            getattr(record, "time", "") or ""
        )

        return f"{date_value} {time_value}".strip()

    @staticmethod
    def _ensure_machine_slot_yield_alarm_table(
            connection: sqlite3.Connection,
    ) -> None:

        connection.execute(
            MACHINE_SLOT_YIELD_ALARM_TABLE_SQL
        )

        # Existing databases may already contain the old
        # Machine Slot Yield Alarm table. Add the new tracking
        # columns without deleting historical alarm data.
        columns = {
            str(row["name"])
            for row in connection.execute(
                "PRAGMA table_info(machine_slot_yield_alarm)"
            ).fetchall()
        }

        additions = {
            "scrap_codes": "TEXT NOT NULL DEFAULT ''",
            "model": "TEXT NOT NULL DEFAULT ''",
            "quick_check_result": "TEXT NOT NULL DEFAULT ''",
            "cal_check_result": "TEXT NOT NULL DEFAULT ''",
            "engineer_action": "TEXT NOT NULL DEFAULT ''",
            "monitor_day1": "TEXT NOT NULL DEFAULT ''",
            "monitor_day2": "TEXT NOT NULL DEFAULT ''",
            "monitor_day3": "TEXT NOT NULL DEFAULT ''",
            "comment": "TEXT NOT NULL DEFAULT ''",
            "total_test": "INTEGER NOT NULL DEFAULT 0",
            "pass_count": "INTEGER NOT NULL DEFAULT 0",
            "fail_count": "INTEGER NOT NULL DEFAULT 0",
            "yield_percent": "REAL",
        }

        for name, definition in additions.items():
            if name not in columns:
                connection.execute(
                    f"ALTER TABLE machine_slot_yield_alarm "
                    f"ADD COLUMN {name} {definition}"
                )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_machine_slot_yield_alarm_date
            ON machine_slot_yield_alarm (
                alarm_date,
                machine,
                slot
            )
            """
        )

        from repositories.machine_alarm_details import ensure_details
        ensure_details(connection)

    @staticmethod
    def _machine_alarm_window(
            records,
            count: int,
    ):
        rows = list(records)[-count:]

        if not rows:
            return None

        return rows

    @staticmethod
    def _calculate_consecutive_fail_alarms(
            records,
    ) -> tuple[bool, bool]:
        """
        Tính đúng logic FAIL 2 lần liên tiếp giống
        Machine Slot Yield Tab.

        Trả về:
            fail_two_consecutive
            same_model_fail
        """

        ordered = sorted(
            list(records),
            key=lambda row: (
                str(
                    getattr(
                        row,
                        "date",
                        "",
                    )
                    or ""
                ),
                str(
                    getattr(
                        row,
                        "time",
                        "",
                    )
                    or ""
                ),
                str(
                    getattr(
                        row,
                        "file_name",
                        "",
                    )
                    or ""
                ),
            ),
        )

        fail_two_consecutive = False
        same_model_fail = False

        if len(ordered) < 2:
            return (
                False,
                False,
            )

        for index in range(
            len(ordered) - 1
        ):

            first = ordered[index]
            second = ordered[index + 1]

            first_result = str(
                getattr(
                    first,
                    "result",
                    "",
                )
                or ""
            ).strip().upper()

            second_result = str(
                getattr(
                    second,
                    "result",
                    "",
                )
                or ""
            ).strip().upper()

            if not (
                first_result == "FAIL"
                and second_result == "FAIL"
            ):
                continue

            fail_two_consecutive = True

            first_model = str(
                getattr(
                    first,
                    "partno",
                    "",
                )
                or ""
            ).strip().casefold()

            second_model = str(
                getattr(
                    second,
                    "partno",
                    "",
                )
                or ""
            ).strip().casefold()

            # Fallback nếu record dùng field model
            if not first_model:
                first_model = str(
                    getattr(
                        first,
                        "model",
                        "",
                    )
                    or ""
                ).strip().casefold()

            if not second_model:
                second_model = str(
                    getattr(
                        second,
                        "model",
                        "",
                    )
                    or ""
                ).strip().casefold()

            if (
                first_model
                and second_model
                and first_model == second_model
            ):
                same_model_fail = True

            if (
                fail_two_consecutive
                and same_model_fail
            ):
                break

        return (
            fail_two_consecutive,
            same_model_fail,
        )

    @staticmethod
    def _machine_alarm_evidence(
            records,
            alarm15: bool,
            alarm30: bool,
            fail_two_consecutive: bool,
            same_model_fail: bool,
    ) -> dict:
        """
        Xác định chính xác dữ liệu nguồn của Alarm để TAB Alarm
        có thể hiển thị theo đúng nguyên nhân:
          - FAIL 2 lần liên tục -> Scrap Code
          - FAIL 2 lần liên tục cùng Model -> Model
          - Yield thấp 15/30 -> khoảng test tương ứng
        """

        ordered = sorted(
            list(records),
            key=lambda row: (
                str(getattr(row, "date", "") or ""),
                str(getattr(row, "time", "") or ""),
                str(getattr(row, "file_name", "") or ""),
            ),
        )

        evidence = {
            "start_record": ordered[0] if ordered else None,
            "end_record": ordered[-1] if ordered else None,
            "scrap_codes": "",
            "model": "",
        }

        # Latest consecutive FAIL pair is the most useful evidence.
        consecutive_pair = None

        if fail_two_consecutive or same_model_fail:
            for i in range(len(ordered) - 2, -1, -1):
                first = ordered[i]
                second = ordered[i + 1]

                first_fail = (
                    str(getattr(first, "result", "") or "")
                    .strip().upper() == "FAIL"
                )
                second_fail = (
                    str(getattr(second, "result", "") or "")
                    .strip().upper() == "FAIL"
                )

                if first_fail and second_fail:
                    consecutive_pair = (first, second)
                    break

        evidence["consecutive_pair"] = consecutive_pair

        if consecutive_pair:
            first, second = consecutive_pair

            if fail_two_consecutive:
                codes = []
                for record in (first, second):
                    code = str(
                        getattr(record, "scrapcode", "") or ""
                    ).strip()
                    if code and code not in codes:
                        codes.append(code)
                evidence["scrap_codes"] = ", ".join(codes)

            if same_model_fail:
                first_model = str(
                    getattr(first, "partno", "") or ""
                ).strip()
                second_model = str(
                    getattr(second, "partno", "") or ""
                ).strip()

                if (
                    first_model
                    and second_model
                    and first_model.casefold() == second_model.casefold()
                ):
                    evidence["model"] = first_model

            if fail_two_consecutive or same_model_fail:
                evidence["start_record"] = first
                evidence["end_record"] = second

        # Yield alarms use the latest 15/30 tests as evidence.
        if alarm15 or alarm30:
            windows = []
            if alarm15:
                last15 = AlarmRepository._machine_alarm_window(
                    ordered, 15
                )
                if last15:
                    windows.append(last15)
            if alarm30:
                last30 = AlarmRepository._machine_alarm_window(
                    ordered, 30
                )
                if last30:
                    windows.append(last30)

            for window in windows:
                if not window:
                    continue
                if (
                    evidence["start_record"] is None
                    or (
                        str(getattr(window[0], "date", "") or ""),
                        str(getattr(window[0], "time", "") or ""),
                    )
                    < (
                        str(getattr(evidence["start_record"], "date", "") or ""),
                        str(getattr(evidence["start_record"], "time", "") or ""),
                    )
                ):
                    evidence["start_record"] = window[0]

                if (
                    evidence["end_record"] is None
                    or (
                        str(getattr(window[-1], "date", "") or ""),
                        str(getattr(window[-1], "time", "") or ""),
                    )
                    > (
                        str(getattr(evidence["end_record"], "date", "") or ""),
                        str(getattr(evidence["end_record"], "time", "") or ""),
                    )
                ):
                    evidence["end_record"] = window[-1]

        return evidence

    def _calculate_machine_slot_yield_alarm(
            self,
            machine: str,
            slot: int,
            records,
            target_15: float,
            target_30: float,
            alarm15: bool,
            alarm30: bool,
            fail_two_consecutive: bool = False,
            same_model_fail: bool = False,
    ) -> tuple | None:
        """
        Tạo một Machine Slot Yield Alarm.

        Alarm khi có 2 FAIL liên tiếp trong 5 ngày gần nhất.
        Không phân biệt cùng Model hay khác Model.
        """

        ordered = sorted(
            list(records),
            key=lambda row: (
                str(
                    getattr(
                        row,
                        "date",
                        "",
                    )
                    or ""
                ),
                str(
                    getattr(
                        row,
                        "time",
                        "",
                    )
                    or ""
                ),
                str(
                    getattr(
                        row,
                        "file_name",
                        "",
                    )
                    or ""
                ),
            ),
        )

        if not ordered:
            return None

        last15 = self._machine_alarm_window(
            ordered,
            15,
        )

        last30 = self._machine_alarm_window(
            ordered,
            30,
        )

        y15 = (
            sum(
                1
                for row in last15
                if str(
                    getattr(
                        row,
                        "result",
                        "",
                    )
                    or ""
                ).strip().upper() == "PASS"
            )
            / len(last15)
            * 100.0
            if last15
            else None
        )

        y30 = (
            sum(
                1
                for row in last30
                if str(
                    getattr(
                        row,
                        "result",
                        "",
                    )
                    or ""
                ).strip().upper() == "PASS"
            )
            / len(last30)
            * 100.0
            if last30
            else None
        )

        alarm = (
            bool(fail_two_consecutive)
            or bool(same_model_fail)
            or bool(alarm15)
            or bool(alarm30)
        )

        if not alarm:
            return None

        reasons: list[str] = []

        if fail_two_consecutive:
            reasons.append(
                "Fail 2 lần liên tục"
            )

        if same_model_fail:
            reasons.append(
                "Fail 2 lần liên tục cùng mã hàng"
            )

        if alarm15:
            reasons.append(
                "Fail hiệu suất thấp 15 lần liên tục"
            )

        if alarm30:
            reasons.append(
                "Fail hiệu suất thấp 30 lần liên tục"
            )

        start_record = ordered[0]
        end_record = ordered[-1]

        alarm_date = str(
            getattr(
                end_record,
                "date",
                "",
            )
            or ""
        )

        fail_qty = sum(
            1
            for row in ordered
            if str(
                getattr(
                    row,
                    "result",
                    "",
                )
                or ""
            ).strip().upper() == "FAIL"
        )

        return (
            alarm_date,
            machine,
            int(slot),
            self._machine_alarm_datetime(
                start_record
            ),
            self._machine_alarm_datetime(
                end_record
            ),
            y15,
            float(target_15),
            y30,
            float(target_30),
            " | ".join(reasons),
            fail_qty,
        )

    @staticmethod
    def _recent_consecutive_fail_events(
        records,
        days: int = 5,
    ) -> list[tuple[object, object, bool]]:
        """
        Tìm các cặp FAIL liên tiếp trong N ngày gần nhất so với hôm nay.

        Quy tắc mới:
            - Hai lần FAIL liên tiếp là Alarm.
            - Không phân biệt cùng Model hay khác Model.
            - Nếu cùng Model, trả về same_model=True để hiển thị lý do.
            - Cả hai lần FAIL của cặp phải nằm trong cửa sổ N ngày.
        """
        ordered = sorted(
            list(records or []),
            key=lambda row: (
                str(getattr(row, "date", "") or ""),
                str(getattr(row, "time", "") or ""),
                str(getattr(row, "file_name", "") or ""),
                str(getattr(row, "file_path", "") or ""),
            ),
        )

        today = date.today()
        start_day = today - timedelta(days=max(days - 1, 0))
        events = {}

        for index in range(len(ordered) - 1):
            first = ordered[index]
            second = ordered[index + 1]

            first_result = str(getattr(first, "result", "") or "").strip().upper()
            second_result = str(getattr(second, "result", "") or "").strip().upper()
            if first_result != "FAIL" or second_result != "FAIL":
                continue

            first_date_text = str(getattr(first, "date", "") or "")
            second_date_text = str(getattr(second, "date", "") or "")

            if (
                len(first_date_text) != 8
                or not first_date_text.isdigit()
                or len(second_date_text) != 8
                or not second_date_text.isdigit()
            ):
                continue

            try:
                first_day = datetime.strptime(
                    first_date_text, "%Y%m%d"
                ).date()
                second_day = datetime.strptime(
                    second_date_text, "%Y%m%d"
                ).date()
            except ValueError:
                continue

            # Cả hai lần FAIL phải nằm trong 5 ngày gần nhất.
            if not (
                start_day <= first_day <= today
                and start_day <= second_day <= today
            ):
                continue

            first_model = str(
                getattr(first, "partno", "") or getattr(first, "model", "") or ""
            ).strip()
            second_model = str(
                getattr(second, "partno", "") or getattr(second, "model", "") or ""
            ).strip()

            same_model = bool(
                first_model and second_model
                and first_model.casefold() == second_model.casefold()
            )

            # Table hiện tại chỉ cho 1 alarm / machine / slot / ngày.
            # Nếu cùng ngày có nhiều cặp FAIL, giữ cặp mới nhất.
            event_key = second_date_text
            events[event_key] = (first, second, same_model)

        return [events[key] for key in sorted(events)]

    def sync_machine_slot_yield_result(self, result, date_from=None, date_to=None,
                                      target_15=None, target_30=None,
                                      target_15_model=None, target_30_model=None):
        from repositories.machine_alarm_details import sync_result
        return sync_result(self, result, date_from, date_to, target_15, target_30,
                           target_15_model, target_30_model)

    # ============================================================
    # GET MACHINE SLOT YIELD ALARM
    # ============================================================

    def get_alarm_rows(
            self,
            date_from: str,
            date_to: str,
    ) -> AlarmResult:
        """
        Lấy Machine Slot Yield Alarm từ database.

        Các trường nguồn như Scrap Code/Model được tạo từ Log Test
        khi Machine Slot Yield đồng bộ Alarm.
        Monitor Day 1/2/3 được cập nhật từ Log Test sau Date Complete.
        """

        connection = self._create_read_connection()

        try:
            self._ensure_machine_slot_yield_alarm_table(
                connection
            )

            rows = connection.execute(
                """SELECT * FROM machine_slot_yield_alarm
                   WHERE alarm_date BETWEEN ? AND ?
                   ORDER BY alarm_date DESC, end_datetime DESC, machine, slot""",
                (date_from, date_to),
            ).fetchall()
        finally:
            connection.close()

        return AlarmResult(
            date_from=str(date_from),
            date_to=str(date_to),
            rows=[
                AlarmRow(
                    alarm_type="Machine Slot Yield",
                    alarm_date=str(row["alarm_date"] or ""),
                    eqp="N/A",
                    machine=str(row["machine"] or ""),
                    chamber="N/A",
                    slot=int(row["slot"] or 0),
                    start_datetime=str(row["start_datetime"] or ""),
                    end_datetime=str(row["end_datetime"] or ""),
                    fail_qty="N/A",
                    scrap_codes=str(row["scrap_codes"] or ""),
                    models=str(row["model"] or ""),
                    lotids="N/A",
                    yield_15=row["yield_15"],
                    target_15=row["target_15"],
                    yield_30=row["yield_30"],
                    target_30=row["target_30"],
                    yield_15_model=row["yield_15_model"],
                    yield_30_model=row["yield_30_model"],
                    total_test=int(row["total_test"] or 0),
                    pass_count=int(row["pass_count"] or 0),
                    fail_count=int(row["fail_count"] or 0),
                    yield_percent=row["yield_percent"],
                    reason=str(row["reason"] or ""),
                    status=str(
                        row["status"] or "Chưa tiến hành"
                    ),
                    date_complete=str(row["date_complete"] or ""),
                    quick_check_result=str(
                        row["quick_check_result"] or ""
                    ),
                    cal_check_result=str(
                        row["cal_check_result"] or ""
                    ),
                    engineer_action=str(
                        row["engineer_action"] or ""
                    ),
                    monitor_day1=str(
                        row["monitor_day1"] or ""
                    ),
                    monitor_day2=str(
                        row["monitor_day2"] or ""
                    ),
                    monitor_day3=str(
                        row["monitor_day3"] or ""
                    ),
                    comment=str(row["comment"] or ""),
                    engineer=str(row["engineer"] or ""),
                )
                for row in rows
            ],
        )

    # ============================================================
    # MONITOR RESULT FROM LOG TEST
    # ============================================================

    @staticmethod
    def _parse_date_complete(value: str):
        """Đọc Date Complete dạng dd/MM/yyyy HH:mm:ss hoặc yyyy-MM-dd HH:mm:ss."""
        value = str(value or "").strip()
        if not value:
            return None

        for fmt in (
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d %H:%M:%S",
        ):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        return None

    def _refresh_monitor_results(
            self,
            date_from: str,
            date_to: str,
    ) -> None:
        """
        Sau khi Alarm chuyển Đã hoàn thành, lấy Test Result của:
            Day 1 = ngày kế tiếp Date Complete
            Day 2 = ngày thứ 2
            Day 3 = ngày thứ 3

        Nếu một ngày có nhiều test, lấy kết quả test cuối cùng của ngày.
        """

        from repositories.machine_slot_yield_repository import (
            MachineSlotYieldRepository,
        )

        read_connection = self._create_read_connection()
        try:
            alarms = read_connection.execute(
                """
                SELECT
                    alarm_date,
                    machine,
                    slot,
                    date_complete,
                    monitor_day1,
                    monitor_day2,
                    monitor_day3
                FROM machine_slot_yield_alarm
                WHERE alarm_date BETWEEN ? AND ?
                  AND TRIM(COALESCE(date_complete, '')) != ''
                """,
                (date_from, date_to),
            ).fetchall()
        finally:
            read_connection.close()

        if not alarms:
            return

        config_path = (
            self.database_path.parent
            / "machine_slot_log_folder.json"
        )
        target_path = (
            self.database_path.parent
            / "machine_slot_targets.json"
        )

        repo = MachineSlotYieldRepository(target_path)
        log_root = repo.load_log_folder()

        if not log_root:
            return

        from datetime import timedelta

        parsed = [
            (row, self._parse_date_complete(row["date_complete"]))
            for row in alarms
        ]
        parsed = [
            item for item in parsed
            if item[1] is not None
        ]

        if not parsed:
            return

        min_day = min(dt.date() for _, dt in parsed) + timedelta(days=1)
        max_day = max(dt.date() for _, dt in parsed) + timedelta(days=3)

        result = repo.load(
            log_root=log_root,
            date_from=min_day.strftime("%Y%m%d"),
            date_to=max_day.strftime("%Y%m%d"),
            include_latest_tests=False,
        )

        records_by_key = {}
        for record in result.records:
            key = (
                str(getattr(record, "machine", "") or "").strip().casefold(),
                int(getattr(record, "slot", 0) or 0),
                str(getattr(record, "date", "") or ""),
            )
            records_by_key.setdefault(key, []).append(record)

        updates = []
        for row, complete_dt in parsed:
            values = []
            for offset in (1, 2, 3):
                monitor_date = (
                    complete_dt.date() + timedelta(days=offset)
                ).strftime("%Y%m%d")

                key = (
                    str(row["machine"] or "").strip().casefold(),
                    int(row["slot"] or 0),
                    monitor_date,
                )
                day_records = records_by_key.get(key, [])

                if not day_records:
                    values.append("")
                else:
                    day_records.sort(
                        key=lambda r: (
                            str(getattr(r, "time", "") or ""),
                            str(getattr(r, "file_name", "") or ""),
                        )
                    )
                    values.append(
                        str(
                            getattr(day_records[-1], "result", "") or ""
                        ).strip().upper()
                    )

            updates.append(
                (
                    values[0],
                    values[1],
                    values[2],
                    str(row["alarm_date"]),
                    str(row["machine"]),
                    int(row["slot"]),
                )
            )

        connection = create_connection(
            self.database_path,
            busy_timeout_ms=5_000,
        )
        try:
            connection.execute("BEGIN IMMEDIATE")
            for d1, d2, d3, alarm_date, machine, slot in updates:
                connection.execute(
                    """
                    UPDATE machine_slot_yield_alarm
                    SET
                        monitor_day1 = ?,
                        monitor_day2 = ?,
                        monitor_day3 = ?,
                        updated_at = ?
                    WHERE alarm_date = ?
                      AND machine = ?
                      AND slot = ?
                    """,
                    (
                        d1,
                        d2,
                        d3,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        alarm_date,
                        machine,
                        slot,
                    ),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # ============================================================
    # UPDATE STATUS / ENGINEER
    # ============================================================

    def update_tracking(
            self,
            expected,
            field: str,
            value: str,
    ):
        """
        Lưu thông tin cải tiến của Machine Slot Yield Alarm.
        Các trường có thể chỉnh sửa:
            status
            quick_check_result
            cal_check_result
            engineer_action
            comment
            engineer
        """

        from services.alarm_engineers import load_engineers

        allowed_fields = {
            "status",
            "quick_check_result",
            "cal_check_result",
            "engineer_action",
            "comment",
            "engineer",
        }

        if field not in allowed_fields:
            raise ValueError(
                "Cột Alarm không được phép chỉnh sửa."
            )

        value = str(value or "").strip()

        if field == "status" and value not in (
            "Chưa tiến hành",
            "Đang tiến hành",
            "Đã hoàn thành",
        ):
            raise ValueError("Status không hợp lệ.")

        if field in ("quick_check_result", "cal_check_result"):
            if value and value.upper() not in ("PASS", "FAIL"):
                raise ValueError(
                    f"{field} chỉ được chọn PASS hoặc FAIL."
                )
            value = value.upper()

        if field == "engineer" and value:
            if value not in load_engineers(self.database_path):
                raise ValueError(
                    "Engineer không còn trong engineers.json. "
                    "Vui lòng tải lại bảng."
                )

        is_machine_alarm = (
            isinstance(expected, AlarmRow)
            or str(getattr(expected, "alarm_type", "")) == "Machine Slot Yield"
        )

        if not is_machine_alarm:
            # Keep legacy Slot Fail Alarm behavior.
            key = (
                expected.alarm_date,
                expected.eqp,
                expected.chamber,
                expected.slot,
            )
            connection = None
            try:
                connection = create_connection(
                    self.database_path,
                    busy_timeout_ms=5_000,
                )
                row = connection.execute(
                    """
                    SELECT *
                    FROM slot_fail_alarm
                    WHERE alarm_date = ?
                      AND eqp = ?
                      AND chamber = ?
                      AND slot = ?
                    """,
                    key,
                ).fetchone()

                if row is None:
                    raise ValueError(
                        "Alarm không còn tồn tại. Vui lòng bấm Apply Filter."
                    )

                latest = SlotFailAlarmRow(
                    **{
                        name: row[name]
                        for name in SlotFailAlarmRow.__dataclass_fields__
                    }
                )

                old_values = (
                    latest.status,
                    latest.date_complete,
                    latest.engineer,
                )

                expected_values = (
                    str(getattr(expected, "status", "")),
                    str(getattr(expected, "date_complete", "")),
                    str(getattr(expected, "engineer", "")),
                )

                if old_values != expected_values:
                    connection.rollback()
                    return latest, True

                if getattr(latest, field) != value:
                    if field == "status":
                        complete = (
                            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            if value == "Đã hoàn thành"
                            else ""
                        )
                        latest = replace(
                            latest,
                            status=value,
                            date_complete=complete,
                            monitor_day1=(
                                latest.monitor_day1
                                if value == "Đã hoàn thành"
                                else ""
                            ),
                            monitor_day2=(
                                latest.monitor_day2
                                if value == "Đã hoàn thành"
                                else ""
                            ),
                            monitor_day3=(
                                latest.monitor_day3
                                if value == "Đã hoàn thành"
                                else ""
                            ),
                        )
                    else:
                        latest = replace(latest, **{field: value})

                    connection.execute(
                        """
                        UPDATE slot_fail_alarm
                        SET
                            status = ?,
                            date_complete = ?,
                            engineer = ?
                        WHERE alarm_date = ?
                          AND eqp = ?
                          AND chamber = ?
                          AND slot = ?
                          AND status = ?
                          AND date_complete = ?
                          AND engineer = ?
                        """,
                        (
                            latest.status,
                            latest.date_complete,
                            latest.engineer,
                            *key,
                            *old_values,
                        ),
                    )

                connection.commit()
                return latest, False

            finally:
                if connection is not None:
                    connection.close()

        connection = None
        try:
            connection = create_connection(
                self.database_path,
                busy_timeout_ms=5_000,
            )
            self._ensure_machine_slot_yield_alarm_table(connection)
            connection.execute("BEGIN IMMEDIATE")

            key = (
                str(expected.alarm_date),
                str(expected.machine),
                int(expected.slot),
            )

            row = connection.execute(
                """
                SELECT *
                FROM machine_slot_yield_alarm
                WHERE alarm_date = ?
                  AND machine = ?
                  AND slot = ?
                """,
                key,
            ).fetchone()

            if row is None:
                raise ValueError(
                    "Alarm không còn tồn tại. Vui lòng bấm Apply Filter."
                )

            latest = AlarmRow(
                alarm_type="Machine Slot Yield",
                alarm_date=str(row["alarm_date"] or ""),
                eqp="N/A",
                machine=str(row["machine"] or ""),
                chamber="N/A",
                slot=int(row["slot"] or 0),
                start_datetime=str(row["start_datetime"] or ""),
                end_datetime=str(row["end_datetime"] or ""),
                fail_qty="N/A",
                scrap_codes=str(row["scrap_codes"] or ""),
                models=str(row["model"] or ""),
                lotids="N/A",
                yield_15=row["yield_15"],
                target_15=row["target_15"],
                yield_30=row["yield_30"],
                target_30=row["target_30"],
                yield_15_model=row["yield_15_model"],
                yield_30_model=row["yield_30_model"],
                total_test=int(row["total_test"] or 0),
                pass_count=int(row["pass_count"] or 0),
                fail_count=int(row["fail_count"] or 0),
                yield_percent=row["yield_percent"],
                reason=str(row["reason"] or ""),
                status=str(row["status"] or "Chưa tiến hành"),
                date_complete=str(row["date_complete"] or ""),
                quick_check_result=str(row["quick_check_result"] or ""),
                cal_check_result=str(row["cal_check_result"] or ""),
                engineer_action=str(row["engineer_action"] or ""),
                monitor_day1=str(row["monitor_day1"] or ""),
                monitor_day2=str(row["monitor_day2"] or ""),
                monitor_day3=str(row["monitor_day3"] or ""),
                comment=str(row["comment"] or ""),
                engineer=str(row["engineer"] or ""),
            )

            tracking_fields = (
                "status",
                "date_complete",
                "quick_check_result",
                "cal_check_result",
                "engineer_action",
                "monitor_day1",
                "monitor_day2",
                "monitor_day3",
                "comment",
                "engineer",
            )

            old_values = tuple(
                str(getattr(latest, name, "") or "")
                for name in tracking_fields
            )
            expected_values = tuple(
                str(getattr(expected, name, "") or "")
                for name in tracking_fields
            )

            if old_values != expected_values:
                connection.rollback()
                return latest, True

            if getattr(latest, field, "") != value:
                if field == "status":
                    complete = (
                        datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        if value == "Đã hoàn thành"
                        else ""
                    )
                    latest = replace(
                        latest,
                        status=value,
                        date_complete=complete,
                    )
                else:
                    latest = replace(
                        latest,
                        **{field: value},
                    )

                connection.execute(
                    """
                    UPDATE machine_slot_yield_alarm
                    SET
                        status = ?,
                        date_complete = ?,
                        quick_check_result = ?,
                        cal_check_result = ?,
                        engineer_action = ?,
                        monitor_day1 = ?,
                        monitor_day2 = ?,
                        monitor_day3 = ?,
                        comment = ?,
                        engineer = ?,
                        updated_at = ?
                    WHERE alarm_date = ?
                      AND machine = ?
                      AND slot = ?
                      AND status = ?
                      AND date_complete = ?
                      AND quick_check_result = ?
                      AND cal_check_result = ?
                      AND engineer_action = ?
                      AND monitor_day1 = ?
                      AND monitor_day2 = ?
                      AND monitor_day3 = ?
                      AND comment = ?
                      AND engineer = ?
                    """,
                    (
                        latest.status,
                        latest.date_complete,
                        latest.quick_check_result,
                        latest.cal_check_result,
                        latest.engineer_action,
                        latest.monitor_day1,
                        latest.monitor_day2,
                        latest.monitor_day3,
                        latest.comment,
                        latest.engineer,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        *key,
                        *old_values,
                    ),
                )

            connection.commit()
            return latest, False

        except sqlite3.OperationalError as error:
            if (
                getattr(error, "sqlite_errorcode", 0) & 255
            ) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)                     or "locked" in str(error).lower():
                raise ValueError(
                    "Không thể lưu thay đổi vì database đang được sử dụng."
                ) from error
            raise
        finally:
            if connection is not None:
                connection.close()


    # ============================================================
    # BATCH SAVE TRACKING
    # ============================================================

    def save_tracking_changes(
        self,
        changes,
    ) -> list:
        """
        Lưu nhiều thay đổi Alarm trong một transaction.

        changes:
            [(expected_alarm_row, {field: value, ...}), ...]

        Dùng cho nút Save trên TAB Alarm.
        """
        if not changes:
            return []

        allowed_fields = {
            "status",
            "quick_check_result",
            "cal_check_result",
            "engineer_action",
            "comment",
        }

        connection = None

        try:
            connection = create_connection(
                self.database_path,
                busy_timeout_ms=5_000,
            )
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_machine_slot_yield_alarm_table(connection)

            results = []

            for expected, field_changes in changes:
                if not field_changes:
                    continue

                if str(
                    getattr(expected, "alarm_type", "")
                ) != "Machine Slot Yield":
                    raise ValueError(
                        "TAB Alarm hiện tại chỉ cho phép "
                        "lưu Machine Slot Yield Alarm."
                    )

                key = (
                    str(expected.alarm_date),
                    str(expected.machine),
                    int(expected.slot),
                )

                row = connection.execute(
                    """
                    SELECT *
                    FROM machine_slot_yield_alarm
                    WHERE alarm_date = ?
                      AND machine = ?
                      AND slot = ?
                    """,
                    key,
                ).fetchone()

                if row is None:
                    raise ValueError(
                        "Một Alarm không còn tồn tại. "
                        "Vui lòng bấm Apply Filter."
                    )

                # Optimistic concurrency: nếu DB đã bị thay đổi
                # từ nơi khác thì dừng transaction.
                tracked_fields = (
                    "status",
                    "date_complete",
                    "quick_check_result",
                    "cal_check_result",
                    "engineer_action",
                    "monitor_day1",
                    "monitor_day2",
                    "monitor_day3",
                    "comment",
                    "engineer",
                )

                for name in tracked_fields:
                    db_value = str(row[name] or "")
                    expected_value = str(
                        getattr(expected, name, "") or ""
                    )
                    if db_value != expected_value:
                        raise ValueError(
                            f"Alarm {expected.machine} / Slot "
                            f"{expected.slot} đã thay đổi bởi người khác. "
                            "Vui lòng tải lại dữ liệu."
                        )

                values = {
                    "status": str(row["status"] or "Chưa tiến hành"),
                    "date_complete": str(row["date_complete"] or ""),
                    "quick_check_result": str(
                        row["quick_check_result"] or ""
                    ).upper(),
                    "cal_check_result": str(
                        row["cal_check_result"] or ""
                    ).upper(),
                    "engineer_action": str(
                        row["engineer_action"] or ""
                    ),
                    "monitor_day1": str(
                        row["monitor_day1"] or ""
                    ),
                    "monitor_day2": str(
                        row["monitor_day2"] or ""
                    ),
                    "monitor_day3": str(
                        row["monitor_day3"] or ""
                    ),
                    "comment": str(row["comment"] or ""),
                    "engineer": str(row["engineer"] or ""),
                }

                # field_changes là dict; hỗ trợ cả trường hợp
                # caller truyền list các (field, value).
                if isinstance(field_changes, dict):
                    items = field_changes.items()
                else:
                    items = field_changes

                for field, value in items:
                    if field not in allowed_fields:
                        raise ValueError(
                            f"Cột Alarm không được phép chỉnh sửa: {field}"
                        )

                    value = str(value or "").strip()

                    if field == "status":
                        if value not in (
                            "Chưa tiến hành",
                            "Đang tiến hành",
                            "Đã hoàn thành",
                        ):
                            raise ValueError(
                                "Status không hợp lệ."
                            )

                    if field in (
                        "quick_check_result",
                        "cal_check_result",
                    ):
                        if value and value.upper() not in (
                            "PASS",
                            "FAIL",
                        ):
                            raise ValueError(
                                f"{field} chỉ được chọn PASS hoặc FAIL."
                            )
                        value = value.upper()

                    values[field] = value

                if "status" in field_changes:
                    if values["status"] == "Đã hoàn thành":
                        values["date_complete"] = (
                            datetime.now().strftime(
                                "%d/%m/%Y %H:%M:%S"
                            )
                        )
                    else:
                        values["date_complete"] = ""

                connection.execute(
                    """
                    UPDATE machine_slot_yield_alarm
                    SET
                        status = ?,
                        date_complete = ?,
                        quick_check_result = ?,
                        cal_check_result = ?,
                        engineer_action = ?,
                        monitor_day1 = ?,
                        monitor_day2 = ?,
                        monitor_day3 = ?,
                        comment = ?,
                        engineer = ?,
                        updated_at = ?
                    WHERE
                        alarm_date = ?
                        AND machine = ?
                        AND slot = ?
                    """,
                    (
                        values["status"],
                        values["date_complete"],
                        values["quick_check_result"],
                        values["cal_check_result"],
                        values["engineer_action"],
                        values["monitor_day1"],
                        values["monitor_day2"],
                        values["monitor_day3"],
                        values["comment"],
                        values["engineer"],
                        datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        *key,
                    ),
                )

                latest_row = connection.execute(
                    """
                    SELECT *
                    FROM machine_slot_yield_alarm
                    WHERE alarm_date = ?
                      AND machine = ?
                      AND slot = ?
                    """,
                    key,
                ).fetchone()

                results.append(
                    AlarmRow(
                        alarm_type="Machine Slot Yield",
                        alarm_date=str(
                            latest_row["alarm_date"] or ""
                        ),
                        eqp="N/A",
                        machine=str(
                            latest_row["machine"] or ""
                        ),
                        chamber="N/A",
                        slot=int(
                            latest_row["slot"] or 0
                        ),
                        start_datetime=str(
                            latest_row["start_datetime"] or ""
                        ),
                        end_datetime=str(
                            latest_row["end_datetime"] or ""
                        ),
                        fail_qty="N/A",
                        scrap_codes=str(
                            latest_row["scrap_codes"] or ""
                        ),
                        models=str(
                            latest_row["model"] or ""
                        ),
                        lotids="N/A",
                        yield_15=latest_row["yield_15"],
                        target_15=latest_row["target_15"],
                        yield_30=latest_row["yield_30"],
                        target_30=latest_row["target_30"],
                        yield_15_model=latest_row["yield_15_model"],
                        yield_30_model=latest_row["yield_30_model"],
                        total_test=int(latest_row["total_test"] or 0),
                        pass_count=int(latest_row["pass_count"] or 0),
                        fail_count=int(latest_row["fail_count"] or 0),
                        yield_percent=latest_row["yield_percent"],
                        reason=str(
                            latest_row["reason"] or ""
                        ),
                        status=str(
                            latest_row["status"]
                            or "Chưa tiến hành"
                        ),
                        date_complete=str(
                            latest_row["date_complete"] or ""
                        ),
                        quick_check_result=str(
                            latest_row["quick_check_result"] or ""
                        ),
                        cal_check_result=str(
                            latest_row["cal_check_result"] or ""
                        ),
                        engineer_action=str(
                            latest_row["engineer_action"] or ""
                        ),
                        monitor_day1=str(
                            latest_row["monitor_day1"] or ""
                        ),
                        monitor_day2=str(
                            latest_row["monitor_day2"] or ""
                        ),
                        monitor_day3=str(
                            latest_row["monitor_day3"] or ""
                        ),
                        comment=str(
                            latest_row["comment"] or ""
                        ),
                        engineer=str(
                            latest_row["engineer"] or ""
                        ),
                    )
                )

            connection.commit()
            return results

        except Exception:
            if connection is not None and connection.in_transaction:
                connection.rollback()
            raise

        finally:
            if connection is not None:
                connection.close()

    # ============================================================
    # LATEST MACHINE SLOT YIELD ALARM DATE
    # ============================================================

    def get_latest_machine_slot_yield_alarm_date(self) -> str | None:
        """Lấy ngày Alarm mới nhất để mở TAB Alarm."""

        connection = self._create_read_connection()
        try:
            row = connection.execute(
                """
                SELECT MAX(alarm_date) AS latest_date
                FROM machine_slot_yield_alarm
                """
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            return None

        value = str(row["latest_date"] or "").strip()
        return value or None

    # ============================================================
    # SLOT FAIL HISTORY
    # ============================================================

    def get_slot_fail_history(
            self,
            eqp: str,
            chamber: int,
            slot: int,
    ) -> SlotFailHistoryResult:
        """
        Lấy toàn bộ FAIL của một slot,
        không phụ thuộc Tier.
        """

        connection = self._create_read_connection()

        try:

            rows = connection.execute(
                """
                SELECT
                    DATE,
                    TIME,
                    MODEL,
                    LOTNO,
                    SCRAPCODE,
                    QTY

                FROM prime_data

                WHERE EQP = ?
                  AND Chamber = ?
                  AND Slot = ?
                  AND RESULT = 'FAIL'

                ORDER BY
                    DATE DESC,
                    TIME DESC,
                    id DESC
                """,
                (
                    eqp,
                    chamber,
                    slot,
                ),
            ).fetchall()

        finally:

            connection.close()

        return SlotFailHistoryResult(
            eqp=eqp,
            chamber=chamber,
            slot=slot,
            rows=[
                SlotFailHistoryRow(
                    date=str(
                        row["DATE"]
                    ),
                    time=str(
                        row["TIME"]
                    ),
                    model=str(
                        row["MODEL"]
                        or ""
                    ),
                    lotid=str(
                        row["LOTNO"]
                        or ""
                    ),
                    scrap=str(
                        row["SCRAPCODE"]
                        or ""
                    ),
                    fail_qty=int(
                        row["QTY"]
                        or 0
                    ),
                )
                for row in rows
            ],
        )

    # ============================================================
    # CONNECTION
    # ============================================================

    def _create_read_connection(
            self,
    ) -> sqlite3.Connection:
        """Tạo connection cho truy vấn worker."""

        if self.database_path is None:

            raise ValueError(
                "database_path chưa được cấu hình."
            )

        return create_connection(
            self.database_path
        )