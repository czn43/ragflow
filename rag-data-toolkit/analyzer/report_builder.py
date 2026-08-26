from pathlib import Path

from analyzer.statistics import build_statistics
from utils.file_utils import dump_json, load_json, read_jsonl


def build_report(root: Path) -> dict:
    docs = read_jsonl(root / 'data/05_validated/validated.jsonl')
    stats = load_json(root / 'reports/pipeline_stats.json', {})
    report = build_statistics(docs, stats)
    dump_json(root / 'reports/quality_report.json', report)
    return report
