"""Persist alarm summaries only; keep rule windows in the current log result."""
from collections import defaultdict
from datetime import datetime
from database.connection import create_connection
from services.machine_alarm_rules import evaluate_slot, window_yield, sort_key, is_pass


def ensure_details(connection):
    columns = {r['name'] for r in connection.execute('PRAGMA table_info(machine_slot_yield_alarm)')}
    for name in ('yield_15_model', 'yield_30_model'):
        if name not in columns:
            connection.execute(f'ALTER TABLE machine_slot_yield_alarm ADD COLUMN {name} REAL')



def sync_result(repository, result, date_from=None, date_to=None,
                target_15=None, target_30=None, target_15_model=None, target_30_model=None):
    if result is None:
        return 0
    date_from = str(getattr(result, 'date_from', '') or date_from or '')
    date_to = str(getattr(result, 'date_to', '') or date_to or '')
    if not date_from or not date_to:
        return 0
    from repositories.machine_slot_yield_repository import MachineSlotYieldRepository
    config = MachineSlotYieldRepository(repository.database_path.parent / 'machine_slot_targets.json')
    defaults = config.load_all_targets()
    values = (target_15, target_30, target_15_model, target_30_model)
    names = ('target_15', 'target_30', 'target_15_model', 'target_30_model')
    targets = tuple(float(value if value is not None else
                         (getattr(result, name, None) if getattr(result, name, None) is not None else default))
                    for value, name, default in zip(values, names, defaults))
    grouped = defaultdict(list)
    for record in result.records:
        if date_from <= record.date <= date_to:
            grouped[(record.machine, record.slot)].append(record)
    # Explicit successful read scope includes machines with no matching tests.
    machines = set(getattr(result, 'loaded_machines', ()) or [m for m, s in grouped])
    latest = getattr(result, 'latest_tests', None)
    if latest is None:
        raise ValueError('Thiếu 5 test mới nhất. Vui lòng đọc lại Log Folder trước khi tính Alarm.')
    candidates = {}
    for key, records in grouped.items():
        ordered = sorted(records, key=sort_key)
        for day, events in evaluate_slot(ordered, latest.get(key, []), targets).items():
            candidates[(day, *key)] = (ordered, events)

    result.alarm_events = {key: events for key, (_, events) in candidates.items()}
    connection = create_connection(repository.database_path, busy_timeout_ms=10000)
    try:
        connection.execute('BEGIN IMMEDIATE')
        repository._ensure_machine_slot_yield_alarm_table(connection)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        existing = connection.execute('''SELECT id, alarm_date, machine, slot, status, reason,
                   start_datetime, end_datetime, scrap_codes, model
            FROM machine_slot_yield_alarm WHERE alarm_date BETWEEN ? AND ?''', (date_from, date_to)).fetchall()
        existing_by_key = {(row['alarm_date'], row['machine'], row['slot']): row
                           for row in existing}
        for row in existing:
            key = (row['alarm_date'], row['machine'], row['slot'])
            if (row['machine'] in machines and key not in candidates
                    and str(row['status'] or '').strip() not in ('Đã hoàn thành', 'Hoàn thành')
                    and 'Fail 2 lần liên tục' not in str(row['reason'] or '')):
                # Keep completed alarms and leave mail deduplication history untouched.
                connection.execute('DELETE FROM machine_slot_yield_alarm WHERE id=?', (row['id'],))
        for (day, machine, slot), (ordered, events) in sorted(candidates.items()):
            representative = events[0]
            reasons = list(dict.fromkeys(e['reason'] for e in events))
            models = list(dict.fromkeys(t['model'] for e in events for t in e['tests'] if t['model']))
            codes = list(dict.fromkeys(t['scrapcode'] for e in events for t in e['tests']
                                      if t['result'].upper() == 'FAIL' and t['scrapcode']))
            same_values = {}
            for count in (15, 30):
                matches = [e for e in events if e['rule'] == f'model{count}']
                same_values[count] = matches[0]['yield_percent'] if matches else None
            passed = sum(is_pass(r) for r in ordered)
            # A saved 2-FAIL Alarm can outlive the rolling five-day creation
            # window. If a newly found Yield rule shares its row, retain the
            # saved pair and append the new reason instead of replacing it.
            previous = existing_by_key.get((day, machine, slot))
            if (previous is not None and
                    'Fail 2 lần liên tục' in str(previous['reason'] or '') and
                    not any(e['rule'] == 'consecutive' for e in events)):
                reasons = list(dict.fromkeys(
                    [part.strip() for part in str(previous['reason']).split('|') if part.strip()]
                    + reasons))
                representative = dict(representative)
                representative['start'] = previous['start_datetime']
                representative['end'] = previous['end_datetime']
                codes = list(dict.fromkeys(
                    [part.strip() for part in str(previous['scrap_codes'] or '').split(',')
                     if part.strip()] + codes))
                models = list(dict.fromkeys(
                    [part.strip() for part in str(previous['model'] or '').split('/')
                     if part.strip()] + models))
            data = dict(alarm_date=day, machine=machine, slot=slot,
                start_datetime=representative['start'], end_datetime=representative['end'],
                yield_15=window_yield(ordered, 15), target_15=targets[0],
                yield_30=window_yield(ordered, 30), target_30=targets[1],
                yield_15_model=same_values[15], yield_30_model=same_values[30],
                total_test=len(ordered), pass_count=passed, fail_count=len(ordered)-passed,
                yield_percent=passed / len(ordered) * 100.0,
                reason=' | '.join(reasons), scrap_codes=', '.join(codes), model=' / '.join(models),
                created_at=now, updated_at=now)
            columns = list(data)
            updates = [c for c in columns if c not in ('alarm_date', 'machine', 'slot', 'created_at')]
            connection.execute(
                f"INSERT INTO machine_slot_yield_alarm ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) "
                "ON CONFLICT(alarm_date,machine,slot) DO UPDATE SET " +
                ','.join(f'{c}=excluded.{c}' for c in updates), tuple(data.values()))
        connection.commit()
        # Keep Monitor updates, but run them during the explicit/automatic
        # calculation, never while opening the Alarm list. The caller is a
        # worker thread; any monitor failure cannot undo a committed Alarm.
        try:
            repository._refresh_monitor_results(date_from, date_to)
        except Exception:
            pass
        return len(candidates)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

