from __future__ import annotations

import re
from core.models import CleaningAction


def clean_noise(text: str, noise_cfg: dict) -> tuple[str, list[CleaningAction], list[str]]:
    if not text:
        return '', [], []
    actions: list[CleaningAction] = []
    issues: list[str] = []
    lines = text.split('\n')

    # Remove full lines matching configured regex patterns.
    patterns = noise_cfg.get('line_remove', [])
    kept = []
    for line in lines:
        matched = None
        for pattern in patterns:
            if re.search(pattern, line, flags=re.I):
                matched = pattern
                break
        if matched:
            actions.append(CleaningAction('LINE_NOISE', removed_text=line, note=matched))
            issues.append('NAVIGATION_NOISE')
        else:
            kept.append(line)
    text = '\n'.join(kept).strip()

    # High-confidence trailing markers: operate by lines to reduce false positives.
    def _matches_marker(line: str, marker: str) -> bool:
        import unicodedata
        l = unicodedata.normalize('NFKC', line).strip()
        m = unicodedata.normalize('NFKC', marker).strip()
        base = m.rstrip(':：').strip()
        if base in {'上一篇', '下一篇', '责任编辑'}:
            return re.match(r'^' + re.escape(base) + r'\s*[:：]', l) is not None
        if base in {'网站地图', '联系我们', 'ICP备案', '公安备案', '评论在审核通过后将对所有人可见'}:
            return l.startswith(base)
        return l.startswith(m)

    markers = noise_cfg.get('trailing_markers', [])
    if text and markers:
        raw_lines = [ln for ln in text.split('\n') if ln.strip()]
        # Only inspect the latter half (or last 12 lines) of a document.
        start_idx = max(0, min(len(raw_lines) // 2, len(raw_lines) - 12))
        cut_idx = None
        cut_marker = None
        for idx in range(start_idx, len(raw_lines)):
            for marker in markers:
                if _matches_marker(raw_lines[idx], marker):
                    cut_idx = idx
                    cut_marker = marker
                    break
            if cut_idx is not None:
                break
        if cut_idx is not None:
            removed_lines = raw_lines[cut_idx:]
            kept_lines = raw_lines[:cut_idx]
            removed = '\n'.join(removed_lines).strip()
            text = '\n'.join(kept_lines).strip()
            actions.append(CleaningAction('TRAILING_NOISE', removed_text=removed[:1000], note=f'marker={cut_marker}'))
            issues.append('TRAILING_NOISE')

    # Remove obvious social hashtag-only tail lines.
    cleaned_lines = []
    for line in text.split('\n'):
        if re.fullmatch(r'(#[^#\s]{1,30}\s*){2,}', line.strip()):
            actions.append(CleaningAction('TAG_POLLUTION', removed_text=line))
            issues.append('TAG_POLLUTION')
            continue
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines).strip()
    return text, [a for a in actions], sorted(set(issues))
