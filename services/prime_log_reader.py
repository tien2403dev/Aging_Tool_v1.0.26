# from __future__ import annotations
#
# import os
# import re
# import sqlite3
# import tempfile
#
# from dataclasses import dataclass
# from datetime import datetime
# from pathlib import Path
#
#
# STAGING_INSERT_BATCH_SIZE = 5_000
#
# class PrimeLogValidationError(Exception):
#     """Lỗi dữ liệu tại một dòng trong file log."""
#
#     def __init__(
#         self,
#         file_name: str,
#         source_row: int,
#         message: str,
#     ):
#         super().__init__(
#             f"File {file_name}, dòng {source_row}: {message}"
#         )
#
#
# @dataclass
# class PrimeLogStageResult:
#     staging_database_path: Path
#     business_dates: set[str]
#     row_count: int
#     file_count: int
#
#
# class PrimeLogReader:
#     """
#     Đọc log PRIME từ folder Get_Result_History.
#
#     Chỉ duyệt theo cấu trúc:
#
#     Get_Result_History
#         /<folder máy chỉ gồm số>
#         /<folder con bất kỳ>
#         /YYYYMM
#         /*_ResultHistory_YYYYMMDD_*.txt
#     """
#
#     def stage_folder(
#         self,
#         root_folder: Path,
#         business_date: str,
#     ) -> PrimeLogStageResult:
#         """Tìm và đưa log của ngày đã chọn vào staging database."""
#
#         root_folder = Path(root_folder)
#
#         self._validate_root_folder(
#             root_folder
#         )
#
#         self._validate_business_date(
#             business_date
#         )
#
#         log_files = self._find_log_files(
#             root_folder=root_folder,
#             business_date=business_date,
#         )
#
#         if not log_files:
#             display_date = datetime.strptime(
#                 business_date,
#                 "%Y%m%d",
#             ).strftime(
#                 "%Y-%m-%d"
#             )
#
#             raise ValueError(
#                 "Không tìm thấy file log ngày "
#                 f"{display_date} trong folder đã chọn."
#             )
#
#         staging_path = (
#             self._create_staging_database()
#         )
#
#         try:
#             row_count = self._read_and_stage(
#                 log_files=log_files,
#                 business_date=business_date,
#                 staging_path=staging_path,
#             )
#
#             if row_count == 0:
#                 raise ValueError(
#                     "Các file log của ngày đã chọn đều rỗng, "
#                     "không có dữ liệu để import."
#                 )
#
#             return PrimeLogStageResult(
#                 staging_database_path=staging_path,
#                 business_dates={business_date},
#                 row_count=row_count,
#                 file_count=len(log_files),
#             )
#
#         except Exception:
#             self.delete_staging_database(
#                 staging_path
#             )
#             raise
#
#     def delete_staging_database(
#         self,
#         staging_path: Path,
#     ) -> None:
#         """Xóa database staging sau khi import."""
#
#         try:
#             if staging_path.exists():
#                 staging_path.unlink()
#
#         except OSError:
#             pass
#
#     @staticmethod
#     def _validate_root_folder(
#         root_folder: Path,
#     ) -> None:
#         """Kiểm tra folder người dùng đã chọn."""
#
#         if not root_folder.exists():
#             raise FileNotFoundError(
#                 f"Không tìm thấy folder: {root_folder}"
#             )
#
#         if not root_folder.is_dir():
#             raise ValueError(
#                 "Đường dẫn đã chọn không phải là folder."
#             )
#
#     @staticmethod
#     def _validate_business_date(
#         business_date: str,
#     ) -> None:
#         """Kiểm tra ngày import theo YYYYMMDD."""
#
#         if (
#             len(business_date) != 8
#             or not business_date.isascii()
#             or not business_date.isdigit()
#         ):
#             raise ValueError(
#                 "Ngày import phải có định dạng YYYYMMDD."
#             )
#
#         try:
#             datetime.strptime(
#                 business_date,
#                 "%Y%m%d",
#             )
#
#         except ValueError as error:
#             raise ValueError(
#                 "Ngày import không hợp lệ."
#             ) from error
#
#     def _find_log_files(
#             self,
#             root_folder: Path,
#             business_date: str,
#     ) -> list[Path]:
#         """
#         Tìm file log đúng ngày mà không quét đệ quy
#         toàn bộ ổ mạng.
#
#         Quy tắc:
#         - Folder máy phải có tên hoàn toàn bằng số.
#         - Duyệt tất cả folder con trực tiếp trong folder máy.
#         - Không phụ thuộc tên Chamber1, Chamber2, CB1, CB2...
#         - Chỉ truy cập folder tháng đúng với ngày đã chọn.
#         """
#
#         month_name = business_date[:6]
#
#         machine_folders: list[Path] = []
#         log_files: list[Path] = []
#
#         # Chỉ lấy folder máy có tên hoàn toàn bằng số:
#         # 701, 702, 903...
#         with os.scandir(
#                 root_folder
#         ) as machine_entries:
#             for machine_entry in machine_entries:
#                 if (
#                         machine_entry.name.isascii()
#                         and machine_entry.name.isdigit()
#                         and machine_entry.is_dir()
#                 ):
#                     machine_folders.append(
#                         Path(machine_entry.path)
#                     )
#
#         machine_folders.sort(
#             key=lambda path: path.name
#         )
#
#         for machine_folder in machine_folders:
#             child_folders: list[Path] = []
#
#             # Lấy tất cả folder con trực tiếp trong folder máy.
#             # Không kiểm tra tên Chamber1, Chamber2, CB1, CB2...
#             with os.scandir(
#                     machine_folder
#             ) as child_entries:
#                 for child_entry in child_entries:
#                     if child_entry.is_dir():
#                         child_folders.append(
#                             Path(child_entry.path)
#                         )
#
#             child_folders.sort(
#                 key=lambda path: path.name.lower()
#             )
#
#             for child_folder in child_folders:
#                 # Chỉ truy cập đúng folder tháng cần import.
#                 # Ví dụ chọn 2026-08-20 thì chỉ tìm 202608.
#                 month_folder = (
#                         child_folder
#                         / month_name
#                 )
#
#                 if not month_folder.is_dir():
#                     continue
#
#                 with os.scandir(
#                         month_folder
#                 ) as file_entries:
#                     for file_entry in file_entries:
#                         if not file_entry.is_file():
#                             continue
#
#                         if self._is_target_log_file(
#                                 file_name=file_entry.name,
#                                 business_date=business_date,
#                         ):
#                             log_files.append(
#                                 Path(file_entry.path)
#                             )
#
#         log_files.sort(
#             key=lambda path: str(path).lower()
#         )
#
#         return log_files
#
#     @staticmethod
#     def _is_target_log_file(
#             file_name: str,
#             business_date: str,
#     ) -> bool:
#         """Kiểm tra đúng file ResultHistory của ngày đã chọn."""
#
#         file_path = Path(file_name)
#
#         if file_path.suffix.lower() != ".txt":
#             return False
#
#         pattern = re.compile(
#             rf"^[^_]+_(?:[^_]+_)*ResultHistory_"
#             rf"{re.escape(business_date)}(?:_|$)",
#             re.IGNORECASE,
#         )
#
#         return (
#                 pattern.search(file_path.stem)
#                 is not None
#         )
#
#     def _read_and_stage(
#         self,
#         log_files: list[Path],
#         business_date: str,
#         staging_path: Path,
#     ) -> int:
#         """Đọc tuần tự từng file và insert staging theo batch."""
#
#         connection = sqlite3.connect(
#             staging_path
#         )
#
#         try:
#             self._create_staging_table(
#                 connection
#             )
#
#             insert_rows: list[tuple] = []
#             row_count = 0
#
#             for log_path in log_files:
#                 eqp = self._get_eqp_from_file_name(
#                     log_path
#                 )
#
#                 # Các log trong hình chỉ chứa ký tự ASCII,
#                 # vì vậy UTF-8 cũng đọc được file ANSI không dấu.
#                 with log_path.open(
#                     "r",
#                     encoding="utf-8-sig",
#                 ) as log_file:
#                     for source_row, raw_line in enumerate(
#                         log_file,
#                         start=1,
#                     ):
#                         line = raw_line.strip()
#
#                         if not line:
#                             continue
#
#                         # record = self._normalize_line(
#                         #     file_name=log_path.name,
#                         #     source_row=source_row,
#                         #     line=line,
#                         #     eqp=eqp,
#                         #     selected_date=business_date,
#                         # )
#                         record = self._normalize_line(
#                             file_name=log_path.name,
#                             source_row=source_row,
#                             line=line,
#                             eqp=eqp,
#                         )
#
#                         insert_rows.append(
#                             record
#                         )
#
#                         row_count += 1
#
#                         if (
#                             len(insert_rows)
#                             >= STAGING_INSERT_BATCH_SIZE
#                         ):
#                             self._insert_staging_rows(
#                                 connection,
#                                 insert_rows,
#                             )
#
#                             insert_rows.clear()
#
#             if insert_rows:
#                 self._insert_staging_rows(
#                     connection,
#                     insert_rows,
#                 )
#
#             # Tăng tốc so sánh dòng lệch ngày với database chính.
#             connection.execute(
#                 """
#                 CREATE INDEX idx_staging_prime_import_match
#                 ON staging_prime_data (
#                     DATE,
#                     EQP,
#                     TIME,
#                     Slot
#                 )
#                 """
#             )
#
#             connection.commit()
#
#             return row_count
#
#         except UnicodeDecodeError as error:
#             connection.rollback()
#
#             raise ValueError(
#                 "Không đọc được mã hóa của file log."
#             ) from error
#
#         except Exception:
#             connection.rollback()
#             raise
#
#         finally:
#             connection.close()
#
#     @staticmethod
#     def _get_eqp_from_file_name(
#             log_path: Path,
#     ) -> str:
#         """
#         Lấy tên máy từ phần đầu tiên của tên file,
#         phân cách bởi dấu "_".
#
#         Ví dụ:
#         AT-H902_1_ResultHistory_20260826_1.txt
#         -> AT-H902
#         """
#
#         eqp = log_path.stem.split(
#             "_",
#             1,
#         )[0].strip()
#
#         if not eqp:
#             raise ValueError(
#                 "Không lấy được EQP từ tên file: "
#                 f"{log_path.name}"
#             )
#
#         return eqp
#
#     def _normalize_line(
#             self,
#             file_name: str,
#             source_row: int,
#             line: str,
#             eqp: str,
#     ) -> tuple:
#         """
#         Phân tích một dòng log theo thứ tự:
#
#         DATE_TIME, SLOT, PARTNO, LOTNO,
#         INTERFACE, RESULT, SCRAPCODE.
#         """
#
#         columns = line.split()
#
#         # PASS thường chỉ có 6 cột vì không có scrap code.
#         if len(columns) not in (6, 7):
#             raise PrimeLogValidationError(
#                 file_name,
#                 source_row,
#                 "phải có 6 cột bắt buộc "
#                 "và tối đa 1 cột SCRAPCODE",
#             )
#
#         raw_date_time = columns[0]
#         slot_text = columns[1]
#         part_no = columns[2]
#         lot_no = columns[3]
#         interface = columns[4]
#         result = columns[5].upper()
#
#         raw_scrap_code = (
#             columns[6]
#             if len(columns) == 7
#             else ""
#         )
#
#         date_text = self._normalize_date_time(
#             raw_value=raw_date_time,
#             file_name=file_name,
#             source_row=source_row,
#         )
#
#         if (
#             not slot_text.isascii()
#             or not slot_text.isdigit()
#         ):
#             raise PrimeLogValidationError(
#                 file_name,
#                 source_row,
#                 "SLOT phải là số nguyên",
#             )
#
#         # int("079") trả về 79:
#         # tự động bỏ số 0 phía trước.
#         slot = int(slot_text)
#
#         if not 1 <= slot <= 240:
#             raise PrimeLogValidationError(
#                 file_name,
#                 source_row,
#                 "SLOT phải nằm trong khoảng 1 đến 240",
#             )
#
#         if len(part_no) < 5:
#             raise PrimeLogValidationError(
#                 file_name,
#                 source_row,
#                 "PARTNO phải có ít nhất 5 ký tự",
#             )
#
#         if result not in (
#             "PASS",
#             "FAIL",
#         ):
#             raise PrimeLogValidationError(
#                 file_name,
#                 source_row,
#                 "RESULT chỉ được là PASS hoặc FAIL",
#             )
#
#         scrap_code = self._normalize_scrap_code(
#             result=result,
#             raw_scrap_code=raw_scrap_code,
#             file_name=file_name,
#             source_row=source_row,
#         )
#
#         # Giữ nguyên cách xác định chamber hiện tại.
#         chamber = (
#             1
#             if slot <= 120
#             else 2
#         )
#
#         model = part_no[:5]
#
#         business_date = date_text[:8]
#
#         time_text = (
#             f"{date_text[8:10]}:"
#             f"{date_text[10:12]}:"
#             f"{date_text[12:14]}"
#         )
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
#     @staticmethod
#     def _normalize_date_time(
#         raw_value: str,
#         file_name: str,
#         source_row: int,
#     ) -> str:
#         """Kiểm tra DATE/TIME có dạng YYYYMMDDHHMMSS."""
#
#         if (
#             len(raw_value) != 14
#             or not raw_value.isascii()
#             or not raw_value.isdigit()
#         ):
#             raise PrimeLogValidationError(
#                 file_name,
#                 source_row,
#                 "DATE/TIME phải có dạng YYYYMMDDHHMMSS",
#             )
#
#         try:
#             datetime.strptime(
#                 raw_value,
#                 "%Y%m%d%H%M%S",
#             )
#
#         except ValueError as error:
#             raise PrimeLogValidationError(
#                 file_name,
#                 source_row,
#                 "DATE/TIME không hợp lệ",
#             ) from error
#
#         return raw_value
#
#     @staticmethod
#     def _normalize_scrap_code(
#         result: str,
#         raw_scrap_code: str,
#         file_name: str,
#         source_row: int,
#     ) -> str:
#         """Chuẩn hóa scrap code giống logic PRIME hiện tại."""
#
#         if result == "PASS":
#             return ""
#
#         scrap_code = raw_scrap_code.strip()
#
#         if scrap_code in (
#             "",
#             "-",
#         ):
#             return ""
#
#         if (
#             not scrap_code.isascii()
#             or not scrap_code.isdigit()
#         ):
#             raise PrimeLogValidationError(
#                 file_name,
#                 source_row,
#                 "SCRAPCODE phải là số hoặc để trống",
#             )
#
#         return scrap_code
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
#             prefix="aging_prime_log_",
#             suffix=".db",
#         )
#
#         os.close(
#             file_descriptor
#         )
#
#         return Path(file_path)




