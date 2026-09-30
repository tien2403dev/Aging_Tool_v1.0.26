from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from repositories.import_lock_repository import (
    ImportLockRepository,
)
from repositories.prime_repository import PrimeRepository
from services.import_lock_heartbeat import (
    ImportLockHeartbeat,
)
from services.prime_log_reader import PrimeLogReader

@dataclass
class PrimeImportResult:
    file_name: str
    imported_row_count: int
    deleted_row_count: int
    imported_dates: list[str]


class PrimeImportService:
    """
    Điều phối toàn bộ import PRIME.

    Không chứa PyQt UI code.
    Không truy vấn SQL trực tiếp.
    """

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        self.database_path = Path(database_path)

        self.lock_repository = ImportLockRepository(
            self.database_path
        )

        self.prime_repository = PrimeRepository(
            self.database_path
        )

        # self.excel_reader = PrimeExcelReader()
        self.log_reader = PrimeLogReader()

    def import_folder(
            self,
            root_folder: Union[str, Path],
            business_date: str,
    ) -> PrimeImportResult:
        """
        Import PRIME từ các file TXT của ngày đã chọn.

        Dữ liệu chỉ được thay đổi sau khi toàn bộ file log
        đã đọc và validate thành công.
        """

        root_folder = Path(root_folder)

        lock_info = None
        heartbeat = None
        stage_result = None

        try:
            lock_info = self.lock_repository.acquire_lock(
                import_type="PRIME",
                file_name=(
                    f"{root_folder.name} | {business_date}"
                ),
            )

            heartbeat = ImportLockHeartbeat(
                lock_repository=self.lock_repository,
                batch_id=lock_info.batch_id,
            )

            heartbeat.start()

            stage_result = self.log_reader.stage_folder(
                root_folder=root_folder,
                business_date=business_date,
            )

            replace_result = (
                self.prime_repository.replace_from_staging(
                    staging_database_path=(
                        stage_result.staging_database_path
                    ),
                    business_dates=(
                        stage_result.business_dates
                    ),
                )
            )

            return PrimeImportResult(
                file_name=root_folder.name,
                imported_row_count=(
                    replace_result.inserted_row_count
                ),
                deleted_row_count=(
                    replace_result.deleted_row_count
                ),
                imported_dates=(
                    replace_result.replaced_dates
                ),
            )

        finally:
            if stage_result is not None:
                self.log_reader.delete_staging_database(
                    stage_result.staging_database_path
                )

            if heartbeat is not None:
                heartbeat.stop()

            if lock_info is not None:
                self.lock_repository.release_lock(
                    lock_info.batch_id
                )