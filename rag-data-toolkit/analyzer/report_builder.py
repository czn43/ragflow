from pathlib import Path

from analyzer.statistics import build_statistics
from utils.file_utils import dump_json, load_json, read_jsonl
from utils.workspace import data_path, report_path


def build_report(root: Path) -> dict:
    docs = read_jsonl(data_path(root, '05_validated', 'validated.jsonl'))
    audits = read_jsonl(data_path(root, '_internal', 'record_audit.jsonl'))
    stats = load_json(report_path(root, 'pipeline_stats.json'), {})
    report = build_statistics(docs, stats, audits)
    dump_json(report_path(root, 'quality_report.json'), report)
    return report
