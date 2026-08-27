from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from tqdm import tqdm

from analyzer.report_builder import build_report
from cleaner.pipeline import ProcessingPipeline
from crawler.detail_crawler import DetailCrawler
from crawler.http_client import HttpClient
from crawler.list_crawler import ListCrawler
from crawler.playwright_list_crawler import PlaywrightListCrawler
from exporter.csv_exporter import export_preview_csv
from exporter.jsonl_exporter import export_final_jsonl
from utils.file_utils import dump_json, load_json, write_jsonl
from utils.logger import setup_logger
from core.schema import exact_standard_record
from utils.run_utils import reset_run_outputs

ROOT = Path(__file__).resolve().parent
VERSION = '1.6.0'


def load_yaml(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def resolve_site_path(site_path: str) -> Path:
    p = Path(site_path)
    return p if p.is_absolute() else ROOT / p


def load_config(site_path: str) -> tuple[dict, dict]:
    path = resolve_site_path(site_path)
    if not path.exists():
        raise FileNotFoundError(f'site config not found: {path}')
    site = load_yaml(path)
    app = load_yaml(ROOT / 'config/app.yaml')
    crawler_defaults = app.get('crawler', {})
    site.setdefault('crawler', {})
    for k, v in crawler_defaults.items():
        site['crawler'].setdefault(k, v)
    site.setdefault('discovery', {})
    for k, v in app.get('discovery', {}).items():
        site['discovery'].setdefault(k, v)
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


def cmd_inspect(cfg: dict, url: str | None, validate_top: int, logger) -> dict:
    starts = cfg.get('crawler', {}).get('start_urls') or []
    target = url or (starts[0] if starts else None)
    if not target:
        raise ValueError('inspect requires --url or crawler.start_urls')
    pagination_type = str(cfg.get('pagination', {}).get('type', '')).lower()
    if pagination_type == 'playwright_click':
        crawler = PlaywrightListCrawler(cfg, logger)
        report = crawler.inspect_url(target)
    else:
        crawler = ListCrawler(make_http(cfg), cfg, logger)
        report = crawler.inspect_url(target, validate_top=validate_top)
    dump_json(ROOT / 'reports/inspect_report.json', report)

    print('\n=== Inspect Result ===')
    print(f"URL: {report.get('url')}")
    print(f"HTTP: {report.get('http_status')}")
    if report.get('domain_warning'):
        print(f"WARNING: {report['domain_warning']}")
    if report.get('render_engine') == 'playwright':
        print('Render engine: Playwright')
        print(f"Browser source: {report.get('browser_source')}")
        if report.get('browser_executable'):
            print(f"Browser executable: {report.get('browser_executable')}")
        print(f"Configured selector matches: {report.get('selector_matches', 0)}")
        print(f"Next selector matches: {report.get('next_selector_matches', 0)}")
        print('Sample items:')
        for i, c in enumerate(report.get('sample_items', [])[:10], 1):
            print(f"  {i:02d}. {c.get('url')}  {(c.get('title') or '')[:50]}")
    else:
        print(f"Links: {report.get('total_links', 0)}")
        print(f"Same-domain links: {report.get('same_domain_links', 0)}")
        print(f"Configured selector matches: {report.get('selector_matches', 0)}")
        print(f"Looks like detail page: {report.get('looks_like_detail_page', False)}")
        print(f"Auto-discovery candidates: {report.get('candidate_count', 0)}")
        print('Top candidates:')
        for i, c in enumerate(report.get('top_candidates', [])[:10], 1):
            print(f"  {i:02d}. score={c['score']:>2} {c['url']}  {c.get('text', '')[:50]}")
    print(f"Report: {ROOT / 'reports/inspect_report.json'}")
    return report


def cmd_crawl(cfg: dict, max_pages: int, max_docs: int, logger, clean_run: bool = False) -> None:
    if clean_run:
        reset_run_outputs(ROOT)
        logger.info('clean-run: previous run outputs cleared')

    http = make_http(cfg)
    pagination_type = str(cfg.get('pagination', {}).get('type', '')).lower()
    if pagination_type == 'playwright_click':
        crawler = PlaywrightListCrawler(cfg, logger)
    else:
        crawler = ListCrawler(http, cfg, logger)
    urls = crawler.discover(max_pages=max_pages, max_docs=max_docs)
    write_jsonl(ROOT / 'data/00_urls/urls.jsonl', urls)
    dump_json(ROOT / 'reports/crawl_summary.json', {
        'version': VERSION,
        'discovered_urls': len(urls),
        'fallback_used': crawler.diagnostics.get('fallback_used', False),
        'pagination_type': pagination_type,
    })
    dump_json(ROOT / 'reports/discovery_diagnostics.json', crawler.diagnostics)
    logger.info('discovered urls=%s fallback_used=%s', len(urls), crawler.diagnostics.get('fallback_used'))

    if not urls:
        logger.warning(
            'No URLs discovered. Run: python main.py inspect --site <config> --url <start_url> '
            'and review reports/inspect_report.json'
        )

    detail = DetailCrawler(http, cfg, logger, ROOT)
    success = 0
    try:
        for item in tqdm(urls, desc='抓取详情页', unit='篇'):
            raw = detail.crawl_one(item)
            if raw.http_status and raw.http_status < 400 and raw.raw_html_path:
                success += 1
    finally:
        detail.close()

    raw_records = []
    for p in sorted((ROOT / 'data/01_raw/json').glob('*.json')):
        d = load_json(p)
        if d:
            raw_records.append(exact_standard_record(d))
    write_jsonl(ROOT / 'data/01_raw/raw.jsonl', raw_records)
    logger.info('detail crawl success=%s total=%s raw_json=%s', success, len(urls), len(raw_records))


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


def add_site_arg(s: argparse.ArgumentParser) -> None:
    s.add_argument('--site', default='config/sites/demo.yaml', help='网站 YAML 配置')


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=f'RAG 比赛数据采集清洗工具 v{VERSION}')
    p.add_argument('--version', action='version', version=VERSION)
    sub = p.add_subparsers(dest='command', required=True)

    inspect_p = sub.add_parser('inspect', help='诊断网页结构、Selector、候选文章链接和详情页可能性')
    add_site_arg(inspect_p)
    inspect_p.add_argument('--url', help='要诊断的 URL；省略则取 start_urls 第一项')
    inspect_p.add_argument('--validate-top', type=int, default=5, help='实际抓取验证前 N 个候选链接')

    for name in ['crawl', 'process', 'analyze', 'export', 'all']:
        s = sub.add_parser(name)
        add_site_arg(s)
        if name in {'crawl', 'all'}:
            s.add_argument('--max-pages', type=int, default=20)
            s.add_argument('--max-docs', type=int, default=100)
            s.add_argument('--clean-run', action='store_true', help='开始前清理上一次 data/reports 运行产物')
    return p


def main() -> int:
    args = build_parser().parse_args()
    logger = setup_logger(str(ROOT / 'logs/app.log'))
    try:
        cfg, noise = load_config(args.site)
        if args.command == 'inspect':
            cmd_inspect(cfg, args.url, args.validate_top, logger)
        elif args.command == 'crawl':
            cmd_crawl(cfg, args.max_pages, args.max_docs, logger, args.clean_run)
        elif args.command == 'process':
            cmd_process(cfg, noise, logger)
        elif args.command == 'analyze':
            cmd_analyze(logger)
        elif args.command == 'export':
            cmd_export(logger)
        elif args.command == 'all':
            cmd_crawl(cfg, args.max_pages, args.max_docs, logger, args.clean_run)
            cmd_process(cfg, noise, logger)
            cmd_analyze(logger)
            cmd_export(logger)
        return 0
    except Exception as e:
        logger.exception('fatal error: %s', e)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
