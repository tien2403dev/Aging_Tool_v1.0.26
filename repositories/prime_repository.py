# from __future__ import annotations
#
# import sqlite3
#
# from dataclasses import dataclass
# from datetime import datetime, timedelta
# from pathlib import Path
# from typing import Iterable, Union
#
# from database.connection import create_connection
# from repositories.filter_option_cache_repository import (
#     FilterOptionCacheRepository,
# )
# from repositories.alarm_repository import (
#     AlarmRepository,
# )
# from repositories.import_status_repository import (
#     ImportStatusRepository,
# )
# INSERT_BATCH_SIZE = 5_000
# DELETE_DATE_BATCH_SIZE = 500
#
# # PRIME có thể hoàn thành và xuất hiện trong CUM
# # muộn tối đa 4 ngày.
# TIER_MAX_DELAY_DAYS = 4
#
#
# @dataclass
# class PrimeReplaceResult:
#     deleted_row_count: int
#     inserted_row_count: int
#     replaced_dates: list[str]
#
#
# class PrimeRepository:
#     """
#     Chỉ phụ trách thao tác với bảng prime_data.
#
#     Không đọc Excel.
#     Không chứa logic UI.
#     """
#
#     def __init__(
#         self,
#         database_path: Union[str, Path],
#     ):
#         self.database_path = database_path
#
#     def replace_from_staging(
#             self,
#             staging_database_path: Union[str, Path],
#             business_dates: Iterable[str],
#     ) -> PrimeReplaceResult:
#         """
#         Thay toàn bộ dữ liệu của ngày người dùng chọn.
#
#         Với dòng lệch ngày, chỉ xóa dòng trùng theo:
#         EQP + DATE + TIME + SLOT.
#
#         Toàn bộ thao tác chạy trong một transaction.
#         Có lỗi ở bất kỳ bước nào thì rollback.
#         """
#
#         replaced_dates = sorted(
#             set(business_dates)
#         )
#
#         if not replaced_dates:
#             raise ValueError(
#                 "Không có DATE nào để import"
#             )
#
#         main_connection = create_connection(
#             self.database_path
#         )
#
#         staging_connection = sqlite3.connect(
#             str(staging_database_path)
#         )
#
#         staging_attached = False
#
#         try:
#             # Gắn staging vào connection chính để SQLite
#             # có thể JOIN trực tiếp, không load key vào RAM.
#             main_connection.execute(
#                 "ATTACH DATABASE ? AS staging_prime",
#                 (str(staging_database_path),),
#             )
#
#             staging_attached = True
#
#             main_connection.execute(
#                 "BEGIN IMMEDIATE"
#             )
#
#             filter_cache_repository = (
#                 FilterOptionCacheRepository()
#             )
#
#             # Chuẩn bị toàn bộ ID phải xóa:
#             # - Toàn bộ ngày chính.
#             # - Dòng lệch ngày trùng khóa.
#             self._prepare_delete_ids(
#                 connection=main_connection,
#                 replaced_dates=replaced_dates,
#             )
#             alarm_repository = AlarmRepository()
#
#             # Lấy cả slot của dữ liệu cũ và staging
#             # trước khi xóa dữ liệu PRIME.
#             alarm_repository.prepare_affected_slots_for_prime_replace(
#                 connection=main_connection,
#             )
#
#             # Trừ cache trước khi xóa dữ liệu chính.
#             filter_cache_repository.remove_prime_for_delete_ids(
#                 main_connection=main_connection,
#             )
#
#             deleted_row_count = (
#                 self._delete_prepared_rows(
#                     connection=main_connection,
#                 )
#             )
#
#             inserted_row_count = (
#                 self._insert_staging_data(
#                     main_connection=main_connection,
#                     staging_connection=staging_connection,
#                 )
#             )
#
#             # Đồng bộ tier cho tất cả dòng vừa import,
#             # bao gồm cả những dòng lệch ngày.
#             self._sync_inserted_tiers_from_existing_cum(
#                 connection=main_connection,
#             )
#             # Tính lại alarm trong cùng transaction.
#             # PRIME chưa có Tier sẽ không tạo alarm.
#             alarm_repository.rebuild_affected_slots(
#                 connection=main_connection,
#             )
#
#             # Cộng lại cache từ toàn bộ staging.
#             filter_cache_repository.add_prime_from_staging(
#                 main_connection=main_connection,
#                 staging_connection=staging_connection,
#             )
#
#             filter_cache_repository.finalize(
#                 main_connection=main_connection
#             )
#             # Lấy DATE thực tế trong staging, gồm cả các dòng
#             # lệch ngày có trong folder log vừa import.
#             imported_data_dates = [
#                 row[0]
#                 for row in main_connection.execute(
#                     """
#                     SELECT DISTINCT DATE
#                     FROM staging_prime.staging_prime_data
#                     ORDER BY DATE
#                     """
#                 ).fetchall()
#             ]
#
#             ImportStatusRepository.upsert_dates(
#                 connection=main_connection,
#                 data_type="PRIME",
#                 business_dates=imported_data_dates,
#             )
#
#             main_connection.commit()
#
#             return PrimeReplaceResult(
#                 deleted_row_count=deleted_row_count,
#                 inserted_row_count=inserted_row_count,
#                 replaced_dates=replaced_dates,
#             )
#
#         except Exception:
#             if main_connection.in_transaction:
#                 main_connection.rollback()
#
#             raise
#
#         finally:
#             staging_connection.close()
#
#             if staging_attached:
#                 try:
#                     main_connection.execute(
#                         "DETACH DATABASE staging_prime"
#                     )
#                 except sqlite3.Error:
#                     pass
#
#             main_connection.close()
#
#     def _prepare_delete_ids(
#             self,
#             connection: sqlite3.Connection,
#             replaced_dates: list[str],
#     ) -> None:
#         """
#         Chuẩn bị danh sách ID cần xóa.
#
#         Bao gồm:
#         1. Toàn bộ dữ liệu của ngày người dùng chọn.
#         2. Dòng lệch ngày trùng EQP + DATE + TIME + SLOT.
#         """
#
#         connection.execute(
#             """
#             CREATE TEMP TABLE temp_prime_delete_ids (
#                 id INTEGER PRIMARY KEY
#             ) WITHOUT ROWID
#             """
#         )
#
#         # Thêm toàn bộ ID thuộc ngày người dùng chọn.
#         for date_batch in self._chunks(
#                 replaced_dates,
#                 DELETE_DATE_BATCH_SIZE,
#         ):
#             placeholders = ", ".join(
#                 "?"
#                 for _ in date_batch
#             )
#
#             connection.execute(
#                 f"""
#                 INSERT OR IGNORE INTO temp_prime_delete_ids (
#                     id
#                 )
#                 SELECT id
#                 FROM prime_data
#                 WHERE DATE IN ({placeholders})
#                 """,
#                 date_batch,
#             )
#
#         placeholders = ", ".join(
#             "?"
#             for _ in replaced_dates
#         )
#
#         # Với dòng lệch ngày, chỉ thêm ID nếu trùng:
#         # EQP + DATE + TIME + SLOT.
#         connection.execute(
#             f"""
#             INSERT OR IGNORE INTO temp_prime_delete_ids (
#                 id
#             )
#             SELECT prime.id
#             FROM prime_data AS prime
#             INNER JOIN staging_prime.staging_prime_data AS stage
#                 ON stage.DATE = prime.DATE
#                AND stage.EQP = prime.EQP
#                AND stage.TIME = prime.TIME
#                AND stage.Slot = prime.Slot
#             WHERE stage.DATE NOT IN ({placeholders})
#             """,
#             replaced_dates,
#         )
#
#     @staticmethod
#     def _delete_prepared_rows(
#             connection: sqlite3.Connection,
#     ) -> int:
#         """Xóa các dòng đã chuẩn bị và trả số dòng bị xóa."""
#
#         deleted_row_count = connection.execute(
#             """
#             SELECT COUNT(*)
#             FROM temp_prime_delete_ids
#             """
#         ).fetchone()[0]
#
#         connection.execute(
#             """
#             DELETE FROM prime_data
#             WHERE id IN (
#                 SELECT id
#                 FROM temp_prime_delete_ids
#             )
#             """
#         )
#
#         return deleted_row_count
#
#     def _insert_staging_data(
#         self,
#         main_connection: sqlite3.Connection,
#         staging_connection: sqlite3.Connection,
#     ) -> int:
#         """
#         Đọc staging từng batch và insert vào database chính.
#
#         Không load toàn bộ staging data vào RAM.
#         Không truyền QTY vì prime_data tự dùng DEFAULT 1.
#         """
#
#         staging_cursor = staging_connection.execute(
#             """
#             SELECT
#                 DATE,
#                 TIME,
#                 PARTNO,
#                 LOTNO,
#                 INTERFACE,
#                 RESULT,
#                 SCRAPCODE,
#                 EQP,
#                 Chamber,
#                 Slot,
#                 MODEL
#             FROM staging_prime_data
#             """
#         )
#
#         inserted_row_count = 0
#
#         while True:
#             rows = staging_cursor.fetchmany(
#                 INSERT_BATCH_SIZE
#             )
#
#             if not rows:
#                 break
#
#             main_connection.executemany(
#                 """
#                 INSERT INTO prime_data (
#                     DATE,
#                     TIME,
#                     PARTNO,
#                     LOTNO,
#                     INTERFACE,
#                     RESULT,
#                     SCRAPCODE,
#                     EQP,
#                     Chamber,
#                     Slot,
#                     MODEL
#                 )
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 """,
#                 rows,
#             )
#
#             inserted_row_count += len(rows)
#
#         return inserted_row_count
#
#     def _sync_inserted_tiers_from_existing_cum(
#             self,
#             connection: sqlite3.Connection,
#     ) -> None:
#         """
#         Đồng bộ Tier cho tất cả dòng vừa import.
#
#         Bao gồm cả dòng có DATE khác ngày người dùng chọn.
#         PRIME ngày P tìm Tier trong CUM từ P đến P + 4 ngày.
#         """
#
#         # Lấy DATE thực tế của tất cả dòng trong staging.
#         # Vì vậy nếu import ngày 17 nhưng file có dòng ngày 16,
#         # cả ngày 16 và ngày 17 đều được xử lý.
#         staged_dates = connection.execute(
#             """
#             SELECT DISTINCT DATE
#             FROM staging_prime.staging_prime_data
#             ORDER BY DATE
#             """
#         ).fetchall()
#
#         for row in staged_dates:
#             prime_date = row[0]
#
#             cum_end_date = (
#                     datetime.strptime(
#                         prime_date,
#                         "%Y%m%d",
#                     )
#                     + timedelta(days=TIER_MAX_DELAY_DAYS)
#             ).strftime("%Y%m%d")
#
#             connection.execute(
#                 """
#                 UPDATE prime_data AS prime
#                 SET TIER = (
#                     SELECT cum.TIER
#                     FROM cum_data AS cum
#                     WHERE cum.LOTID = prime.LOTNO
#                       AND cum.DATE BETWEEN ? AND ?
#                     ORDER BY cum.DATE
#                     LIMIT 1
#                 )
#                 WHERE prime.DATE = ?
#                   AND EXISTS (
#                       SELECT 1
#                       FROM staging_prime.staging_prime_data AS stage
#                       WHERE stage.DATE = prime.DATE
#                         AND stage.EQP = prime.EQP
#                         AND stage.TIME = prime.TIME
#                         AND stage.Slot = prime.Slot
#                   )
#                 """,
#                 (
#                     prime_date,
#                     cum_end_date,
#                     prime_date,
#                 ),
#             )
#
#     @staticmethod
#     def _chunks(
#         values: list[str],
#         chunk_size: int,
#     ):
#         for start_index in range(
#             0,
#             len(values),
#             chunk_size,
#         ):
#             yield values[
#                 start_index:
#                 start_index + chunk_size
#             ]


