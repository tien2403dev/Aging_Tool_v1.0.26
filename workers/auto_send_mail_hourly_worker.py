from __future__ import annotations

import traceback
from datetime import date, timedelta
from pathlib import Path

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal

from repositories.auto_import_scheduler_repository import (
    AutoImportSchedulerRepository,
)
from repositories.machine_slot_yield_repository import (
    MachineSlotYieldRepository,
)
from repositories.alarm_repository import AlarmRepository
from repositories.auto_send_mail_scheduler_repository import (
    AutoSendMailSchedulerRepository,
)
from services.mail_send_job_service import (
    MailSendJobService,
    NoMailToSendError,
)


class AutoSendMailHourlySignals(QObject):
    succeeded = pyqtSignal(object)
    skipped = pyqtSignal(str)
    failed = pyqtSignal(str)
    finished = pyqtSignal()


class AutoSendMailHourlyWorker(QRunnable):
    """
    Mỗi lần chạy:
        1. Cập nhật Machine Slot Yield Alarm từ TXT (30 ngày dữ liệu,
           nhưng điều kiện Alarm chỉ 5 ngày gần nhất).
        2. Kiểm tra Slot Fail Alarm hiện có.
        3. Gửi ngay các Alarm chưa gửi.
    """

    def __init__(self, database_path: str | Path):
        super().__init__()
        self.database_path = Path(database_path)
        self.signals = AutoSendMailHourlySignals()
        self.setAutoDelete(False)

    @staticmethod
    def _log(message: str) -> None:
        try:
            log_dir = Path(__file__).resolve().parents[1] / "log"
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / "auto_send_mail_runtime.log"
            timestamp = __import__("datetime").datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            with path.open("a", encoding="utf-8") as f:
                f.write(f"{timestamp} | {message}\n")
        except BaseException:
            pass

    def run(self) -> None:
        try:
            scheduler_config = (
                AutoSendMailSchedulerRepository(
                    self.database_path
                ).get_config()
            )

            if not scheduler_config.enabled:
                self.signals.skipped.emit(
                    "Auto Send Mail đang OFF."
                )
                return

            # ------------------------------------------------
            # Cập nhật Machine Slot Yield Alarm
            # ------------------------------------------------
            try:
                msy_repository = MachineSlotYieldRepository(
                    self.database_path.parent
                    / "machine_slot_targets.json"
                )

                log_folder = (
                    msy_repository.load_log_folder()
                )

                if not log_folder:
                    auto_import_config = (
                        AutoImportSchedulerRepository(
                            self.database_path
                        ).get_config()
                    )
                    log_folder = (
                        auto_import_config.log_folder
                    )

                if log_folder and Path(log_folder).is_dir():
                    target_date = date.today()
                    date_from = (
                        target_date - timedelta(days=30)
                    ).strftime("%Y%m%d")
                    date_to = target_date.strftime("%Y%m%d")

                    result = msy_repository.load(
                        log_root=log_folder,
                        date_from=date_from,
                        date_to=date_to,
                    )

                    AlarmRepository(
                        self.database_path
                    ).sync_machine_slot_yield_result(
                        result=result,
                        date_from=date_from,
                        date_to=date_to,
                        target_15=result.target_15,
                        target_30=result.target_30,
                    )

                    self._log(
                        "Hourly update Machine Slot Yield Alarm thành công "
                        f"| {date_from}-{date_to}"
                    )
                else:
                    self._log(
                        "Hourly update bỏ qua: chưa có Log Folder hợp lệ."
                    )

            except BaseException as error:
                # Không được để lỗi đọc TXT làm mất khả năng
                # gửi Slot Fail Alarm.
                self._log(
                    "Machine Slot Yield refresh lỗi | "
                    f"{type(error).__name__}: {error}"
                )

            # ------------------------------------------------
            # Gửi mail unified
            # ------------------------------------------------
            result = MailSendJobService(
                self.database_path
            ).run(
                target_date=date.today().strftime("%Y%m%d"),
                log_callback=self._job_log,
            )

            self.signals.succeeded.emit(result)

        except NoMailToSendError as error:
            message = str(error).strip() or (
                "Không có Alarm mới cần gửi."
            )
            self._log(f"SKIP | {message}")
            self.signals.skipped.emit(message)

        except BaseException as error:
            self._log(
                "ERROR | "
                f"{type(error).__name__}: {error}"
            )
            try:
                traceback.print_exc()
            except BaseException:
                pass
            self.signals.failed.emit(
                f"{type(error).__name__}: "
                f"{str(error).strip() or 'Lỗi không xác định.'}"
            )

        finally:
            try:
                self.signals.finished.emit()
            except BaseException:
                pass

    def _job_log(self, level: str, message: str) -> None:
        self._log(f"{level} | {message}")
