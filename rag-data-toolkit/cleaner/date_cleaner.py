from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


@dataclass
class DateParseResult:
    raw: str
    normalized: str | None
    valid: bool
    reason: str | None = None


PATTERNS = [
    re.compile(r'(?P<y>\d{4})[年\-/\.](?P<m>\d{1,2})[月\-/\.](?P<d>\d{1,2})日?'),
]


def parse_date(raw_date: str | None) -> DateParseResult:
    raw = (raw_date or '').strip()
    if not raw:
        return DateParseResult(raw, None, False, 'EMPTY_DATE')
    for p in PATTERNS:
        m = p.search(raw)
        if not m:
            continue
        try:
            dt = date(int(m.group('y')), int(m.group('m')), int(m.group('d')))
        except ValueError:
            return DateParseResult(raw, None, False, 'DATE_PARSE_ERROR')
        if dt > date.today():
            return DateParseResult(raw, dt.isoformat(), False, 'FUTURE_DATE')
        return DateParseResult(raw, dt.isoformat(), True, None)
    return DateParseResult(raw, None, False, 'DATE_PARSE_ERROR')
