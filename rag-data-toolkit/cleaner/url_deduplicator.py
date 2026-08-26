from __future__ import annotations

from crawler.url_normalizer import normalize_url


def deduplicate_raw_documents(raw_docs: list[dict]) -> tuple[list[dict], list[dict]]:
    kept: dict[str, dict] = {}
    duplicates: list[dict] = []
    for doc in raw_docs:
        key = normalize_url(doc.get('source_url', ''))
        if not key:
            doc = dict(doc)
            doc['reject_reason'] = 'INVALID_URL'
            duplicates.append(doc)
            continue
        prev = kept.get(key)
        if not prev:
            kept[key] = doc
            continue
        # Keep latest crawl_time.
        if (doc.get('crawl_time') or '') > (prev.get('crawl_time') or ''):
            prev = dict(prev)
            prev['reject_reason'] = 'DUPLICATE_URL'
            duplicates.append(prev)
            kept[key] = doc
        else:
            dup = dict(doc)
            dup['reject_reason'] = 'DUPLICATE_URL'
            duplicates.append(dup)
    return list(kept.values()), duplicates
