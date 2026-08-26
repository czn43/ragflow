from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from core.models import UrlItem
from crawler.url_normalizer import normalize_url


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
        raise ValueError('site config list.item_selector is required')
    items = []
    for item in soup.select(item_selector):
        link_selector = list_cfg.get('link_selector', 'a')
        link = item.select_one(link_selector)
        if link is None or not link.get('href'):
            continue
        url = normalize_url(link.get('href'), current_url)
        if not url:
            continue
        title_selector = list_cfg.get('title_selector')
        title = _text(item.select_one(title_selector)) if title_selector else _text(link)
        date_selector = list_cfg.get('date_selector')
        publish_time = _text(item.select_one(date_selector)) if date_selector else None
        items.append(UrlItem(url=url, title=title, publish_time=publish_time, source_page=current_url))
    return items


def get_next_url(html: str, current_url: str, cfg: dict, page_no: int) -> str | None:
    p = cfg.get('pagination', {})
    ptype = p.get('type', 'next_link')
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


class ListCrawler:
    def __init__(self, http_client, cfg: dict, logger):
        self.http = http_client
        self.cfg = cfg
        self.logger = logger

    def discover(self, max_pages: int = 20, max_docs: int = 100) -> list[UrlItem]:
        starts = self.cfg.get('crawler', {}).get('start_urls') or []
        if not starts:
            raise ValueError('crawler.start_urls is empty')
        collected: dict[str, UrlItem] = {}
        for start in starts:
            current = normalize_url(start)
            page_no = 1
            empty_new_pages = 0
            while current and page_no <= max_pages and len(collected) < max_docs:
                result = self.http.get(current)
                self.logger.info('list page=%s url=%s status=%s', page_no, current, result.status_code)
                if not result.text or not result.status_code or result.status_code >= 400:
                    break
                items = parse_list_page(result.text, current, self.cfg)
                new_count = 0
                for it in items:
                    if it.url not in collected:
                        collected[it.url] = it
                        new_count += 1
                        if len(collected) >= max_docs:
                            break
                empty_new_pages = empty_new_pages + 1 if new_count == 0 else 0
                if empty_new_pages >= 2:
                    break
                next_url = get_next_url(result.text, current, self.cfg, page_no)
                if not next_url or next_url == current:
                    break
                current = next_url
                page_no += 1
        return list(collected.values())[:max_docs]
