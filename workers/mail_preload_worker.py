from __future__ import annotations

import importlib

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot,
)


class MailPreloadWorker(QObject):
    """
    Import trước các module gửi mail
    sau khi giao diện chính đã hiển thị.

    Worker chỉ import module,
    không login và không gửi request.
    """

    succeeded = pyqtSignal()
    failed = pyqtSignal(str)

    @pyqtSlot()
    def run(self) -> None:
        try:
            # Import worker login.
            # Module này sẽ kéo theo mail_service
            # và requests.
            importlib.import_module(
                "workers.mail_login_worker"
            )

            # Import worker gửi mail.
            importlib.import_module(
                "workers.mail_send_worker"
            )

            self.succeeded.emit()

        except Exception as error:
            error_message = str(error).strip()

            self.failed.emit(
                error_message
                or "Không thể tải thư viện gửi mail."
            )