from __future__ import annotations

import os
import re
import sqlite3
import tempfile

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


STAGING_INSERT_BATCH_SIZE = 5_000

class PrimeLogValidationError(Exception):
    """Lỗi dữ liệu tại một dòng trong file log."""

    def __init__(
        self,
        file_name: str,
        source_row: int,
        message: str,
    ):
        super().__init__(
            f"File {file_name}, dòng {source_row}: {message}"
        )


@dataclass
class PrimeLogStageResult:
    staging_database_path: Path
    business_dates: set[str]
    row_count: int
    file_count: int


class PrimeLogReader:
    """
    Đọc log PRIME từ folder chứa log của tất cả máy.

    Chỉ duyệt theo cấu trúc:

    <folder log gốc>
        /AT-H701 CB1
        /ResultHistory_YYYYMMDD_*.txt
    """

    def stage_folder(
        self,
        root_folder: Path,
        business_date: str,
    ) -> PrimeLogStageResult:
        """Tìm và đưa log của ngày đã chọn vào staging database."""

        root_folder = Path(root_folder)

        self._validate_root_folder(
            root_folder
        )

        self._validate_business_date(
            business_date
        )

        log_files = self._find_log_files(
            root_folder=root_folder,
            business_date=business_date,
        )

        if not log_files:
            display_date = datetime.strptime(
                business_date,
                "%Y%m%d",
            ).strftime(
                "%Y-%m-%d"
            )

            raise ValueError(
                "Không tìm thấy file log ngày "
                f"{display_date} trong folder đã chọn."
            )

        staging_path = (
            self._create_staging_database()
        )

        try:
            row_count = self._read_and_stage(
                log_files=log_files,
                business_date=business_date,
                staging_path=staging_path,
            )

            if row_count == 0:
                raise ValueError(
                    "Các file log của ngày đã chọn đều rỗng, "
                    "không có dữ liệu để import."
                )

            return PrimeLogStageResult(
                staging_database_path=staging_path,
                business_dates={business_date},
                row_count=row_count,
                file_count=len(log_files),
            )

        except Exception:
            self.delete_staging_database(
                staging_path
            )
            raise

    def delete_staging_database(
        self,
        staging_path: Path,
    ) -> None:
        """Xóa database staging sau khi import."""

        try:
            if staging_path.exists():
                staging_path.unlink()

        except OSError:
            pass

    @staticmethod
    def _validate_root_folder(
        root_folder: Path,
    ) -> None:
        """Kiểm tra folder người dùng đã chọn."""

        if not root_folder.exists():
            raise FileNotFoundError(
                f"Không tìm thấy folder: {root_folder}"
            )

        if not root_folder.is_dir():
            raise ValueError(
                "Đường dẫn đã chọn không phải là folder."
            )

    @staticmethod
    def _validate_business_date(
        business_date: str,
    ) -> None:
        """Kiểm tra ngày import theo YYYYMMDD."""

        if (
            len(business_date) != 8
            or not business_date.isascii()
            or not business_date.isdigit()
        ):
            raise ValueError(
                "Ngày import phải có định dạng YYYYMMDD."
            )

        try:
            datetime.strptime(
                business_date,
                "%Y%m%d",
            )

        except ValueError as error:
            raise ValueError(
                "Ngày import không hợp lệ."
            ) from error

    def _find_log_files(
            self,
            root_folder: Path,
            business_date: str,
    ) -> list[Path]:
        """
        Tìm file log đúng ngày trong từng folder máy/chamber.

        Quy tắc:
        - Chỉ duyệt các folder con trực tiếp của folder gốc.
        - File TXT nằm trực tiếp trong từng folder con.
        - Ngày trong tên file phải đúng với ngày cần import.
        - Folder không có file của ngày cần import sẽ được bỏ qua.
        """

        log_folders: list[Path] = []
        log_files: list[Path] = []

        with os.scandir(
                root_folder
        ) as folder_entries:
            for folder_entry in folder_entries:
                if folder_entry.is_dir():
                    log_folders.append(
                        Path(folder_entry.path)
                    )

        log_folders.sort(
            key=lambda path: path.name.lower()
        )

        for log_folder in log_folders:
            with os.scandir(
                    log_folder
            ) as file_entries:
                for file_entry in file_entries:
                    if not file_entry.is_file():
                        continue

                    if self._is_target_log_file(
                            file_name=file_entry.name,
                            business_date=business_date,
                    ):
                        log_files.append(
                            Path(file_entry.path)
                        )

        log_files.sort(
            key=lambda path: str(path).lower()
        )

        return log_files

    @staticmethod
    def _is_target_log_file(
            file_name: str,
            business_date: str,
    ) -> bool:
        """Trích xuất và kiểm tra ngày trong tên file ResultHistory."""

        file_path = Path(file_name)

        if file_path.suffix.lower() != ".txt":
            return False

        pattern = re.compile(
            r"^ResultHistory_(\d{8})(?:_|$)",
            re.IGNORECASE,
        )

        match = pattern.search(file_path.stem)

        return (
            match is not None
            and match.group(1) == business_date
        )

    def _read_and_stage(
        self,
        log_files: list[Path],
        business_date: str,
        staging_path: Path,
    ) -> int:
        """Đọc tuần tự từng file và insert staging theo batch."""

        connection = sqlite3.connect(
            staging_path
        )

        try:
            self._create_staging_table(
                connection
            )

            insert_rows: list[tuple] = []
            row_count = 0

            for log_path in log_files:
                eqp = self._get_eqp_from_folder_name(
                    log_path
                )

                # Các log trong hình chỉ chứa ký tự ASCII,
                # vì vậy UTF-8 cũng đọc được file ANSI không dấu.
                with log_path.open(
                    "r",
                    encoding="utf-8-sig",
                ) as log_file:
                    for source_row, raw_line in enumerate(
                        log_file,
                        start=1,
                    ):
                        line = raw_line.strip()

                        if not line:
                            continue

                        # record = self._normalize_line(
                        #     file_name=log_path.name,
                        #     source_row=source_row,
                        #     line=line,
                        #     eqp=eqp,
                        #     selected_date=business_date,
                        # )
                        record = self._normalize_line(
                            file_name=log_path.name,
                            source_row=source_row,
                            line=line,
                            eqp=eqp,
                        )

                        insert_rows.append(
                            record
                        )

                        row_count += 1

                        if (
                            len(insert_rows)
                            >= STAGING_INSERT_BATCH_SIZE
                        ):
                            self._insert_staging_rows(
                                connection,
                                insert_rows,
                            )

                            insert_rows.clear()

            if insert_rows:
                self._insert_staging_rows(
                    connection,
                    insert_rows,
                )

            # Tăng tốc so sánh dòng lệch ngày với database chính.
            connection.execute(
                """
                CREATE INDEX idx_staging_prime_import_match
                ON staging_prime_data (
                    DATE,
                    EQP,
                    TIME,
                    Slot
                )
                """
            )

            connection.commit()

            return row_count

        except UnicodeDecodeError as error:
            connection.rollback()

            raise ValueError(
                "Không đọc được mã hóa của file log."
            ) from error

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    @staticmethod
    def _get_eqp_from_folder_name(
            log_path: Path,
    ) -> str:
        """
        Lấy 7 ký tự đầu tiên trong tên folder chứa file log.

        Ví dụ:
        AT-H701 CB1/ResultHistory_20260908_1.txt
        -> AT-H701.
        """

        folder_name = log_path.parent.name.strip()
        eqp = folder_name[:7].strip()

        if len(eqp) != 7:
            raise ValueError(
                "Không lấy được 7 ký tự tên EQP từ folder: "
                f"{folder_name}"
            )

        return eqp

    def _normalize_line(
            self,
            file_name: str,
            source_row: int,
            line: str,
            eqp: str,
    ) -> tuple:
        """
        Phân tích một dòng log theo thứ tự:

        DATE_TIME, SLOT, PARTNO, LOTNO,
        INTERFACE, RESULT, SCRAPCODE.
        """

        columns = line.split()

        # PASS thường chỉ có 6 cột vì không có scrap code.
        if len(columns) not in (6, 7):
            raise PrimeLogValidationError(
                file_name,
                source_row,
                "phải có 6 cột bắt buộc "
                "và tối đa 1 cột SCRAPCODE",
            )

        raw_date_time = columns[0]
        slot_text = columns[1]
        part_no = columns[2]
        lot_no = columns[3]
        interface = columns[4]
        result = columns[5].upper()

        raw_scrap_code = (
            columns[6]
            if len(columns) == 7
            else ""
        )

        date_text = self._normalize_date_time(
            raw_value=raw_date_time,
            file_name=file_name,
            source_row=source_row,
        )

        if (
            not slot_text.isascii()
            or not slot_text.isdigit()
        ):
            raise PrimeLogValidationError(
                file_name,
                source_row,
                "SLOT phải là số nguyên",
            )

        # int("079") trả về 79:
        # tự động bỏ số 0 phía trước.
        slot = int(slot_text)

        if not 1 <= slot <= 240:
            raise PrimeLogValidationError(
                file_name,
                source_row,
                "SLOT phải nằm trong khoảng 1 đến 240",
            )

        if len(part_no) < 5:
            raise PrimeLogValidationError(
                file_name,
                source_row,
                "PARTNO phải có ít nhất 5 ký tự",
            )

        if result not in (
            "PASS",
            "FAIL",
        ):
            raise PrimeLogValidationError(
                file_name,
                source_row,
                "RESULT chỉ được là PASS hoặc FAIL",
            )

        scrap_code = self._normalize_scrap_code(
            result=result,
            raw_scrap_code=raw_scrap_code,
            file_name=file_name,
            source_row=source_row,
        )

        # Giữ nguyên cách xác định chamber hiện tại.
        chamber = (
            1
            if slot <= 120
            else 2
        )

        model = part_no[:5]

        business_date = date_text[:8]

        time_text = (
            f"{date_text[8:10]}:"
            f"{date_text[10:12]}:"
            f"{date_text[12:14]}"
        )

        return (
            business_date,
            time_text,
            part_no,
            lot_no,
            interface,
            result,
            scrap_code,
            eqp,
            chamber,
            slot,
            model,
        )

    @staticmethod
    def _normalize_date_time(
        raw_value: str,
        file_name: str,
        source_row: int,
    ) -> str:
        """Kiểm tra DATE/TIME có dạng YYYYMMDDHHMMSS."""

        if (
            len(raw_value) != 14
            or not raw_value.isascii()
            or not raw_value.isdigit()
        ):
            raise PrimeLogValidationError(
                file_name,
                source_row,
                "DATE/TIME phải có dạng YYYYMMDDHHMMSS",
            )

        try:
            datetime.strptime(
                raw_value,
                "%Y%m%d%H%M%S",
            )

        except ValueError as error:
            raise PrimeLogValidationError(
                file_name,
                source_row,
                "DATE/TIME không hợp lệ",
            ) from error

        return raw_value

    @staticmethod
    def _normalize_scrap_code(
        result: str,
        raw_scrap_code: str,
        file_name: str,
        source_row: int,
    ) -> str:
        """Chuẩn hóa scrap code giống logic PRIME hiện tại."""

        if result == "PASS":
            return ""

        scrap_code = raw_scrap_code.strip()

        if scrap_code in (
            "",
            "-",
        ):
            return ""

        if (
            not scrap_code.isascii()
            or not scrap_code.isdigit()
        ):
            raise PrimeLogValidationError(
                file_name,
                source_row,
                "SCRAPCODE phải là số hoặc để trống",
            )

        return scrap_code

    @staticmethod
    def _create_staging_table(
        connection: sqlite3.Connection,
    ) -> None:
        connection.execute(
            """
            CREATE TABLE staging_prime_data (
                DATE TEXT NOT NULL,
                TIME TEXT NOT NULL,
                PARTNO TEXT NOT NULL,
                LOTNO TEXT NOT NULL,
                INTERFACE TEXT NOT NULL,
                RESULT TEXT NOT NULL,
                SCRAPCODE TEXT NOT NULL,
                EQP TEXT NOT NULL,
                Chamber INTEGER NOT NULL,
                Slot INTEGER NOT NULL,
                MODEL TEXT NOT NULL
            )
            """
        )

    @staticmethod
    def _insert_staging_rows(
        connection: sqlite3.Connection,
        rows: list[tuple],
    ) -> None:
        connection.executemany(
            """
            INSERT INTO staging_prime_data (
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

    @staticmethod
    def _create_staging_database() -> Path:
        file_descriptor, file_path = tempfile.mkstemp(
            prefix="aging_prime_log_",
            suffix=".db",
        )

        os.close(
            file_descriptor
        )

        return Path(file_path)
