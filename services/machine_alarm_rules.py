"""Pure alarm rules shared by the UI and database synchronisation."""
from collections import defaultdict
from datetime import date, timedelta

RULE_NAMES = {
    'model15': 'Fail hiệu suất 15 lần liên tục cùng model',
    'model30': 'Fail hiệu suất 30 lần liên tục cùng model',
    'yield15': 'Yield Last 15 thấp hơn Target 15',
    'yield30': 'Yield Last 30 thấp hơn Target 30',
}
PRIORITY = {'consecutive': 0, 'model15': 1, 'model30': 2, 'yield15': 3, 'yield30': 4}


def sort_key(record):
    return tuple(str(getattr(record, field, '') or '') for field in
                 ('date', 'time', 'file_name', 'file_path')) + (int(getattr(record, 'line_number', 0) or 0),)


def model_of(record):
    return str(getattr(record, 'partno', '') or '').strip()[:5].upper()


def is_pass(record):
    return str(getattr(record, 'result', '') or '').strip().upper() == 'PASS'


def window_yield(records, count):
    if len(records) < count:
        return None
    return sum(is_pass(r) for r in records[-count:]) / count * 100.0


def snapshot(record):
    fields = ('date', 'time', 'machine', 'slot', 'result', 'partno', 'lotno',
              'interface', 'scrapcode', 'file_name', 'file_path', 'line_number')
    data = {key: getattr(record, key, '') for key in fields}
    data['model'] = model_of(record)
    return data


def evidence(rule, records, target=None, model=''):
    passed = sum(is_pass(r) for r in records)
    reason = RULE_NAMES.get(rule, '')
    if rule == 'consecutive':
        same = bool(model_of(records[0])) and model_of(records[0]) == model_of(records[1])
        reason = 'Fail 2 lần liên tục ' + ('cùng Model' if same else 'khác Model')
    return dict(rule=rule, reason=reason, model=model,
                start=f'{records[0].date} {records[0].time}',
                end=f'{records[-1].date} {records[-1].time}',
                alarm_date=records[-1].date, count=len(records), passed=passed,
                failed=len(records)-passed, yield_percent=passed / len(records) * 100.0,
                target=target, tests=[snapshot(r) for r in records])


def evidence_key(item):
    return PRIORITY[item['rule']], item['end'], item['start'], item['model']


def evaluate_slot(records, latest_tests, targets, today=None):
    """Return one list of exact rule windows per alarm day.

    targets = general15, general30, model15, model30.
    latest_tests must be read up to the current time, independently of From/To.
    """
    today = today or date.today()
    ordered = sorted((r for r in records if str(r.result).strip().upper() in ('PASS', 'FAIL')), key=sort_key)
    events = defaultdict(list)
    if not ordered:
        return {}
    # Keep the newest consecutive FAIL pair of each day, as in the old rule.
    first_day = (today - timedelta(days=4)).strftime('%Y%m%d')
    last_day = today.strftime('%Y%m%d')
    pairs = {}
    for first, second in zip(ordered, ordered[1:]):
        if (not is_pass(first) and not is_pass(second)
                and first_day <= first.date <= last_day
                and first_day <= second.date <= last_day):
            pairs[second.date] = (first, second)
    for day, pair in pairs.items():
        # Materialize only the newest pair retained for this day.
        events[day].append(evidence('consecutive', list(pair)))

    last5 = sorted(latest_tests, key=sort_key)[-5:]
    recovered = len(last5) == 5 and all(is_pass(r) for r in last5)
    if not recovered:
        for count, target in ((15, targets[0]), (30, targets[1])):
            value = window_yield(ordered, count)
            if value is not None and value < target:
                item = evidence(f'yield{count}', ordered[-count:], target)
                events[item['alarm_date']].append(item)
        models = defaultdict(list)
        for record in ordered:
            model = model_of(record)
            if model:
                models[model].append(record)
        for model, tests in models.items():
            for count, target in ((15, targets[2]), (30, targets[3])):
                seen_days = set()
                passed = 0
                for i, record in enumerate(tests):
                    passed += is_pass(record)
                    if i >= count:
                        passed -= is_pass(tests[i-count])
                    if i + 1 < count or record.date in seen_days:
                        continue
                    if passed / count * 100.0 < target:
                        item = evidence(f'model{count}', tests[i-count+1:i+1], target, model)
                        events[record.date].append(item)
                        seen_days.add(record.date)
    return {day: sorted(items, key=evidence_key) for day, items in events.items()}
