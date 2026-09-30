
from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlencode

import requests
from requests import Request


BASE_URL = "http://107.11.192.45"

LOGIN_URL = (
    f"{BASE_URL}/DATA/Ajax_UserLoginGet.asp"
)

MAIL_URL = (
    f"{BASE_URL}/IMS/DATA/Ajax_MailSend.asp"
)


# ============================================================
# LOGIN INFO
# ============================================================

@dataclass(frozen=True)
class MailLoginInfo:
    """Thông tin trả về sau khi đăng nhập mail."""

    user_id: str
    employee_no: str
    name_en: str
    name_vn: str
    organization_code: str
    organization_en: str
    organization_vn: str


# ============================================================
# MAIL SERVICE
# ============================================================

class MailService:
    """
    Đăng nhập và làm việc với hệ thống mail nội bộ.

    Mục tiêu:
        - Không để lỗi mail làm đóng chương trình.
        - Login/Send đều trả kết quả dạng:
              (True, result)
              (False, error_message)
        - Session luôn được đóng an toàn.
    """

    LOGIN_TIMEOUT_SECONDS = 30
    SEND_TIMEOUT_SECONDS = 30

    def __init__(self):
        self.session = None
        self.user_info = None
        self.cookies = {}
        self.is_logged_in = False

    # ========================================================
    # LOGIN
    # ========================================================

    def login(
        self,
        user_id: str,
        password: str,
    ) -> tuple[bool, MailLoginInfo | str]:
        """
        Đăng nhập hệ thống mail nội bộ.

        Thành công:
            (True, MailLoginInfo)

        Thất bại:
            (False, error_message)
        """

        user_id = str(
            user_id or ""
        ).strip()

        password = str(
            password or ""
        )

        if not user_id:
            return (
                False,
                "User ID người gửi đang để trống.",
            )

        if not password:
            return (
                False,
                "Mật khẩu người gửi đang để trống.",
            )

        # ----------------------------------------------------
        # Clear session cũ
        # ----------------------------------------------------

        try:
            self.clear_session()
        except BaseException:
            self.session = None
            self.user_info = None
            self.cookies = {}
            self.is_logged_in = False

        session = requests.Session()

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": f"{BASE_URL}/",
            "Origin": BASE_URL,
            "Content-Type": (
                "application/x-www-form-urlencoded"
            ),
        }

        payload = {
            "STR_LAN": "vn",
            "CD_USER": user_id,
            "STR_PASS": password,
        }

        # ----------------------------------------------------
        # LOGIN REQUEST
        # ----------------------------------------------------

        try:

            response = session.post(
                LOGIN_URL,
                data=payload,
                headers=headers,
                timeout=self.LOGIN_TIMEOUT_SECONDS,
            )

        except requests.Timeout:

            self._safe_close_session(
                session
            )

            return (
                False,
                (
                    "Đăng nhập quá thời gian chờ "
                    f"{self.LOGIN_TIMEOUT_SECONDS} giây."
                ),
            )

        except requests.ConnectionError:

            self._safe_close_session(
                session
            )

            return (
                False,
                (
                    "Không thể kết nối tới hệ thống "
                    "mail nội bộ."
                ),
            )

        except requests.RequestException as error:

            self._safe_close_session(
                session
            )

            return (
                False,
                (
                    "Lỗi khi gửi yêu cầu đăng nhập: "
                    f"{error}"
                ),
            )

        except BaseException as error:

            self._safe_close_session(
                session
            )

            return (
                False,
                (
                    "Lỗi bất thường khi đăng nhập: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        # ----------------------------------------------------
        # HTTP STATUS
        # ----------------------------------------------------

        if response.status_code != 200:

            self._safe_close_session(
                session
            )

            return (
                False,
                (
                    "Hệ thống mail trả về HTTP "
                    f"{response.status_code}."
                ),
            )

        # ----------------------------------------------------
        # RESPONSE TEXT
        # ----------------------------------------------------

        try:

            response_text = (
                response.content.decode(
                    "utf-8",
                    errors="ignore",
                )
            )

        except BaseException as error:

            self._safe_close_session(
                session
            )

            return (
                False,
                (
                    "Không thể đọc phản hồi đăng nhập: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        lower_text = response_text.lower()

        if (
            "fail" in lower_text
            or "invalid" in lower_text
            or "error" in lower_text
        ):

            self._safe_close_session(
                session
            )

            return (
                False,
                (
                    "Đăng nhập thất bại. "
                    "User ID hoặc mật khẩu không đúng."
                ),
            )

        # ----------------------------------------------------
        # PARSE LOGIN INFO
        # ----------------------------------------------------

        try:

            info = response_text.split("</>")

            if len(info) < 11:

                self._safe_close_session(
                    session
                )

                return (
                    False,
                    (
                        "Đăng nhập thất bại: cấu trúc "
                        "phản hồi không hợp lệ "
                        f"({len(info)} trường)."
                    ),
                )

            login_user_id = info[0].strip()
            employee_no = info[1].strip()
            name_en = info[2].strip()
            organization_code = info[3].strip()
            organization_en = info[4].strip()
            name_vn = info[9].strip()
            organization_vn = info[10].strip()

        except BaseException as error:

            self._safe_close_session(
                session
            )

            return (
                False,
                (
                    "Không thể phân tích thông tin "
                    "đăng nhập: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        if (
            not login_user_id
            or not employee_no
        ):

            self._safe_close_session(
                session
            )

            return (
                False,
                (
                    "Đăng nhập thất bại: hệ thống "
                    "không trả về thông tin người dùng."
                ),
            )

        login_info = MailLoginInfo(
            user_id=login_user_id,
            employee_no=employee_no,
            name_en=name_en,
            name_vn=name_vn,
            organization_code=organization_code,
            organization_en=organization_en,
            organization_vn=organization_vn,
        )

        # ----------------------------------------------------
        # COOKIES
        # ----------------------------------------------------

        cookies = {
            "ck_Lan": "vn",
            "ck_Pattern": "2U",

            "ck_cdUser": login_user_id,
            "ck_noEmp": employee_no,

            # Chỉ dùng dữ liệu tiếng Anh trong Cookie.
            "ck_strName_en": name_en,
            "ck_strName_ko": name_en,
            "ck_strName_vn": name_en,

            "ck_cdOrg": organization_code,

            "ck_strOrg_en": organization_en,
            "ck_strOrg_ko": organization_en,
            "ck_strOrg_vn": organization_en,

            "ck_strTel": "",
            "ck_strHp": "",
            "ck_strEmail": "",

            "ck_Mrp_Lan": "vn",

            "ck_Mrp_cdUser": login_user_id,
            "ck_Mrp_noEmp": employee_no,

            "ck_Mrp_strName_en": name_en,
            "ck_Mrp_strName_ko": name_en,
            "ck_Mrp_strName_vn": name_en,

            "ck_Mrp_cdOrg": organization_code,

            "ck_Mrp_strOrg_en": organization_en,
            "ck_Mrp_strOrg_ko": organization_en,
            "ck_Mrp_strOrg_vn": organization_en,

            "ck_Mrp_strTel": "",
            "ck_Mrp_strHp": "",
            "ck_Mrp_strEmail": "",
        }

        # ----------------------------------------------------
        # APPLY COOKIES
        # ----------------------------------------------------

        try:

            for key, value in cookies.items():

                session.cookies.set(
                    key,
                    value,
                )

        except BaseException as error:

            self._safe_close_session(
                session
            )

            return (
                False,
                (
                    "Không thể thiết lập phiên đăng nhập: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        # ----------------------------------------------------
        # SAVE SESSION
        # ----------------------------------------------------

        self.session = session
        self.cookies = cookies
        self.user_info = login_info
        self.is_logged_in = True

        return True, login_info

    # ========================================================
    # BUILD MAIL ADDRESS
    # ========================================================

    @staticmethod
    def _build_mail_address_string(
        users: list[tuple[str, str]],
        address_type: str,
    ) -> str:
        """Tạo chuỗi TO/CC theo định dạng hệ thống mail."""

        address_type = str(
            address_type or ""
        ).strip().upper()

        if address_type not in (
            "TO",
            "CC",
        ):
            raise ValueError(
                "Loại người nhận không hợp lệ."
            )

        result = []

        for user_id, display_name in users:

            user_id = str(
                user_id or ""
            ).strip()

            display_name = str(
                display_name or ""
            ).strip()

            if not user_id:
                continue

            result.append(
                f"{address_type}^{user_id}^"
                f"{display_name} ({user_id})"
            )

        return "|".join(result)

    # ========================================================
    # SEND MAIL
    # ========================================================

    def send_mail(
        self,
        receivers: list[tuple[str, str]],
        cc_receivers: list[tuple[str, str]],
        subject: str,
        html: str,
        text: str,
    ) -> tuple[bool, str]:
        """
        Gửi email bằng session đã đăng nhập.

        Mọi lỗi đều được chuyển thành:
            (False, error_message)

        Không để lỗi thoát ra ngoài.
        """

        # ----------------------------------------------------
        # CHECK LOGIN
        # ----------------------------------------------------

        if (
            not self.is_logged_in
            or self.session is None
            or self.user_info is None
        ):

            return (
                False,
                "Vui lòng đăng nhập trước khi gửi mail.",
            )

        # ----------------------------------------------------
        # SUBJECT
        # ----------------------------------------------------

        subject = str(
            subject or ""
        ).strip()

        if not subject:

            return (
                False,
                "Subject không được để trống.",
            )

        # ----------------------------------------------------
        # BUILD RECEIVER
        # ----------------------------------------------------

        try:

            receiver_string = (
                self._build_mail_address_string(
                    receivers,
                    "TO",
                )
            )

        except BaseException as error:

            return (
                False,
                (
                    "Không thể tạo danh sách Receiver: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        if not receiver_string:

            return (
                False,
                "Danh sách Receiver đang để trống.",
            )

        # ----------------------------------------------------
        # BUILD CC
        # ----------------------------------------------------

        try:

            cc_string = (
                self._build_mail_address_string(
                    cc_receivers,
                    "CC",
                )
            )

        except BaseException as error:

            return (
                False,
                (
                    "Không thể tạo danh sách CC: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        # ----------------------------------------------------
        # STR_TO
        # ----------------------------------------------------

        address_parts = [
            receiver_string
        ]

        if cc_string:
            address_parts.append(
                cc_string
            )

        str_to = "|".join(
            address_parts
        )

        # ----------------------------------------------------
        # USER DATA
        # ----------------------------------------------------

        try:

            cd_mst = (
                str(
                    int(
                        time.time() * 1000
                    )
                )
                + self.user_info.user_id
            )

            sender_name = (
                self.user_info.name_vn
                or self.user_info.name_en
            )

        except BaseException as error:

            return (
                False,
                (
                    "Không thể tạo thông tin người gửi: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        # ----------------------------------------------------
        # PAYLOAD
        # ----------------------------------------------------

        payload = {
            "CD_MST": cd_mst,
            "STR_LEN": "vn",
            "CD_USER": self.user_info.user_id,
            "STR_USER": sender_name,
            "CD_TYPE": "Send",
            "CD_IMPORTANT": "0",
            "STR_SUBJECT": subject,
            "CNT_ATTACH": "0",
            "SIZE_MAIL": "100",
            "STR_HTML": html,
            "STR_TEXT": text,
            "STR_TO": str_to,

            # Hệ thống hiện tại dùng STR_TO
            # cho Receiver + CC.
            "STR_CC": "",

            "STR_BC": "",
            "NEW_ATTACH": "",
            "DEL_ATTACH": "",
            "OLD_ATTACH": "",
            "CD_STATUS": "Y",
        }

        # ----------------------------------------------------
        # ENCODE
        # ----------------------------------------------------

        try:

            body = urlencode(
                payload,
                encoding="utf-8",
            )

        except BaseException as error:

            return (
                False,
                (
                    "Không thể tạo nội dung Mail Request: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        # ----------------------------------------------------
        # HEADERS
        # ----------------------------------------------------

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": (
                f"{BASE_URL}/IMS/Write.html"
            ),
            "Origin": BASE_URL,
            "Content-Type": (
                "application/x-www-form-urlencoded; "
                "charset=UTF-8"
            ),
            "X-Requested-With": "XMLHttpRequest",
        }

        # ----------------------------------------------------
        # REQUEST
        # ----------------------------------------------------

        try:

            request = Request(
                "POST",
                MAIL_URL,
                data=body.encode("utf-8"),
                headers=headers,
            )

            prepared = (
                self.session.prepare_request(
                    request
                )
            )

        except BaseException as error:

            return (
                False,
                (
                    "Không thể tạo Mail Request: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        # ----------------------------------------------------
        # SEND REQUEST
        # ----------------------------------------------------

        try:

            response = self.session.send(
                prepared,
                timeout=self.SEND_TIMEOUT_SECONDS,
            )

        except requests.Timeout:

            return (
                False,
                (
                    "Gửi mail quá thời gian chờ "
                    f"{self.SEND_TIMEOUT_SECONDS} giây."
                ),
            )

        except requests.ConnectionError:

            return (
                False,
                (
                    "Mất kết nối tới hệ thống "
                    "mail nội bộ."
                ),
            )

        except requests.RequestException as error:

            return (
                False,
                f"Lỗi gửi mail: {error}",
            )

        except BaseException as error:

            return (
                False,
                (
                    "Lỗi bất thường khi gửi mail: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        try:

            response_text = (
                response.content.decode(
                    "utf-8",
                    errors="ignore",
                ).strip()
            )

        except BaseException as error:

            return (
                False,
                (
                    "Không thể đọc phản hồi "
                    "từ hệ thống mail: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

        # ----------------------------------------------------
        # HTTP STATUS
        # ----------------------------------------------------

        if response.status_code != 200:

            return (
                False,
                (
                    "Hệ thống mail trả về HTTP "
                    f"{response.status_code}."
                ),
            )

        # ----------------------------------------------------
        # SERVER RESPONSE
        # ----------------------------------------------------

        lower_text = (
            response_text.lower()
        )

        if (
            "fail" in lower_text
            or "error" in lower_text
        ):

            return (
                False,
                (
                    response_text
                    or "Hệ thống mail báo gửi thất bại."
                ),
            )

        return (
            True,
            response_text,
        )

    # ========================================================
    # SAFE CLOSE SESSION
    # ========================================================

    @staticmethod
    def _safe_close_session(
        session,
    ) -> None:
        """
        Đóng requests.Session an toàn.

        Tuyệt đối không để lỗi close session
        làm crash chương trình.
        """

        if session is None:
            return

        try:
            session.close()
        except BaseException:
            pass

    # ========================================================
    # CLEAR SESSION
    # ========================================================

    def clear_session(self) -> None:
        """
        Đóng session đăng nhập hiện tại.

        Hàm này không được phép làm crash PGM.
        """

        current_session = self.session

        self.session = None
        self.user_info = None
        self.cookies = {}
        self.is_logged_in = False

        self._safe_close_session(
            current_session
        )

