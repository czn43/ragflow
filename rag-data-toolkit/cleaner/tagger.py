from __future__ import annotations


def generate_tags(doc: dict, cfg: dict) -> list[str]:
    rules = cfg.get('tag_rules', {}) or {}
    text_title = doc.get('title', '')
    text_category = doc.get('category', '') or ''
    text_content = doc.get('content', '')
    scored = []
    for tag, keywords in rules.items():
        score = 0
        for kw in keywords or []:
            if kw in text_title:
                score += 5
            if kw in text_category:
                score += 3
            if kw in text_content:
                score += 1
        if score > 0:
            scored.append((score, tag))
    scored.sort(key=lambda x: (-x[0], x[1]))
    max_tags = int(cfg.get('metadata', {}).get('max_tags', 5))
    return [tag for _, tag in scored[:max_tags]]
