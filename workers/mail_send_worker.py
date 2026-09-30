from __future__ import annotations

import traceback
from pathlib import Path
from typing import Union

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal

from services.mail_send_job_service import MailSendJobService


class MailSendWorkerSignals(QObject):
    """Signals an toàn cho worker gửi mail."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)
    finished = pyqtSignal()


class MailSendWorker(QRunnable):
    """
    Worker gửi Mail chạy bằng QThreadPool.

    Khi xảy ra lỗi:
        1. Hiển thị lỗi đầy đủ cho UI.
        2. Ghi traceback vào mail_send_error.log.
    """

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        super().__init__()

        self.database_path = Path(database_path)
        self.signals = MailSendWorkerSignals()

        self.setAutoDelete(False)

    # ========================================================
    # RUN
    # ========================================================

    def run(self) -> None:

        try:

            result = MailSendJobService(
                self.database_path
            ).run()

            try:

                self.signals.succeeded.emit(
                    result
                )

            except BaseException:

                # UI có thể đã đóng trong lúc worker hoàn thành.
                pass

        except BaseException as error:

            # ------------------------------------------------
            # Lấy traceback đầy đủ
            # ------------------------------------------------

            try:

                full_traceback = (
                    traceback.format_exc()
                )

            except BaseException:

                full_traceback = (
                    f"{type(error).__name__}: "
                    f"{str(error)}"
                )

            # ------------------------------------------------
            # Error text
            # ------------------------------------------------

            error_text = (
                str(error).strip()
                or type(error).__name__
            )

            # ------------------------------------------------
            # Ghi log
            # ------------------------------------------------

            try:

                self._write_error_log(
                    error_text=error_text,
                    full_traceback=full_traceback,
                )

            except BaseException:

                pass

            # ------------------------------------------------
            # Console
            # ------------------------------------------------

            try:

                print(
                    "\n"
                    "========== MAIL SEND ERROR ==========\n"
                    f"{type(error).__name__}: "
                    f"{error_text}\n\n"
                    f"{full_traceback}"
                    "\n======================================\n"
                )

            except BaseException:

                pass

            # ------------------------------------------------
            # Gửi lỗi về UI
            # ------------------------------------------------

            try:

                self.signals.failed.emit(
                    "Gửi Mail thất bại.\n\n"
                    f"{type(error).__name__}: "
                    f"{error_text}\n\n"
                    "Chi tiết lỗi:\n"
                    f"{full_traceback}"
                )

            except BaseException:

                pass

        finally:

            try:

                self.signals.finished.emit()

            except BaseException:

                pass

    # ========================================================
    # WRITE ERROR LOG
    # ========================================================

    def _write_error_log(
        self,
        error_text: str,
        full_traceback: str,
    ) -> None:
        """
        Ghi lỗi gửi Mail ra file.

        Ưu tiên ghi cạnh database để dễ tìm trong EXE.
        Nếu không ghi được thì thử ghi cạnh executable.
        """

        log_text = (
            "\n"
            "==================================================\n"
            "AGING TOOL - MAIL SEND ERROR\n"
            "==================================================\n"
            f"Database:\n"
            f"{self.database_path}\n\n"
            f"Error:\n"
            f"{error_text}\n\n"
            f"Traceback:\n"
            f"{full_traceback}\n"
        )

        # ----------------------------------------------------
        # Vị trí 1: cạnh database
        # ----------------------------------------------------

        try:

            database_log = (
                self.database_path.parent
                / "mail_send_error.log"
            )

            with database_log.open(
                "a",
                encoding="utf-8",
            ) as file:

                file.write(
                    log_text
                )

            return

        except BaseException:

            pass

        # ----------------------------------------------------
        # Vị trí 2: thư mục chương trình
        # ----------------------------------------------------

        try:

            program_log = (
                Path.cwd()
                / "mail_send_error.log"
            )

            with program_log.open(
                "a",
                encoding="utf-8",
            ) as file:

                file.write(
                    log_text
                )

        except BaseException:

            pass