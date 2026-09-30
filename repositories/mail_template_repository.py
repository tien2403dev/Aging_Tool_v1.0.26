
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Union

from database.connection import create_connection


# ============================================================
# MAIL TEMPLATE
# ============================================================

@dataclass(frozen=True)
class MailTemplate:
    """Template được người dùng lưu trong database."""

    subject: str
    heading: str
    closing: str


# ============================================================
# MAIL ALARM DETAIL
# ============================================================

@dataclass(frozen=True)
class MailAlarmDetail:
    """
    Một dòng chi tiết trong nội dung email.

    SLOT_FAIL:
        lấy từ prime_data.

    MACHINE_SLOT_YIELD:
        không có PRIME FAIL detail,
        các thông tin Yield nằm ở MailAlarmPreview.
    """

    file_date: str
    time: str
    model: str
    lot_id: str
    scrap_code: str
    fail_qty: int


# ============================================================
# MAIL ALARM PREVIEW
# ============================================================

@dataclass
class MailAlarmPreview:
    """
    Một Alarm và các dòng chi tiết thuộc Alarm.

    Hỗ trợ:

        SLOT_FAIL
        MACHINE_SLOT_YIELD
    """

    alarm_id: int
    alarm_date: str
    eqp: str
    chamber: int
    slot: int
    start_datetime: str
    end_datetime: str
    details: list[MailAlarmDetail]

    # --------------------------------------------------------
    # V17 - Unified Alarm
    # --------------------------------------------------------

    alarm_type: str = "SLOT_FAIL"

    machine: str = ""

    reason: str = ""

    yield_15: float | None = None

    target_15: float | None = None

    yield_30: float | None = None

    target_30: float | None = None

    total_test: int = 0
    pass_count: int = 0
    fail_count: int = 0
    yield_percent: float | None = None

    status: str = ""

    model: str = ""

    scrap_codes: str = ""

    yield_15_model: float | None = None
    target_15_model: float | None = None
    yield_30_model: float | None = None
    target_30_model: float | None = None



# ============================================================
# REPOSITORY
# ============================================================

