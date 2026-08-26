from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'spm', 'from', 'source', '_t', 'timestamp'
}


def normalize_url(url: str, base_url: str | None = None) -> str:
    if not url:
        return ''
    if base_url:
        url = urljoin(base_url, url)
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or 'https'
    netloc = parts.netloc.lower()
    if not netloc:
        return ''
    if (scheme == 'http' and netloc.endswith(':80')) or (scheme == 'https' and netloc.endswith(':443')):
        netloc = netloc.rsplit(':', 1)[0]

    path = parts.path or '/'
    while '//' in path:
        path = path.replace('//', '/')
    if path != '/' and path.endswith('/'):
        path = path[:-1]

    query_pairs = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        if k.lower() not in TRACKING_PARAMS:
            query_pairs.append((k, v))
    query_pairs.sort()
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ''))
