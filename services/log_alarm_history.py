"""Rebuild an Alarm row's rule windows directly from PRIME log files on click.

No test history is persisted. A historical consecutive FAIL is checked at its
saved Start/End rather than against today's five-day creation horizon.
"""
from collections import defaultdict, OrderedDict
import fnmatch
import os
from threading import RLock
from datetime import datetime
from pathlib import Path

from repositories.machine_slot_yield_repository import MachineSlotYieldRepository
from services.machine_alarm_rules import (
    evaluate_slot, evidence, is_pass, model_of, sort_key,
)


# Shared RAM cache only. Never persist test records or alarm windows.
# Bound both entries and records so large log folders do not fill RAM.
_FILE_CACHE = OrderedDict()
_CACHE_LOCK = RLock()
_CACHE_RECORDS = 0
_MAX_CACHE_FILES = 128
_MAX_CACHE_RECORDS = 100_000


def _signature(path):
    stat = path.stat()
    return (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns,
            stat.st_dev, stat.st_ino)


class _HistoryReader:
    """Fresh file listing per click; reuse unchanged parsed files across clicks."""

    _date_from_filename = staticmethod(MachineSlotYieldRepository._date_from_filename)

    def __init__(self, slot):
        self.slot = slot
        self._files = None

    def _find_txt_files(self, machine_root):
        if self._files is None:
            files = []
            pending = [machine_root]
            while pending:
                directory = pending.pop()
                try:
                    with os.scandir(directory) as entries:
                        for entry in entries:
                            if entry.is_dir(follow_symlinks=False):
                                pending.append(Path(entry.path))
                            elif (fnmatch.fnmatch(entry.name, '*.txt')
                                  and entry.is_file()):
                                files.append(Path(entry.path))
                except (FileNotFoundError, PermissionError):
                    continue
            self._files = sorted(files, key=lambda p: str(p).casefold())
        return self._files

    def _read_file(self, path, machine, fallback_date):
        global _CACHE_RECORDS
        key = (os.path.abspath(path), machine, fallback_date)
        before = _signature(path)
        with _CACHE_LOCK:
            cached = _FILE_CACHE.get(key)
            if cached is not None:
                signature, grouped, count = cached
                if signature == before:
                    _FILE_CACHE.move_to_end(key)
                    return grouped.get(self.slot, ())
                del _FILE_CACHE[key]
                _CACHE_RECORDS -= count

        # Keep the original parser, encoding fallback and source line numbers.
        records = MachineSlotYieldRepository._read_file(path, machine, fallback_date)
        grouped = defaultdict(list)
        for record in records:
            grouped[record.slot].append(record)
        grouped = {slot: tuple(rows) for slot, rows in grouped.items()}
        count = len(records)
        # A file being written is usable for this read, but must not be cached.
        if count <= _MAX_CACHE_RECORDS and _signature(path) == before:
            with _CACHE_LOCK:
                previous = _FILE_CACHE.pop(key, None)
                if previous is not None:
                    _CACHE_RECORDS -= previous[2]
                while _FILE_CACHE and (len(_FILE_CACHE) >= _MAX_CACHE_FILES or
                        _CACHE_RECORDS + count > _MAX_CACHE_RECORDS):
                    _, evicted = _FILE_CACHE.popitem(last=False)
                    _CACHE_RECORDS -= evicted[2]
                _FILE_CACHE[key] = (before, grouped, count)
                _CACHE_RECORDS += count
        return grouped.get(self.slot, ())


def _day(value):
    text = str(value or '').strip()
    if len(text) < 8 or not text[:8].isdigit():
        return ''
    return text[:8]


