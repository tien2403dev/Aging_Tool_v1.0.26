from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


DATE_RE = re.compile(r"(?<!\d)(20\d{6})(?!\d)")

DEFAULT_TARGET_15 = 95.0
DEFAULT_TARGET_30 = 95.0


@dataclass
class TestRecord:
    machine: str
    date: str
    time: str
    slot: int
    result: str
    partno: str
    lotno: str
    interface: str
    scrapcode: str
    file_name: str
    file_path: str
    model: str = ""
    line_number: int = 0


@dataclass
class SlotSummary:
    machine: str
    slot: int

    test_count: int
    pass_count: int
    fail_count: int

    yield_percent: float | None

    last15_yield: float | None
    last30_yield: float | None

    target_15: float
    target_30: float

    status_15: str
    status_30: str
    status: str

    alarm15: bool
    alarm30: bool


@dataclass
class DailySummary:
    machine: str
    date: str
    slot: int
    test_count: int
    pass_count: int
    fail_count: int
    yield_percent: float | None


@dataclass
class MachineSlotResult:
    date_from: str
    date_to: str
    records: list[TestRecord]
    summaries: list[SlotSummary]
    daily: list[DailySummary]

    target_15: float
    target_30: float
    target_15_model: float | None = None
    target_30_model: float | None = None
    latest_tests: dict | None = None
    loaded_machines: list[str] = field(default_factory=list)
    alarm_events: dict = field(default_factory=dict)


