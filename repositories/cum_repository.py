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


from repositories.import_status_repository import (
    ImportStatusRepository,
)
INSERT_BATCH_SIZE = 5_000
DELETE_DATE_BATCH_SIZE = 500

# PRIME có thể hoàn thành và xuất hiện trong CUM
# muộn tối đa 4 ngày.
TIER_MAX_DELAY_DAYS = 4


@dataclass
class CumReplaceResult:
    deleted_row_count: int
    inserted_row_count: int
    inserted_scrap_detail_count: int
    replaced_dates: list[str]


class CumRepository:
    """
    Chỉ phụ trách thao tác với cum_data
    và cum_scrap_detail.

    Không đọc Excel.
    Không chứa PyQt UI code.
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
    ) -> CumReplaceResult:
        """
        Xóa dữ liệu CUM cũ theo DATE, sau đó insert
        cum_data và cum_scrap_detail từ staging database.

        Toàn bộ chạy trong một transaction.
        Nếu lỗi thì rollback toàn bộ.
        """

        replaced_dates = sorted(set(business_dates))

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

        staging_connection.row_factory = sqlite3.Row

        try:
            main_connection.execute("BEGIN IMMEDIATE")

            filter_cache_repository = (
                FilterOptionCacheRepository()
            )

            filter_cache_repository.remove_cum_for_dates(
                main_connection=main_connection,
                business_dates=replaced_dates,
            )

            deleted_row_count = self._delete_existing_dates(
                connection=main_connection,
                business_dates=replaced_dates,
            )

            (
                inserted_row_count,
                inserted_scrap_detail_count,
            ) = self._insert_staging_data(
                main_connection=main_connection,
                staging_connection=staging_connection,
            )

            # Đồng bộ Tier cho PRIME để phục vụ bộ lọc và thống kê.
            self._sync_prime_tiers(
                connection=main_connection,
                business_dates=replaced_dates,
            )
            filter_cache_repository.add_cum_from_staging(
                main_connection=main_connection,
                staging_connection=staging_connection,
            )

            filter_cache_repository.finalize(
                main_connection=main_connection
            )
            ImportStatusRepository.upsert_dates(
                connection=main_connection,
                data_type="CUM",
                business_dates=replaced_dates,
            )

            main_connection.commit()

            return CumReplaceResult(
                deleted_row_count=deleted_row_count,
                inserted_row_count=inserted_row_count,
                inserted_scrap_detail_count=(
                    inserted_scrap_detail_count
                ),
                replaced_dates=replaced_dates,
            )

        except Exception:
            if main_connection.in_transaction:
                main_connection.rollback()

            raise

        finally:
            staging_connection.close()
            main_connection.close()

    def _delete_existing_dates(
        self,
        connection: sqlite3.Connection,
        business_dates: list[str],
    ) -> int:
        """
        Khi xóa cum_data, SQLite tự xóa các dòng
        cum_scrap_detail liên quan bằng ON DELETE CASCADE.
        """

        deleted_row_count = 0

        for date_batch in self._chunks(
            business_dates,
            DELETE_DATE_BATCH_SIZE,
        ):
            placeholders = ", ".join(
                "?"
                for _ in date_batch
            )

            cursor = connection.execute(
                f"""
                DELETE FROM cum_data
                WHERE DATE IN ({placeholders})
                """,
                date_batch,
            )

            deleted_row_count += cursor.rowcount

        return deleted_row_count

    def _insert_staging_data(
        self,
        main_connection: sqlite3.Connection,
        staging_connection: sqlite3.Connection,
    ) -> tuple[int, int]:
        """
        Insert parent cum_data và child cum_scrap_detail.

        Dữ liệu được đọc từng batch từ staging,
        không load toàn bộ file vào RAM.
        """

        next_cum_data_id = self._get_next_cum_data_id(
            main_connection
        )

        staging_cursor = staging_connection.execute(
            """
            SELECT
                stage_id,
                DATE,
                TIME,
                LOTID,
                PRODUCT,
                EQPID,
                INQTY,
                OUTQTY,
                FAILQTY,
                YIELD,
                SCRAP,
                MODEL,
                TIER
            FROM staging_cum_data
            ORDER BY stage_id
            """
        )

        inserted_row_count = 0
        inserted_scrap_detail_count = 0

        while True:
            staging_rows = staging_cursor.fetchmany(
                INSERT_BATCH_SIZE
            )

            if not staging_rows:
                break

            cum_rows = [
                (
                    row["DATE"],
                    row["TIME"],
                    row["LOTID"],
                    row["PRODUCT"],
                    row["EQPID"],
                    row["INQTY"],
                    row["OUTQTY"],
                    row["FAILQTY"],
                    row["YIELD"],
                    row["SCRAP"],
                    row["MODEL"],
                    row["TIER"],
                )
                for row in staging_rows
            ]

            main_connection.executemany(
                """
                INSERT INTO cum_data (
                    DATE,
                    TIME,
                    LOTID,
                    PRODUCT,
                    EQPID,
                    INQTY,
                    OUTQTY,
                    FAILQTY,
                    YIELD,
                    SCRAP,
                    MODEL,
                    TIER
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                cum_rows,
            )

            # BEGIN IMMEDIATE + global import lock đảm bảo
            # không có writer khác chèn cum_data trong transaction.
            # SQLite AUTOINCREMENT cấp id liên tiếp cho batch này.
            stage_to_cum_id = {
                row["stage_id"]: (
                    next_cum_data_id + index
                )
                for index, row in enumerate(
                    staging_rows
                )
            }

            scrap_rows = self._get_scrap_rows_for_batch(
                staging_connection=staging_connection,
                stage_to_cum_id=stage_to_cum_id,
            )

            if scrap_rows:
                main_connection.executemany(
                    """
                    INSERT INTO cum_scrap_detail (
                        cum_data_id,
                        scrap_code,
                        qty
                    )
                    VALUES (?, ?, ?)
                    """,
                    scrap_rows,
                )

            inserted_row_count += len(cum_rows)
            inserted_scrap_detail_count += len(scrap_rows)
            next_cum_data_id += len(cum_rows)

        return (
            inserted_row_count,
            inserted_scrap_detail_count,
        )

    def _sync_prime_tiers(
            self,
            connection: sqlite3.Connection,
            business_dates: list[str],
    ) -> list[str]:
        """
        Tính lại Tier cho PRIME có thể sinh ra CUM vừa import.

        Quy tắc: PRIME ngày P được phép nhận Tier từ CUM
        trong khoảng P đến P + 4 ngày. Vì vậy khi import
        CUM ngày C, cần tính lại PRIME từ C - 4 ngày đến C.

        LOT không tồn tại trong cửa sổ CUM sẽ nhận NULL.
        """

        affected_prime_dates: set[str] = set()

        # Tìm tất cả ngày PRIME có thể bị ảnh hưởng
        # bởi những ngày CUM vừa được import.
        for cum_date in business_dates:
            parsed_cum_date = datetime.strptime(
                cum_date,
                "%Y%m%d",
            )

            for days_back in range(
                    TIER_MAX_DELAY_DAYS + 1
            ):
                affected_prime_dates.add(
                    (
                            parsed_cum_date
                            - timedelta(days=days_back)
                    ).strftime("%Y%m%d")
                )

        # Tính lại Tier riêng cho từng ngày PRIME.
        for prime_date in sorted(affected_prime_dates):
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
                """,
                (
                    prime_date,
                    cum_end_date,
                    prime_date,
                ),
            )
        return sorted(affected_prime_dates)

    @staticmethod
    def _get_next_cum_data_id(
        connection: sqlite3.Connection,
    ) -> int:
        """
        Lấy ID đầu tiên sẽ được cấp cho lần insert tiếp theo.

        cum_data dùng AUTOINCREMENT, nên sqlite_sequence
        giữ chính xác sequence ngay cả khi dữ liệu cũ đã bị xóa.
        """

        row = connection.execute(
            """
            SELECT seq
            FROM sqlite_sequence
            WHERE name = 'cum_data'
            """
        ).fetchone()

        if row is None:
            return 1

        return row["seq"] + 1

    @staticmethod
    def _get_scrap_rows_for_batch(
        staging_connection: sqlite3.Connection,
        stage_to_cum_id: dict[int, int],
    ) -> list[tuple]:
        """
        Chỉ đọc scrap detail thuộc batch cha đang insert.
        """

        stage_ids = list(stage_to_cum_id)

        if not stage_ids:
            return []

        min_stage_id = min(stage_ids)
        max_stage_id = max(stage_ids)

        detail_rows = staging_connection.execute(
            """
            SELECT
                stage_id,
                scrap_code,
                qty
            FROM staging_cum_scrap_detail
            WHERE stage_id BETWEEN ? AND ?
            ORDER BY stage_id, scrap_code
            """,
            (
                min_stage_id,
                max_stage_id,
            ),
        ).fetchall()

        return [
            (
                stage_to_cum_id[row["stage_id"]],
                row["scrap_code"],
                row["qty"],
            )
            for row in detail_rows
            if row["stage_id"] in stage_to_cum_id
        ]

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