def _load_slot_through_day(repository, root, machine, slot, alarm_date, start_day, models):
    machine_root = Path(root) / machine
    if not machine_root.is_dir():
        return []
    files = defaultdict(list)
    for path in repository._find_txt_files(machine_root):
        file_day = repository._date_from_filename(path.name)
        if file_day and file_day <= alarm_date:
            files[file_day].append(path)
    records = []
    # Read all files of the Alarm day. Continue into previous days until the
    # last 30 tests of every involved Model are available; 30 also covers the
    # non-Model window and a cross-midnight FAIL pair.
    needed_models = {str(m).strip().upper()[:5] for m in models if str(m).strip()}
    counts = defaultdict(int)
    for file_day in sorted(files, reverse=True):
        if file_day < alarm_date and file_day < start_day and len(records) >= 30 and all(
                counts[m] >= 30 for m in needed_models):
            break
        for path in files[file_day]:
            for record in repository._read_file(path, machine, file_day):
                if record.slot != slot or record.date > alarm_date:
                    continue
                records.append(record)
                counts[model_of(record)] += 1
    return sorted(records, key=sort_key)


def _latest_five(repository, root, machine, slot):
    # The old log history reader scans newest files directly, independent of
    # the From/To filter. Read all files of a day before deciding to stop.
    machine_root = Path(root) / machine
    files = defaultdict(list)
    for path in repository._find_txt_files(machine_root):
        file_day = repository._date_from_filename(path.name)
        if file_day:
            files[file_day].append(path)
    current = datetime.now().strftime('%Y%m%d %H:%M:%S')
    rows = []
    for file_day in sorted(files, reverse=True):
        if file_day > current[:8]:
            continue
        if len(rows) >= 5:
            break
        for path in files[file_day]:
            rows.extend(record for record in repository._read_file(path, machine, file_day)
                        if record.slot == slot and f'{record.date} {record.time}' <= current)
        rows.sort(key=sort_key)
        rows = rows[-5:]
    return rows


def _saved_consecutive(records, start, end, reason):
    if 'Fail 2 lần liên tục' not in reason:
        return None
    for first, second in zip(records, records[1:]):
        if (f'{first.date} {first.time}' != start or
                f'{second.date} {second.time}' != end or
                is_pass(first) or is_pass(second)):
            continue
        same_partno = bool(first.partno) and first.partno.strip().casefold() == second.partno.strip().casefold()
        same_model = bool(model_of(first)) and model_of(first) == model_of(second)
        if 'khác Model' in reason and same_partno:
            continue
        if 'cùng Model' in reason and not (same_partno or same_model):
            continue
        item = evidence('consecutive', [first, second])
        item['reason'] = next((part.strip() for part in reason.split('|')
                               if 'Fail 2 lần liên tục' in part), item['reason'])
        return item
    return None


def load_alarm_history(log_root, machine, slot, alarm_row, target_15_model, target_30_model):
    """Return only the rule windows currently supported by this saved row/log.

    Evaluating the historical day is separate from creating new alarms, whose
    consecutive rule still uses the five days leading up to the current day.
    """
    alarm_date = _day(alarm_row.alarm_date)
    if not alarm_date:
        return []
    repository = _HistoryReader(slot)
    reason = str(alarm_row.reason or '')
    models = str(alarm_row.models or '').replace(',', '/').split('/')
    records = _load_slot_through_day(repository, log_root, machine, slot,
                                     alarm_date, _day(alarm_row.start_datetime) or alarm_date, models)
    if not records:
        return []
    start = str(alarm_row.start_datetime or '').strip()
    end = str(alarm_row.end_datetime or '').strip()
    stored_pair = _saved_consecutive(records, start, end, reason)
    latest = _latest_five(repository, log_root, machine, slot)
    targets = (float(alarm_row.target_15 or 0), float(alarm_row.target_30 or 0),
               float(target_15_model), float(target_30_model))
    windows = evaluate_slot(records, latest, targets,
                            today=datetime.strptime(alarm_date, '%Y%m%d').date()).get(alarm_date, [])
    matched = []
    if stored_pair is not None:
        matched.append(stored_pair)
    for window in windows:
        if window['rule'] == 'consecutive':
            continue
        if window['reason'] in reason:
            matched.append(window)
    return matched
