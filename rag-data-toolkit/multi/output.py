from __future__ import annotations

import csv
import re
from pathlib import Path

from core.schema import exact_standard_record
from utils.file_utils import dump_json, write_jsonl


def safe_name(text: str, fallback: str) -> str:
    text = re.sub(r'[\\/:*?"<>|\r\n\t]+', '_', text or '').strip(' ._')
    text = re.sub(r'\s+', '_', text)
    return text[:80] or fallback


def export_combined(final_dir: Path, records: list[dict]) -> None:
    final_dir.mkdir(parents=True, exist_ok=True)
    docs = [exact_standard_record(x) for x in records]
    write_jsonl(final_dir / 'combined_final.jsonl', docs)

    split_dir = final_dir / 'json'
    split_dir.mkdir(parents=True, exist_ok=True)
    for old in split_dir.glob('*.json'):
        old.unlink()
    for idx, doc in enumerate(docs, 1):
        name = safe_name(doc.get('title') or '', f'article_{idx:04d}')
        dump_json(split_dir / f'{idx:04d}_{name}.json', doc)

    fields = ['sourceName', 'sourceUrl', 'title', 'category', 'publishTime', 'attachmentCount', 'contentChars']
    with (final_dir / 'final_preview.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for doc in docs:
            writer.writerow({
                'sourceName': doc.get('sourceName', ''),
                'sourceUrl': doc.get('sourceUrl', ''),
                'title': doc.get('title', ''),
                'category': doc.get('category', ''),
                'publishTime': doc.get('publishTime', ''),
                'attachmentCount': doc.get('attachmentCount', 0),
                'contentChars': len(doc.get('contentText') or ''),
            })
