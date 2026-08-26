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


def build_statistics(documents: list[dict], pipeline_stats: dict | None = None) -> dict:
    n = len(documents)
    lengths = [int(d.get('char_count') or len(d.get('content') or '')) for d in documents]
    source_counts = Counter((d.get('source_name') or 'UNKNOWN') for d in documents)
    category_counts = Counter((d.get('category') or 'UNKNOWN') for d in documents)
    issue_counts = Counter(i for d in documents for i in (d.get('issues') or []))
    years = Counter()
    invalid_dates = 0
    for d in documents:
        dt = d.get('publish_time')
        if not dt:
            invalid_dates += 1
            continue
        try:
            years[datetime.strptime(dt, '%Y-%m-%d').year] += 1
        except ValueError:
            invalid_dates += 1

    bins = {'0-99': 0, '100-499': 0, '500-999': 0, '1000-1999': 0, '2000-4999': 0, '5000+': 0}
    for x in lengths:
        if x < 100: bins['0-99'] += 1
        elif x < 500: bins['100-499'] += 1
        elif x < 1000: bins['500-999'] += 1
        elif x < 2000: bins['1000-1999'] += 1
        elif x < 5000: bins['2000-4999'] += 1
        else: bins['5000+'] += 1

    completeness = {}
    for field in ['title', 'content', 'publish_time', 'source_name', 'source_url']:
        c = sum(1 for d in documents if d.get(field))
        completeness[field] = {'count': c, 'ratio': _ratio(c, n)}

    top_sources = [{'source': k, 'count': v, 'ratio': _ratio(v, n)} for k, v in source_counts.most_common(20)]
    top1_ratio = top_sources[0]['ratio'] if top_sources else 0
    top3_ratio = round(sum(x['count'] for x in top_sources[:3]) / n, 4) if n else 0

    return {
        'summary': {
            'final_count': n,
            'pipeline': pipeline_stats or {},
        },
        'completeness': completeness,
        'content_length': {
            'min': min(lengths) if lengths else None,
            'max': max(lengths) if lengths else None,
            'mean': round(sum(lengths) / len(lengths), 2) if lengths else None,
            'p50': percentile(lengths, 0.50),
            'p90': percentile(lengths, 0.90),
            'p95': percentile(lengths, 0.95),
            'buckets': bins,
        },
        'source_distribution': {
            'top20': top_sources,
            'top1_ratio': top1_ratio,
            'top3_ratio': top3_ratio,
        },
        'category_distribution': dict(category_counts.most_common()),
        'date_distribution': {
            'years': dict(sorted(years.items())),
            'missing_or_invalid': invalid_dates,
        },
        'issues': dict(issue_counts.most_common()),
    }
