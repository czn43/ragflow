from __future__ import annotations

from copy import deepcopy
from typing import Any

STANDARD_FIELDS = [
    'sourceName',
    'sourceUrl',
    'title',
    'contentText',
    'category',
    'publishTime',
    'attachments',
    'attachmentCount',
]


def make_standard_record(
    *,
    source_name: str = '',
    source_url: str = '',
    title: str = '',
    content_text: str = '',
    category: str = '',
    publish_time: str = '',
    attachments: list[Any] | None = None,
) -> dict[str, Any]:
    attachments = deepcopy(attachments or [])
    return {
        'sourceName': source_name or '',
        'sourceUrl': source_url or '',
        'title': title or '',
        'contentText': content_text or '',
        'category': category or '',
        'publishTime': publish_time or '',
        'attachments': attachments,
        'attachmentCount': len(attachments),
    }


def exact_standard_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return exactly the competition-facing schema and no technical fields."""
    attachments = record.get('attachments')
    if not isinstance(attachments, list):
        attachments = []
    return {
        'sourceName': str(record.get('sourceName') or ''),
        'sourceUrl': str(record.get('sourceUrl') or ''),
        'title': str(record.get('title') or ''),
        'contentText': str(record.get('contentText') or ''),
        'category': str(record.get('category') or ''),
        'publishTime': str(record.get('publishTime') or ''),
        'attachments': deepcopy(attachments),
        'attachmentCount': len(attachments),
    }


def coerce_standard_record(record: dict[str, Any]) -> dict[str, Any]:
    """Accept v1.5 snake_case records or v1.6 standard records."""
    if 'sourceUrl' in record or 'contentText' in record:
        return exact_standard_record(record)
    return make_standard_record(
        source_name=record.get('source_name') or record.get('sourceName') or '',
        source_url=record.get('source_url') or record.get('sourceUrl') or '',
        title=record.get('title') or record.get('raw_title') or '',
        content_text=record.get('content') or record.get('contentText') or '',
        category=record.get('category') or '',
        publish_time=record.get('publish_time') or record.get('publishTime') or '',
        attachments=record.get('attachments') or [],
    )
