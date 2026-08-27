from __future__ import annotations

from collections import Counter
from datetime import datetime
import math


def percentile(values: list[int], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    k = (len(xs) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(xs[int(k)])
    return xs[f] * (c - k) + xs[c] * (k - f)


def _ratio(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


def build_statistics(documents: list[dict], pipeline_stats: dict | None = None, audits: list[dict] | None = None) -> dict:
    n = len(documents)
    audits = audits or []
    lengths = [len(d.get('contentText') or '') for d in documents]
    source_counts = Counter((d.get('sourceName') or 'UNKNOWN') for d in documents)
    category_counts = Counter((d.get('category') or 'UNKNOWN') for d in documents)
    issue_counts = Counter(i for a in audits for i in (a.get('issues') or []))

    years = Counter()
    invalid_dates = 0
    for d in documents:
        dt = d.get('publishTime')
        if not dt:
            invalid_dates += 1
            continue
        try:
            years[datetime.strptime(dt, '%Y-%m-%d').year] += 1
        except ValueError:
            invalid_dates += 1

    buckets = Counter()
    for x in lengths:
        if x < 100:
            buckets['0-99'] += 1
        elif x < 500:
            buckets['100-499'] += 1
        elif x < 1000:
            buckets['500-999'] += 1
        elif x < 2000:
            buckets['1000-1999'] += 1
        elif x < 5000:
            buckets['2000-4999'] += 1
        else:
            buckets['5000+'] += 1

    completeness = {}
    for field in ['sourceName', 'sourceUrl', 'title', 'contentText', 'category', 'publishTime']:
        ok = sum(1 for d in documents if str(d.get(field) or '').strip())
        completeness[field] = {'count': ok, 'ratio': _ratio(ok, n)}

    return {
        'summary': {
            'final_count': n,
            **(pipeline_stats or {}),
        },
        'completeness': completeness,
        'content_length': {
            'min': min(lengths) if lengths else None,
            'max': max(lengths) if lengths else None,
            'mean': round(sum(lengths) / len(lengths), 2) if lengths else None,
            'p50': percentile(lengths, 0.50),
            'p90': percentile(lengths, 0.90),
            'p95': percentile(lengths, 0.95),
            'buckets': dict(buckets),
        },
        'source_distribution': dict(source_counts.most_common()),
        'category_distribution': dict(category_counts.most_common()),
        'year_distribution': dict(sorted(years.items())),
        'invalid_or_missing_dates': invalid_dates,
        'issues': dict(issue_counts.most_common()),
    }
