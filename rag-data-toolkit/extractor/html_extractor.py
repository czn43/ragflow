from __future__ import annotations

import json
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


def extract_by_rule(html: str, cfg: dict) -> ExtractResult:
    soup = BeautifulSoup(html, 'lxml')
    detail = cfg.get('detail', {})
    title = _select_text(soup, detail.get('title', {}).get('selectors'), sep=' ')
    content = _select_text(soup, detail.get('content', {}).get('selectors'), sep='\n')
    publish_time = _select_text(soup, detail.get('publish_time', {}).get('selectors'), sep=' ')
    source_name = _select_text(soup, detail.get('source', {}).get('selectors'), sep=' ')
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