#
# from __future__ import annotations
#
# import sqlite3
#
# from dataclasses import dataclass
# from datetime import datetime, timedelta
# from pathlib import Path
# from typing import Iterable, Union
#
# from database.connection import create_connection
# from repositories.filter_option_cache_repository import (
#     FilterOptionCacheRepository,
# )
# from repositories.alarm_repository import (
#     AlarmRepository,
# )
# from repositories.import_status_repository import (
#     ImportStatusRepository,
# )
# INSERT_BATCH_SIZE = 5_000
# DELETE_DATE_BATCH_SIZE = 500
#
# # PRIME có thể hoàn thành và xuất hiện trong CUM
# # muộn tối đa 4 ngày.
# TIER_MAX_DELAY_DAYS = 4
#
#
# @dataclass
# class PrimeReplaceResult:
#     deleted_row_count: int
#     inserted_row_count: int
#     replaced_dates: list[str]
#
#
# class PrimeRepository:
#     """
#     Chỉ phụ trách thao tác với bảng prime_data.
#
#     Không đọc Excel.
#     Không chứa logic UI.
#     """
#
#     def __init__(
#         self,
#         database_path: Union[str, Path],
#     ):
#         self.database_path = database_path
#
#     def replace_from_staging(
#             self,
#             staging_database_path: Union[str, Path],
#             business_dates: Iterable[str],
#     ) -> PrimeReplaceResult:
#         """
#         Thay toàn bộ dữ liệu của ngày người dùng chọn.
#
#         Với dòng lệch ngày, chỉ xóa dòng trùng theo:
#         EQP + DATE + TIME + SLOT.
#
#         Toàn bộ thao tác chạy trong một transaction.
#         Có lỗi ở bất kỳ bước nào thì rollback.
#         """
#
#         replaced_dates = sorted(
#             set(business_dates)
#         )
#
#         if not replaced_dates:
#             raise ValueError(
#                 "Không có DATE nào để import"
#             )
#
#         main_connection = create_connection(
#             self.database_path
#         )
#
#         staging_connection = sqlite3.connect(
#             str(staging_database_path)
#         )
#
#         staging_attached = False
#
#         try:
#             # Gắn staging vào connection chính để SQLite
#             # có thể JOIN trực tiếp, không load key vào RAM.
#             main_connection.execute(
#                 "ATTACH DATABASE ? AS staging_prime",
#                 (str(staging_database_path),),
#             )
#
#             staging_attached = True
#
#             main_connection.execute(
#                 "BEGIN IMMEDIATE"
#             )
#
#             filter_cache_repository = (
#                 FilterOptionCacheRepository()
#             )
#
#             # Chuẩn bị toàn bộ ID phải xóa:
#             # - Toàn bộ ngày chính.
#             # - Dòng lệch ngày trùng khóa.
#             self._prepare_delete_ids(
#                 connection=main_connection,
#                 replaced_dates=replaced_dates,
#             )
#             alarm_repository = AlarmRepository()
#
#             # Lấy cả slot của dữ liệu cũ và staging
#             # trước khi xóa dữ liệu PRIME.
#             alarm_repository.prepare_affected_slots_for_prime_replace(
#                 connection=main_connection,
#             )
#
#             # Trừ cache trước khi xóa dữ liệu chính.
#             filter_cache_repository.remove_prime_for_delete_ids(
#                 main_connection=main_connection,
#             )
#
#             deleted_row_count = (
#                 self._delete_prepared_rows(
#                     connection=main_connection,
#                 )
#             )
#
#             inserted_row_count = (
#                 self._insert_staging_data(
#                     main_connection=main_connection,
#                     staging_connection=staging_connection,
#                 )
#             )
#
#             # Đồng bộ tier cho tất cả dòng vừa import,
#             # bao gồm cả những dòng lệch ngày.
#             self._sync_inserted_tiers_from_existing_cum(
#                 connection=main_connection,
#             )
#             # Tính lại alarm trong cùng transaction.
#             # PRIME chưa có Tier sẽ không tạo alarm.
#             alarm_repository.rebuild_affected_slots(
#                 connection=main_connection,
#             )
#
#             # Cộng lại cache từ toàn bộ staging.
#             filter_cache_repository.add_prime_from_staging(
#                 main_connection=main_connection,
#                 staging_connection=staging_connection,
#             )
#
#             filter_cache_repository.finalize(
#                 main_connection=main_connection
#             )
#             # Lấy DATE thực tế trong staging, gồm cả các dòng
#             # lệch ngày có trong folder log vừa import.
#             imported_data_dates = [
#                 row[0]
#                 for row in main_connection.execute(
#                     """
#                     SELECT DISTINCT DATE
#                     FROM staging_prime.staging_prime_data
#                     ORDER BY DATE
#                     """
#                 ).fetchall()
#             ]
#
#             ImportStatusRepository.upsert_dates(
#                 connection=main_connection,
#                 data_type="PRIME",
#                 business_dates=imported_data_dates,
#             )
#
#             main_connection.commit()
#
#             return PrimeReplaceResult(
#                 deleted_row_count=deleted_row_count,
#                 inserted_row_count=inserted_row_count,
#                 replaced_dates=replaced_dates,
#             )
#
#         except Exception:
#             if main_connection.in_transaction:
#                 main_connection.rollback()
#
#             raise
#
#         finally:
#             staging_connection.close()
#
#             if staging_attached:
#                 try:
#                     main_connection.execute(
#                         "DETACH DATABASE staging_prime"
#                     )
#                 except sqlite3.Error:
#                     pass
#
#             main_connection.close()
#
#     def _prepare_delete_ids(
#             self,
#             connection: sqlite3.Connection,
#             replaced_dates: list[str],
#     ) -> None:
#         """
#         Chuẩn bị danh sách ID cần xóa.
#
#         Bao gồm:
#         1. Toàn bộ dữ liệu của ngày người dùng chọn.
#         2. Dòng lệch ngày trùng EQP + DATE + TIME + SLOT.
#         """
#
#         connection.execute(
#             """
#             CREATE TEMP TABLE temp_prime_delete_ids (
#                 id INTEGER PRIMARY KEY
#             ) WITHOUT ROWID
#             """
#         )
#
#         # Thêm toàn bộ ID thuộc ngày người dùng chọn.
#         for date_batch in self._chunks(
#                 replaced_dates,
#                 DELETE_DATE_BATCH_SIZE,
#         ):
#             placeholders = ", ".join(
#                 "?"
#                 for _ in date_batch
#             )
#
#             connection.execute(
#                 f"""
#                 INSERT OR IGNORE INTO temp_prime_delete_ids (
#                     id
#                 )
#                 SELECT id
#                 FROM prime_data
#                 WHERE DATE IN ({placeholders})
#                 """,
#                 date_batch,
#             )
#
#         placeholders = ", ".join(
#             "?"
#             for _ in replaced_dates
#         )
#
#         # Với dòng lệch ngày, chỉ thêm ID nếu trùng:
#         # EQP + DATE + TIME + SLOT.
#         connection.execute(
#             f"""
#             INSERT OR IGNORE INTO temp_prime_delete_ids (
#                 id
#             )
#             SELECT prime.id
#             FROM prime_data AS prime
#             INNER JOIN staging_prime.staging_prime_data AS stage
#                 ON stage.DATE = prime.DATE
#                AND stage.EQP = prime.EQP
#                AND stage.TIME = prime.TIME
#                AND stage.Slot = prime.Slot
#             WHERE stage.DATE NOT IN ({placeholders})
#             """,
#             replaced_dates,
#         )
#
#     @staticmethod
#     def _delete_prepared_rows(
#             connection: sqlite3.Connection,
#     ) -> int:
#         """Xóa các dòng đã chuẩn bị và trả số dòng bị xóa."""
#
#         deleted_row_count = connection.execute(
#             """
#             SELECT COUNT(*)
#             FROM temp_prime_delete_ids
#             """
#         ).fetchone()[0]
#
#         connection.execute(
#             """
#             DELETE FROM prime_data
#             WHERE id IN (
#                 SELECT id
#                 FROM temp_prime_delete_ids
#             )
#             """
#         )
#
#         return deleted_row_count
#
#     def _insert_staging_data(
#         self,
#         main_connection: sqlite3.Connection,
#         staging_connection: sqlite3.Connection,
#     ) -> int:
#         """
#         Đọc staging từng batch và insert vào database chính.
#
#         Không load toàn bộ staging data vào RAM.
#         Không truyền QTY vì prime_data tự dùng DEFAULT 1.
#         """
#
#         staging_cursor = staging_connection.execute(
#             """
#             SELECT
#                 DATE,
#                 TIME,
#                 PARTNO,
#                 LOTNO,
#                 INTERFACE,
#                 RESULT,
#                 SCRAPCODE,
#                 EQP,
#                 Chamber,
#                 Slot,
#                 MODEL
#             FROM staging_prime_data
#             """
#         )
#
#         inserted_row_count = 0
#
#         while True:
#             rows = staging_cursor.fetchmany(
#                 INSERT_BATCH_SIZE
#             )
#
#             if not rows:
#                 break
#
#             main_connection.executemany(
#                 """
#                 INSERT INTO prime_data (
#                     DATE,
#                     TIME,
#                     PARTNO,
#                     LOTNO,
#                     INTERFACE,
#                     RESULT,
#                     SCRAPCODE,
#                     EQP,
#                     Chamber,
#                     Slot,
#                     MODEL
#                 )
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 """,
#                 rows,
#             )
#
#             inserted_row_count += len(rows)
#
#         return inserted_row_count
#
#     def _sync_inserted_tiers_from_existing_cum(
#             self,
#             connection: sqlite3.Connection,
#     ) -> None:
#         """
#         Đồng bộ Tier cho tất cả dòng vừa import.
#
#         Bao gồm cả dòng có DATE khác ngày người dùng chọn.
#         PRIME ngày P tìm Tier trong CUM từ P đến P + 4 ngày.
#         """
#
#         # Lấy DATE thực tế của tất cả dòng trong staging.
#         # Vì vậy nếu import ngày 17 nhưng file có dòng ngày 16,
#         # cả ngày 16 và ngày 17 đều được xử lý.
#         staged_dates = connection.execute(
#             """
#             SELECT DISTINCT DATE
#             FROM staging_prime.staging_prime_data
#             ORDER BY DATE
#             """
#         ).fetchall()
#
#         for row in staged_dates:
#             prime_date = row[0]
#
#             cum_end_date = (
#                     datetime.strptime(
#                         prime_date,
#                         "%Y%m%d",
#                     )
#                     + timedelta(days=TIER_MAX_DELAY_DAYS)
#             ).strftime("%Y%m%d")
#
#             connection.execute(
#                 """
#                 UPDATE prime_data AS prime
#                 SET TIER = (
#                     SELECT cum.TIER
#                     FROM cum_data AS cum
#                     WHERE cum.LOTID = prime.LOTNO
#                       AND cum.DATE BETWEEN ? AND ?
#                     ORDER BY cum.DATE
#                     LIMIT 1
#                 )
#                 WHERE prime.DATE = ?
#                   AND EXISTS (
#                       SELECT 1
#                       FROM staging_prime.staging_prime_data AS stage
#                       WHERE stage.DATE = prime.DATE
#                         AND stage.EQP = prime.EQP
#                         AND stage.TIME = prime.TIME
#                         AND stage.Slot = prime.Slot
#                   )
#                 """,
#                 (
#                     prime_date,
#                     cum_end_date,
#                     prime_date,
#                 ),
#             )
#
#     @staticmethod
#     def _chunks(
#         values: list[str],
#         chunk_size: int,
#     ):
#         for start_index in range(
#             0,
#             len(values),
#             chunk_size,
#         ):
#             yield values[
#                 start_index:
#                 start_index + chunk_size
#             ]




