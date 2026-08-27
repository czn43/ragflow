from __future__ import annotations

from dataclasses import asdict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from core.models import UrlItem
from crawler.article_discovery import count_page_links, discover_links, score_article_url
from crawler.url_normalizer import normalize_url
from extractor.html_extractor import extract


def _text(node) -> str | None:
    if node is None:
        return None
    t = node.get_text(' ', strip=True)
    return t or None


def parse_list_page(html: str, current_url: str, cfg: dict) -> list[UrlItem]:
    soup = BeautifulSoup(html, 'lxml')
    list_cfg = cfg.get('list', {})
    item_selector = list_cfg.get('item_selector')
    if not item_selector:
        return []
    items = []
    try:
        selected_items = soup.select(item_selector)
    except Exception:
        return []
    for item in selected_items:
        link_selector = list_cfg.get('link_selector', 'a')
        link = item if link_selector == '@self' else item.select_one(link_selector)
        if link is None or not link.get('href'):
            continue
        url = normalize_url(link.get('href'), current_url)
        if not url:
            continue
        title_selector = list_cfg.get('title_selector')
        title = _text(item.select_one(title_selector)) if title_selector else _text(link)
        date_selector = list_cfg.get('date_selector')
        publish_time = _text(item.select_one(date_selector)) if date_selector else None
        source_selector = list_cfg.get('source_selector')
        source_name = _text(item.select_one(source_selector)) if source_selector else None
        items.append(UrlItem(url=url, title=title, publish_time=publish_time, source_page=current_url, source_name=source_name))
    return items


def get_next_url(html: str, current_url: str, cfg: dict, page_no: int) -> str | None:
    p = cfg.get('pagination', {})
    ptype = p.get('type', 'next_link')
    if ptype == 'none':
        return None
    if ptype == 'next_link':
        selector = p.get('next_selector')
        if not selector:
            return None
        soup = BeautifulSoup(html, 'lxml')
        node = soup.select_one(selector)
        if node is None or not node.get('href'):
            return None
        return normalize_url(node.get('href'), current_url)
    if ptype == 'url_template':
        template = p.get('template')
        if not template:
            return None
        return template.format(page=page_no + 1)
    if ptype == 'page_parameter':
        param = p.get('param', 'page')
        parts = urlsplit(current_url)
        q = dict(parse_qsl(parts.query, keep_blank_values=True))
        q[param] = str(page_no + 1)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), ''))
    return None


def looks_like_detail_page(html: str, url: str, cfg: dict) -> tuple[bool, dict]:
    start_mode = str(cfg.get('crawler', {}).get('start_mode', 'auto')).lower()
    if start_mode == 'detail':
        return True, {'reason': 'forced_detail_mode'}
    if start_mode == 'list':
        return False, {'reason': 'forced_list_mode'}

    score, reasons = score_article_url(url, '', cfg)
    threshold = int(cfg.get('discovery', {}).get('detail_url_score', 4))
    info = {'url_score': score, 'url_reasons': reasons, 'detail_url_score': threshold}
    if score < threshold:
        info['reason'] = 'url_score_too_low'
        return False, info

    ext = extract(html, cfg)
    min_chars = int(cfg.get('detail', {}).get('min_content_chars', 100))
    content_len = len((ext.content or '').strip())
    info.update({'extraction_method': ext.extraction_method, 'content_chars': content_len})
    if content_len >= min_chars:
        info['reason'] = 'article_like_url_and_extractable_content'
        return True, info
    info['reason'] = 'article_like_url_but_content_too_short'
    return False, info


