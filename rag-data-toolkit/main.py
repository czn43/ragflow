from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from tqdm import tqdm

from analyzer.report_builder import build_report
from cleaner.pipeline import ProcessingPipeline
from crawler.detail_crawler import DetailCrawler
from crawler.http_client import HttpClient
from crawler.list_crawler import ListCrawler
from exporter.csv_exporter import export_preview_csv
from exporter.jsonl_exporter import export_final_jsonl
from utils.file_utils import dump_json, write_jsonl
from utils.logger import setup_logger

ROOT = Path(__file__).resolve().parent


def load_yaml(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def load_config(site_path: str) -> tuple[dict, dict]:
    site = load_yaml(ROOT / site_path) if not Path(site_path).is_absolute() else load_yaml(Path(site_path))
    app = load_yaml(ROOT / 'config/app.yaml')
    # app defaults, site overrides
    crawler_defaults = app.get('crawler', {})
    site.setdefault('crawler', {})
    for k, v in crawler_defaults.items():
        site['crawler'].setdefault(k, v)
    noise = load_yaml(ROOT / 'config/noise_rules.yaml')
    return site, noise


def make_http(cfg: dict) -> HttpClient:
    c = cfg.get('crawler', {})
    d = c.get('delay', {})
    return HttpClient(
        timeout=int(c.get('timeout', 15)),
        retries=int(c.get('retries', 3)),
        delay_min=float(d.get('min', 0.2)),
        delay_max=float(d.get('max', 0.8)),
        user_agent=c.get('user_agent'),
    )


def cmd_crawl(cfg: dict, max_pages: int, max_docs: int, logger) -> None:
    http = make_http(cfg)
    urls = ListCrawler(http, cfg, logger).discover(max_pages=max_pages, max_docs=max_docs)
    write_jsonl(ROOT / 'data/00_urls/urls.jsonl', urls)
    dump_json(ROOT / 'reports/crawl_summary.json', {'discovered_urls': len(urls)})
    logger.info('discovered urls=%s', len(urls))

    detail = DetailCrawler(http, cfg, logger, ROOT)
    success = 0
    for item in tqdm(urls, desc='抓取详情页', unit='篇'):
        raw = detail.crawl_one(item)
        if raw.http_status and raw.http_status < 400 and raw.raw_html_path:
            success += 1
    logger.info('detail crawl success=%s total=%s', success, len(urls))


def cmd_process(cfg: dict, noise: dict, logger) -> None:
    pipeline = ProcessingPipeline(ROOT, cfg, noise, logger)
    pipeline.run()


def cmd_analyze(logger) -> None:
    report = build_report(ROOT)
    logger.info('quality report final_count=%s', report.get('summary', {}).get('final_count'))


def cmd_export(logger) -> None:
    n1 = export_final_jsonl(ROOT)
    n2 = export_preview_csv(ROOT)
    logger.info('export final_jsonl=%s preview_csv=%s', n1, n2)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='RAG 比赛数据采集清洗工具 P0 第一版')
    sub = p.add_subparsers(dest='command', required=True)
    for name in ['crawl', 'process', 'analyze', 'export', 'all']:
        s = sub.add_parser(name)
        s.add_argument('--site', default='config/sites/demo.yaml', help='网站 YAML 配置')
        if name in {'crawl', 'all'}:
            s.add_argument('--max-pages', type=int, default=20)
            s.add_argument('--max-docs', type=int, default=100)
    return p


def main() -> int:
    args = build_parser().parse_args()
    logger = setup_logger(str(ROOT / 'logs/app.log'))
    try:
        cfg, noise = load_config(args.site)
        if args.command == 'crawl':
            cmd_crawl(cfg, args.max_pages, args.max_docs, logger)
        elif args.command == 'process':
            cmd_process(cfg, noise, logger)
        elif args.command == 'analyze':
            cmd_analyze(logger)
        elif args.command == 'export':
            cmd_export(logger)
        elif args.command == 'all':
            cmd_crawl(cfg, args.max_pages, args.max_docs, logger)
            cmd_process(cfg, noise, logger)
            cmd_analyze(logger)
            cmd_export(logger)
        return 0
    except Exception as e:
        logger.exception('fatal error: %s', e)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