class MailTemplateRepository:
    """
    Đọc Mail Template và dữ liệu Alarm cho email.

    Email hiện hỗ trợ:

        1. Slot Fail Alarm
        2. Machine Slot Yield Alarm
    """

    TEMPLATE_ID = 1

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        self.database_path = Path(
            database_path
        )

    # ========================================================
    # TEMPLATE
    # ========================================================

    def get_template(self) -> MailTemplate:
        """
        Đọc template hiện tại từ database.
        """

        connection = create_connection(
            self.database_path
        )

        try:

            row = connection.execute(
                """
                SELECT
                    subject,
                    heading,
                    closing
                FROM mail_template
                WHERE id = ?
                """,
                (
                    self.TEMPLATE_ID,
                ),
            ).fetchone()

            if row is None:

                raise RuntimeError(
                    "Không tìm thấy Mail Template."
                )

            return MailTemplate(
                subject=str(
                    row["subject"] or ""
                ),

                heading=str(
                    row["heading"] or ""
                ),

                closing=str(
                    row["closing"] or ""
                ),
            )

        finally:

            connection.close()

    # ========================================================
    # SAVE TEMPLATE
    # ========================================================

    def save_template(
        self,
        subject: str,
        heading: str,
        closing: str,
    ) -> None:
        """
        Lưu template.

        Không lưu Body Preview.
        """

        subject = subject.strip()

        if not subject:

            raise ValueError(
                "Subject không được để trống."
            )

        connection = create_connection(
            self.database_path
        )

        try:

            connection.execute(
                """
                INSERT INTO mail_template (
                    id,
                    subject,
                    heading,
                    closing
                )
                VALUES (?, ?, ?, ?)

                ON CONFLICT(id)
                DO UPDATE SET
                    subject = excluded.subject,
                    heading = excluded.heading,
                    closing = excluded.closing
                """,
                (
                    self.TEMPLATE_ID,
                    subject,
                    heading.strip(),
                    closing.strip(),
                ),
            )

            connection.commit()

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()

    # ========================================================
    # GET ALARM PREVIEWS
    # ========================================================

    def get_alarm_previews(
        self,
        target_dates: str | Iterable[str],
    ) -> list[MailAlarmPreview]:
        """
        Lấy toàn bộ Alarm thuộc các ngày được chọn.

        Bao gồm:

            SLOT_FAIL
            MACHINE_SLOT_YIELD

        Không lọc theo Scrap Code.

        Không lọc theo Status.

        Việc Alarm đã gửi hay chưa được xử lý bởi:

            MailSendRepository.filter_unsent_alarms()
        """

        # ----------------------------------------------------
        # Chuẩn hóa ngày
        # ----------------------------------------------------

        if isinstance(
            target_dates,
            str,
        ):

            normalized_dates = [
                target_dates
            ]

        else:

            normalized_dates = list(
                dict.fromkeys(
                    target_dates
                )
            )

        if not normalized_dates:
            return []

        # ----------------------------------------------------
        # Validate ngày
        # ----------------------------------------------------

        for target_date in normalized_dates:

            self._validate_date(
                target_date
            )

        # ----------------------------------------------------
        # Lấy 2 loại Alarm
        # ----------------------------------------------------

        slot_fail_alarms = (
            self._get_slot_fail_alarms(
                normalized_dates
            )
        )

        machine_yield_alarms = (
            self._get_machine_slot_yield_alarms(
                normalized_dates
            )
        )

        # ----------------------------------------------------
        # Gộp
        # ----------------------------------------------------

        alarms = (
            slot_fail_alarms
            + machine_yield_alarms
        )

        # ----------------------------------------------------
        # Sort:
        #
        # ngày mới nhất
        # loại Alarm
        # machine/EQP
        # chamber
        # slot
        # ----------------------------------------------------

        alarms.sort(
            key=lambda alarm: (
                alarm.alarm_date,
                alarm.alarm_type,
                alarm.eqp,
                alarm.machine,
                alarm.chamber,
                alarm.slot,
            ),
            reverse=True,
        )

        return alarms

    # ========================================================
    # SLOT FAIL ALARM
    # ========================================================

    def _get_slot_fail_alarms(
        self,
        normalized_dates: list[str],
    ) -> list[MailAlarmPreview]:
        """
        Lấy Slot Fail Alarm và các PRIME FAIL
        thuộc từng Alarm.
        """

        date_placeholders = ", ".join(
            "?"
            for _ in normalized_dates
        )

        connection = create_connection(
            self.database_path
        )

        try:

            rows = connection.execute(
                f"""
                SELECT
                    alarm.id AS alarm_id,

                    alarm.alarm_date,

                    alarm.eqp,

                    alarm.chamber,

                    alarm.slot,

                    alarm.start_datetime,

                    alarm.end_datetime,

                    alarm.models AS alarm_models,

                    prime.id AS prime_id,

                    prime.DATE AS file_date,

                    prime.TIME AS fail_time,

                    prime.MODEL AS model,

                    prime.LOTNO AS lot_id,

                    prime.SCRAPCODE AS scrap_code,

                    prime.QTY AS fail_qty

                FROM slot_fail_alarm AS alarm

                LEFT JOIN prime_data AS prime

                    ON prime.EQP =
                        alarm.eqp

                   AND prime.Chamber =
                        alarm.chamber

                   AND prime.Slot =
                        alarm.slot

                   AND prime.RESULT =
                        'FAIL'

                   AND trim(
                        coalesce(
                            prime.MODEL,
                            ''
                        )
                   ) <> ''

                   AND instr(
                        ', ' ||
                        alarm.models ||
                        ', ',
                        ', ' ||
                        trim(
                            prime.MODEL
                        ) ||
                        ', '
                   ) > 0

                   AND (
                        prime.DATE >
                        substr(
                            alarm.start_datetime,
                            1,
                            8
                        )

                        OR (

                            prime.DATE =
                            substr(
                                alarm.start_datetime,
                                1,
                                8
                            )

                            AND prime.TIME >=
                            substr(
                                alarm.start_datetime,
                                10,
                                8
                            )
                        )
                   )

                   AND (
                        prime.DATE <
                        substr(
                            alarm.end_datetime,
                            1,
                            8
                        )

                        OR (

                            prime.DATE =
                            substr(
                                alarm.end_datetime,
                                1,
                                8
                            )

                            AND prime.TIME <=
                            substr(
                                alarm.end_datetime,
                                10,
                                8
                            )
                        )
                   )

                WHERE alarm.alarm_date IN (
                    {date_placeholders}
                )

                ORDER BY
                    alarm.alarm_date DESC,
                    alarm.eqp,
                    alarm.chamber,
                    alarm.slot,
                    prime.DATE DESC,
                    prime.TIME DESC,
                    prime.id DESC
                """,
                tuple(
                    normalized_dates
                ),
            ).fetchall()

        finally:

            connection.close()

        # ----------------------------------------------------
        # Group theo Alarm ID
        # ----------------------------------------------------

        alarms_by_id: dict[
            int,
            MailAlarmPreview,
        ] = {}

        for row in rows:

            alarm_id = int(
                row["alarm_id"]
            )

            alarm = alarms_by_id.get(
                alarm_id
            )

            if alarm is None:

                alarm = MailAlarmPreview(
                    alarm_id=alarm_id,

                    alarm_date=str(
                        row["alarm_date"]
                    ),

                    eqp=str(
                        row["eqp"]
                    ),

                    chamber=int(
                        row["chamber"]
                    ),

                    slot=int(
                        row["slot"]
                    ),

                    start_datetime=str(
                        row["start_datetime"]
                    ),

                    end_datetime=str(
                        row["end_datetime"]
                    ),

                    details=[],

                    alarm_type="SLOT_FAIL",

                    machine="",

                    reason="Slot Fail Alarm",

                    status="",

                    model=str(
                        row["alarm_models"]
                        or ""
                    ),
                )

                alarms_by_id[
                    alarm_id
                ] = alarm

            # ------------------------------------------------
            # Không có PRIME detail
            # ------------------------------------------------

            if row["prime_id"] is None:
                continue

            # ------------------------------------------------
            # Thêm PRIME FAIL detail
            # ------------------------------------------------

            alarm.details.append(
                MailAlarmDetail(
                    file_date=str(
                        row["file_date"]
                    ),

                    time=str(
                        row["fail_time"]
                    ),

                    model=str(
                        row["model"]
                        or ""
                    ),

                    lot_id=str(
                        row["lot_id"]
                        or ""
                    ),

                    scrap_code=str(
                        row["scrap_code"]
                        or ""
                    ),

                    fail_qty=int(
                        row["fail_qty"]
                        or 0
                    ),
                )
            )

        return list(
            alarms_by_id.values()
        )

    # ========================================================
    # MACHINE SLOT YIELD ALARM
    # ========================================================

    def _get_machine_slot_yield_alarms(
        self,
        normalized_dates: list[str],
    ) -> list[MailAlarmPreview]:
        """
        Lấy Machine Slot Yield Alarm.

        Không JOIN prime_data.

        Mỗi dòng trong machine_slot_yield_alarm
        tương ứng với một Alarm.
        """

        date_placeholders = ", ".join(
            "?"
            for _ in normalized_dates
        )

        connection = create_connection(
            self.database_path
        )

        # Same-model targets are current saved settings; old alarm rows do
        # not contain a historical snapshot of these targets.
        from repositories.machine_slot_yield_repository import MachineSlotYieldRepository

        try:
            targets = MachineSlotYieldRepository(
                self.database_path.parent / "machine_slot_targets.json"
            ).load_all_targets()
            columns = {row["name"] for row in connection.execute(
                "PRAGMA table_info(machine_slot_yield_alarm)"
            )}
            model_columns = ", ".join(
                name if name in columns else f"NULL AS {name}"
                for name in ("yield_15_model", "yield_30_model")
            )
            rows = connection.execute(
                f"""
                SELECT
                    id,

                    alarm_date,

                    machine,

                    slot,

                    start_datetime,

                    end_datetime,

                    {model_columns},
                    yield_15,

                    target_15,

                    yield_30,

                    target_30,

                    total_test,
                    pass_count,
                    fail_count,
                    yield_percent,

                    reason,

                    model,

                    status,
                    scrap_codes

                FROM machine_slot_yield_alarm

                WHERE alarm_date IN (
                    {date_placeholders}
                )

                ORDER BY
                    alarm_date DESC,
                    machine,
                    slot
                """,
                tuple(
                    normalized_dates
                ),
            ).fetchall()

        finally:

            connection.close()

        alarms: list[
            MailAlarmPreview
        ] = []

        for row in rows:

            alarms.append(
                MailAlarmPreview(
                    alarm_id=int(
                        row["id"]
                    ),

                    alarm_date=str(
                        row["alarm_date"]
                    ),

                    # Machine Slot Yield không có EQP
                    eqp="N/A",

                    # Machine Slot Yield không có Chamber
                    chamber=0,

                    slot=int(
                        row["slot"]
                    ),

                    start_datetime=str(
                        row["start_datetime"]
                        or ""
                    ),

                    end_datetime=str(
                        row["end_datetime"]
                        or ""
                    ),

                    details=[],

                    alarm_type=(
                        "MACHINE_SLOT_YIELD"
                    ),

                    machine=str(
                        row["machine"]
                        or ""
                    ),

                    reason=str(
                        row["reason"]
                        or ""
                    ),

                    yield_15=(
                        self._to_float(
                            row["yield_15"]
                        )
                    ),

                    target_15=(
                        self._to_float(
                            row["target_15"]
                        )
                    ),

                    yield_30=(
                        self._to_float(
                            row["yield_30"]
                        )
                    ),

                    target_30=(
                        self._to_float(
                            row["target_30"]
                        )
                    ),

                    yield_15_model=self._to_float(row["yield_15_model"]),
                    target_15_model=targets[2],
                    yield_30_model=self._to_float(row["yield_30_model"]),
                    target_30_model=targets[3],
                    total_test=int(row["total_test"] or 0),
                    pass_count=int(row["pass_count"] or 0),
                    fail_count=int(row["fail_count"] or 0),
                    yield_percent=self._to_float(row["yield_percent"]),

                    status=str(
                        row["status"]
                        or ""
                    ),

                    model=str(
                        row["model"]
                        or ""
                    ),

                    scrap_codes=str(
                        row["scrap_codes"]
                        or ""
                    ),
                )
            )

        return alarms

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _to_float(
        value,
    ) -> float | None:
        """
        Chuyển giá trị DB sang float an toàn.
        """

        if value is None:
            return None

        try:

            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

    @staticmethod
    def _validate_date(
        target_date: str,
    ) -> None:
        """
        Validate yyyyMMdd.
        """

        if (
            len(target_date) != 8
            or not target_date.isdigit()
        ):

            raise ValueError(
                "Ngày Alarm phải có dạng yyyyMMdd."
            )

