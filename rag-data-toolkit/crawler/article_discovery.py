from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from crawler.url_normalizer import normalize_url


STATIC_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico',
    '.css', '.js', '.json', '.xml', '.rss', '.mp3', '.mp4', '.avi', '.mov',
    '.zip', '.rar', '.7z', '.gz', '.tar', '.pdf', '.doc', '.docx', '.xls',
    '.xlsx', '.ppt', '.pptx', '.exe', '.apk', '.dmg', '.woff', '.woff2', '.ttf'
}

POSITIVE_PATH_WORDS = (
    '/article/', '/articles/', '/news/', '/content/', '/detail/', '/details/',
    '/info/', '/information/', '/zx/', '/xw/', '/dt/', '/gg/', '/notice/'
)
NEGATIVE_PATH_WORDS = (
    '/list/', '/lists/', '/channel/', '/category/', '/categories/', '/tag/',
    '/search/', '/about/', '/contact/', '/login/', '/register/', '/user/',
    '/video/', '/live/', '/special/', '/topic/'
)
ID_QUERY_KEYS = {'id', 'articleid', 'article_id', 'contentid', 'content_id', 'newsid', 'news_id'}


@dataclass
class LinkCandidate:
    url: str
    text: str
    score: int
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _host_matches(host: str, allowed_domain: str | None) -> bool:
    if not allowed_domain:
        return True
    host = host.split(':', 1)[0].lower().strip('.')
    allowed = allowed_domain.split(':', 1)[0].lower().strip('.')
    return host == allowed or host.endswith('.' + allowed) or allowed.endswith('.' + host)


def effective_allowed_domain(current_url: str, cfg: dict) -> tuple[str, str | None]:
    """Return the domain used for discovery and an optional warning.

    A copied demo config often still contains example.gov.cn while start_urls has
    already been changed. In that case using site.domain would silently filter
    every real link. Fall back to the current page host and report the mismatch.
    """
    current_host = urlsplit(current_url).netloc.split(':', 1)[0].lower()
    configured = (cfg.get('site', {}).get('domain') or '').strip().lower()
    if configured and _host_matches(current_host, configured):
        return configured, None
    if configured and not _host_matches(current_host, configured):
        return current_host, f'site.domain={configured} does not match start host={current_host}; using current host'
    return current_host, None


def _path_extension(path: str) -> str:
    leaf = path.rsplit('/', 1)[-1].lower()
    if '.' not in leaf:
        return ''
    return '.' + leaf.rsplit('.', 1)[-1]


def score_article_url(url: str, text: str = '', cfg: dict | None = None) -> tuple[int, list[str]]:
    cfg = cfg or {}
    auto = cfg.get('discovery', {})
    positive_words = tuple(auto.get('positive_path_words') or POSITIVE_PATH_WORDS)
    negative_words = tuple(auto.get('negative_path_words') or NEGATIVE_PATH_WORDS)

    parts = urlsplit(url)
    path = parts.path.lower()
    query = parse_qs(parts.query)
    score = 0
    reasons: list[str] = []

    ext = _path_extension(path)
    if ext in STATIC_EXTENSIONS:
        return -100, ['static_file']

    if ext == '.shtml':
        score += 5
        reasons.append('shtml')
    elif ext in {'.html', '.htm'}:
        score += 3
        reasons.append('html')

    if re.search(r'(?<!\d)\d{6,}(?!\d)', path):
        score += 4
        reasons.append('numeric_id')
    elif re.search(r'/\d{4,}(?:[./_-]|$)', path):
        score += 2
        reasons.append('numeric_segment')

    if re.search(r'/20\d{2}[/-](?:0?[1-9]|1[0-2])(?:[/-](?:0?[1-9]|[12]\d|3[01]))?', path):
        score += 2
        reasons.append('date_path')

    for word in positive_words:
        if word and word.lower() in path:
            score += 2
            reasons.append(f'positive:{word}')
            break

    for word in negative_words:
        if word and word.lower() in path:
            score -= 4
            reasons.append(f'negative:{word}')
            break

    if path in {'', '/'} or path.endswith('/'):
        score -= 3
        reasons.append('root_or_directory')

    if re.search(r'/(index|default)(?:_?\d+)?\.(?:s?html?|php|aspx?)$', path):
        score -= 4
        reasons.append('index_page')

    lowered_keys = {k.lower() for k in query}
    if lowered_keys & ID_QUERY_KEYS:
        score += 3
        reasons.append('id_query')

    cleaned_text = re.sub(r'\s+', ' ', text or '').strip()
    if 8 <= len(cleaned_text) <= 120:
        score += 1
        reasons.append('article_like_anchor_text')
    elif len(cleaned_text) > 180:
        score -= 1
        reasons.append('oversized_anchor_text')

    return score, reasons


def discover_links(html: str, current_url: str, cfg: dict, limit: int = 500) -> list[LinkCandidate]:
    soup = BeautifulSoup(html, 'lxml')
    site_domain, _ = effective_allowed_domain(current_url, cfg)
    allow_external = bool(cfg.get('discovery', {}).get('allow_external', False))
    min_score = int(cfg.get('discovery', {}).get('min_score', 3))
    seen: dict[str, LinkCandidate] = {}

    for a in soup.select('a[href]'):
        raw = (a.get('href') or '').strip()
        if not raw or raw.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            continue
        url = normalize_url(raw, current_url)
        if not url:
            continue
        parts = urlsplit(url)
        if parts.scheme not in {'http', 'https'}:
            continue
        if not allow_external and not _host_matches(parts.netloc, site_domain or urlsplit(current_url).netloc):
            continue
        text = a.get_text(' ', strip=True)
        score, reasons = score_article_url(url, text, cfg)
        if score < min_score:
            continue
        cand = LinkCandidate(url=url, text=text, score=score, reasons=reasons)
        old = seen.get(url)
        if old is None or cand.score > old.score:
            seen[url] = cand

    return sorted(seen.values(), key=lambda x: (-x.score, x.url))[:limit]


def count_page_links(html: str, current_url: str, cfg: dict) -> dict:
    soup = BeautifulSoup(html, 'lxml')
    site_domain, warning = effective_allowed_domain(current_url, cfg)
    total = 0
    same_domain = 0
    for a in soup.select('a[href]'):
        raw = (a.get('href') or '').strip()
        if not raw or raw.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            continue
        total += 1
        url = normalize_url(raw, current_url)
        if url and _host_matches(urlsplit(url).netloc, site_domain or urlsplit(current_url).netloc):
            same_domain += 1
    out = {'total_links': total, 'same_domain_links': same_domain, 'effective_domain': site_domain}
    if warning:
        out['domain_warning'] = warning
    return out
