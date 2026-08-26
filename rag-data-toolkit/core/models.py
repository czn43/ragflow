from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class UrlItem:
    url: str
    title: str | None = None
    publish_time: str | None = None
    source_page: str | None = None


@dataclass
class HttpResult:
    url: str
    final_url: str | None = None
    status_code: int | None = None
    text: str | None = None
    encoding: str | None = None
    error: str | None = None
    retry_count: int = 0


@dataclass
class RawDocument:
    id: str
    source_url: str
    final_url: str | None
    crawl_time: str
    http_status: int | None
    raw_title: str | None = None
    raw_publish_time: str | None = None
    source_name: str | None = None
    category: str | None = None
    raw_html_path: str | None = None
    error: str | None = None


@dataclass
class CleaningAction:
    rule: str
    removed_text: str = ''
    note: str = ''


@dataclass
class ExtractResult:
    title: str | None
    content: str | None
    publish_time: str | None = None
    source_name: str | None = None
    author: str | None = None
    extraction_method: str = 'failed'


@dataclass
class Document:
    id: str
    title: str
    content: str
    source_url: str
    source_name: str
    publish_time: str | None
    crawl_time: str
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    region: str | None = None
    document_type: str | None = None
    char_count: int = 0
    quality_score: int = 0
    quality_level: str = 'LOW'
    status: str = 'valid'
    issues: list[str] = field(default_factory=list)
    cleaning_actions: list[dict[str, Any]] = field(default_factory=list)
    content_hash: str = ''
    url_hash: str = ''
    cleaning_version: str = 'v1.0'
    extraction_method: str = ''

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
