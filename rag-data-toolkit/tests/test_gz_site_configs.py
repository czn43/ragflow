"""Config regression tests for the Guangzhou / Shenzhen education & talent sources."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / 'config' / 'sites'
TASK_PATH = ROOT / 'config' / 'tasks' / 'guangdong_education_talent_p0.yaml'


def load_site(filename: str) -> dict:
    with (SITE_DIR / filename).open(encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def load_task() -> dict:
    with TASK_PATH.open(encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def first_selector(cfg: dict, field: str) -> str:
    node = cfg.get('detail', {}).get(field)
    assert isinstance(node, dict), f'detail.{field} must be a mapping'
    selectors = node.get('selectors')
    assert isinstance(selectors, list) and selectors, f'detail.{field}.selectors must be a non-empty list'
    return selectors[0]


def test_gz_edu_policy_explain_config():
    cfg = load_site('gd_gz_edu_policy_explain.yaml')
    assert cfg['crawler']['start_urls'][0].startswith('https://jyj.gz.gov.cn/yw/zcjd/')
    assert cfg['list']['item_selector'] == 'div.news_list ul li'
    assert cfg['list']['link_selector'] == "a[href*='/content/post_']"
    assert cfg['list']['date_selector'] == 'span'
    assert cfg['pagination'] == {'type': 'next_link', 'next_selector': '.pagediv a.next'}
    assert first_selector(cfg, 'title') == '.content_title'
    assert first_selector(cfg, 'content') == '.content_article'
    assert cfg['metadata']['category'] == '教育与人才-广州教育-政策解读'


def test_gz_hrss_employment_covers_all_sibling_columns():
    cfg = load_site('gd_gz_hrss_employment.yaml')
    starts = cfg['crawler']['start_urls']
    assert len(starts) == 15, 'all 15 就业/人才 sibling columns must be covered'
    for path in ('/jy/', '/yjrcrh/', '/rsks/', '/gzzc/', '/gccrc/', '/lxry/', '/bsh/',
                 '/jxjy/', '/rczc/', '/sb/', '/ldyg/', '/jnts/', '/lhjy/', '/ylbx/', '/rsrcpx/'):
        assert any(path in url for url in starts), f'missing column {path}'
    assert cfg['list']['item_selector'] == 'ul.infoList li'
    assert cfg['list']['date_selector'] == 'span.time'
    assert cfg['pagination'] == {'type': 'next_link', 'next_selector': '.pagediv a.next'}
    assert first_selector(cfg, 'content') == '.content'
    assert first_selector(cfg, 'publish_time') == '.publishTime'
    assert cfg['metadata']['category'] == '教育与人才-广州就业人才'


def test_p0_task_registers_gz_sources_once():
    task = load_task()
    entries = [e for e in task.get('sites', []) if e.get('enabled') is True]
    counts: dict[str, int] = {}
    for e in entries:
        counts[e['id']] = counts.get(e['id'], 0) + 1
    expected = {
        'gd_gz_edu_policy_explain': 'config/sites/gd_gz_edu_policy_explain.yaml',
        'gd_gz_hrss_employment': 'config/sites/gd_gz_hrss_employment.yaml',
    }
    for site_id, path in expected.items():
        assert counts.get(site_id) == 1, f'{site_id} must be registered exactly once'
        match = next(e for e in entries if e['id'] == site_id)
        assert match['config'] == path
