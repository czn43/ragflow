from __future__ import annotations

import argparse
import re
import shutil
from copy import deepcopy
from pathlib import Path

import yaml
from tqdm import tqdm

from analyzer.report_builder import build_report
from analyzer.statistics import build_statistics
from cleaner.pipeline import ProcessingPipeline
from crawler.detail_crawler import DetailCrawler
from crawler.http_client import HttpClient
from crawler.list_crawler import ListCrawler
from crawler.playwright_list_crawler import PlaywrightListCrawler
from exporter.csv_exporter import export_preview_csv
from exporter.jsonl_exporter import export_final_jsonl
from multi.merger import SiteBundle, merge_site_records
from multi.output import export_combined
from utils.file_utils import dump_json, load_json, read_jsonl, write_jsonl
from utils.logger import setup_logger
from core.schema import exact_standard_record
from utils.run_utils import reset_run_outputs
from utils.workspace import data_path, report_path, mark_flat_workspace

ROOT = Path(__file__).resolve().parent
VERSION = '1.9.1'


def load_yaml(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def resolve_project_path(path_text: str) -> Path:
    p = Path(path_text)
    return p if p.is_absolute() else ROOT / p


def resolve_site_path(site_path: str) -> Path:
    return resolve_project_path(site_path)


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


def deep_merge(base: dict, override: dict | None) -> dict:
    out = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


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
    if pagination_type in {'playwright_click', 'playwright_load_more'}:
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
        print(f"Pagination type: {report.get('pagination_type')}")
        print(f"Configured selector matches: {report.get('selector_matches', 0)}")
        if report.get('pagination_type') == 'playwright_load_more':
            print(f"Load-more selector matches: {report.get('load_more_selector_matches', 0)}")
            print(f"Fallback next-link matches: {report.get('fallback_next_link_matches', 0)}")
        else:
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


def cmd_crawl(
    cfg: dict,
    max_pages: int,
    max_docs: int,
    logger,
    clean_run: bool = False,
    work_root: Path = ROOT,
) -> None:
    if clean_run:
        reset_run_outputs(work_root)
        logger.info('clean-run: previous run outputs cleared root=%s', work_root)

    http = make_http(cfg)
    pagination_type = str(cfg.get('pagination', {}).get('type', '')).lower()
    if pagination_type in {'playwright_click', 'playwright_load_more'}:
        crawler = PlaywrightListCrawler(cfg, logger)
    else:
        crawler = ListCrawler(http, cfg, logger)
    urls = crawler.discover(max_pages=max_pages, max_docs=max_docs)
    write_jsonl(data_path(work_root, '00_urls', 'urls.jsonl'), urls)
    dump_json(report_path(work_root, 'crawl_summary.json'), {
        'version': VERSION,
        'discovered_urls': len(urls),
        'fallback_used': crawler.diagnostics.get('fallback_used', False),
        'pagination_type': pagination_type,
    })
    dump_json(report_path(work_root, 'discovery_diagnostics.json'), crawler.diagnostics)
    logger.info('discovered urls=%s fallback_used=%s root=%s', len(urls), crawler.diagnostics.get('fallback_used'), work_root)

    if not urls:
        logger.warning(
            'No URLs discovered. Run inspect for this site and review its selectors/pagination.'
        )

    detail = DetailCrawler(http, cfg, logger, work_root)
    success = 0
    try:
        for item in tqdm(urls, desc='抓取详情页', unit='篇'):
            raw = detail.crawl_one(item)
            if raw.http_status and raw.http_status < 400 and raw.raw_html_path:
                success += 1
    finally:
        detail.close()

    raw_records = []
    for p in sorted(data_path(work_root, '01_raw', 'json').glob('*.json')):
        d = load_json(p)
        if d:
            raw_records.append(exact_standard_record(d))
    write_jsonl(data_path(work_root, '01_raw', 'raw.jsonl'), raw_records)
    logger.info('detail crawl success=%s total=%s raw_json=%s root=%s', success, len(urls), len(raw_records), work_root)


def cmd_process(cfg: dict, noise: dict, logger, work_root: Path = ROOT) -> None:
    pipeline = ProcessingPipeline(work_root, cfg, noise, logger)
    pipeline.run()


def cmd_analyze(logger, work_root: Path = ROOT) -> dict:
    report = build_report(work_root)
    logger.info('quality report final_count=%s root=%s', report.get('summary', {}).get('final_count'), work_root)
    return report


def cmd_export(logger, work_root: Path = ROOT) -> None:
    n1 = export_final_jsonl(work_root)
    n2 = export_preview_csv(work_root)
    logger.info('export final_jsonl=%s preview_csv=%s root=%s', n1, n2, work_root)


def sanitize_id(value: str) -> str:
    value = re.sub(r'[^0-9A-Za-z._-]+', '_', str(value or '')).strip('._-')
    return value or 'task'


def load_task(task_path: str) -> tuple[dict, Path]:
    path = resolve_project_path(task_path)
    if not path.exists():
        raise FileNotFoundError(f'task config not found: {path}')
    cfg = load_yaml(path)
    if not isinstance(cfg.get('sites'), list):
        raise ValueError('task YAML must contain sites: [...]')
    return cfg, path


def _selected_sites(task_cfg: dict, only_sites: set[str] | None = None) -> list[dict]:
    out = []
    for idx, entry in enumerate(task_cfg.get('sites') or []):
        if not isinstance(entry, dict) or not entry.get('enabled', True):
            continue
        site_id = sanitize_id(entry.get('id') or f'site_{idx + 1}')
        if only_sites and site_id not in only_sites:
            continue
        item = deepcopy(entry)
        item['_site_id'] = site_id
        item['_order'] = idx
        out.append(item)
    return out


def _task_paths(task_cfg: dict) -> tuple[str, Path, Path, Path]:
    task = task_cfg.get('task') or {}
    task_id = sanitize_id(task.get('id') or task.get('name') or 'competition_task')
    runs_root = ROOT / 'data' / 'runs' / task_id
    final_root = ROOT / 'data' / 'final' / task_id
    reports_root = ROOT / 'reports' / 'tasks' / task_id
    return task_id, runs_root, final_root, reports_root


def merge_task_outputs(task_cfg: dict, logger, only_sites: set[str] | None = None) -> dict:
    task_id, runs_root, final_root, task_reports_root = _task_paths(task_cfg)
    entries = _selected_sites(task_cfg, only_sites=None)  # merge all available enabled site outputs
    bundles: list[SiteBundle] = []
    site_rows = []

    for entry in entries:
        site_id = entry['_site_id']
        site_root = runs_root / site_id
        mark_flat_workspace(site_root)
        final_file = site_root / '06_final' / 'final.jsonl'
        records = read_jsonl(final_file)
        if not final_file.exists():
            site_rows.append({
                'siteId': site_id,
                'siteName': entry.get('name') or site_id,
                'status': 'missing',
                'finalCount': 0,
                'finalFile': str(final_file.relative_to(ROOT)).replace('\\', '/'),
            })
            continue
        bundles.append(SiteBundle(
            site_id=site_id,
            site_name=str(entry.get('name') or site_id),
            priority=int(entry.get('priority', 100)),
            records=records,
        ))
        q = load_json(site_root / 'reports' / 'quality_report.json', {}) or {}
        site_rows.append({
            'siteId': site_id,
            'siteName': entry.get('name') or site_id,
            'priority': int(entry.get('priority', 100)),
            'status': 'ready',
            'finalCount': len(records),
            'qualitySummary': q.get('summary', {}),
            'finalFile': str(final_file.relative_to(ROOT)).replace('\\', '/'),
        })

    if not bundles:
        raise RuntimeError(f'no site final.jsonl files are available for task {task_id}')

    merge_cfg = task_cfg.get('merge') or {}
    combined, duplicates, merge_stats = merge_site_records(
        bundles,
        dedup_url=bool(merge_cfg.get('dedup_url', True)),
        dedup_content=bool(merge_cfg.get('dedup_content', True)),
    )

    if final_root.exists():
        shutil.rmtree(final_root)
    final_root.mkdir(parents=True, exist_ok=True)
    export_combined(final_root, combined)
    write_jsonl(final_root / 'global_duplicates.jsonl', duplicates)

    quality = build_statistics(combined, {
        'multi_source_input': merge_stats['input_count'],
        'global_duplicate_count': merge_stats['duplicate_count'],
        'site_count': len(bundles),
    }, [])
    task_reports_root.mkdir(parents=True, exist_ok=True)
    dump_json(task_reports_root / 'quality_report.json', quality)

    summary = {
        'version': VERSION,
        'taskId': task_id,
        'taskName': (task_cfg.get('task') or {}).get('name') or task_id,
        'siteCountConfigured': len(entries),
        'siteCountMerged': len(bundles),
        'sites': site_rows,
        'merge': {
            'dedupUrl': bool(merge_cfg.get('dedup_url', True)),
            'dedupContent': bool(merge_cfg.get('dedup_content', True)),
            **merge_stats,
        },
        'outputs': {
            'combinedFinal': str((final_root / 'combined_final.jsonl').relative_to(ROOT)).replace('\\', '/'),
            'splitJsonDir': str((final_root / 'json').relative_to(ROOT)).replace('\\', '/'),
            'previewCsv': str((final_root / 'final_preview.csv').relative_to(ROOT)).replace('\\', '/'),
            'globalDuplicates': str((final_root / 'global_duplicates.jsonl').relative_to(ROOT)).replace('\\', '/'),
            'qualityReport': str((task_reports_root / 'quality_report.json').relative_to(ROOT)).replace('\\', '/'),
        },
    }
    dump_json(task_reports_root / 'multi_summary.json', summary)
    logger.info('multi merge task=%s sites=%s input=%s final=%s duplicates=%s', task_id, len(bundles), merge_stats['input_count'], len(combined), len(duplicates))
    return summary


def cmd_multi(
    task_path: str,
    logger,
    *,
    clean_run: bool = False,
    resume: bool = False,
    only_sites_text: str | None = None,
    fail_fast: bool = False,
) -> dict:
    task_cfg, resolved_task_path = load_task(task_path)
    task_id, runs_root, final_root, task_reports_root = _task_paths(task_cfg)
    only_sites = {sanitize_id(x.strip()) for x in (only_sites_text or '').split(',') if x.strip()} or None
    entries = _selected_sites(task_cfg, only_sites=only_sites)
    if not entries:
        raise ValueError('no enabled sites selected in task YAML')

    if clean_run:
        if runs_root.exists():
            shutil.rmtree(runs_root)
        if final_root.exists():
            shutil.rmtree(final_root)
        if task_reports_root.exists():
            shutil.rmtree(task_reports_root)
        logger.info('multi clean-run cleared task=%s', task_id)

    runs_root.mkdir(parents=True, exist_ok=True)
    task_reports_root.mkdir(parents=True, exist_ok=True)
    execution = []

    print(f'\n=== Multi Source Task: {(task_cfg.get("task") or {}).get("name") or task_id} ({task_id}) ===')
    print(f'Task config: {resolved_task_path}')
    print(f'Sites selected: {len(entries)}')

    for idx, entry in enumerate(entries, 1):
        site_id = entry['_site_id']
        site_name = str(entry.get('name') or site_id)
        site_root = runs_root / site_id
        mark_flat_workspace(site_root)
        final_file = site_root / '06_final' / 'final.jsonl'
        print(f'\n[{idx}/{len(entries)}] {site_id} - {site_name}')

        if resume and final_file.exists():
            count = len(read_jsonl(final_file))
            logger.info('multi resume skip site=%s final_count=%s', site_id, count)
            execution.append({'siteId': site_id, 'siteName': site_name, 'status': 'skipped_existing', 'finalCount': count})
            print(f'  skip existing final: {count}')
            continue

        try:
            cfg, noise = load_config(str(entry.get('config') or ''))
            cfg = deep_merge(cfg, entry.get('overrides') or {})
            # Every rerun of a selected site starts from a clean isolated run directory.
            reset_run_outputs(site_root)
            max_pages = int(entry.get('max_pages', 20))
            max_docs = int(entry.get('max_docs', 100))
            cmd_crawl(cfg, max_pages, max_docs, logger, clean_run=False, work_root=site_root)
            cmd_process(cfg, noise, logger, work_root=site_root)
            q = cmd_analyze(logger, work_root=site_root)
            cmd_export(logger, work_root=site_root)
            final_count = len(read_jsonl(final_file))
            execution.append({
                'siteId': site_id,
                'siteName': site_name,
                'status': 'success',
                'finalCount': final_count,
                'qualitySummary': q.get('summary', {}),
            })
            print(f'  success final={final_count}')
        except Exception as exc:
            logger.exception('multi site failed site=%s error=%s', site_id, exc)
            execution.append({'siteId': site_id, 'siteName': site_name, 'status': 'failed', 'error': str(exc)})
            print(f'  FAILED: {exc}')
            if fail_fast or bool((task_cfg.get('task') or {}).get('fail_fast', False)):
                raise

    dump_json(task_reports_root / 'execution.json', {
        'version': VERSION,
        'taskId': task_id,
        'taskConfig': str(resolved_task_path.relative_to(ROOT)).replace('\\', '/') if resolved_task_path.is_relative_to(ROOT) else str(resolved_task_path),
        'execution': execution,
    })

    # Merge every enabled site that currently has a final output. This means --sites can
    # be used to rerun only one source while preserving and reusing other successful runs.
    summary = merge_task_outputs(task_cfg, logger)
    print('\n=== Multi Source Merge ===')
    print(f"Input: {summary['merge']['input_count']}")
    print(f"Global duplicates: {summary['merge']['duplicate_count']}")
    print(f"Final: {summary['merge']['final_count']}")
    print(f"Output: {summary['outputs']['combinedFinal']}")
    return summary


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

    multi_p = sub.add_parser('multi', help='按 task YAML 依次运行多个数据源，并做跨站合并去重')
    multi_p.add_argument('--task', required=True, help='多数据源任务 YAML，例如 config/tasks/low_altitude.yaml')
    multi_p.add_argument('--clean-run', action='store_true', help='清空该 task 以前的所有站点运行结果和合并结果')
    multi_p.add_argument('--resume', action='store_true', help='已有站点 final.jsonl 时跳过该站，适合断点续跑')
    multi_p.add_argument('--sites', help='只重跑指定 site id，逗号分隔；完成后仍会合并其他已有站点结果')
    multi_p.add_argument('--fail-fast', action='store_true', help='任一站失败立即停止；默认继续其他站')

    merge_p = sub.add_parser('merge', help='不重新爬取，只把 task 下已有各站 final.jsonl 重新合并')
    merge_p.add_argument('--task', required=True, help='多数据源任务 YAML')
    return p


def main() -> int:
    args = build_parser().parse_args()
    logger = setup_logger(str(ROOT / 'logs/app.log'))
    try:
        if args.command == 'multi':
            cmd_multi(
                args.task,
                logger,
                clean_run=args.clean_run,
                resume=args.resume,
                only_sites_text=args.sites,
                fail_fast=args.fail_fast,
            )
            return 0
        if args.command == 'merge':
            task_cfg, _ = load_task(args.task)
            summary = merge_task_outputs(task_cfg, logger)
            print(f"Merged final: {summary['outputs']['combinedFinal']}")
            print(f"Final count: {summary['merge']['final_count']}")
            return 0

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
