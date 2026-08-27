from __future__ import annotations

import re
from pathlib import Path

from core.schema import exact_standard_record
from utils.file_utils import dump_json, read_jsonl, write_jsonl


def _safe_name(text: str, fallback: str) -> str:
    text = re.sub(r'[\\/:*?"<>|\r\n\t]+', '_', text or '').strip(' ._')
    text = re.sub(r'\s+', '_', text)
    return (text[:80] or fallback)


def export_final_jsonl(root: Path) -> int:
    docs = [exact_standard_record(x) for x in read_jsonl(root / 'data/05_validated/validated.jsonl')]
    write_jsonl(root / 'data/06_final/final.jsonl', docs)

    split_dir = root / 'data/06_final/json'
    split_dir.mkdir(parents=True, exist_ok=True)
    for old in split_dir.glob('*.json'):
        old.unlink()
    for idx, doc in enumerate(docs, 1):
        name = _safe_name(doc.get('title') or '', f'article_{idx:04d}')
        dump_json(split_dir / f'{idx:04d}_{name}.json', doc)
    return len(docs)