from __future__ import annotations

import sqlite3

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Union

from database.connection import create_connection
from repositories.filter_option_cache_repository import (
    FilterOptionCacheRepository,
)
from repositories.alarm_repository import (
    AlarmRepository,
)
from repositories.import_status_repository import (
    ImportStatusRepository,
)
INSERT_BATCH_SIZE = 5_000
DELETE_DATE_BATCH_SIZE = 500

# PRIME có thể hoàn thành và xuất hiện trong CUM
# muộn tối đa 4 ngày.
TIER_MAX_DELAY_DAYS = 4


@dataclass
class PrimeReplaceResult:
    deleted_row_count: int
    inserted_row_count: int
    replaced_dates: list[str]


class PrimeRepository:
    """
    Chỉ phụ trách thao tác với bảng prime_data.

    Không đọc Excel.
    Không chứa logic UI.
    """

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        self.database_path = database_path

    def replace_from_staging(
            self,
            staging_database_path: Union[str, Path],
            business_dates: Iterable[str],
    ) -> PrimeReplaceResult:
        """
        Thay toàn bộ dữ liệu của ngày người dùng chọn.

        Với dòng lệch ngày, chỉ xóa dòng trùng theo:
        EQP + DATE + TIME + SLOT.

        Toàn bộ thao tác chạy trong một transaction.
        Có lỗi ở bất kỳ bước nào thì rollback.
        """

        replaced_dates = sorted(
            set(business_dates)
        )

        if not replaced_dates:
            raise ValueError(
                "Không có DATE nào để import"
            )

        main_connection = create_connection(
            self.database_path
        )

        staging_connection = sqlite3.connect(
            str(staging_database_path)
        )

        staging_attached = False

        try:
            # Gắn staging vào connection chính để SQLite
            # có thể JOIN trực tiếp, không load key vào RAM.
            main_connection.execute(
                "ATTACH DATABASE ? AS staging_prime",
                (str(staging_database_path),),
            )

            staging_attached = True

            main_connection.execute(
                "BEGIN IMMEDIATE"
            )

            filter_cache_repository = (
                FilterOptionCacheRepository()
            )

            # Chuẩn bị toàn bộ ID phải xóa:
            # - Toàn bộ ngày chính.
            # - Dòng lệch ngày trùng khóa.
            self._prepare_delete_ids(
                connection=main_connection,
                replaced_dates=replaced_dates,
            )
            alarm_repository = AlarmRepository()

            # Lấy cả slot của dữ liệu cũ và staging
            # trước khi xóa dữ liệu PRIME.
            alarm_repository.prepare_affected_slots_for_prime_replace(
                connection=main_connection,
            )

            # Trừ cache trước khi xóa dữ liệu chính.
            filter_cache_repository.remove_prime_for_delete_ids(
                main_connection=main_connection,
            )

            deleted_row_count = (
                self._delete_prepared_rows(
                    connection=main_connection,
                )
            )

            inserted_row_count = (
                self._insert_staging_data(
                    main_connection=main_connection,
                    staging_connection=staging_connection,
                )
            )

            # Lấy DATE thực tế trong staging.
            #
            # Ví dụ chọn import ngày 20260830 nhưng file có
            # một vài dòng thuộc ngày 20260829 thì kết quả là:
            # ["20260829", "20260830"]
            imported_data_dates = [
                str(row[0])
                for row in main_connection.execute(
                    """
                    SELECT DISTINCT DATE
                    FROM staging_prime.staging_prime_data
                    ORDER BY DATE
                    """
                ).fetchall()
            ]

            # Đồng bộ Tier cho tất cả dòng vừa import,
            # bao gồm cả những dòng lệch ngày.
            self._sync_inserted_tiers_from_existing_cum(
                connection=main_connection,
            )

            # Chỉ xóa và build lại alarm của các ngày
            # thực tế có trong staging.
            alarm_repository.rebuild_affected_slots(
                connection=main_connection,
                affected_dates=imported_data_dates,
            )

            # Cộng lại cache từ toàn bộ staging.
            filter_cache_repository.add_prime_from_staging(
                main_connection=main_connection,
                staging_connection=staging_connection,
            )

            filter_cache_repository.finalize(
                main_connection=main_connection
            )
            # Lấy DATE thực tế trong staging, gồm cả các dòng
            # lệch ngày có trong folder log vừa import.

            ImportStatusRepository.upsert_dates(
                connection=main_connection,
                data_type="PRIME",
                business_dates=imported_data_dates,
            )

            main_connection.commit()

            return PrimeReplaceResult(
                deleted_row_count=deleted_row_count,
                inserted_row_count=inserted_row_count,
                replaced_dates=replaced_dates,
            )

        except Exception:
            if main_connection.in_transaction:
                main_connection.rollback()

            raise

        finally:
            staging_connection.close()

            if staging_attached:
                try:
                    main_connection.execute(
                        "DETACH DATABASE staging_prime"
                    )
                except sqlite3.Error:
                    pass

            main_connection.close()

    def _prepare_delete_ids(
            self,
            connection: sqlite3.Connection,
            replaced_dates: list[str],
    ) -> None:
        """
        Chuẩn bị danh sách ID cần xóa.

        Bao gồm:
        1. Toàn bộ dữ liệu của ngày người dùng chọn.
        2. Dòng lệch ngày trùng EQP + DATE + TIME + SLOT.
        """

        connection.execute(
            """
            CREATE TEMP TABLE temp_prime_delete_ids (
                id INTEGER PRIMARY KEY
            ) WITHOUT ROWID
            """
        )

        # Thêm toàn bộ ID thuộc ngày người dùng chọn.
        for date_batch in self._chunks(
                replaced_dates,
                DELETE_DATE_BATCH_SIZE,
        ):
            placeholders = ", ".join(
                "?"
                for _ in date_batch
            )

            connection.execute(
                f"""
                INSERT OR IGNORE INTO temp_prime_delete_ids (
                    id
                )
                SELECT id
                FROM prime_data
                WHERE DATE IN ({placeholders})
                """,
                date_batch,
            )

        placeholders = ", ".join(
            "?"
            for _ in replaced_dates
        )

        # Với dòng lệch ngày, chỉ thêm ID nếu trùng:
        # EQP + DATE + TIME + SLOT.
        connection.execute(
            f"""
            INSERT OR IGNORE INTO temp_prime_delete_ids (
                id
            )
            SELECT prime.id
            FROM prime_data AS prime
            INNER JOIN staging_prime.staging_prime_data AS stage
                ON stage.DATE = prime.DATE
               AND stage.EQP = prime.EQP
               AND stage.TIME = prime.TIME
               AND stage.Slot = prime.Slot
            WHERE stage.DATE NOT IN ({placeholders})
            """,
            replaced_dates,
        )

    @staticmethod
    def _delete_prepared_rows(
            connection: sqlite3.Connection,
    ) -> int:
        """Xóa các dòng đã chuẩn bị và trả số dòng bị xóa."""

        deleted_row_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM temp_prime_delete_ids
            """
        ).fetchone()[0]

        connection.execute(
            """
            DELETE FROM prime_data
            WHERE id IN (
                SELECT id
                FROM temp_prime_delete_ids
            )
            """
        )

        return deleted_row_count

    def _insert_staging_data(
        self,
        main_connection: sqlite3.Connection,
        staging_connection: sqlite3.Connection,
    ) -> int:
        """
        Đọc staging từng batch và insert vào database chính.

        Không load toàn bộ staging data vào RAM.
        Không truyền QTY vì prime_data tự dùng DEFAULT 1.
        """

        staging_cursor = staging_connection.execute(
            """
            SELECT
                DATE,
                TIME,
                PARTNO,
                LOTNO,
                INTERFACE,
                RESULT,
                SCRAPCODE,
                EQP,
                Chamber,
                Slot,
                MODEL
            FROM staging_prime_data
            """
        )

        inserted_row_count = 0

        while True:
            rows = staging_cursor.fetchmany(
                INSERT_BATCH_SIZE
            )

            if not rows:
                break

            main_connection.executemany(
                """
                INSERT INTO prime_data (
                    DATE,
                    TIME,
                    PARTNO,
                    LOTNO,
                    INTERFACE,
                    RESULT,
                    SCRAPCODE,
                    EQP,
                    Chamber,
                    Slot,
                    MODEL
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

            inserted_row_count += len(rows)

        return inserted_row_count

    def _sync_inserted_tiers_from_existing_cum(
            self,
            connection: sqlite3.Connection,
    ) -> None:
        """
        Đồng bộ Tier cho tất cả dòng vừa import.

        Bao gồm cả dòng có DATE khác ngày người dùng chọn.
        PRIME ngày P tìm Tier trong CUM từ P đến P + 4 ngày.
        """

        # Lấy DATE thực tế của tất cả dòng trong staging.
        # Vì vậy nếu import ngày 17 nhưng file có dòng ngày 16,
        # cả ngày 16 và ngày 17 đều được xử lý.
        staged_dates = connection.execute(
            """
            SELECT DISTINCT DATE
            FROM staging_prime.staging_prime_data
            ORDER BY DATE
            """
        ).fetchall()

        for row in staged_dates:
            prime_date = row[0]

            cum_end_date = (
                    datetime.strptime(
                        prime_date,
                        "%Y%m%d",
                    )
                    + timedelta(days=TIER_MAX_DELAY_DAYS)
            ).strftime("%Y%m%d")

            connection.execute(
                """
                UPDATE prime_data AS prime
                SET TIER = (
                    SELECT cum.TIER
                    FROM cum_data AS cum
                    WHERE cum.LOTID = prime.LOTNO
                      AND cum.DATE BETWEEN ? AND ?
                    ORDER BY cum.DATE
                    LIMIT 1
                )
                WHERE prime.DATE = ?
                  AND EXISTS (
                      SELECT 1
                      FROM staging_prime.staging_prime_data AS stage
                      WHERE stage.DATE = prime.DATE
                        AND stage.EQP = prime.EQP
                        AND stage.TIME = prime.TIME
                        AND stage.Slot = prime.Slot
                  )
                """,
                (
                    prime_date,
                    cum_end_date,
                    prime_date,
                ),
            )

    @staticmethod
    def _chunks(
        values: list[str],
        chunk_size: int,
    ):
        for start_index in range(
            0,
            len(values),
            chunk_size,
        ):
            yield values[
                start_index:
                start_index + chunk_size
            ]
