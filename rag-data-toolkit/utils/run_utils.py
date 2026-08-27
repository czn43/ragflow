from __future__ import annotations

import shutil
from pathlib import Path

from utils.workspace import data_root, reports_root


RUN_OUTPUT_DIRS = [
    '00_urls',
    '01_raw/html',
    '01_raw/json',
    '01_raw/meta',
    '02_extracted',
    '03_dedup',
    '04_clean',
    '05_validated',
    '06_final',
    '_internal',
    'failed',
    'rejected',
]

RUN_REPORT_FILES = [
    'crawl_summary.json',
    'discovery_diagnostics.json',
    'inspect_report.json',
    'pipeline_stats.json',
    'actions.json',
    'quality_report.json',
]


def reset_run_outputs(root: Path) -> None:
    droot = data_root(root)
    rroot = reports_root(root)
    for rel in RUN_OUTPUT_DIRS:
        path = droot / rel
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    samples = rroot / 'samples'
    if samples.exists():
        shutil.rmtree(samples)
    samples.mkdir(parents=True, exist_ok=True)
    for rel in RUN_REPORT_FILES:
        path = rroot / rel
        if path.exists():
            path.unlink()
