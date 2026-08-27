from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from cleaner.text_normalizer import normalize_text
from core.schema import exact_standard_record
from crawler.url_normalizer import normalize_url
from utils.hash_utils import make_content_hash


@dataclass
class SiteBundle:
    site_id: str
    site_name: str
    priority: int
    records: list[dict[str, Any]]


def merge_site_records(
    bundles: list[SiteBundle],
    *,
    dedup_url: bool = True,
    dedup_content: bool = True,
) -> tuple[list[dict], list[dict], dict]:
    """Merge site finals using the fixed eight-field competition schema.

    Sites are processed by ascending priority and then task-file order. Therefore,
    when the same article exists on several sites, a lower numeric priority wins.
    """
    ordered = sorted(enumerate(bundles), key=lambda x: (x[1].priority, x[0]))
    kept: list[dict] = []
    duplicates: list[dict] = []
    seen_urls: dict[str, dict] = {}
    seen_contents: dict[str, dict] = {}
    per_site_input: Counter[str] = Counter()
    per_site_kept: Counter[str] = Counter()

    for _, bundle in ordered:
        for raw in bundle.records:
            per_site_input[bundle.site_id] += 1
            doc = exact_standard_record(raw)
            normalized_url = normalize_url(doc.get('sourceUrl') or '')
            doc['sourceUrl'] = normalized_url or doc.get('sourceUrl') or ''

            if dedup_url and normalized_url and normalized_url in seen_urls:
                kept_info = seen_urls[normalized_url]
                duplicates.append({
                    **doc,
                    '_rejectReason': 'GLOBAL_DUPLICATE_URL',
                    '_siteId': bundle.site_id,
                    '_siteName': bundle.site_name,
                    '_keptSiteId': kept_info['site_id'],
                    '_keptSourceUrl': kept_info['source_url'],
                })
                continue

            content_norm = normalize_text(doc.get('contentText') or '')
            content_hash = make_content_hash(content_norm) if content_norm else ''
            if dedup_content and content_hash and content_hash in seen_contents:
                kept_info = seen_contents[content_hash]
                duplicates.append({
                    **doc,
                    '_rejectReason': 'GLOBAL_DUPLICATE_CONTENT',
                    '_siteId': bundle.site_id,
                    '_siteName': bundle.site_name,
                    '_keptSiteId': kept_info['site_id'],
                    '_keptSourceUrl': kept_info['source_url'],
                })
                continue

            kept.append(doc)
            per_site_kept[bundle.site_id] += 1
            info = {
                'site_id': bundle.site_id,
                'site_name': bundle.site_name,
                'source_url': doc.get('sourceUrl') or '',
            }
            if normalized_url:
                seen_urls[normalized_url] = info
            if content_hash:
                seen_contents[content_hash] = info

    reason_counts = Counter(d.get('_rejectReason') or 'UNKNOWN' for d in duplicates)
    stats = {
        'input_count': sum(per_site_input.values()),
        'final_count': len(kept),
        'duplicate_count': len(duplicates),
        'duplicate_reasons': dict(reason_counts),
        'per_site_input': dict(per_site_input),
        'per_site_kept_after_global_dedup': dict(per_site_kept),
    }
    return kept, duplicates, stats
