from __future__ import annotations


def score_document(doc: dict) -> tuple[int, str]:
    score = 0
    title = (doc.get('title') or '').strip()
    content = (doc.get('content') or '').strip()
    if title:
        score += 15
    if content:
        score += 25
    if len(content) >= 300:
        score += 15
    if len(content) >= 800:
        score += 5
    if doc.get('publish_time'):
        score += 10
    if doc.get('source_name') and doc.get('source_name') != 'UNKNOWN':
        score += 10
    if (doc.get('source_url') or '').startswith(('http://', 'https://')):
        score += 10
    serious_pollution = {'ENCODING_ERROR', 'EMPTY_CONTENT'}
    if not set(doc.get('issues') or []).intersection(serious_pollution):
        score += 10

    penalties = {
        'TAG_POLLUTION': 5,
        'DATE_PARSE_ERROR': 5,
        'FUTURE_DATE': 5,
        'SHORT_CONTENT': 15,
        'ENCODING_ERROR': 30,
    }
    for issue in set(doc.get('issues') or []):
        score -= penalties.get(issue, 0)
    score = max(0, min(100, score))
    level = 'HIGH' if score >= 80 else ('MEDIUM' if score >= 60 else 'LOW')
    return score, level
