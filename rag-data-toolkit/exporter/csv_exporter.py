import csv
from pathlib import Path
from utils.file_utils import read_jsonl


def export_preview_csv(root: Path) -> int:
    docs = read_jsonl(root / 'data/05_validated/validated.jsonl')
    path = root / 'data/06_final/final_preview.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ['id', 'title', 'publish_time', 'source_name', 'category', 'char_count', 'quality_score', 'source_url']
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in docs:
            w.writerow({k: d.get(k) for k in fields})
    return len(docs)
