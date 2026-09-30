
from __future__ import annotations

from html import escape

from repositories.mail_template_repository import (
    MailAlarmPreview,
)


class MailContentBuilder:
    """
    Tạo Body Email cho:

        1. SLOT_FAIL
        2. MACHINE_SLOT_YIELD
    """

    # ========================================================
    # PUBLIC - HTML
    # ========================================================

    @classmethod
    def build_alarm_body_html(
        cls,
        target_dates: list[str],
        alarms: list[MailAlarmPreview],
        heading: str = "",
        closing: str = "",
    ) -> str:

        html_parts = [
            """
            <html>
            <body style="
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 14px;
                color: #111827;
                background-color: #FFFFFF;
            ">
            """
        ]

        # ----------------------------------------------------
        # Heading
        # ----------------------------------------------------

        if heading.strip():

            html_parts.append(
                cls._build_paragraph_html(
                    heading
                )
            )

        # ----------------------------------------------------
        # Không có Alarm
        # ----------------------------------------------------

        if not alarms:

            formatted_dates = ", ".join(
                cls._format_date(value)
                for value in target_dates
            )

            html_parts.append(
                (
                    '<div style="color:#64748B;'
                    'font-style:italic;">'
                    "Không có Slot Fail Alarm hoặc "
                    "Machine Slot Yield Alarm chưa gửi "
                    "trong các ngày: "
                    f"{escape(formatted_dates)}."
                    "</div>"
                )
            )

            if closing.strip():

                html_parts.append(
                    cls._build_paragraph_html(
                        closing
                    )
                )

            html_parts.append(
                "</body></html>"
            )

            return "".join(
                html_parts
            )

        # ----------------------------------------------------
        # Group theo ngày
        # ----------------------------------------------------

        alarms_by_date = (
            cls._group_alarms_by_date(
                target_dates=target_dates,
                alarms=alarms,
            )
        )

        for section_index, (
            alarm_date,
            date_alarms,
        ) in enumerate(
            alarms_by_date.items()
        ):

            formatted_date = (
                cls._format_date(
                    alarm_date
                )
            )

            top_margin = (
                "0"
                if section_index == 0
                else "32px"
            )

            html_parts.append(
                (
                    '<div style="font-size:14px;'
                    'font-weight:500;'
                    f'margin-top:{top_margin};'
                    'margin-bottom:18px;">'
                    "Alarm ngày: "
                    f"{escape(formatted_date)}"
                    "</div>"
                )
            )

            # ------------------------------------------------
            # Tách 2 loại Alarm
            # ------------------------------------------------

            slot_fail_alarms = [
                alarm
                for alarm in date_alarms
                if alarm.alarm_type
                == "SLOT_FAIL"
            ]

            machine_yield_alarms = [
                alarm
                for alarm in date_alarms
                if alarm.alarm_type
                == "MACHINE_SLOT_YIELD"
            ]

            # ------------------------------------------------
            # SLOT FAIL
            # ------------------------------------------------

            if slot_fail_alarms:

                html_parts.append(
                    cls._build_section_title_html(
                        "SLOT FAIL ALARM"
                    )
                )

                for alarm in slot_fail_alarms:

                    html_parts.append(
                        cls._build_slot_fail_block(
                            alarm
                        )
                    )

            # ------------------------------------------------
            # MACHINE SLOT YIELD
            # ------------------------------------------------

            if machine_yield_alarms:

                for alarm in machine_yield_alarms:

                    html_parts.append(
                        cls._build_machine_slot_yield_block(
                            alarm
                        )
                    )

        # ----------------------------------------------------
        # Closing
        # ----------------------------------------------------

        if closing.strip():

            html_parts.append(
                cls._build_paragraph_html(
                    closing
                )
            )

        html_parts.append(
            "</body></html>"
        )

        return "".join(
            html_parts
        )

    # ========================================================
    # PUBLIC - TEXT
    # ========================================================

    @classmethod
    def build_alarm_body_text(
        cls,
        target_dates: list[str],
        alarms: list[MailAlarmPreview],
        heading: str = "",
        closing: str = "",
    ) -> str:
        """
        Tạo nội dung Text tương ứng với HTML.
        """

        lines: list[str] = []

        # ----------------------------------------------------
        # Heading
        # ----------------------------------------------------

        if heading.strip():

            lines.extend(
                [
                    heading.strip(),
                    "",
                ]
            )

        # ----------------------------------------------------
        # Không có Alarm
        # ----------------------------------------------------

        if not alarms:

            formatted_dates = ", ".join(
                cls._format_date(value)
                for value in target_dates
            )

            lines.append(
                (
                    "Không có Slot Fail Alarm hoặc "
                    "Machine Slot Yield Alarm chưa gửi "
                    "trong các ngày: "
                    f"{formatted_dates}."
                )
            )

            if closing.strip():

                lines.extend(
                    [
                        "",
                        closing.strip(),
                    ]
                )

            return "\n".join(
                lines
            )

        # ----------------------------------------------------
        # Group theo ngày
        # ----------------------------------------------------

        alarms_by_date = (
            cls._group_alarms_by_date(
                target_dates=target_dates,
                alarms=alarms,
            )
        )

        for alarm_date, date_alarms in (
            alarms_by_date.items()
        ):

            if lines:

                lines.append("")

            lines.extend(
                [
                    "Alarm ngày: "
                    + cls._format_date(
                        alarm_date
                    ),
                ]
            )

            # ------------------------------------------------
            # Tách loại Alarm
            # ------------------------------------------------

            slot_fail_alarms = [
                alarm
                for alarm in date_alarms
                if alarm.alarm_type
                == "SLOT_FAIL"
            ]

            machine_yield_alarms = [
                alarm
                for alarm in date_alarms
                if alarm.alarm_type
                == "MACHINE_SLOT_YIELD"
            ]

            # ------------------------------------------------
            # SLOT FAIL
            # ------------------------------------------------

            if slot_fail_alarms:

                lines.extend(
                    [
                        "",
                        "========== SLOT FAIL ALARM ==========",
                    ]
                )

                for alarm in slot_fail_alarms:

                    lines.extend(
                        cls._build_slot_fail_text(
                            alarm
                        )
                    )

            # ------------------------------------------------
            # MACHINE SLOT YIELD
            # ------------------------------------------------

            if machine_yield_alarms:

                for alarm in machine_yield_alarms:

                    lines.extend(
                        cls._build_machine_slot_yield_text(
                            alarm
                        )
                    )

        # ----------------------------------------------------
        # Closing
        # ----------------------------------------------------

        if closing.strip():

            lines.extend(
                [
                    "",
                    closing.strip(),
                ]
            )

        return "\n".join(
            lines
        )

    # ========================================================
    # SLOT FAIL - HTML
    # ========================================================

    @classmethod
    def _build_slot_fail_block(
        cls,
        alarm: MailAlarmPreview,
    ) -> str:

        start_date = (
            alarm.start_datetime[:8]
        )

        if (
            start_date
            == alarm.alarm_date
        ):

            alarm_type = (
                "Lỗi từ 2 lần trở lên trong ngày"
            )

        else:

            alarm_type = (
                "Lỗi từ 2 lần liên tiếp qua nhiều ngày"
            )

        html_parts = [
            """
            <div style="
                margin-top:10px;
                margin-bottom:22px;
            ">
            """,
            (
                '<div style="font-weight:600;'
                'margin-bottom:5px;">'
                f"EQP: {escape(alarm.eqp)}"
                "&nbsp;&nbsp;&amp;&nbsp;&nbsp;"
                f"Chamber: {alarm.chamber}"
                "&nbsp;&nbsp;&amp;&nbsp;&nbsp;"
                f"Slot: {alarm.slot}"
                "</div>"
            ),
            (
                '<div style="color:#EF4444;'
                'font-weight:600;'
                'margin-bottom:5px;">'
                "Alarm Type: "
                f"{escape(alarm_type)}"
                "</div>"
            ),
            """
            <table
                cellspacing="0"
                cellpadding="5"
                style="
                    border-collapse:collapse;
                    font-size:12px;
                    margin-bottom:10px;
                "
            >
                <thead>
                    <tr style="
                        background-color:#0D6EFD;
                        color:#FFFFFF;
                        font-weight:600;
                    ">
                        <th style="
                            border:1px solid #CBD5E1;
                            min-width:90px;
                        ">
                            File Date
                        </th>

                        <th style="
                            border:1px solid #CBD5E1;
                            min-width:145px;
                        ">
                            Date time
                        </th>

                        <th style="
                            border:1px solid #CBD5E1;
                            min-width:75px;
                        ">
                            Model
                        </th>

                        <th style="
                            border:1px solid #CBD5E1;
                            min-width:105px;
                        ">
                            Lot ID
                        </th>

                        <th style="
                            border:1px solid #CBD5E1;
                            min-width:100px;
                        ">
                            Scrap code
                        </th>

                        <th style="
                            border:1px solid #CBD5E1;
                            min-width:65px;
                        ">
                            Fail qty
                        </th>
                    </tr>
                </thead>

                <tbody>
            """
        ]

        # ----------------------------------------------------
        # Không có detail
        # ----------------------------------------------------

        if not alarm.details:

            html_parts.append(
                """
                <tr>
                    <td
                        colspan="6"
                        style="
                            border:1px solid #CBD5E1;
                            color:#64748B;
                            text-align:center;
                        "
                    >
                        Không tìm thấy dữ liệu FAIL chi tiết.
                    </td>
                </tr>
                """
            )

        # ----------------------------------------------------
        # Có detail
        # ----------------------------------------------------

        else:

            for detail in alarm.details:

                formatted_file_date = (
                    cls._format_date(
                        detail.file_date
                    )
                )

                formatted_datetime = (
                    cls._format_datetime(
                        detail.file_date,
                        detail.time,
                    )
                )

                html_parts.append(
                    f"""
                    <tr>
                        <td style="
                            border:1px solid #CBD5E1;
                            text-align:center;
                        ">
                            {escape(
                                formatted_file_date
                            )}
                        </td>

                        <td style="
                            border:1px solid #CBD5E1;
                            text-align:center;
                        ">
                            {escape(
                                formatted_datetime
                            )}
                        </td>

                        <td style="
                            border:1px solid #CBD5E1;
                            text-align:center;
                        ">
                            {escape(
                                detail.model
                            )}
                        </td>

                        <td style="
                            border:1px solid #CBD5E1;
                            text-align:center;
                        ">
                            {escape(
                                detail.lot_id
                            )}
                        </td>

                        <td style="
                            border:1px solid #CBD5E1;
                            text-align:center;
                        ">
                            {escape(
                                detail.scrap_code
                            )}
                        </td>

                        <td style="
                            border:1px solid #CBD5E1;
                            text-align:center;
                        ">
                            {detail.fail_qty}
                        </td>
                    </tr>
                    """
                )

        html_parts.extend(
            [
                """
                </tbody>
            </table>
            """,
                "</div>",
            ]
        )

        return "".join(
            html_parts
        )

    # ========================================================
    # MACHINE SLOT YIELD - HTML
    # ========================================================

    @classmethod
    def _build_machine_slot_yield_block(
        cls,
        alarm: MailAlarmPreview,
    ) -> str:

        html_parts = [
            """
            <div style="
                margin-top:10px;
                margin-bottom:22px;
            ">
            """,
            (
                '<div style="font-weight:600;'
                'margin-bottom:5px;">'
                f"Machine: {escape(alarm.machine)}"
                "&nbsp;&nbsp;&amp;&nbsp;&nbsp;"
                f"Slot: {alarm.slot}"
                "</div>"
            ),
            (
                '<div style="margin-bottom:8px;">'
                f"Date: {escape(alarm.alarm_date)}"
                "&nbsp;&nbsp;|&nbsp;&nbsp;"
                f"Start: {escape(alarm.start_datetime)}"
                "&nbsp;&nbsp;|&nbsp;&nbsp;"
                f"End: {escape(alarm.end_datetime)}"
                "</div>"
            ),
        ]

        html_parts.append(
            """
            <table cellspacing="0" cellpadding="5" style="border-collapse:collapse;font-size:12px;margin-bottom:8px;">
                <tr>
                    <th valign="middle" style="vertical-align:middle;border:1px solid #CBD5E1;">Total Test last 30 day</th>
                    <th valign="middle" style="vertical-align:middle;border:1px solid #CBD5E1;">Pass</th>
                    <th valign="middle" style="vertical-align:middle;border:1px solid #CBD5E1;">Fail</th>
                    <th valign="middle" style="vertical-align:middle;border:1px solid #CBD5E1;">Yield</th>
                </tr>
                <tr>
                    <td style="border:1px solid #CBD5E1;text-align:center;">%s</td>
                    <td style="border:1px solid #CBD5E1;text-align:center;">%s</td>
                    <td style="border:1px solid #CBD5E1;text-align:center;">%s</td>
                    <td style="border:1px solid #CBD5E1;text-align:center;">%s</td>
                </tr>
            </table>
            """ % (
                alarm.total_test,
                alarm.pass_count,
                alarm.fail_count,
                cls._format_yield(alarm.yield_percent),
            )
        )

        # ----------------------------------------------------
        # Yield table
        # ----------------------------------------------------

        html_parts.append(
            """
            <table
                cellspacing="0"
                cellpadding="5"
                style="
                    border-collapse:collapse;
                    font-size:12px;
                    margin-bottom:8px;
                "
            >
                <thead>
                    <tr style="
                        background-color:#0D6EFD;
                        color:#FFFFFF;
                        font-weight:600;
                    ">
                        <th valign="middle" style="vertical-align:middle;
                            border:1px solid #CBD5E1;
                            min-width:80px;
                        ">
                            Machine
                        </th>

                        <th valign="middle" style="vertical-align:middle;
                            border:1px solid #CBD5E1;
                            min-width:55px;
                        ">
                            Slot
                        </th>

                        <th valign="middle" style="vertical-align:middle;
                            border:1px solid #CBD5E1;
                            min-width:80px;
                        ">
                            Yield 15
                        </th>

                        <th valign="middle" style="vertical-align:middle;
                            border:1px solid #CBD5E1;
                            min-width:80px;
                        ">
                            Target 15
                        </th>

                        <th valign="middle" style="vertical-align:middle;
                            border:1px solid #CBD5E1;
                            min-width:80px;
                        ">
                            Yield 30
                        </th>

                        <th valign="middle" style="vertical-align:middle;
                            border:1px solid #CBD5E1;
                            min-width:80px;
                        ">
                            Target 30
                        </th>

                        <th valign="middle" style="vertical-align:middle;border:1px solid #CBD5E1;white-space:nowrap;">
                            Yield 15<br>cùng Model
                        </th>
                        <th valign="middle" style="vertical-align:middle;border:1px solid #CBD5E1;white-space:nowrap;">
                            Target 15<br>cùng Model
                        </th>
                        <th valign="middle" style="vertical-align:middle;border:1px solid #CBD5E1;white-space:nowrap;">
                            Yield 30<br>cùng Model
                        </th>
                        <th valign="middle" style="vertical-align:middle;border:1px solid #CBD5E1;white-space:nowrap;">
                            Target 30<br>cùng Model
                        </th>
                    </tr>
                </thead>

                <tbody>
            """
        )

        html_parts.append(
            f"""
            <tr>
                <td style="
                    border:1px solid #CBD5E1;
                    text-align:center;
                ">
                    {escape(alarm.machine)}
                </td>

                <td style="
                    border:1px solid #CBD5E1;
                    text-align:center;
                ">
                    {alarm.slot}
                </td>

                <td style="
                    border:1px solid #CBD5E1;
                    text-align:center;
                ">
                    {cls._format_yield(
                        alarm.yield_15
                    )}
                </td>

                <td style="
                    border:1px solid #CBD5E1;
                    text-align:center;
                ">
                    {cls._format_yield(
                        alarm.target_15
                    )}
                </td>

                <td style="
                    border:1px solid #CBD5E1;
                    text-align:center;
                ">
                    {cls._format_yield(
                        alarm.yield_30
                    )}
                </td>

                <td style="
                    border:1px solid #CBD5E1;
                    text-align:center;
                ">
                    {cls._format_yield(
                        alarm.target_30
                    )}
                </td>

                <td style="border:1px solid #CBD5E1;text-align:center;">
                    {cls._format_yield(alarm.yield_15_model)}
                </td>
                <td style="border:1px solid #CBD5E1;text-align:center;">
                    {cls._format_yield(alarm.target_15_model)}
                </td>
                <td style="border:1px solid #CBD5E1;text-align:center;">
                    {cls._format_yield(alarm.yield_30_model)}
                </td>
                <td style="border:1px solid #CBD5E1;text-align:center;">
                    {cls._format_yield(alarm.target_30_model)}
                </td>
            </tr>
            """
        )

        html_parts.extend(
            [
                """
                </tbody>
            </table>
            """,
                (
                    '<div style="margin-top:6px;">'
                    f"<b>Scrap Code:</b> {escape(alarm.scrap_codes)}"
                    "</div>"
                ),
                (
                    '<div style="margin-top:4px;">'
                    f"<b>Model:</b> {escape(alarm.model)}"
                    "</div>"
                ),
                (
                    '<div style="margin-top:4px; color:red">'
                    f"<b>Reason:</b> {escape(alarm.reason)}"
                    "</div>"
                ),
                "</div>",
            ]
        )

        return "".join(
            html_parts
        )

    # ========================================================
    # SLOT FAIL - TEXT
    # ========================================================

    @classmethod
    def _build_slot_fail_text(
        cls,
        alarm: MailAlarmPreview,
    ) -> list[str]:

        start_date = (
            alarm.start_datetime[:8]
        )

        if (
            start_date
            == alarm.alarm_date
        ):

            alarm_type = (
                "Lỗi từ 2 lần trở lên trong ngày"
            )

        else:

            alarm_type = (
                "Lỗi từ 2 lần liên tiếp qua nhiều ngày"
            )

        lines = [
            "",
            (
                f"EQP: {alarm.eqp} & "
                f"Chamber: {alarm.chamber} & "
                f"Slot: {alarm.slot}"
            ),
            f"Alarm Type: {alarm_type}",
        ]

        if not alarm.details:

            lines.append(
                "Không tìm thấy dữ liệu FAIL chi tiết."
            )

            return lines

        for detail in alarm.details:

            lines.append(
                " | ".join(
                    [
                        cls._format_date(
                            detail.file_date
                        ),

                        cls._format_datetime(
                            detail.file_date,
                            detail.time,
                        ),

                        detail.model,

                        detail.lot_id,

                        detail.scrap_code,

                        str(
                            detail.fail_qty
                        ),
                    ]
                )
            )

        return lines

    # ========================================================
    # MACHINE SLOT YIELD - TEXT
    # ========================================================

    @classmethod
    def _build_machine_slot_yield_text(
        cls,
        alarm: MailAlarmPreview,
    ) -> list[str]:

        return [
            "",
            (
                f"Date: {alarm.alarm_date} | "
                f"Machine: {alarm.machine} | "
                f"Slot: {alarm.slot}"
            ),
            (
                f"Start: {alarm.start_datetime} | "
                f"End: {alarm.end_datetime}"
            ),
            (
                f"Total Test: {alarm.total_test} | "
                f"PASS: {alarm.pass_count} | "
                f"FAIL: {alarm.fail_count} | "
                f"Yield: {cls._format_yield(alarm.yield_percent)}"
            ),
            (
                f"Last 15: {cls._format_yield(alarm.yield_15)} | "
                f"Target 15: {cls._format_yield(alarm.target_15)}"
            ),
            (
                f"Last 30: {cls._format_yield(alarm.yield_30)} | "
                f"Target 30: {cls._format_yield(alarm.target_30)}"
            ),
            (
                f"Yield 15 cùng Model: {cls._format_yield(alarm.yield_15_model)} | "
                f"Target 15 cùng Model: {cls._format_yield(alarm.target_15_model)}"
            ),
            (
                f"Yield 30 cùng Model: {cls._format_yield(alarm.yield_30_model)} | "
                f"Target 30 cùng Model: {cls._format_yield(alarm.target_30_model)}"
            ),
            f"SCRAP CODE: {alarm.scrap_codes}",
            f"Model: {alarm.model}",
            f"Reason: {alarm.reason}",
        ]

    # ========================================================
    # SECTION TITLE
    # ========================================================

    @staticmethod
    def _build_section_title_html(
        title: str,
    ) -> str:

        return (
            '<div style="'
            'font-size:14px;'
            'font-weight:700;'
            'color:#1E3A8A;'
            'margin-top:12px;'
            'margin-bottom:10px;'
            'padding-bottom:5px;'
            'border-bottom:1px solid #CBD5E1;'
            '">'
            f"{escape(title)}"
            "</div>"
        )

    # ========================================================
    # GROUP BY DATE
    # ========================================================

    @staticmethod
    def _group_alarms_by_date(
        target_dates: list[str],
        alarms: list[MailAlarmPreview],
    ) -> dict[
        str,
        list[MailAlarmPreview],
    ]:
        """
        Nhóm Alarm theo ngày,
        ưu tiên thứ tự target_dates.
        """

        grouped: dict[
            str,
            list[MailAlarmPreview],
        ] = {}

        for alarm in alarms:

            grouped.setdefault(
                alarm.alarm_date,
                [],
            ).append(
                alarm
            )

        ordered_dates = [
            value
            for value in dict.fromkeys(
                target_dates
            )
            if value in grouped
        ]

        extra_dates = sorted(
            (
                value
                for value in grouped
                if value not in ordered_dates
            ),
            reverse=True,
        )

        return {
            value: grouped[value]
            for value in [
                *ordered_dates,
                *extra_dates,
            ]
        }

    # ========================================================
    # PARAGRAPH
    # ========================================================

    @staticmethod
    def _build_paragraph_html(
        value: str,
    ) -> str:
        """
        Tạo đoạn Heading hoặc Closing an toàn.
        """

        return (
            '<div style="'
            'white-space:pre-wrap;'
            'margin-bottom:18px;'
            '">'
            f"{escape(value.strip())}"
            "</div>"
        )

    # ========================================================
    # FORMAT DATE
    # ========================================================

    @staticmethod
    def _format_date(
        value: str,
    ) -> str:

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
    # FORMAT DATETIME
    # ========================================================

    @staticmethod
    def _format_datetime(
        date_value: str,
        time_value: str,
    ) -> str:

        if (
            len(date_value) == 8
            and date_value.isdigit()
        ):

            return (
                f"{date_value[0:4]}-"
                f"{date_value[4:6]}-"
                f"{date_value[6:8]} "
                f"{time_value}"
            )

        return (
            f"{date_value} {time_value}"
        ).strip()

    # ========================================================
    # FORMAT YIELD
    # ========================================================

    @staticmethod
    def _format_yield(
        value: float | None,
    ) -> str:

        if value is None:

            return "-"

        # Nếu DB lưu 0.98 -> hiển thị 98.00%
        if 0 <= value <= 1:

            return (
                f"{value * 100:.2f}%"
            )

        # Nếu DB đã lưu 98 -> hiển thị 98.00%
        return (
            f"{value:.2f}%"
        )

