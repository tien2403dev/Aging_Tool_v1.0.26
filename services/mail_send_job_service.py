
from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    timedelta,
)
from pathlib import Path
from typing import (
    Callable,
    Union,
)

from repositories.mail_configuration_repository import (
    MailConfigurationRepository,
)
from repositories.mail_send_repository import (
    MailSendRepository,
)
from repositories.mail_template_repository import (
    MailTemplateRepository,
)
from services.mail_content_builder import (
    MailContentBuilder,
)
from services.mail_service import MailService


# ============================================================
# EXCEPTION
# ============================================================

class NoMailToSendError(Exception):
    """Không có Alarm mới cần gửi."""


# ============================================================
# RESULT
# ============================================================

@dataclass(frozen=True)
class MailSendJobResult:
    """Kết quả của một lần gửi mail."""

    target_date: str

    target_dates: tuple[str, ...]

    sent_slot_count: int

    receiver_count: int

    cc_count: int


# ============================================================
# MAIL SEND JOB SERVICE
# ============================================================

class MailSendJobService:
    """
    Cơ chế gửi chung cho:

        - Nút Send Mail
        - Scheduled Task

    Unified Alarm:

        1. SLOT_FAIL
        2. MACHINE_SLOT_YIELD
    """

    # Kiểm tra ngày gửi và 3 ngày trước đó.
    CHECK_DAY_COUNT = 4

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
    # LOG
    # ========================================================

    @staticmethod
    def _write_log(
        log_callback: Callable[
            [str, str],
            None,
        ] | None,
        level: str,
        message: str,
    ) -> None:
        """
        Ghi log nếu caller truyền log_callback.

        Lỗi log không được phép làm hỏng
        quá trình gửi mail.
        """

        if log_callback is None:
            return

        try:

            log_callback(
                level,
                message,
            )

        except Exception:

            pass

    # ========================================================
    # RUN
    # ========================================================

    def run(
        self,
        target_date: str | None = None,
        log_callback: (
            Callable[[str, str], None]
            | None
        ) = None,
    ) -> MailSendJobResult:
        """
        Gửi toàn bộ Alarm chưa gửi thuộc:

            target_date
            + 3 ngày trước đó.

        Bao gồm:

            SLOT_FAIL
            MACHINE_SLOT_YIELD
        """

        # ----------------------------------------------------
        # Target date
        # ----------------------------------------------------

        if target_date is None:

            target_date = date.today().strftime(
                "%Y%m%d"
            )

        self._validate_target_date(
            target_date
        )

        # ----------------------------------------------------
        # Build 4 ngày
        # ----------------------------------------------------

        target_dates = (
            self._build_target_dates(
                target_date
            )
        )

        formatted_target_dates = ", ".join(
            self._format_date(value)
            for value in target_dates
        )

        self._write_log(
            log_callback,
            "INFO",
            (
                "Bắt đầu Mail Send Job | "
                "Unified Alarm | "
                "Các ngày Alarm: "
                f"{formatted_target_dates}"
            ),
        )

        mail_service = MailService()

        send_repository = (
            MailSendRepository(
                self.database_path
            )
        )

        lock_token = None

        try:

            # =================================================
            # SEND LOCK
            # =================================================

            lock_token = (
                send_repository
                .acquire_send_lock()
            )

            # =================================================
            # MAIL CONFIGURATION
            # =================================================

            config_repository = (
                MailConfigurationRepository(
                    self.database_path
                )
            )

            sender = (
                config_repository
                .get_enabled_sender()
            )

            if sender is None:

                self._write_log(
                    log_callback,
                    "ERROR",
                    (
                        "Không có Sender nào "
                        "được Enable."
                    ),
                )

                raise ValueError(
                    (
                        "Chưa có Sender nào "
                        "được Enable."
                    )
                )

            if not sender.password:

                self._write_log(
                    log_callback,
                    "ERROR",
                    (
                        "Sender chưa có mật khẩu | "
                        f"User ID: {sender.user_id}"
                    ),
                )

                raise ValueError(
                    (
                        "Sender đang Enable "
                        "chưa có mật khẩu."
                    )
                )

            # =================================================
            # RECIPIENTS
            # =================================================

            recipients = (
                config_repository
                .get_recipients()
            )

            receivers = [
                (
                    recipient.user_id,
                    recipient.display_name,
                )
                for recipient in recipients
                if (
                    recipient.recipient_type
                    == "RECEIVER"
                )
            ]

            cc_receivers = [
                (
                    recipient.user_id,
                    recipient.display_name,
                )
                for recipient in recipients
                if (
                    recipient.recipient_type
                    == "CC"
                )
            ]

            receiver_log = ", ".join(
                self._format_person(
                    user_id,
                    display_name,
                )
                for (
                    user_id,
                    display_name,
                ) in receivers
            )

            cc_log = ", ".join(
                self._format_person(
                    user_id,
                    display_name,
                )
                for (
                    user_id,
                    display_name,
                ) in cc_receivers
            )

            self._write_log(
                log_callback,
                "INFO",
                (
                    "Receiver | "
                    f"{receiver_log or 'Không có'}"
                ),
            )

            self._write_log(
                log_callback,
                "INFO",
                (
                    "CC | "
                    f"{cc_log or 'Không có'}"
                ),
            )

            if not receivers:

                raise ValueError(
                    (
                        "Chưa có người nhận "
                        "loại Receiver."
                    )
                )

            # =================================================
            # TEMPLATE
            # =================================================

            template_repository = (
                MailTemplateRepository(
                    self.database_path
                )
            )

            template = (
                template_repository
                .get_template()
            )

            # =================================================
            # GET ALL ALARMS
            # =================================================

            alarms = (
                template_repository
                .get_alarm_previews(
                    target_dates
                )
            )

            # -------------------------------------------------
            # Đếm theo loại
            # -------------------------------------------------

            slot_fail_count = sum(
                1
                for alarm in alarms
                if alarm.alarm_type
                == "SLOT_FAIL"
            )

            machine_yield_count = sum(
                1
                for alarm in alarms
                if alarm.alarm_type
                == "MACHINE_SLOT_YIELD"
            )

            self._write_log(
                log_callback,
                "INFO",
                (
                    "Kiểm tra Unified Alarm | "
                    f"Tổng: {len(alarms)} | "
                    f"SLOT_FAIL: {slot_fail_count} | "
                    "MACHINE_SLOT_YIELD: "
                    f"{machine_yield_count}"
                ),
            )

            # =================================================
            # NO ALARM
            # =================================================

            if not alarms:

                self._write_log(
                    log_callback,
                    "SKIP",
                    (
                        "Không có Slot Fail Alarm "
                        "hoặc Machine Slot Yield Alarm | "
                        "Các ngày: "
                        f"{formatted_target_dates}"
                    ),
                )

                raise NoMailToSendError(
                    (
                        "Không có Slot Fail Alarm "
                        "hoặc Machine Slot Yield Alarm "
                        "trong các ngày "
                        f"{formatted_target_dates}."
                    )
                )

            # =================================================
            # FILTER ALREADY SENT
            # =================================================

            unsent_alarms = (
                send_repository
                .filter_unsent_alarms(
                    alarms=alarms,
                )
            )

            # =================================================
            # BUILD V17 KEY
            #
            # alarm_date
            # alarm_type
            # eqp
            # machine
            # slot
            # =================================================

            unsent_keys = {
                self._build_alarm_key(
                    alarm
                )
                for alarm in unsent_alarms
            }

            all_keys = {
                self._build_alarm_key(
                    alarm
                )
                for alarm in alarms
            }

            skipped_keys = (
                all_keys
                - unsent_keys
            )

            # =================================================
            # LOG ALREADY SENT
            # =================================================

            if skipped_keys:

                skipped_alarms = [
                    alarm
                    for alarm in alarms
                    if (
                        self._build_alarm_key(
                            alarm
                        )
                        in skipped_keys
                    )
                ]

                for alarm in sorted(
                    skipped_alarms,
                    key=self._alarm_sort_key,
                ):

                    self._write_log(
                        log_callback,
                        "SKIP ALARM",
                        self._format_alarm_log(
                            alarm
                        )
                        + " | "
                        "Đã gửi trước đó -> bỏ qua",
                    )

            # =================================================
            # ALL ALREADY SENT
            # =================================================

            if not unsent_alarms:

                raise NoMailToSendError(
                    (
                        "Tất cả Slot Fail Alarm "
                        "và Machine Slot Yield Alarm "
                        "trong các ngày "
                        f"{formatted_target_dates} "
                        "đã được gửi trước đó."
                    )
                )

            # =================================================
            # COUNT UNSENT
            # =================================================

            unsent_slot_fail_count = sum(
                1
                for alarm in unsent_alarms
                if alarm.alarm_type
                == "SLOT_FAIL"
            )

            unsent_machine_yield_count = sum(
                1
                for alarm in unsent_alarms
                if alarm.alarm_type
                == "MACHINE_SLOT_YIELD"
            )

            self._write_log(
                log_callback,
                "INFO",
                (
                    "Alarm chưa gửi | "
                    f"Tổng: {len(unsent_alarms)} | "
                    f"SLOT_FAIL: "
                    f"{unsent_slot_fail_count} | "
                    "MACHINE_SLOT_YIELD: "
                    f"{unsent_machine_yield_count}"
                ),
            )

            # =================================================
            # BUILD MAIL HTML
            # =================================================

            html = (
                MailContentBuilder
                .build_alarm_body_html(
                    target_dates=target_dates,
                    alarms=unsent_alarms,
                    heading=template.heading,
                    closing=template.closing,
                )
            )

            # =================================================
            # BUILD MAIL TEXT
            # =================================================

            text = (
                MailContentBuilder
                .build_alarm_body_text(
                    target_dates=target_dates,
                    alarms=unsent_alarms,
                    heading=template.heading,
                    closing=template.closing,
                )
            )

            # =================================================
            # LOGIN
            # =================================================

            self._write_log(
                log_callback,
                "LOGIN",
                (
                    "Bắt đầu đăng nhập hệ thống mail | "
                    f"Sender: {sender.user_id}"
                ),
            )

            login_success, login_detail = (
                mail_service.login(
                    user_id=sender.user_id,
                    password=sender.password,
                )
            )

            if not login_success:

                self._write_log(
                    log_callback,
                    "LOGIN FAILED",
                    (
                        f"Sender: {sender.user_id} | "
                        f"Reason: {login_detail}"
                    ),
                )

                raise RuntimeError(
                    str(login_detail)
                )

            self._write_log(
                log_callback,
                "LOGIN SUCCESS",
                "Đăng nhập thành công",
            )

            # =================================================
            # SEND MAIL
            # =================================================

            send_success, send_detail = (
                mail_service.send_mail(
                    receivers=receivers,
                    cc_receivers=cc_receivers,
                    subject=template.subject,
                    html=html,
                    text=text,
                )
            )

            if not send_success:

                self._write_log(
                    log_callback,
                    "SEND FAILED",
                    (
                        "Gửi mail thất bại | "
                        f"Sender: {sender.user_id} | "
                        f"Reason: {send_detail}"
                    ),
                )

                raise RuntimeError(
                    str(send_detail)
                )

            self._write_log(
                log_callback,
                "SEND SUCCESS",
                (
                    "Hệ thống mail xác nhận "
                    "gửi thành công"
                ),
            )

            # =================================================
            # USER INFO
            # =================================================

            if mail_service.user_info is None:

                raise RuntimeError(
                    (
                        "Không có thông tin Sender "
                        "sau khi đăng nhập."
                    )
                )

            sender_name = (
                mail_service.user_info.name_vn
                or mail_service.user_info.name_en
                or sender.display_name
            )

            sender_snapshot = (
                self._format_person(
                    mail_service.user_info.user_id,
                    sender_name,
                )
            )

            receiver_snapshot = ", ".join(
                self._format_person(
                    user_id,
                    display_name,
                )
                for (
                    user_id,
                    display_name,
                ) in receivers
            )

            cc_snapshot = ", ".join(
                self._format_person(
                    user_id,
                    display_name,
                )
                for (
                    user_id,
                    display_name,
                ) in cc_receivers
            )

            # =================================================
            # RECORD SUCCESSFUL MAIL
            #
            # Mail History + Send History
            # =================================================

            send_repository.record_successful_mail(
                target_date=target_date,
                alarms=unsent_alarms,
                sender=sender_snapshot,
                receivers=receiver_snapshot,
                cc=cc_snapshot,
                subject=template.subject,
                html_content=html,
            )

            # =================================================
            # RESULT COUNT
            #
            # Đếm theo Unified Alarm Key.
            # =================================================

            sent_slot_count = len(
                {
                    self._build_alarm_key(
                        alarm
                    )
                    for alarm in unsent_alarms
                }
            )

            self._write_log(
                log_callback,
                "HISTORY",
                (
                    "Đã ghi Mail History và "
                    "Send History | "
                    f"SLOT_FAIL: "
                    f"{unsent_slot_fail_count} | "
                    "MACHINE_SLOT_YIELD: "
                    f"{unsent_machine_yield_count}"
                ),
            )

            # =================================================
            # RESULT
            # =================================================

            return MailSendJobResult(
                target_date=target_date,

                target_dates=tuple(
                    target_dates
                ),

                sent_slot_count=sent_slot_count,

                receiver_count=len(
                    receivers
                ),

                cc_count=len(
                    cc_receivers
                ),
            )

        finally:

            # -------------------------------------------------
            # Clear mail session
            # -------------------------------------------------

            mail_service.clear_session()

            # -------------------------------------------------
            # Release lock
            # -------------------------------------------------

            if lock_token is not None:

                try:

                    send_repository.release_send_lock(
                        lock_token
                    )

                except Exception:

                    # Lock tự hết hạn sau 5 phút.
                    pass

    # ========================================================
    # BUILD UNIFIED ALARM KEY
    # ========================================================

    @staticmethod
    def _build_alarm_key(
        alarm,
    ) -> tuple[
        str,
        str,
        str,
        str,
        int,
    ]:
        """
        Key đúng theo schema v17:

            alarm_date
            alarm_type
            eqp
            machine
            slot

        Rất quan trọng:

        SLOT_FAIL:
            machine = ""

        MACHINE_SLOT_YIELD:
            eqp = "N/A"
            machine = machine thực tế
        """

        return (
            str(
                alarm.alarm_date
            ),

            str(
                alarm.alarm_type
                or "SLOT_FAIL"
            ),

            str(
                alarm.eqp
                or ""
            ),

            str(
                alarm.machine
                or ""
            ),

            int(
                alarm.slot
            ),
        )

    # ========================================================
    # ALARM SORT KEY
    # ========================================================

    @classmethod
    def _alarm_sort_key(
        cls,
        alarm,
    ):
        """
        Sort log:

            ngày
            loại Alarm
            EQP
            Machine
            Slot
        """

        return (
            alarm.alarm_date,

            alarm.alarm_type,

            alarm.eqp,

            alarm.machine,

            alarm.slot,
        )

    # ========================================================
    # FORMAT ALARM LOG
    # ========================================================

    @classmethod
    def _format_alarm_log(
        cls,
        alarm,
    ) -> str:
        """
        Format log cho từng Alarm.
        """

        alarm_type = (
            str(
                alarm.alarm_type
                or "SLOT_FAIL"
            )
        )

        date_text = cls._format_date(
            str(
                alarm.alarm_date
            )
        )

        if alarm_type == "MACHINE_SLOT_YIELD":

            return (
                f"Type: MACHINE_SLOT_YIELD | "
                f"Ngày: {date_text} | "
                f"Machine: {alarm.machine} | "
                f"Slot: {alarm.slot}"
            )

        return (
            f"Type: SLOT_FAIL | "
            f"Ngày: {date_text} | "
            f"EQP: {alarm.eqp} | "
            f"Chamber: {alarm.chamber} | "
            f"Slot: {alarm.slot}"
        )

    # ========================================================
    # BUILD TARGET DATES
    # ========================================================

    @staticmethod
    def _build_target_dates(
        target_date: str,
    ) -> list[str]:
        """
        Tạo:

            target_date
            target_date - 1
            target_date - 2
            target_date - 3
        """

        anchor_date = datetime.strptime(
            target_date,
            "%Y%m%d",
        ).date()

        return [
            (
                anchor_date
                - timedelta(
                    days=day_offset
                )
            ).strftime(
                "%Y%m%d"
            )
            for day_offset in range(
                MailSendJobService.CHECK_DAY_COUNT
            )
        ]

    # ========================================================
    # FORMAT PERSON
    # ========================================================

    @staticmethod
    def _format_person(
        user_id: str,
        display_name: str,
    ) -> str:

        user_id = str(
            user_id or ""
        ).strip()

        display_name = str(
            display_name or ""
        ).strip()

        if display_name:

            return (
                f"{display_name}"
                f"({user_id})"
            )

        return user_id

    # ========================================================
    # FORMAT DATE
    # ========================================================

    @staticmethod
    def _format_date(
        value: str,
    ) -> str:

        value = str(
            value or ""
        )

        if (
            len(value) == 8
            and value.isdigit()
        ):

            return (
                f"{value[6:8]}/"
                f"{value[4:6]}/"
                f"{value[0:4]}"
            )

        return value

    # ========================================================
    # VALIDATE DATE
    # ========================================================

    @staticmethod
    def _validate_target_date(
        value: str,
    ) -> None:

        try:

            parsed = datetime.strptime(
                value,
                "%Y%m%d",
            )

            if (
                parsed.strftime(
                    "%Y%m%d"
                )
                != value
            ):

                raise ValueError

        except ValueError as error:

            raise ValueError(
                (
                    "Ngày gửi mail phải có "
                    "dạng yyyyMMdd."
                )
            ) from error

