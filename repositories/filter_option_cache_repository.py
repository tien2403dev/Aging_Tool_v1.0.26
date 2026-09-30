from __future__ import annotations

import sqlite3


DELETE_DATE_BATCH_SIZE = 500


class FilterOptionCacheRepository:
    """
    Duy trì các bảng cache option của bộ lọc.

    Tất cả hàm phải được gọi trong cùng transaction
    với thao tác xóa/insert PRIME hoặc CUM.
    """

    def remove_prime_for_delete_ids(
            self,
            main_connection: sqlite3.Connection,
    ) -> None:
        """
        Trừ cache cho những dòng PRIME chuẩn bị bị xóa.

        Danh sách id cần xóa đã được PrimeRepository
        lưu trong TEMP table temp_prime_delete_ids.
        """

        self._apply_eqp_deltas(
            main_connection,
            main_connection.execute(
                """
                SELECT
                    prime.EQP,
                    -COUNT(*)
                FROM prime_data AS prime
                INNER JOIN temp_prime_delete_ids AS target
                    ON target.id = prime.id
                GROUP BY prime.EQP
                """
            ).fetchall(),
        )

        self._apply_chamber_deltas(
            main_connection,
            main_connection.execute(
                """
                SELECT
                    prime.Chamber,
                    -COUNT(*)
                FROM prime_data AS prime
                INNER JOIN temp_prime_delete_ids AS target
                    ON target.id = prime.id
                GROUP BY prime.Chamber
                """
            ).fetchall(),
        )

        self._apply_prime_scrap_deltas(
            main_connection,
            main_connection.execute(
                """
                SELECT
                    prime.SCRAPCODE,
                    -COUNT(*)
                FROM prime_data AS prime
                INNER JOIN temp_prime_delete_ids AS target
                    ON target.id = prime.id
                WHERE TRIM(
                    COALESCE(prime.SCRAPCODE, '')
                ) != ''
                GROUP BY prime.SCRAPCODE
                """
            ).fetchall(),
        )

        self._apply_model_deltas(
            main_connection,
            main_connection.execute(
                """
                SELECT
                    prime.MODEL,
                    -COUNT(*)
                FROM prime_data AS prime
                INNER JOIN temp_prime_delete_ids AS target
                    ON target.id = prime.id
                GROUP BY prime.MODEL
                """
            ).fetchall(),
        )

    def remove_prime_for_dates(
        self,
        main_connection: sqlite3.Connection,
        business_dates: list[str],
    ) -> None:
        for date_batch in self._chunks(business_dates):
            placeholders = ", ".join(
                "?" for _ in date_batch
            )

            self._apply_eqp_deltas(
                main_connection,
                main_connection.execute(
                    f"""
                    SELECT EQP, -COUNT(*)
                    FROM prime_data
                    WHERE DATE IN ({placeholders})
                    GROUP BY EQP
                    """,
                    date_batch,
                ).fetchall(),
            )

            self._apply_chamber_deltas(
                main_connection,
                main_connection.execute(
                    f"""
                    SELECT Chamber, -COUNT(*)
                    FROM prime_data
                    WHERE DATE IN ({placeholders})
                    GROUP BY Chamber
                    """,
                    date_batch,
                ).fetchall(),
            )

            self._apply_prime_scrap_deltas(
                main_connection,
                main_connection.execute(
                    f"""
                    SELECT SCRAPCODE, -COUNT(*)
                    FROM prime_data
                    WHERE DATE IN ({placeholders})
                      AND TRIM(
                          COALESCE(SCRAPCODE, '')
                      ) != ''
                    GROUP BY SCRAPCODE
                    """,
                    date_batch,
                ).fetchall(),
            )
            self._apply_model_deltas(
                main_connection,
                main_connection.execute(
                    f"""
                    SELECT
                        MODEL,
                        -COUNT(*)
                    FROM prime_data
                    WHERE DATE IN ({placeholders})
                    GROUP BY MODEL
                    """,
                    date_batch,
                ).fetchall(),
            )

    def add_prime_from_staging(
        self,
        main_connection: sqlite3.Connection,
        staging_connection: sqlite3.Connection,
    ) -> None:
        self._apply_eqp_deltas(
            main_connection,
            staging_connection.execute(
                """
                SELECT EQP, COUNT(*)
                FROM staging_prime_data
                GROUP BY EQP
                """
            ).fetchall(),
        )

        self._apply_chamber_deltas(
            main_connection,
            staging_connection.execute(
                """
                SELECT Chamber, COUNT(*)
                FROM staging_prime_data
                GROUP BY Chamber
                """
            ).fetchall(),
        )

        self._apply_prime_scrap_deltas(
            main_connection,
            staging_connection.execute(
                """
                SELECT SCRAPCODE, COUNT(*)
                FROM staging_prime_data
                WHERE TRIM(
                    COALESCE(SCRAPCODE, '')
                ) != ''
                GROUP BY SCRAPCODE
                """
            ).fetchall(),
        )
        self._apply_model_deltas(
            main_connection,
            staging_connection.execute(
                """
                SELECT
                    MODEL,
                    COUNT(*)
                FROM staging_prime_data
                GROUP BY MODEL
                """
            ).fetchall(),
        )

    def remove_cum_for_dates(
        self,
        main_connection: sqlite3.Connection,
        business_dates: list[str],
    ) -> None:
        for date_batch in self._chunks(business_dates):
            placeholders = ", ".join(
                "?" for _ in date_batch
            )

            self._apply_cum_scrap_deltas(
                main_connection,
                main_connection.execute(
                    f"""
                    SELECT
                        detail.scrap_code,
                        -COUNT(*)
                    FROM cum_scrap_detail AS detail
                    INNER JOIN cum_data AS cum
                        ON cum.id = detail.cum_data_id
                    WHERE cum.DATE IN ({placeholders})
                    GROUP BY detail.scrap_code
                    """,
                    date_batch,
                ).fetchall(),
            )

    def add_cum_from_staging(
        self,
        main_connection: sqlite3.Connection,
        staging_connection: sqlite3.Connection,
    ) -> None:
        self._apply_cum_scrap_deltas(
            main_connection,
            staging_connection.execute(
                """
                SELECT
                    scrap_code,
                    COUNT(*)
                FROM staging_cum_scrap_detail
                GROUP BY scrap_code
                """
            ).fetchall(),
        )

    @staticmethod
    def finalize(
        main_connection: sqlite3.Connection,
    ) -> None:
        """
        Cache âm nghĩa là dữ liệu cache đã không còn khớp
        với dữ liệu thực. Raise để transaction rollback,
        tuyệt đối không âm thầm làm sai option filter.
        """

        invalid_eqp = main_connection.execute(
            """
            SELECT 1
            FROM filter_eqp_option
            WHERE row_count < 0
            LIMIT 1
            """
        ).fetchone()

        invalid_chamber = main_connection.execute(
            """
            SELECT 1
            FROM filter_chamber_option
            WHERE row_count < 0
            LIMIT 1
            """
        ).fetchone()

        invalid_scrap = main_connection.execute(
            """
            SELECT 1
            FROM filter_scrap_code_option
            WHERE prime_row_count < 0
               OR cum_row_count < 0
            LIMIT 1
            """
        ).fetchone()
        invalid_model = main_connection.execute(
            """
            SELECT 1
            FROM filter_model_option
            WHERE row_count < 0
            LIMIT 1
            """
        ).fetchone()

        if (
                invalid_eqp is not None
                or invalid_chamber is not None
                or invalid_scrap is not None
                or invalid_model is not None
        ):
            raise RuntimeError(
                "Filter option cache không khớp dữ liệu. "
                "Vui lòng rebuild cache trước khi import lại."
            )

        main_connection.execute(
            """
            DELETE FROM filter_eqp_option
            WHERE row_count = 0
            """
        )

        main_connection.execute(
            """
            DELETE FROM filter_chamber_option
            WHERE row_count = 0
            """
        )

        main_connection.execute(
            """
            DELETE FROM filter_scrap_code_option
            WHERE prime_row_count = 0
              AND cum_row_count = 0
            """
        )
        main_connection.execute(
            """
            DELETE FROM filter_model_option
            WHERE row_count = 0
            """
        )

    @staticmethod
    def _apply_eqp_deltas(
            connection: sqlite3.Connection,
            rows,
    ) -> None:
        for eqp, delta in rows:
            if delta < 0:
                cursor = connection.execute(
                    """
                    UPDATE filter_eqp_option
                    SET row_count = row_count + ?
                    WHERE eqp = ?
                    """,
                    (delta, eqp),
                )

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        "Filter EQP cache không khớp dữ liệu. "
                        "Vui lòng rebuild cache."
                    )
            else:
                connection.execute(
                    """
                    INSERT INTO filter_eqp_option (
                        eqp,
                        row_count
                    )
                    VALUES (?, ?)
                    ON CONFLICT(eqp)
                    DO UPDATE SET
                        row_count = row_count + excluded.row_count
                    """,
                    (eqp, delta),
                )

    @staticmethod
    def _apply_chamber_deltas(
            connection: sqlite3.Connection,
            rows,
    ) -> None:
        for chamber, delta in rows:
            if delta < 0:
                cursor = connection.execute(
                    """
                    UPDATE filter_chamber_option
                    SET row_count = row_count + ?
                    WHERE chamber = ?
                    """,
                    (delta, chamber),
                )

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        "Filter Chamber cache không khớp dữ liệu. "
                        "Vui lòng rebuild cache."
                    )
            else:
                connection.execute(
                    """
                    INSERT INTO filter_chamber_option (
                        chamber,
                        row_count
                    )
                    VALUES (?, ?)
                    ON CONFLICT(chamber)
                    DO UPDATE SET
                        row_count = row_count + excluded.row_count
                    """,
                    (chamber, delta),
                )

    @staticmethod
    def _apply_prime_scrap_deltas(
            connection: sqlite3.Connection,
            rows,
    ) -> None:
        for scrap_code, delta in rows:
            if delta < 0:
                cursor = connection.execute(
                    """
                    UPDATE filter_scrap_code_option
                    SET prime_row_count = prime_row_count + ?
                    WHERE scrap_code = ?
                    """,
                    (delta, scrap_code),
                )

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        "Filter Scrap Code cache không khớp dữ liệu. "
                        "Vui lòng rebuild cache."
                    )
            else:
                connection.execute(
                    """
                    INSERT INTO filter_scrap_code_option (
                        scrap_code,
                        prime_row_count,
                        cum_row_count
                    )
                    VALUES (?, ?, 0)
                    ON CONFLICT(scrap_code)
                    DO UPDATE SET
                        prime_row_count =
                            prime_row_count
                            + excluded.prime_row_count
                    """,
                    (scrap_code, delta),
                )

    @staticmethod
    def _apply_cum_scrap_deltas(
            connection: sqlite3.Connection,
            rows,
    ) -> None:
        for scrap_code, delta in rows:
            if delta < 0:
                cursor = connection.execute(
                    """
                    UPDATE filter_scrap_code_option
                    SET cum_row_count = cum_row_count + ?
                    WHERE scrap_code = ?
                    """,
                    (delta, scrap_code),
                )

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        "Filter Scrap Code cache không khớp dữ liệu. "
                        "Vui lòng rebuild cache."
                    )
            else:
                connection.execute(
                    """
                    INSERT INTO filter_scrap_code_option (
                        scrap_code,
                        prime_row_count,
                        cum_row_count
                    )
                    VALUES (?, 0, ?)
                    ON CONFLICT(scrap_code)
                    DO UPDATE SET
                        cum_row_count =
                            cum_row_count
                            + excluded.cum_row_count
                    """,
                    (scrap_code, delta),
                )

    @staticmethod
    def _chunks(
        values: list[str],
    ):
        for start_index in range(
            0,
            len(values),
            DELETE_DATE_BATCH_SIZE,
        ):
            yield values[
                start_index:
                start_index + DELETE_DATE_BATCH_SIZE
            ]

    @staticmethod
    def _apply_model_deltas(
            connection: sqlite3.Connection,
            rows,
    ) -> None:
        for model, delta in rows:
            if delta < 0:
                cursor = connection.execute(
                    """
                    UPDATE filter_model_option
                    SET row_count = row_count + ?
                    WHERE model = ?
                    """,
                    (delta, model),
                )

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        "Filter Model cache không khớp dữ liệu. "
                        "Vui lòng rebuild cache."
                    )
            else:
                connection.execute(
                    """
                    INSERT INTO filter_model_option (
                        model,
                        row_count
                    )
                    VALUES (?, ?)

                    ON CONFLICT(model)
                    DO UPDATE SET
                        row_count =
                            row_count
                            + excluded.row_count
                    """,
                    (model, delta),
                )