class MachineSlotYieldRepository:
    """
    Đọc trực tiếp PRIME ResultHistory TXT từ Log Folder.

    Machine Slot Yield có:
        - Target riêng
        - Log Folder riêng

    File cấu hình:

        machine_slot_targets.json
        machine_slot_log_folder.json

    Hai file này nằm cùng thư mục với database.

    Nếu machine_slot_log_folder.json chưa tồn tại,
    giao diện sẽ lấy Log Folder từ File Management làm mặc định.
    """

    def __init__(
        self,
        target_path: str | Path,
    ):
        self.target_path = Path(
            target_path
        )

        self.log_folder_path = (
            self.target_path.parent
            / "machine_slot_log_folder.json"
        )

    # ============================================================
    # LOG FOLDER
    # ============================================================

    def load_log_folder(self) -> str:
        """
        Đọc Log Folder riêng của Machine Slot Yield.

        Nếu chưa từng lưu:
            return ""

        Khi return "":
            UI sẽ fallback sang Log Folder
            trong File Management.
        """

        if not self.log_folder_path.exists():
            return ""

        try:

            data = json.loads(
                self.log_folder_path.read_text(
                    encoding="utf-8"
                )
            )

            log_folder = str(
                data.get(
                    "log_folder",
                    "",
                )
            ).strip()

            return log_folder

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):

            return ""

    def save_log_folder(
        self,
        log_folder: str | Path,
    ) -> None:
        """
        Lưu Log Folder riêng cho Machine Slot Yield.
        """

        log_folder = str(
            log_folder
        ).strip()

        if not log_folder:

            raise ValueError(
                "Log Folder không được để trống."
            )

        folder = Path(
            log_folder
        )

        if not folder.exists():

            raise ValueError(
                f"Không tìm thấy Log Folder:\n{folder}"
            )

        if not folder.is_dir():

            raise ValueError(
                f"Đường dẫn không phải Folder:\n{folder}"
            )

        self.log_folder_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.log_folder_path.write_text(
            json.dumps(
                {
                    "log_folder": str(
                        folder
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def clear_log_folder(self) -> None:
        """
        Xóa Log Folder riêng.

        Sau khi xóa, Machine Slot Yield
        sẽ quay lại dùng Log Folder
        trong File Management.
        """

        if self.log_folder_path.exists():

            try:
                self.log_folder_path.unlink()

            except OSError as error:

                raise ValueError(
                    f"Không thể xóa cấu hình Log Folder:\n{error}"
                )

    # ============================================================
    # MACHINE
    # ============================================================

    def list_machines(
        self,
        log_root: str | Path,
    ) -> list[str]:

        root = Path(
            log_root
        )

        if not root.is_dir():
            return []

        return sorted(
            [
                p.name
                for p in root.iterdir()
                if p.is_dir()
            ],
            key=str.casefold,
        )

    # ============================================================
    # LOAD
    # ============================================================

    def load(
        self,
        log_root: str | Path,
        date_from: str,
        date_to: str,
        machine: str | None = None,
        last_days: int | None = None,
        include_latest_tests: bool = True,
    ) -> MachineSlotResult:

        root = Path(
            log_root
        )

        if not root.is_dir():

            raise ValueError(
                f"Không tìm thấy Log Folder:\n{root}"
            )

        start = datetime.strptime(
            date_from,
            "%Y%m%d",
        ).date()

        end = datetime.strptime(
            date_to,
            "%Y%m%d",
        ).date()

        if start > end:

            raise ValueError(
                "Ngày From không được lớn hơn ngày To."
            )

        # --------------------------------------------------------
        # Last N days
        # --------------------------------------------------------

        if last_days is not None:

            if not 1 <= last_days <= 30:

                raise ValueError(
                    "Số ngày gần nhất phải từ 1 đến 30."
                )

            end = date.today()

            start = (
                end
                - timedelta(
                    days=last_days - 1
                )
            )

            date_from = start.strftime(
                "%Y%m%d"
            )

            date_to = end.strftime(
                "%Y%m%d"
            )

        # --------------------------------------------------------
        # Machine
        # --------------------------------------------------------

        machine_names = (
            [machine]
            if machine and machine != "ALL"
            else self.list_machines(root)
        )

        if not machine_names:

            raise ValueError(
                "Không tìm thấy folder máy trong Log Folder."
            )

        # --------------------------------------------------------
        # Read TXT
        # --------------------------------------------------------

        records: list[TestRecord] = []
        latest_tests = {}
        from services.machine_alarm_rules import sort_key
        now = datetime.now().strftime("%Y%m%d %H:%M:%S")
        loaded_machines = []
        for machine_name in machine_names:
            machine_root = root / machine_name
            if not machine_root.is_dir():
                continue
            loaded_machines.append(machine_name)
            files_by_day = defaultdict(list)
            for path in self._find_txt_files(machine_root):
                file_date = self._date_from_filename(path.name)
                if file_date:
                    files_by_day[file_date].append(path)
            selected_records = []
            parsed = {}
            for file_day in sorted(files_by_day):
                if not date_from <= file_day <= date_to:
                    continue
                for path in files_by_day[file_day]:
                    rows = self._read_file(path, machine_name, file_day)
                    parsed[path] = rows
                    selected_records.extend(r for r in rows if date_from <= r.date <= date_to)
            records.extend(selected_records)
            if not include_latest_tests:
                continue
            # As in v0 history: daily log names determine which files to read.
            # Only slots in the selected data can produce new alarms. Scan
            # newest days first, all files of a day, and stop once they have 5.
            pending = {r.slot for r in selected_records}
            for file_day in sorted(files_by_day, reverse=True):
                if not pending:
                    break
                if file_day > now[:8]:
                    continue
                day_rows = defaultdict(list)
                for path in files_by_day[file_day]:
                    rows = parsed.get(path)
                    if rows is None:
                        rows = self._read_file(path, machine_name, file_day)
                    for record in rows:
                        if record.slot in pending and f"{record.date} {record.time}" <= now:
                            day_rows[record.slot].append(record)
                for slot, rows in day_rows.items():
                    key = (machine_name, slot)
                    recent = latest_tests.setdefault(key, [])
                    recent.extend(rows)
                    recent.sort(key=sort_key)
                    del recent[:-5]
                pending = {slot for slot in pending
                           if len(latest_tests.get((machine_name, slot), [])) < 5}

        # --------------------------------------------------------
        # Final date filter
        # --------------------------------------------------------

        records = [
            r
            for r in records
            if (
                date_from
                <= r.date
                <= date_to
            )
        ]

        # --------------------------------------------------------
        # Sort
        # --------------------------------------------------------

        records.sort(
            key=lambda r: (
                r.machine.casefold(),
                r.slot,
                r.date,
                r.time,
                r.file_name,
            )
        )

        # --------------------------------------------------------
        # Targets
        # --------------------------------------------------------

        target_15, target_30, target_15_model, target_30_model = self.load_all_targets()

        # --------------------------------------------------------
        # Group
        # --------------------------------------------------------

        grouped: dict[
            tuple[str, int],
            list[TestRecord],
        ] = defaultdict(list)

        daily_grouped: dict[
            tuple[str, str, int],
            list[TestRecord],
        ] = defaultdict(list)

        for record in records:

            grouped[
                (
                    record.machine,
                    record.slot,
                )
            ].append(record)

            daily_grouped[
                (
                    record.machine,
                    record.date,
                    record.slot,
                )
            ].append(record)

        # --------------------------------------------------------
        # Slot Summary
        # --------------------------------------------------------

        summaries: list[SlotSummary] = []

        for (
            machine_name,
            slot,
        ), rows in sorted(
            grouped.items(),
            key=lambda x: (
                x[0][0].casefold(),
                x[0][1],
            ),
        ):

            total = len(rows)

            passed = sum(
                r.result == "PASS"
                for r in rows
            )

            failed = (
                total - passed
            )

            last15 = rows[-15:]
            last30 = rows[-30:]

            yield_all = self._yield(
                rows
            )

            yield_15 = self._yield(last15) if len(last15) == 15 else None

            yield_30 = self._yield(last30) if len(last30) == 30 else None

            status_15 = (
                self._get_status(
                    yield_15,
                    target_15,
                )
            )

            status_30 = (
                self._get_status(
                    yield_30,
                    target_30,
                )
            )

            if (
                status_15
                == "Hiệu suất không đạt"
                or
                status_30
                == "Hiệu suất không đạt"
            ):

                overall_status = (
                    "Hiệu suất không đạt"
                )

            elif (
                status_15 == "N/A"
                and status_30 == "N/A"
            ):

                overall_status = "N/A"

            else:

                overall_status = "PASS"

            summaries.append(
                SlotSummary(
                    machine=machine_name,
                    slot=slot,

                    test_count=total,
                    pass_count=passed,
                    fail_count=failed,

                    yield_percent=yield_all,

                    last15_yield=yield_15,
                    last30_yield=yield_30,

                    target_15=target_15,
                    target_30=target_30,

                    status_15=status_15,
                    status_30=status_30,
                    status=overall_status,

                    alarm15=(
                        status_15
                        == "Hiệu suất không đạt"
                    ),

                    alarm30=(
                        status_30
                        == "Hiệu suất không đạt"
                    ),
                )
            )

        # --------------------------------------------------------
        # Daily
        # --------------------------------------------------------

        daily: list[DailySummary] = []

        for (
            machine_name,
            data_date,
            slot,
        ), rows in sorted(
            daily_grouped.items(),
            key=lambda x: (
                x[0][0].casefold(),
                x[0][1],
                x[0][2],
            ),
        ):

            total = len(rows)

            passed = sum(
                r.result == "PASS"
                for r in rows
            )

            daily.append(
                DailySummary(
                    machine=machine_name,
                    date=data_date,
                    slot=slot,
                    test_count=total,
                    pass_count=passed,
                    fail_count=(
                        total - passed
                    ),
                    yield_percent=self._yield(
                        rows
                    ),
                )
            )

        return MachineSlotResult(
            date_from=date_from,
            date_to=date_to,
            records=records,
            summaries=summaries,
            daily=daily,
            target_15=target_15,
            target_30=target_30,
            target_15_model=target_15_model, target_30_model=target_30_model,
            latest_tests=latest_tests if include_latest_tests else None,
            loaded_machines=loaded_machines,
        )

    # ============================================================
    # STATUS
    # ============================================================

    @staticmethod
    def _get_status(
        yield_value: float | None,
        target: float,
    ) -> str:

        if yield_value is None:
            return "N/A"

        if yield_value < target:
            return "Hiệu suất không đạt"

        return "PASS"

    # ============================================================
    # YIELD
    # ============================================================

    @staticmethod
    def _yield(
        rows: Iterable[TestRecord],
    ) -> float | None:

        rows = list(rows)

        if not rows:
            return None

        return (
            sum(
                r.result == "PASS"
                for r in rows
            )
            / len(rows)
            * 100.0
        )

    # ============================================================
    # FIND TXT
    # ============================================================

    @staticmethod
    def _find_txt_files(
        machine_root: Path,
    ) -> list[Path]:

        return sorted(
            (
                p
                for p in machine_root.rglob(
                    "*.txt"
                )
                if p.is_file()
            ),
            key=lambda p: str(p).casefold(),
        )

    # ============================================================
    # DATE FROM FILE NAME
    # ============================================================

    @staticmethod
    def _date_from_filename(
        file_name: str,
    ) -> str | None:

        match = DATE_RE.search(
            file_name
        )

        if not match:
            return None

        return match.group(1)

    # ============================================================
    # READ FILE
    # ============================================================

    @staticmethod
    def _read_file(
        path: Path,
        machine: str,
        fallback_date: str,
    ) -> list[TestRecord]:

        records: list[TestRecord] = []

        encodings = (
            "utf-8-sig",
            "cp1252",
            "latin-1",
        )

        last_error: Exception | None = None

        for encoding in encodings:

            records = []  # Discard partial rows before retrying another encoding.
            try:

                with path.open(
                    "r",
                    encoding=encoding,
                    errors="strict",
                ) as f:

                    for line_number, raw in enumerate(f, 1):

                        line = raw.strip()

                        if not line:
                            continue

                        record = (
                            MachineSlotYieldRepository
                            ._parse_line(
                                line,
                                machine,
                                path.name,
                                str(path),
                                fallback_date,
                            )
                        )

                        if record is not None:
                            record.line_number = line_number
                            records.append(record)

                return records

            except UnicodeDecodeError as exc:

                last_error = exc
                continue

            except OSError as exc:

                last_error = exc
                break

        if last_error:

            raise ValueError(
                f"Không đọc được file {path}: "
                f"{last_error}"
            )

        return records

    # ============================================================
    # PARSE LINE
    # ============================================================

    @staticmethod
    def _parse_line(
        line: str,
        machine: str,
        file_name: str,
        file_path: str,
        fallback_date: str,
    ) -> TestRecord | None:

        cols = line.split()

        if len(cols) < 6:
            return None

        raw_datetime = cols[0]
        slot_text = cols[1]
        result = cols[5].upper()

        if not slot_text.isdigit():
            return None

        slot = int(slot_text)

        if not 1 <= slot <= 240:
            return None

        if result not in (
            "PASS",
            "FAIL",
        ):
            return None

        data_date = fallback_date
        data_time = "00:00:00"

        # --------------------------------------------------------
        # YYYYMMDDHHMMSS
        # --------------------------------------------------------

        if (
            raw_datetime.isdigit()
            and len(raw_datetime) == 14
        ):

            data_date = raw_datetime[:8]

            data_time = (
                f"{raw_datetime[8:10]}:"
                f"{raw_datetime[10:12]}:"
                f"{raw_datetime[12:14]}"
            )

        # --------------------------------------------------------
        # YYYYMMDD_HH:MM:SS
        # --------------------------------------------------------

        elif "_" in raw_datetime:

            maybe_date, maybe_time = (
                raw_datetime.split(
                    "_",
                    1,
                )
            )

            if (
                maybe_date.isdigit()
                and len(maybe_date) == 8
            ):

                data_date = maybe_date

            if maybe_time:
                data_time = maybe_time[:8]

        # --------------------------------------------------------
        # YYYYMMDD
        # --------------------------------------------------------

        elif (
            raw_datetime.isdigit()
            and len(raw_datetime) == 8
        ):

            data_date = raw_datetime

        return TestRecord(
            machine=machine,
            date=data_date,
            time=data_time,
            slot=slot,
            result=result,
            partno=(
                cols[2]
                if len(cols) > 2
                else ""
            ),
            lotno=(
                cols[3]
                if len(cols) > 3
                else ""
            ),
            interface=(
                cols[4]
                if len(cols) > 4
                else ""
            ),
            scrapcode=(
                cols[6]
                if len(cols) > 6
                else ""
            ),
            file_name=file_name,
            file_path=file_path,
            model=cols[2].strip()[:5].upper(),
        )

    # ============================================================
    # RECENT TEST HISTORY
    # ============================================================

    def load_recent_tests(
        self,
        log_root: str | Path,
        machine: str,
        slot: int,
        limit: int = 30,
    ) -> list[TestRecord]:
        """
        Lấy N lần test gần nhất của một Machine + Slot.

        Không giới hạn theo khoảng From/To của Alarm; dữ liệu được lấy
        trực tiếp từ Log Test để khi double-click Alarm có thể xem lịch sử
        test gần nhất của đúng Slot đó.
        """

        root = Path(log_root)
        machine_name = str(machine or "").strip()

        if not root.is_dir():
            raise ValueError(
                f"Không tìm thấy Log Folder:\n{root}"
            )

        if not machine_name:
            return []

        try:
            slot_number = int(slot)
        except (TypeError, ValueError):
            return []

        if limit <= 0:
            return []

        machine_root = root / machine_name
        if not machine_root.is_dir():
            return []

        files = []
        for path in self._find_txt_files(machine_root):
            file_date = self._date_from_filename(path.name)
            if file_date:
                files.append((file_date, path))

        # Đọc file mới nhất trước. Sau đó vẫn sort lại theo timestamp để
        # bảo đảm thứ tự chính xác nếu một file chứa nhiều bản ghi.
        files.sort(
            key=lambda item: (item[0], item[1].name),
            reverse=True,
        )

        records: list[TestRecord] = []

        for file_date, path in files:
            file_records = self._read_file(
                path,
                machine_name,
                file_date,
            )

            for record in file_records:
                if record.slot == slot_number:
                    records.append(record)

            # Nếu đã đủ số lượng thì không cần đọc các file cũ hơn.
            if len(records) >= limit:
                break

        records.sort(
            key=lambda r: (
                r.date,
                r.time,
                r.file_name,
            ),
            reverse=True,
        )

        return records[:limit]

    # ============================================================
    # LOAD TARGETS
    # ============================================================

    def load_targets(
        self,
    ) -> tuple[float, float]:

        if not self.target_path.exists():

            return (
                DEFAULT_TARGET_15,
                DEFAULT_TARGET_30,
            )

        try:

            data = json.loads(
                self.target_path.read_text(
                    encoding="utf-8"
                )
            )

            target_15 = float(
                data.get(
                    "target_15",
                    DEFAULT_TARGET_15,
                )
            )

            target_30 = float(
                data.get(
                    "target_30",
                    DEFAULT_TARGET_30,
                )
            )

            target_15 = max(
                0.0,
                min(100.0, target_15),
            )

            target_30 = max(
                0.0,
                min(100.0, target_30),
            )

            return (
                target_15,
                target_30,
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):

            return (
                DEFAULT_TARGET_15,
                DEFAULT_TARGET_30,
            )

    # ============================================================
    # SAVE TARGETS
    # ============================================================

    def load_all_targets(self):
        old15, old30 = self.load_targets()
        try:
            data = json.loads(self.target_path.read_text(encoding="utf-8"))
            new15 = float(data.get("target_15_model", old15))
            new30 = float(data.get("target_30_model", old30))
            if not (0 <= new15 <= 100 and 0 <= new30 <= 100):
                raise ValueError("Target không hợp lệ")
        except (OSError, ValueError, TypeError):
            new15, new30 = old15, old30
        return old15, old30, new15, new30

    def save_targets(self, target_15, target_30, target_15_model=None, target_30_model=None):
        current = self.load_all_targets()
        values = [float(target_15), float(target_30),
                  float(current[2] if target_15_model is None else target_15_model),
                  float(current[3] if target_30_model is None else target_30_model)]
        if not all(0 <= v <= 100 for v in values):
            raise ValueError("Target phải từ 0 đến 100%.")
        keys = ("target_15", "target_30", "target_15_model", "target_30_model")
        try:
            data = json.loads(self.target_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        data.update(dict(zip(keys, (round(v, 4) for v in values))))
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.target_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.target_path)
