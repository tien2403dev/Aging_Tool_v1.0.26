from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from repositories.cum_repository import CumRepository
from repositories.import_lock_repository import (
    ImportLockRepository,
)
from services.cum_excel_reader import CumExcelReader
from services.import_lock_heartbeat import (
    ImportLockHeartbeat,
)


@dataclass
class CumImportResult:
    file_name: str
    imported_row_count: int
    deleted_row_count: int
    imported_scrap_detail_count: int
    imported_dates: list[str]


class CumImportService:
    """
    Điều phối toàn bộ import CUM.

    Không chứa PyQt UI code.
    Không viết SQL trực tiếp.
    """

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        self.database_path = Path(database_path)

        self.lock_repository = ImportLockRepository(
            self.database_path
        )

        self.cum_repository = CumRepository(
            self.database_path
        )

        self.excel_reader = CumExcelReader()

    def import_file(
        self,
        excel_path: Union[str, Path],
    ) -> CumImportResult:
        """
        Luồng import CUM:

        1. Chiếm GLOBAL_IMPORT_LOCK.
        2. Đọc và validate toàn bộ Excel vào staging local.
        3. Transaction: xóa CUM cũ theo DATE và insert CUM mới.
        4. Xóa staging, dừng heartbeat và release lock.
        """

        excel_path = Path(excel_path)

        lock_info = None
        heartbeat = None
        stage_result = None

        try:
            lock_info = self.lock_repository.acquire_lock(
                import_type="CUM",
                file_name=excel_path.name,
            )

            heartbeat = ImportLockHeartbeat(
                lock_repository=self.lock_repository,
                batch_id=lock_info.batch_id,
            )

            heartbeat.start()

            # File có một dòng sai sẽ raise exception.
            # Database chính chưa bị thay đổi tại đây.
            stage_result = self.excel_reader.stage_file(
                excel_path
            )

            replace_result = (
                self.cum_repository.replace_from_staging(
                    staging_database_path=(
                        stage_result.staging_database_path
                    ),
                    business_dates=(
                        stage_result.business_dates
                    ),
                )
            )

            return CumImportResult(
                file_name=excel_path.name,
                imported_row_count=(
                    replace_result.inserted_row_count
                ),
                deleted_row_count=(
                    replace_result.deleted_row_count
                ),
                imported_scrap_detail_count=(
                    replace_result.inserted_scrap_detail_count
                ),
                imported_dates=(
                    replace_result.replaced_dates
                ),
            )

        finally:
            # Luôn dọn database tạm.
            if stage_result is not None:
                self.excel_reader.delete_staging_database(
                    stage_result.staging_database_path
                )

            # Dừng heartbeat trước khi xóa lock.
            if heartbeat is not None:
                heartbeat.stop()

            # Chỉ xóa đúng lock của batch hiện tại.
            if lock_info is not None:
                self.lock_repository.release_lock(
                    lock_info.batch_id
                )