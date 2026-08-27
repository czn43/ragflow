from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

try:
    import trafilatura
except ImportError:  # optional fallback; selector extraction still works
    trafilatura = None

from core.models import ExtractResult


def _select_text(soup: BeautifulSoup, selectors: list[str] | str | None, sep: str = '\n') -> str | None:
    if not selectors:
        return None
    if isinstance(selectors, str):
        selectors = [selectors]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = node.get_text(sep, strip=True)
            if text:
                return text
    return None


def _postprocess_field(value: str | None, field_cfg: dict[str, Any] | None) -> str | None:
    """Apply lightweight config-driven cleanup to extracted metadata fields.

    This is intentionally small and transparent. It is useful for common news
    templates that render metadata as strings such as ``来源：深圳晚报`` or
    ``发布时间：2026-08-27``. The article body itself is NOT transformed here;
    body cleaning belongs to the cleaning pipeline.

    Supported field config keys:
      - strip_prefixes: ["来源：", "来源:"]
      - regex_extract: "来源[：:]\\s*(.+)"  (group 1 is used when present)
    """
    if value is None:
        return None
    text = value.strip()
    field_cfg = field_cfg or {}

    for prefix in field_cfg.get('strip_prefixes') or []:
        p = str(prefix)
        if text.startswith(p):
            text = text[len(p):].strip()
            break

    pattern = field_cfg.get('regex_extract')
    if pattern:
        try:
            m = re.search(str(pattern), text, flags=re.S)
            if m:
                text = (m.group(1) if m.lastindex else m.group(0)).strip()
        except re.error:
            # A malformed optional regex should not make an entire crawl fail.
            pass

    return text or None


def _field_text(soup: BeautifulSoup, field_cfg: dict | None, sep: str) -> str | None:
    field_cfg = field_cfg or {}
    value = _select_text(soup, field_cfg.get('selectors'), sep=sep)
    return _postprocess_field(value, field_cfg)


def extract_by_rule(html: str, cfg: dict) -> ExtractResult:
    soup = BeautifulSoup(html, 'lxml')
    detail = cfg.get('detail', {})
    title = _field_text(soup, detail.get('title'), sep=' ')
    content = _select_text(soup, (detail.get('content') or {}).get('selectors'), sep='\n')
    publish_time = _field_text(soup, detail.get('publish_time'), sep=' ')
    source_name = _field_text(soup, detail.get('source'), sep=' ')
    min_chars = int(detail.get('min_content_chars', 100))
    if content and len(content.strip()) >= min_chars:
        return ExtractResult(title, content, publish_time, source_name, extraction_method='rule')
    return ExtractResult(title, content, publish_time, source_name, extraction_method='failed')


def extract_by_trafilatura(html: str) -> ExtractResult:
    if trafilatura is None:
        return ExtractResult(None, None, extraction_method='failed')
    try:
        payload = trafilatura.extract(
            html,
            output_format='json',
            with_metadata=True,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        if not payload:
            return ExtractResult(None, None, extraction_method='failed')
        data = json.loads(payload)
        return ExtractResult(
            title=data.get('title'),
            content=data.get('text') or data.get('raw_text'),
            publish_time=data.get('date'),
            source_name=data.get('sitename'),
            author=data.get('author'),
            extraction_method='trafilatura',
        )
    except Exception:
        return ExtractResult(None, None, extraction_method='failed')


def extract(html: str, cfg: dict) -> ExtractResult:
    rule = extract_by_rule(html, cfg)
    min_chars = int(cfg.get('detail', {}).get('min_content_chars', 100))
    if rule.content and len(rule.content.strip()) >= min_chars:
        return rule
    generic = extract_by_trafilatura(html)
    if generic.content and len(generic.content.strip()) >= min_chars:
        if not generic.title:
            generic.title = rule.title
        if not generic.publish_time:
            generic.publish_time = rule.publish_time
        if not generic.source_name:
            generic.source_name = rule.source_name
        return generic
    # Return rule result even if short, so validator can explain why it was rejected/warned.
    return rule
