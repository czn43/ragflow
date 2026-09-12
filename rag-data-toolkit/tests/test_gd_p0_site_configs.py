"""Config regression tests for the Guangdong P0 education/talent sources.

These guard the three configs repaired on 2026-09-12. They are intentionally
network-free: they assert the YAML uses the fields the crawler and extractor
actually read, and that the list entries point at real subcolumns rather than
JS-redirect stubs or retired URLs.
"""
from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[1] / 'config' / 'sites'

# The gkmlpt address returned HTTP 404 on 2026-09-12 and must not come back.
DEAD_GRADUATE_URL = 'https://hrss.gd.gov.cn/gkmlpt/content/4/4725/post_4725709.html'


def load_site(filename: str) -> dict:
    with (CONFIG_DIR / filename).open(encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def detail_selectors(cfg: dict, field: str) -> list[str]:
    node = cfg.get('detail', {}).get(field)
    assert isinstance(node, dict), f'detail.{field} must be a mapping (parser reads detail.{field}.selectors)'
    selectors = node.get('selectors')
    assert isinstance(selectors, list) and selectors, f'detail.{field}.selectors must be a non-empty list'
    return selectors


def test_graduate_policy_uses_live_detail_url():
    cfg = load_site('gd_seed_graduate_policy.yaml')
    starts = cfg.get('crawler', {}).get('start_urls') or []
    assert starts, 'graduate policy start_urls must not be empty'
    assert starts[0] != DEAD_GRADUATE_URL, 'graduate policy still points at the retired gkmlpt URL'
    assert 'hrss.gd.gov.cn' in starts[0]
    assert str(cfg.get('crawler', {}).get('start_mode', '')).lower() == 'detail'


def test_graduate_policy_detail_fields_are_parser_readable():
    cfg = load_site('gd_seed_graduate_policy.yaml')
    for field in ('title', 'content', 'publish_time'):
        detail_selectors(cfg, field)


def test_edu_policy_list_entries_are_real_subcolumns():
    cfg = load_site('gd_edu_policy.yaml')
    starts = cfg.get('crawler', {}).get('start_urls') or []
    assert len(starts) >= 2, 'edu policy must cover at least the normative-doc and local-policy subcolumns'
    for url in starts:
        assert '/zwgknew/jyzcfg/' in url, f'unexpected list entry {url}'
        assert url.endswith('index.html'), f'list entry must be a subcolumn index page: {url}'
    list_cfg = cfg.get('list', {})
    assert list_cfg.get('item_selector'), 'edu policy must configure a list item selector'
    assert 'post_' in str(list_cfg.get('link_selector', '')), 'link selector must target /content/post_*.html'


def test_edu_policy_detail_fields_are_parser_readable():
    cfg = load_site('gd_edu_policy.yaml')
    for field in ('title', 'content', 'publish_time', 'source'):
        detail_selectors(cfg, field)


def test_edu_explain_detail_uses_nested_fields_only():
    cfg = load_site('gd_edu_explain.yaml')
    detail = cfg.get('detail', {})
    stale = ('title_selector', 'content_selector', 'date_selector', 'attachment_selector', 'related_selector')
    for field in stale:
        assert field not in detail, f'edu explain detail still has the unread flat field {field}'
    for field in ('title', 'content', 'publish_time', 'source'):
        detail_selectors(cfg, field)


def test_extractor_reads_nested_detail_fields():
    """Prove the nested schema is what the parser consumes, not the flat one."""
    from extractor.html_extractor import extract_by_rule

    html = (
        '<html><body>'
        '<h1 class="t">标题</h1>'
        f'<div class="body">正文内容{"字" * 200}</div>'
        '<span class="time">时间：2026-07-07</span>'
        '</body></html>'
    )
    cfg = {
        'detail': {
            'min_content_chars': 50,
            'title': {'selectors': ['.t']},
            'content': {'selectors': ['.body']},
            'publish_time': {'selectors': ['.time'], 'regex_extract': r'(\d{4}-\d{1,2}-\d{1,2})'},
        }
    }
    result = extract_by_rule(html, cfg)
    assert result.extraction_method == 'rule'
    assert result.title == '标题'
    assert result.publish_time == '2026-07-07'
    assert '正文内容' in (result.content or '')


def test_edu_development_plan_config_is_parser_readable():
    cfg = load_site('gd_edu_development_plan.yaml')
    starts = cfg.get('crawler', {}).get('start_urls') or []
    assert starts and '/zwgknew/jyfzgh/' in starts[0]
    list_cfg = cfg.get('list', {})
    assert list_cfg.get('item_selector'), 'development plan must configure a list item selector'
    assert 'post_' in str(list_cfg.get('link_selector', '')), 'link selector must target /content/post_*.html'
    assert cfg.get('pagination') == {'type': 'next_link', 'next_selector': '.pages a.next'}
    for field in ('title', 'content', 'publish_time', 'source'):
        detail_selectors(cfg, field)


def test_p0_task_registers_development_plan_once():
    task_path = CONFIG_DIR.parent / 'tasks' / 'guangdong_education_talent_p0.yaml'
    with task_path.open(encoding='utf-8') as f:
        task = yaml.safe_load(f) or {}
    entries = [e for e in task.get('sites', []) if e.get('id') == 'gd_edu_development_plan']
    assert len(entries) == 1, 'development plan must be registered exactly once'
    assert entries[0]['config'] == 'config/sites/gd_edu_development_plan.yaml'
    assert entries[0]['enabled'] is True

