from __future__ import annotations

import shutil
from pathlib import Path


RUN_OUTPUT_DIRS = [
    'data/00_urls',
    'data/01_raw/html',
    'data/01_raw/json',
    'data/01_raw/meta',
    'data/02_extracted',
    'data/03_dedup',
    'data/04_clean',
    'data/05_validated',
    'data/06_final',
    'data/_internal',
    'data/failed',
    'data/rejected',
    'reports/samples',
]

RUN_REPORT_FILES = [
    'reports/crawl_summary.json',
    'reports/discovery_diagnostics.json',
    'reports/inspect_report.json',
    'reports/pipeline_stats.json',
    'reports/actions.json',
    'reports/quality_report.json',
]


def reset_run_outputs(root: Path) -> None:
    for rel in RUN_OUTPUT_DIRS:
        path = root / rel
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    for rel in RUN_REPORT_FILES:
        path = root / rel
        if path.exists():
            path.unlink()
