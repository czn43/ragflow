from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationResult:
    status: str
    issues: list[str]


def validate_document(doc: dict, min_chars: int = 100) -> ValidationResult:
    issues = set(doc.get('issues') or [])
    title = (doc.get('title') or '').strip()
    content = (doc.get('content') or '').strip()
    url = (doc.get('source_url') or '').strip()

    if not title:
        issues.add('EMPTY_TITLE')
    if not content:
        issues.add('EMPTY_CONTENT')
    elif len(content) < min_chars:
        issues.add('SHORT_CONTENT')
    if not url.startswith(('http://', 'https://')):
        issues.add('INVALID_URL')

    severe = {'EMPTY_TITLE', 'EMPTY_CONTENT', 'INVALID_URL', 'ENCODING_ERROR', 'HTTP_ERROR'}
    status = 'reject' if issues.intersection(severe) else ('warning' if issues else 'valid')
    return ValidationResult(status=status, issues=sorted(issues))
