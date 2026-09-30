from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from database.connection import create_connection
from repositories.data_filter import build_data_filter

@dataclass
class YieldEqpRow:
    """Một dòng thống kê Yield theo EQP."""

    eqpid: str
    in_qty: int
    pass_qty: int
    fail_qty: int
    fail_ppm: float | None
    yield_percent: float | None
    scrap_ppm_by_code: dict[str, float]


@dataclass
class YieldEqpSourceResult:
    """Kết quả của một nguồn PRIME hoặc CUM."""

    source: str
    scrap_codes: list[str]
    rows: list[YieldEqpRow]
    total: YieldEqpRow

@dataclass
class PrimeProductYieldRow:
    """Yield của một EQP theo từng Model."""

    eqpid: str
    yield_by_model: dict[str, float]


@dataclass
class PrimeProductYieldResult:
    """Ma trận Yield PRIME theo EQP và Model."""

    models: list[str]
    rows: list[PrimeProductYieldRow]

@dataclass
class YieldEqpResult:
    date_from: str
    date_to: str
    prime: YieldEqpSourceResult
    prime_product: PrimeProductYieldResult
    prime_model_scrap: PrimeModelScrapResult
    cum: YieldEqpSourceResult
    selected_scrap_codes: list[str]
    selected_models: list[str]

@dataclass
class PrimeModelScrapRow:
    """Một dòng thống kê PRIME theo Model."""

    model: str
    in_qty: int
    pass_qty: int
    fail_qty: int
    yield_percent: float | None
    scrap_qty_by_code: dict[str, int]


@dataclass
class PrimeModelScrapResult:
    """Thống kê Model và toàn bộ Scrap Code PRIME."""

    scrap_codes: list[str]
    rows: list[PrimeModelScrapRow]
    total_scrap_qty_by_code: dict[str, int]

