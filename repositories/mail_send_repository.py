
from __future__ import annotations

import uuid

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Union

from database.connection import create_connection
from repositories.mail_template_repository import (
    MailAlarmPreview,
)


# ============================================================
# MAIL HISTORY
# ============================================================

@dataclass(frozen=True)
class MailHistorySummary:
    id: int
    alarm_date: str
    sent_at: str
    sender: str
    receivers: str
    cc: str
    result: str


@dataclass(frozen=True)
class MailHistoryDetail:
    id: int
    alarm_date: str
    sent_at: str
    sender: str
    receivers: str
    cc: str
    result: str
    subject: str
    html_content: str


# ============================================================
# REPOSITORY
# ============================================================

class MailSendRepository:
    """
    Kiểm tra, lưu và quản lý lịch sử các Alarm đã gửi mail.

    Hỗ trợ:
        1. SLOT_FAIL
        2. MACHINE_SLOT_YIELD

    Schema v17 dùng khóa:

        alarm_date
        alarm_type
        eqp
        machine
        slot
    """

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
    # ALARM TYPE HELPERS
    # ========================================================

    @staticmethod
    def _get_alarm_type(
        alarm: MailAlarmPreview,
    ) -> str:
        """
        Lấy loại Alarm.

        Trong giai đoạn chuyển đổi, MailAlarmPreview
        cũ chưa có alarm_type nên mặc định là SLOT_FAIL.
        """

        alarm_type = getattr(
            alarm,
            "alarm_type",
            None,
        )

        if alarm_type is None:
            return "SLOT_FAIL"

        alarm_type = str(
            alarm_type
        ).strip().upper()

        if alarm_type not in {
            "SLOT_FAIL",
            "MACHINE_SLOT_YIELD",
        }:
            return "SLOT_FAIL"

        return alarm_type

    @staticmethod
    def _get_machine(
        alarm: MailAlarmPreview,
    ) -> str:
        """
        Lấy Machine của Alarm.

        Slot Fail:
            machine thường không có,
            sử dụng chuỗi rỗng.

        Machine Slot Yield:
            sử dụng machine thực tế.
        """

        machine = getattr(
            alarm,
            "machine",
            "",
        )

        if machine is None:
            return ""

        return str(
            machine
        ).strip()

    # ========================================================
    # SEND LOCK
    # ========================================================

    def acquire_send_lock(self) -> str:
        """
        Chặn hai máy gửi mail cùng lúc.
        """

        now = datetime.now()

        lock_token = str(
            uuid.uuid4()
        )

        expires_at = (
            now + timedelta(
                minutes=5
            )
        )

        connection = create_connection(
            self.database_path
        )

        try:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            row = connection.execute(
                """
                SELECT expires_at
                FROM mail_send_lock
                WHERE id = 1
                """
            ).fetchone()

            if row is not None:

                try:
                    current_expiry = (
                        datetime.strptime(
                            str(
                                row["expires_at"]
                            ),
                            "%Y-%m-%d %H:%M:%S",
                        )
                    )

                except ValueError:

                    current_expiry = (
                        now + timedelta(
                            minutes=5
                        )
                    )

                if current_expiry > now:

                    connection.rollback()

                    raise RuntimeError(
                        (
                            "Một máy khác đang thực hiện "
                            "gửi mail. Vui lòng thử lại sau."
                        )
                    )

                connection.execute(
                    """
                    DELETE FROM mail_send_lock
                    WHERE id = 1
                    """
                )

            connection.execute(
                """
                INSERT INTO mail_send_lock (
                    id,
                    lock_token,
                    expires_at
                )
                VALUES (
                    1,
                    ?,
                    ?
                )
                """,
                (
                    lock_token,
                    expires_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                ),
            )

            connection.commit()

            return lock_token

        except Exception:

            if connection.in_transaction:
                connection.rollback()

            raise

        finally:

            connection.close()

    # ========================================================
    # RELEASE SEND LOCK
    # ========================================================

    def release_send_lock(
        self,
        lock_token: str,
    ) -> None:
        """
        Chỉ tiến trình giữ đúng token
        mới được mở khóa.
        """

        connection = create_connection(
            self.database_path
        )

        try:

            connection.execute(
                """
                DELETE FROM mail_send_lock
                WHERE
                    id = 1
                    AND lock_token = ?
                """,
                (
                    lock_token,
                ),
            )

            connection.commit()

        finally:

            connection.close()

    # ========================================================
    # FILTER UNSENT ALARMS
    # ========================================================

    def filter_unsent_alarms(
        self,
        alarms: Iterable[MailAlarmPreview],
    ) -> list[MailAlarmPreview]:
        """
        Loại bỏ các Alarm đã gửi.

        V17 phân biệt theo:

            alarm_date
            alarm_type
            eqp
            machine
            slot

        Vì vậy:

            SLOT_FAIL + Slot 10
            MACHINE_SLOT_YIELD + Slot 10

        được coi là 2 Alarm khác nhau.
        """

        alarm_list = list(
            alarms
        )

        if not alarm_list:
            return []

        # ----------------------------------------------------
        # Lấy toàn bộ ngày cần kiểm tra
        # ----------------------------------------------------

        alarm_dates = sorted(
            {
                str(
                    alarm.alarm_date
                )
                for alarm in alarm_list
            }
        )

        if not alarm_dates:
            return alarm_list

        date_placeholders = ", ".join(
            "?" for _ in alarm_dates
        )

        connection = create_connection(
            self.database_path
        )

        try:

            sent_rows = connection.execute(
                f"""
                SELECT
                    alarm_date,
                    alarm_type,
                    eqp,
                    machine,
                    slot
                FROM mail_slot_send_history
                WHERE alarm_date IN (
                    {date_placeholders}
                )
                """,
                tuple(
                    alarm_dates
                ),
            ).fetchall()

        finally:

            connection.close()

        # ----------------------------------------------------
        # Tạo Set khóa đã gửi
        # ----------------------------------------------------

        sent_keys = {
            (
                str(
                    row["alarm_date"]
                ),

                str(
                    row["alarm_type"]
                ),

                str(
                    row["eqp"]
                ),

                str(
                    row["machine"]
                ),

                int(
                    row["slot"]
                ),
            )
            for row in sent_rows
        }

        # ----------------------------------------------------
        # Chỉ giữ Alarm chưa gửi
        # ----------------------------------------------------

        unsent = []

        for alarm in alarm_list:

            alarm_date = str(
                alarm.alarm_date
            )

            alarm_type = (
                self._get_alarm_type(
                    alarm
                )
            )

            eqp = str(
                getattr(
                    alarm,
                    "eqp",
                    "",
                ) or ""
            ).strip()

            machine = (
                self._get_machine(
                    alarm
                )
            )

            slot = int(
                alarm.slot
            )

            key = (
                alarm_date,
                alarm_type,
                eqp,
                machine,
                slot,
            )

            if key not in sent_keys:

                unsent.append(
                    alarm
                )

        return unsent

    # ========================================================
    # RECORD SUCCESSFUL MAIL
    # ========================================================

    def record_successful_mail(
        self,
        target_date: str,
        alarms: Iterable[MailAlarmPreview],
        sender: str,
        receivers: str,
        cc: str,
        subject: str,
        html_content: str,
    ) -> int:
        """
        Lưu một email thành công và các Alarm đã gửi
        trong cùng một transaction.

        V17 lưu:

            alarm_date
            alarm_type
            eqp
            machine
            slot
            sent_at
        """

        alarm_list = list(
            alarms
        )

        if not alarm_list:

            raise ValueError(
                "Không có Alarm để lưu lịch sử mail."
            )

        sent_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ----------------------------------------------------
        # Chuẩn hóa Alarm keys
        # ----------------------------------------------------

        unique_alarm_keys = set()

        for alarm in alarm_list:

            alarm_date = str(
                alarm.alarm_date
            )

            alarm_type = (
                self._get_alarm_type(
                    alarm
                )
            )

            eqp = str(
                getattr(
                    alarm,
                    "eqp",
                    "",
                ) or ""
            ).strip()

            machine = (
                self._get_machine(
                    alarm
                )
            )

            slot = int(
                alarm.slot
            )

            unique_alarm_keys.add(
                (
                    alarm_date,
                    alarm_type,
                    eqp,
                    machine,
                    slot,
                )
            )

        # ----------------------------------------------------
        # Chuẩn bị rows
        # ----------------------------------------------------

        slot_rows = [
            (
                alarm_date,
                alarm_type,
                eqp,
                machine,
                slot,
                sent_at,
            )
            for (
                alarm_date,
                alarm_type,
                eqp,
                machine,
                slot,
            ) in sorted(
                unique_alarm_keys
            )
        ]

        connection = create_connection(
            self.database_path
        )

        try:

            connection.execute(
                "BEGIN IMMEDIATE"
            )

            # ------------------------------------------------
            # Lưu Mail History
            # ------------------------------------------------

            cursor = connection.execute(
                """
                INSERT INTO mail_send_history (
                    alarm_date,
                    sent_at,
                    sender,
                    receivers,
                    cc,
                    result,
                    subject,
                    html_content
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    'Success',
                    ?,
                    ?
                )
                """,
                (
                    target_date,
                    sent_at,
                    sender,
                    receivers,
                    cc,
                    subject,
                    html_content,
                ),
            )

            # ------------------------------------------------
            # Lưu từng Alarm đã gửi
            # ------------------------------------------------

            connection.executemany(
                """
                INSERT OR IGNORE INTO
                    mail_slot_send_history (
                        alarm_date,
                        alarm_type,
                        eqp,
                        machine,
                        slot,
                        sent_at
                    )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                slot_rows,
            )

            connection.commit()

            return int(
                cursor.lastrowid
            )

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()

    # ========================================================
    # MAIL HISTORY
    # ========================================================

    def get_mail_history(
        self,
        limit: int = 500,
    ) -> list[MailHistorySummary]:
        """
        Lấy danh sách email thành công mới nhất.
        """

        limit = max(
            1,
            int(limit),
        )

        connection = create_connection(
            self.database_path
        )

        try:

            rows = connection.execute(
                """
                SELECT
                    id,
                    alarm_date,
                    sent_at,
                    sender,
                    receivers,
                    cc,
                    result
                FROM mail_send_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    limit,
                ),
            ).fetchall()

            return [
                MailHistorySummary(
                    id=int(
                        row["id"]
                    ),

                    alarm_date=str(
                        row["alarm_date"]
                    ),

                    sent_at=str(
                        row["sent_at"]
                    ),

                    sender=str(
                        row["sender"]
                    ),

                    receivers=str(
                        row["receivers"]
                    ),

                    cc=str(
                        row["cc"] or ""
                    ),

                    result=str(
                        row["result"]
                    ),
                )
                for row in rows
            ]

        finally:

            connection.close()

    # ========================================================
    # MAIL HISTORY DETAIL
    # ========================================================

    def get_mail_history_detail(
        self,
        history_id: int,
    ) -> MailHistoryDetail:
        """
        Lấy snapshot đầy đủ của email đã gửi.
        """

        connection = create_connection(
            self.database_path
        )

        try:

            row = connection.execute(
                """
                SELECT
                    id,
                    alarm_date,
                    sent_at,
                    sender,
                    receivers,
                    cc,
                    result,
                    subject,
                    html_content
                FROM mail_send_history
                WHERE id = ?
                """,
                (
                    history_id,
                ),
            ).fetchone()

            if row is None:

                raise ValueError(
                    (
                        "Không tìm thấy "
                        "Mail History đã chọn."
                    )
                )

            return MailHistoryDetail(
                id=int(
                    row["id"]
                ),

                alarm_date=str(
                    row["alarm_date"]
                ),

                sent_at=str(
                    row["sent_at"]
                ),

                sender=str(
                    row["sender"]
                ),

                receivers=str(
                    row["receivers"]
                ),

                cc=str(
                    row["cc"] or ""
                ),

                result=str(
                    row["result"]
                ),

                subject=str(
                    row["subject"]
                ),

                html_content=str(
                    row["html_content"]
                ),
            )

        finally:

            connection.close()

