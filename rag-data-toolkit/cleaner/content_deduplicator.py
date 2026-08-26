from __future__ import annotations


def deduplicate_documents(documents: list[dict]) -> tuple[list[dict], list[dict]]:
    kept: dict[str, dict] = {}
    duplicates: list[dict] = []
    for doc in documents:
        key = doc.get('content_hash')
        if not key:
            key = f"__nohash__:{doc.get('id')}"
        prev = kept.get(key)
        if not prev:
            kept[key] = doc
            continue
        # Prefer higher quality; tie -> earlier published date; then longer content.
        def score(d):
            return (
                int(d.get('quality_score') or 0),
                -(len(d.get('publish_time') or '9999-99-99')),
                int(d.get('char_count') or 0),
            )
        if score(doc) > score(prev):
            old = dict(prev)
            old['reject_reason'] = 'DUPLICATE_CONTENT'
            duplicates.append(old)
            kept[key] = doc
        else:
            dup = dict(doc)
            dup['reject_reason'] = 'DUPLICATE_CONTENT'
            duplicates.append(dup)
    return list(kept.values()), duplicates
