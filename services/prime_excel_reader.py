# from __future__ import annotations
#
# import os
# import sqlite3
# import tempfile
#
# from dataclasses import dataclass
# from datetime import datetime
# from pathlib import Path
#
#
#
# REQUIRED_COLUMNS = {
#     "FileName",
#     "DATE",
#     "SLOT",
#     "PARTNO",
#     "LOTNO",
#     "INTERFACE",
#     "RESULT",
#     "SCRAPCODE",
# }
#
# STAGING_INSERT_BATCH_SIZE = 5_000
#
#
# class PrimeExcelValidationError(Exception):
#     def __init__(
#         self,
#         source_row: int,
#         message: str,
#     ):
#         self.source_row = source_row
#
#         super().__init__(
#             f"Dòng Excel {source_row}: {message}"
#         )
#
#
# @dataclass
# class PrimeStageResult:
#     staging_database_path: Path
#     business_dates: set[str]
#     row_count: int
#
#
# class PrimeExcelReader:
#     """
#     Đọc và kiểm tra file PRIME.
#
#     Dữ liệu hợp lệ được lưu tạm vào SQLite local.
#     Database chính chưa bị thay đổi tại bước này.
#     """
#
#     def stage_file(
#         self,
#         excel_path: Path,
#     ) -> PrimeStageResult:
#         excel_path = Path(excel_path)
#
#         if not excel_path.exists():
#             raise FileNotFoundError(
#                 f"Không tìm thấy file: {excel_path}"
#             )
#
#         if excel_path.suffix.lower() != ".xlsx":
#             raise ValueError(
#                 "PRIME chỉ hỗ trợ file Excel .xlsx"
#             )
#
#         staging_path = self._create_staging_database()
#
#         try:
#             business_dates, row_count = self._read_and_stage(
#                 excel_path=excel_path,
#                 staging_path=staging_path,
#             )
#
#             return PrimeStageResult(
#                 staging_database_path=staging_path,
#                 business_dates=business_dates,
#                 row_count=row_count,
#             )
#
#         except Exception:
#             self.delete_staging_database(staging_path)
#             raise
#
#     def delete_staging_database(
#         self,
#         staging_path: Path,
#     ) -> None:
#         """Xóa database tạm sau khi import kết thúc."""
#
#         try:
#             if staging_path.exists():
#                 staging_path.unlink()
#
#         except OSError:
#             pass
#
#     def _read_and_stage(
#         self,
#         excel_path: Path,
#         staging_path: Path,
#     ) -> tuple[set[str], int]:
#         # Chỉ import openpyxl khi người dùng thực sự bấm Import PRIME.
#         # Tránh làm app chậm lúc mới mở.
#         from openpyxl import load_workbook
#         connection = sqlite3.connect(staging_path)
#
#         try:
#             self._create_staging_table(connection)
#
#             workbook = load_workbook(
#                 filename=excel_path,
#                 read_only=True,
#                 data_only=True,
#             )
#
#             worksheet = workbook.active
#
#             headers = self._get_headers(worksheet)
#
#             business_dates: set[str] = set()
#             insert_rows: list[tuple] = []
#             row_count = 0
#
#             for source_row, values in enumerate(
#                 worksheet.iter_rows(
#                     min_row=2,
#                     values_only=True,
#                 ),
#                 start=2,
#             ):
#                 if self._is_empty_row(values):
#                     continue
#
#                 record = self._normalize_row(
#                     source_row=source_row,
#                     values=values,
#                     headers=headers,
#                 )
#
#                 business_dates.add(record[0])
#                 insert_rows.append(record)
#                 row_count += 1
#
#                 if len(insert_rows) >= STAGING_INSERT_BATCH_SIZE:
#                     self._insert_staging_rows(
#                         connection,
#                         insert_rows,
#                     )
#                     insert_rows.clear()
#
#             if insert_rows:
#                 self._insert_staging_rows(
#                     connection,
#                     insert_rows,
#                 )
#
#             workbook.close()
#
#             if row_count == 0:
#                 raise ValueError(
#                     "File Excel không có dòng dữ liệu nào"
#                 )
#
#             connection.commit()
#
#             return business_dates, row_count
#
#         except Exception:
#             connection.rollback()
#             raise
#
#         finally:
#             connection.close()
#
#     def _get_headers(
#         self,
#         worksheet,
#     ) -> dict[str, int]:
#         header_row = next(
#             worksheet.iter_rows(
#                 min_row=1,
#                 max_row=1,
#                 values_only=True,
#             ),
#             None,
#         )
#
#         if header_row is None:
#             raise ValueError(
#                 "File Excel không có header"
#             )
#
#         headers: dict[str, int] = {}
#
#         for index, value in enumerate(header_row):
#             if value is None:
#                 continue
#
#             header_name = str(value).strip()
#             headers[header_name] = index
#
#         missing_columns = REQUIRED_COLUMNS - set(headers)
#
#         if missing_columns:
#             missing_text = ", ".join(
#                 sorted(missing_columns)
#             )
#
#             raise ValueError(
#                 "Thiếu cột bắt buộc: "
#                 f"{missing_text}"
#             )
#
#         return headers
#
#     def _normalize_row(
#         self,
#         source_row: int,
#         values: tuple,
#         headers: dict[str, int],
#     ) -> tuple:
#         file_name = self._required_text(
#             values,
#             headers,
#             "FileName",
#             source_row,
#         )
#
#         raw_date = self._required_value(
#             values,
#             headers,
#             "DATE",
#             source_row,
#         )
#
#         slot = self._required_integer(
#             values,
#             headers,
#             "SLOT",
#             source_row,
#         )
#
#         part_no = self._required_text(
#             values,
#             headers,
#             "PARTNO",
#             source_row,
#         )
#
#         lot_no = self._required_text(
#             values,
#             headers,
#             "LOTNO",
#             source_row,
#         )
#
#         interface = self._required_text(
#             values,
#             headers,
#             "INTERFACE",
#             source_row,
#         )
#
#         result = self._required_text(
#             values,
#             headers,
#             "RESULT",
#             source_row,
#         ).upper()
#
#         raw_scrap_code = self._get_value(
#             values,
#             headers,
#             "SCRAPCODE",
#         )
#
#         date_text = self._normalize_date(
#             raw_date,
#             source_row,
#         )
#
#         if len(file_name) < 7:
#             raise PrimeExcelValidationError(
#                 source_row,
#                 "FileName phải có ít nhất 7 ký tự",
#             )
#
#         if len(part_no) < 5:
#             raise PrimeExcelValidationError(
#                 source_row,
#                 "PARTNO phải có ít nhất 5 ký tự",
#             )
#
#         if result not in ("PASS", "FAIL"):
#             raise PrimeExcelValidationError(
#                 source_row,
#                 "RESULT chỉ được là PASS hoặc FAIL",
#             )
#
#         if not 1 <= slot <= 240:
#             raise PrimeExcelValidationError(
#                 source_row,
#                 "SLOT phải nằm trong khoảng 1 đến 240",
#             )
#
#         scrap_code = self._normalize_scrap_code(
#             result=result,
#             raw_scrap_code=raw_scrap_code,
#             source_row=source_row,
#         )
#
#         chamber = 1 if slot <= 120 else 2
#
#         business_date = date_text[:8]
#         time_text = (
#             f"{date_text[8:10]}:"
#             f"{date_text[10:12]}:"
#             f"{date_text[12:14]}"
#         )
#
#         eqp = file_name[:7]
#         model = part_no[:5]
#
#         return (
#             business_date,
#             time_text,
#             part_no,
#             lot_no,
#             interface,
#             result,
#             scrap_code,
#             eqp,
#             chamber,
#             slot,
#             model,
#         )
#
#     def _normalize_date(
#         self,
#         raw_value,
#         source_row: int,
#     ) -> str:
#         if isinstance(raw_value, datetime):
#             return raw_value.strftime(
#                 "%Y%m%d%H%M%S"
#             )
#
#         if isinstance(raw_value, int):
#             date_text = str(raw_value)
#
#         elif isinstance(raw_value, float):
#             if not raw_value.is_integer():
#                 raise PrimeExcelValidationError(
#                     source_row,
#                     "DATE không đúng định dạng YYYYMMDDHHMMSS",
#                 )
#
#             date_text = str(int(raw_value))
#
#         else:
#             date_text = str(raw_value).strip()
#
#         if (
#             len(date_text) != 14
#             or not date_text.isdigit()
#         ):
#             raise PrimeExcelValidationError(
#                 source_row,
#                 "DATE phải có dạng YYYYMMDDHHMMSS",
#             )
#
#         try:
#             datetime.strptime(
#                 date_text,
#                 "%Y%m%d%H%M%S",
#             )
#
#         except ValueError:
#             raise PrimeExcelValidationError(
#                 source_row,
#                 "DATE không phải ngày giờ hợp lệ",
#             )
#
#         return date_text
#
#     def _normalize_scrap_code(
#         self,
#         result: str,
#         raw_scrap_code,
#         source_row: int,
#     ) -> str:
#         # PASS luôn lưu rỗng, không lưu dấu "-".
#         if result == "PASS":
#             return ""
#
#         if raw_scrap_code is None:
#             return ""
#
#         if isinstance(raw_scrap_code, int):
#             return str(raw_scrap_code)
#
#         if isinstance(raw_scrap_code, float):
#             if raw_scrap_code.is_integer():
#                 return str(int(raw_scrap_code))
#
#             raise PrimeExcelValidationError(
#                 source_row,
#                 "SCRAPCODE phải là số hoặc để trống",
#             )
#
#         scrap_code = str(raw_scrap_code).strip()
#
#         if scrap_code in ("", "-"):
#             return ""
#
#         if not scrap_code.isdigit():
#             raise PrimeExcelValidationError(
#                 source_row,
#                 "SCRAPCODE phải là số hoặc để trống",
#             )
#
#         return scrap_code
#
#     @staticmethod
#     def _required_value(
#         values: tuple,
#         headers: dict[str, int],
#         column_name: str,
#         source_row: int,
#     ):
#         value = PrimeExcelReader._get_value(
#             values,
#             headers,
#             column_name,
#         )
#
#         if value is None or str(value).strip() == "":
#             raise PrimeExcelValidationError(
#                 source_row,
#                 f"Cột {column_name} không được để trống",
#             )
#
#         return value
#
#     @staticmethod
#     def _required_text(
#         values: tuple,
#         headers: dict[str, int],
#         column_name: str,
#         source_row: int,
#     ) -> str:
#         value = PrimeExcelReader._required_value(
#             values,
#             headers,
#             column_name,
#             source_row,
#         )
#
#         return str(value).strip()
#
#     @staticmethod
#     def _required_integer(
#         values: tuple,
#         headers: dict[str, int],
#         column_name: str,
#         source_row: int,
#     ) -> int:
#         value = PrimeExcelReader._required_value(
#             values,
#             headers,
#             column_name,
#             source_row,
#         )
#
#         if isinstance(value, int):
#             return value
#
#         if isinstance(value, float):
#             if value.is_integer():
#                 return int(value)
#
#             raise PrimeExcelValidationError(
#                 source_row,
#                 f"Cột {column_name} phải là số nguyên",
#             )
#
#         value_text = str(value).strip()
#
#         if not value_text.isdigit():
#             raise PrimeExcelValidationError(
#                 source_row,
#                 f"Cột {column_name} phải là số nguyên",
#             )
#
#         return int(value_text)
#
#     @staticmethod
#     def _get_value(
#         values: tuple,
#         headers: dict[str, int],
#         column_name: str,
#     ):
#         index = headers[column_name]
#
#         if index >= len(values):
#             return None
#
#         return values[index]
#
#     @staticmethod
#     def _is_empty_row(
#         values: tuple,
#     ) -> bool:
#         return all(
#             value is None
#             or str(value).strip() == ""
#             for value in values
#         )
#
#     @staticmethod
#     def _create_staging_table(
#         connection: sqlite3.Connection,
#     ) -> None:
#         connection.execute(
#             """
#             CREATE TABLE staging_prime_data (
#                 DATE TEXT NOT NULL,
#                 TIME TEXT NOT NULL,
#                 PARTNO TEXT NOT NULL,
#                 LOTNO TEXT NOT NULL,
#                 INTERFACE TEXT NOT NULL,
#                 RESULT TEXT NOT NULL,
#                 SCRAPCODE TEXT NOT NULL,
#                 EQP TEXT NOT NULL,
#                 Chamber INTEGER NOT NULL,
#                 Slot INTEGER NOT NULL,
#                 MODEL TEXT NOT NULL
#             )
#             """
#         )
#
#     @staticmethod
#     def _insert_staging_rows(
#         connection: sqlite3.Connection,
#         rows: list[tuple],
#     ) -> None:
#         connection.executemany(
#             """
#             INSERT INTO staging_prime_data (
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
#             )
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#             rows,
#         )
#
#     @staticmethod
#     def _create_staging_database() -> Path:
#         file_descriptor, file_path = tempfile.mkstemp(
#             prefix="aging_prime_",
#             suffix=".db",
#         )
#
#         os.close(file_descriptor)
#
#         return Path(file_path)