class ListCrawler:
    def __init__(self, http_client, cfg: dict, logger):
        self.http = http_client
        self.cfg = cfg
        self.logger = logger
        self.diagnostics: dict = {'start_pages': [], 'fallback_used': False}

    def _auto_items(self, html: str, current: str, max_docs: int) -> list[UrlItem]:
        candidates = discover_links(html, current, self.cfg, limit=max(max_docs * 3, 100))
        return [UrlItem(url=c.url, title=c.text or None, publish_time=None, source_page=current) for c in candidates]

    def inspect_url(self, url: str, validate_top: int = 5) -> dict:
        current = normalize_url(url)
        result = self.http.get(current)
        report = {
            'url': current,
            'http_status': result.status_code,
            'final_url': result.final_url,
            'error': result.error,
        }
        if not result.text or not result.status_code or result.status_code >= 400:
            return report
        report.update(count_page_links(result.text, current, self.cfg))
        selector = self.cfg.get('list', {}).get('item_selector')
        report['configured_item_selector'] = selector
        try:
            selector_items = parse_list_page(result.text, current, self.cfg)
            if selector:
                BeautifulSoup(result.text, 'lxml').select(selector)
            report['selector_error'] = None
        except Exception as e:
            selector_items = []
            report['selector_error'] = f'{type(e).__name__}: {e}'
        report['selector_matches'] = len(selector_items)
        is_detail, detail_info = looks_like_detail_page(result.text, current, self.cfg)
        report['looks_like_detail_page'] = is_detail
        report['detail_detection'] = detail_info
        candidates = discover_links(result.text, current, self.cfg, limit=100)
        report['candidate_count'] = len(candidates)
        report['top_candidates'] = [c.to_dict() for c in candidates[:20]]

        validations = []
        for c in candidates[:max(0, validate_top)]:
            r = self.http.get(c.url)
            entry = {'url': c.url, 'score': c.score, 'http_status': r.status_code}
            if r.text and r.status_code and r.status_code < 400:
                ext = extract(r.text, self.cfg)
                entry.update({
                    'extraction_method': ext.extraction_method,
                    'title': ext.title,
                    'content_chars': len((ext.content or '').strip()),
                    'valid_article': len((ext.content or '').strip()) >= int(self.cfg.get('detail', {}).get('min_content_chars', 100)),
                })
            validations.append(entry)
        report['candidate_validations'] = validations
        return report

    def discover(self, max_pages: int = 20, max_docs: int = 100) -> list[UrlItem]:
        starts = self.cfg.get('crawler', {}).get('start_urls') or []
        if not starts:
            raise ValueError('crawler.start_urls is empty')
        collected: dict[str, UrlItem] = {}
        self.diagnostics = {'start_pages': [], 'fallback_used': False}

        for start in starts:
            current = normalize_url(start)
            page_no = 1
            empty_new_pages = 0
            first_page = True
            while current and page_no <= max_pages and len(collected) < max_docs:
                result = self.http.get(current)
                self.logger.info('list page=%s url=%s status=%s', page_no, current, result.status_code)
                page_diag = {
                    'page': page_no,
                    'url': current,
                    'status': result.status_code,
                    'error': result.error,
                    'selector_matches': 0,
                    'fallback_candidates': 0,
                    'mode': 'unknown',
                }
                if not result.text or not result.status_code or result.status_code >= 400:
                    self.diagnostics['start_pages'].append(page_diag)
                    break

                page_diag.update(count_page_links(result.text, current, self.cfg))

                if first_page:
                    is_detail, detail_info = looks_like_detail_page(result.text, current, self.cfg)
                    page_diag['detail_detection'] = detail_info
                    if is_detail:
                        page_diag['mode'] = 'direct_detail'
                        collected[current] = UrlItem(url=current, title=None, publish_time=None, source_page=current)
                        self.diagnostics['start_pages'].append(page_diag)
                        self.logger.info('start url detected as detail page url=%s', current)
                        break

                items = parse_list_page(result.text, current, self.cfg)
                page_diag['selector_matches'] = len(items)
                if items:
                    page_diag['mode'] = 'selector'
                else:
                    items = self._auto_items(result.text, current, max_docs - len(collected))
                    page_diag['fallback_candidates'] = len(items)
                    page_diag['mode'] = 'auto_discovery'
                    if items:
                        self.diagnostics['fallback_used'] = True
                        self.logger.warning('selector matched 0; auto discovery found=%s url=%s', len(items), current)

                new_count = 0
                for it in items:
                    if it.url not in collected:
                        collected[it.url] = it
                        new_count += 1
                        if len(collected) >= max_docs:
                            break

                page_diag['new_urls'] = new_count
                self.diagnostics['start_pages'].append(page_diag)
                empty_new_pages = empty_new_pages + 1 if new_count == 0 else 0
                if empty_new_pages >= 2:
                    break

                # Auto discovery is intentionally conservative: do not invent pagination.
                # Pagination continues only when a configured next-page strategy exists.
                next_url = get_next_url(result.text, current, self.cfg, page_no)
                if not next_url or next_url == current:
                    break
                current = next_url
                page_no += 1
                first_page = False

        self.diagnostics['discovered_urls'] = len(collected)
        return list(collected.values())[:max_docs]
