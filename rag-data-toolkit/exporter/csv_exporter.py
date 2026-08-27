from __future__ import annotations

import csv
from pathlib import Path
from utils.file_utils import read_jsonl


def export_preview_csv(root: Path) -> int:
    docs = read_jsonl(root / 'data/05_validated/validated.jsonl')
    path = root / 'data/06_final/final_preview.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ['sourceName', 'sourceUrl', 'title', 'category', 'publishTime', 'attachmentCount', 'contentChars']
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in docs:
            w.writerow({
                'sourceName': d.get('sourceName', ''),
                'sourceUrl': d.get('sourceUrl', ''),
                'title': d.get('title', ''),
                'category': d.get('category', ''),
                'publishTime': d.get('publishTime', ''),
                'attachmentCount': d.get('attachmentCount', 0),
                'contentChars': len(d.get('contentText') or ''),
            })
    return len(docs)