class YieldEqpRepository:
    """Chứa truy vấn tổng hợp cho tab Yield EQP."""

    def __init__(
        self,
        database_path: Union[str, Path],
    ):
        self.database_path = Path(database_path)

    def get_yield_eqp_data(
            self,
            date_from: str,
            date_to: str,
            tiers: list[str | None],
            selected_scrap_codes: list[str],
            selected_models: list[str],
    ) -> YieldEqpResult:
        """
        Tải PRIME và CUM bằng cùng một connection.

        Chỉ lấy dữ liệu đã GROUP BY,
        không đưa raw rows lên UI.
        """

        connection = create_connection(
            self.database_path
        )

        # try:
        #     prime_result = self._get_prime_result(
        #         connection=connection,
        #         date_from=date_from,
        #         date_to=date_to,
        #         tiers=tiers,
        #     )
        #
        #     cum_result = self._get_cum_result(
        #         connection=connection,
        #         date_from=date_from,
        #         date_to=date_to,
        #         tiers=tiers,
        #     )
        try:
            (
                prime_product_result,
                prime_quantity_rows,
            ) = self._get_prime_product_result(
                connection=connection,
                date_from=date_from,
                date_to=date_to,
                tiers=tiers,
                selected_models=selected_models,
            )

            prime_result = self._get_prime_result(
                connection=connection,
                date_from=date_from,
                date_to=date_to,
                tiers=tiers,
                quantity_rows=prime_quantity_rows,
                selected_models=selected_models,
            )

            prime_model_scrap_result = (
                self._get_prime_model_scrap_result(
                    connection=connection,
                    date_from=date_from,
                    date_to=date_to,
                    tiers=tiers,
                    selected_models=selected_models,
                )
            )

            cum_result = self._get_cum_result(
                connection=connection,
                date_from=date_from,
                date_to=date_to,
                tiers=tiers,
                selected_models=selected_models,
            )

        finally:
            connection.close()

        return YieldEqpResult(
            date_from=date_from,
            date_to=date_to,
            prime=prime_result,
            prime_product=prime_product_result,
            prime_model_scrap=(
                prime_model_scrap_result
            ),
            cum=cum_result,
            selected_scrap_codes=list(
                selected_scrap_codes
            ),
            selected_models=list(
                selected_models
            ),
        )
    def _get_prime_product_result(
        self,
        connection,
        date_from: str,
        date_to: str,
        tiers: list[str | None],
        selected_models: list[str] | None = None,
    ) -> tuple[
        PrimeProductYieldResult,
        list[dict],
    ]:
        """
        Tổng hợp một lần cho cả bảng Product
        và bảng PRIME theo EQP.

        Không query raw rows và không quét
        prime_data thêm một lần cho tổng EQP.
        """

        tier_sql, tier_params = (
            self._build_tier_filter(
                column_name="TIER",
                tiers=tiers,
            )
        )

        rows = connection.execute(
            f"""
            SELECT
                EQP AS eqpid,
                MODEL AS model,
                COUNT(*) AS in_qty,

                SUM(
                    CASE
                        WHEN RESULT = 'PASS'
                        THEN 1
                        ELSE 0
                    END
                ) AS pass_qty

            FROM prime_data

            WHERE DATE BETWEEN ? AND ?
              {tier_sql}

            GROUP BY
                EQP,
                MODEL

            ORDER BY
                EQP,
                MODEL
            """,
            [
                date_from,
                date_to,
                *tier_params,
            ],
        ).fetchall()

        models = set()

        yield_by_eqp: dict[
            str,
            dict[str, float],
        ] = {}

        # [IN, PASS] của từng EQP.
        quantity_by_eqp: dict[
            str,
            list[int],
        ] = {}

        selected_model_set = set(
            selected_models or []
        )

        for row in rows:
            eqpid = row["eqpid"]
            model = row["model"]

            in_qty = int(
                row["in_qty"] or 0
            )

            pass_qty = int(
                row["pass_qty"] or 0
            )

            models.add(model)

            # Chỉ cộng Model được chọn vào tổng PRIME theo EQP.
            # Dữ liệu bảng Product phía dưới vẫn lấy đầy đủ.
            # Chỉ cộng vào tổng PRIME theo EQP
            # khi Model nằm trong danh sách được chọn.
            if model in selected_model_set:
                eqp_quantity = (
                    quantity_by_eqp.setdefault(
                        eqpid,
                        [0, 0],
                    )
                )

                eqp_quantity[0] += in_qty
                eqp_quantity[1] += pass_qty

            if in_qty > 0:
                yield_percent = (
                    pass_qty / in_qty
                ) * 100
            else:
                yield_percent = 0.0

            yield_by_eqp.setdefault(
                eqpid,
                {},
            )[model] = yield_percent

        product_result = (
            PrimeProductYieldResult(
                models=sorted(models),
                rows=[
                    PrimeProductYieldRow(
                        eqpid=eqpid,
                        yield_by_model=(
                            yield_by_eqp[eqpid]
                        ),
                    )
                    for eqpid in sorted(
                        yield_by_eqp
                    )
                ],
            )
        )

        # Tận dụng chính query Product để tạo
        # tổng IN/PASS cho bảng PRIME theo EQP.
        prime_quantity_rows = [
            {
                "eqpid": eqpid,
                "in_qty": quantities[0],
                "pass_qty": quantities[1],
            }
            for eqpid, quantities in sorted(
                quantity_by_eqp.items()
            )
        ]

        return (
            product_result,
            prime_quantity_rows,
        )
    def _get_prime_result(
        self,
        connection,
        date_from: str,
        date_to: str,
        tiers: list[str | None],
        quantity_rows,
        selected_models: list[str] | None = None,
    ) -> YieldEqpSourceResult:
        """Tổng hợp PRIME theo EQP."""

        scrap_tier_sql, scrap_tier_params = (
            build_data_filter(
                column_name="TIER",
                tiers=tiers,
                selected_models=selected_models,
            )
        )

        scrap_rows = connection.execute(
            f"""
            SELECT
                EQP AS eqpid,
                SCRAPCODE AS scrap_code,
                COUNT(*) AS scrap_qty

            FROM prime_data

            WHERE DATE BETWEEN ? AND ?
              AND RESULT = 'FAIL'
              AND SCRAPCODE <> ''
              {scrap_tier_sql}

            GROUP BY
                EQP,
                SCRAPCODE

            ORDER BY
                EQP,
                SCRAPCODE
            """,
            [
                date_from,
                date_to,
                *scrap_tier_params,
            ],
        ).fetchall()

        return self._build_source_result(
            source="PRIME",
            quantity_rows=quantity_rows,
            scrap_rows=scrap_rows,
        )

    def _get_prime_model_scrap_result(
            self,
            connection,
            date_from: str,
            date_to: str,
            tiers: list[str | None],
            selected_models: list[str] | None = None,
    ) -> PrimeModelScrapResult:
        """
        Một query GROUP BY tạo đồng thời metric Model
        và số lượng của toàn bộ Scrap Code.

        Không lấy raw rows lên Python.
        """

        tier_sql, tier_params = build_data_filter(
            column_name="TIER",
            tiers=tiers,
            selected_models=selected_models,
        )

        grouped_rows = connection.execute(
            f"""
            SELECT
                MODEL AS model,
                SCRAPCODE AS scrap_code,
                COUNT(*) AS in_qty,

                SUM(
                    CASE
                        WHEN RESULT = 'PASS'
                        THEN 1
                        ELSE 0
                    END
                ) AS pass_qty,

                SUM(
                    CASE
                        WHEN RESULT = 'FAIL'
                        THEN 1
                        ELSE 0
                    END
                ) AS fail_qty

            FROM prime_data

            WHERE DATE BETWEEN ? AND ?
              {tier_sql}

            GROUP BY
                MODEL,
                SCRAPCODE

            ORDER BY
                MODEL,
                SCRAPCODE
            """,
            [
                date_from,
                date_to,
                *tier_params,
            ],
        ).fetchall()

        # Mỗi Model lưu [Input, Pass].
        quantity_by_model: dict[
            str,
            list[int],
        ] = {}

        scrap_qty_by_model: dict[
            str,
            dict[str, int],
        ] = {}

        scrap_codes: set[str] = set()

        for grouped_row in grouped_rows:
            model = grouped_row["model"]

            scrap_code = (
                    grouped_row["scrap_code"] or ""
            ).strip()

            in_qty = int(
                grouped_row["in_qty"] or 0
            )

            pass_qty = int(
                grouped_row["pass_qty"] or 0
            )

            fail_qty = int(
                grouped_row["fail_qty"] or 0
            )

            quantities = (
                quantity_by_model.setdefault(
                    model,
                    [0, 0],
                )
            )

            quantities[0] += in_qty
            quantities[1] += pass_qty

            # Fail không có Scrap Code vẫn được tính
            # vào cột Fail, nhưng không tạo cột mã lỗi.
            if fail_qty <= 0 or not scrap_code:
                continue

            scrap_codes.add(
                scrap_code
            )

            model_scraps = (
                scrap_qty_by_model.setdefault(
                    model,
                    {},
                )
            )

            model_scraps[scrap_code] = (
                    model_scraps.get(
                        scrap_code,
                        0,
                    )
                    + fail_qty
            )

        result_rows = []

        for model, quantities in sorted(
                quantity_by_model.items()
        ):
            in_qty, pass_qty = quantities
            fail_qty = in_qty - pass_qty

            result_rows.append(
                PrimeModelScrapRow(
                    model=model,
                    in_qty=in_qty,
                    pass_qty=pass_qty,
                    fail_qty=fail_qty,
                    yield_percent=(
                        (pass_qty / in_qty) * 100
                        if in_qty > 0
                        else None
                    ),
                    scrap_qty_by_code=(
                        scrap_qty_by_model.get(
                            model,
                            {},
                        )
                    ),
                )
            )

        sorted_scrap_codes = sorted(
            scrap_codes
        )

        return PrimeModelScrapResult(
            scrap_codes=sorted_scrap_codes,
            rows=result_rows,
            total_scrap_qty_by_code={
                scrap_code: sum(
                    row.scrap_qty_by_code.get(
                        scrap_code,
                        0,
                    )
                    for row in result_rows
                )
                for scrap_code in sorted_scrap_codes
            },
        )
    def _get_cum_result(
        self,
        connection,
        date_from: str,
        date_to: str,
        tiers: list[str | None],
        selected_models: list[str] | None = None,
    ) -> YieldEqpSourceResult:
        """Tổng hợp CUM theo EQP."""

        # tier_sql, tier_params = (
        #     self._build_tier_filter(
        #         column_name="TIER",
        #         tiers=tiers,
        #     )
        # )
        tier_sql, tier_params = build_data_filter(
            column_name="TIER",
            tiers=tiers,
            selected_models=selected_models,
        )

        quantity_rows = connection.execute(
            f"""
            SELECT
                EQPID AS eqpid,
                SUM(INQTY) AS in_qty,
                SUM(OUTQTY) AS pass_qty

            FROM cum_data

            WHERE DATE BETWEEN ? AND ?
              {tier_sql}

            GROUP BY EQPID
            ORDER BY EQPID
            """,
            [
                date_from,
                date_to,
                *tier_params,
            ],
        ).fetchall()

        # scrap_tier_sql, scrap_tier_params = (
        #     self._build_tier_filter(
        #         column_name="data.TIER",
        #         tiers=tiers,
        #     )
        # )
        scrap_tier_sql, scrap_tier_params = (
            build_data_filter(
                column_name="data.TIER",
                tiers=tiers,
                selected_models=selected_models,
            )
        )

        scrap_rows = connection.execute(
            f"""
            SELECT
                data.EQPID AS eqpid,
                detail.scrap_code,
                SUM(detail.qty) AS scrap_qty

            FROM cum_data AS data

            INNER JOIN cum_scrap_detail AS detail
                ON detail.cum_data_id = data.id

            WHERE data.DATE BETWEEN ? AND ?
              {scrap_tier_sql}

            GROUP BY
                data.EQPID,
                detail.scrap_code

            ORDER BY
                data.EQPID,
                detail.scrap_code
            """,
            [
                date_from,
                date_to,
                *scrap_tier_params,
            ],
        ).fetchall()

        return self._build_source_result(
            source="CUM",
            quantity_rows=quantity_rows,
            scrap_rows=scrap_rows,
        )

    @staticmethod
    def _build_source_result(
        source: str,
        quantity_rows,
        scrap_rows,
    ) -> YieldEqpSourceResult:
        """Ghép metric tổng và Scrap PPM."""

        quantity_by_eqp = {
            row["eqpid"]: (
                int(row["in_qty"] or 0),
                int(row["pass_qty"] or 0),
            )
            for row in quantity_rows
        }

        scrap_qty_by_eqp: dict[
            str,
            dict[str, int],
        ] = {}

        scrap_codes = set()

        for row in scrap_rows:
            eqpid = row["eqpid"]
            scrap_code = row["scrap_code"]
            scrap_qty = int(
                row["scrap_qty"] or 0
            )

            scrap_codes.add(scrap_code)

            scrap_qty_by_eqp.setdefault(
                eqpid,
                {},
            )[scrap_code] = scrap_qty

        rows = []

        for eqpid, quantities in (
            quantity_by_eqp.items()
        ):
            in_qty, pass_qty = quantities

            scrap_ppm_by_code = {
                scrap_code: (
                    scrap_qty / in_qty
                ) * 1_000_000

                for scrap_code, scrap_qty in (
                    scrap_qty_by_eqp.get(
                        eqpid,
                        {},
                    ).items()
                )

                if in_qty > 0
            }

            rows.append(
                YieldEqpRepository._build_row(
                    eqpid=eqpid,
                    in_qty=in_qty,
                    pass_qty=pass_qty,
                    scrap_ppm_by_code=(
                        scrap_ppm_by_code
                    ),
                )
            )

        total = YieldEqpRepository._build_row(
            eqpid="Total",
            in_qty=sum(
                row.in_qty
                for row in rows
            ),
            pass_qty=sum(
                row.pass_qty
                for row in rows
            ),
            scrap_ppm_by_code={},
        )

        return YieldEqpSourceResult(
            source=source,
            scrap_codes=sorted(
                scrap_codes
            ),
            rows=rows,
            total=total,
        )

    @staticmethod
    def _build_row(
        eqpid: str,
        in_qty: int,
        pass_qty: int,
        scrap_ppm_by_code: dict[str, float],
    ) -> YieldEqpRow:
        """Tính Fail, Fail PPM và Yield."""

        fail_qty = in_qty - pass_qty

        if in_qty > 0:
            fail_ppm = (
                fail_qty / in_qty
            ) * 1_000_000

            yield_percent = (
                pass_qty / in_qty
            ) * 100
        else:
            fail_ppm = None
            yield_percent = None

        return YieldEqpRow(
            eqpid=eqpid,
            in_qty=in_qty,
            pass_qty=pass_qty,
            fail_qty=fail_qty,
            fail_ppm=fail_ppm,
            yield_percent=yield_percent,
            scrap_ppm_by_code=(
                scrap_ppm_by_code
            ),
        )

    @staticmethod
    def _build_tier_filter(
            column_name: str,
            tiers: list[str | None],
    ) -> tuple[str, list[str]]:
        """Tạo điều kiện SQL chỉ cho Tier khác NULL."""

        normal_tiers = [
            str(tier)
            for tier in tiers
            if tier is not None
        ]

        # Không chọn Tier nào thì không trả dữ liệu.
        if not normal_tiers:
            return "AND 0 = 1", []

        placeholders = ", ".join(
            "?"
            for _ in normal_tiers
        )

        return (
            f"AND {column_name} IN ({placeholders})",
            normal_tiers,
        )