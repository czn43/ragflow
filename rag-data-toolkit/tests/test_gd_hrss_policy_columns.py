"""Regression tests for the three Guangdong HRSS employment-policy columns.

The national-policy column indexes articles hosted on ``www.mohrss.gov.cn`` and
uses the ``insMainCon*`` template; the provincial and explanation columns are
hosted on ``hrss.gd.gov.cn`` and use the ``article_*`` template. These tests are
network-free and pin both templates plus the PDF attachment discovery.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from core.models import HttpResult, UrlItem
from crawler import detail_crawler as dcmod
from crawler.list_crawler import get_next_url, parse_list_page
from crawler.policy_relation import find_pdf_attachments
from extractor.html_extractor import extract_by_rule

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / 'config' / 'sites'
FIXTURES = Path(__file__).resolve().parent / 'fixtures'

# Two hosts, two templates: the national column points at mohrss.gov.cn.
SITES = {
    'gd_hrss_national_policy.yaml': {
        'path': '/jyzl/zcfg/gjzc/',
        'category': '教育与人才-就业政策-国家政策',
        'document_type': 'employment_policy',
        'link_selector': "a[href*='mohrss.gov.cn']",
        'title_selector': '.insMainConTitle_b',
        'content_selector': '#insMainConTxt .TRS_Editor',
        'date_selector': '.insMainConTitle_c',
    },
    'gd_hrss_employment.yaml': {
        'path': '/jyzl/zcfg/bszc/',
        'category': '教育与人才-就业政策-本省政策',
        'document_type': 'employment_policy',
        'link_selector': "a[href*='/content/post_']",
        'title_selector': '.article_t',
        'content_selector': '.article_con',
        'date_selector': '.article_item',
    },
    'gd_hrss_policy_explain.yaml': {
        'path': '/jyzl/zcfg/zcjd/',
        'category': '教育与人才-就业政策-政策解读',
        'document_type': 'policy_explanation',
        'link_selector': "a[href*='/content/post_']",
        'title_selector': '.article_t',
        'content_selector': '.article_con',
        'date_selector': '.article_item',
    },
}


def load_yaml(path: Path) -> dict:
    with path.open(encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


@pytest.mark.parametrize(('filename', 'expected'), SITES.items())
def test_hrss_column_config_contract(filename: str, expected: dict):
    cfg = load_yaml(SITE_DIR / filename)
    starts = cfg['crawler']['start_urls']
    assert len(starts) == 1
    assert expected['path'] in starts[0]
    assert cfg['crawler']['start_mode'] == 'list'
    assert cfg['list']['item_selector'] == 'ul.list li'
    assert cfg['list']['link_selector'] == expected['link_selector']
    assert cfg['list']['title_selector'] == expected['link_selector']
    assert cfg['list']['date_selector'] == '.pubDate'
    assert cfg['pagination'] == {'type': 'next_link', 'next_selector': '.pages a.next'}
    assert cfg['detail']['title']['selectors'][0] == expected['title_selector']
    assert cfg['detail']['content']['selectors'][0] == expected['content_selector']
    assert expected['date_selector'] in cfg['detail']['publish_time']['selectors']
    # Source is intentionally left to fall back to the site name.
    assert cfg['detail']['source'] == {'selectors': []}
    assert cfg['metadata']['category'] == expected['category']
    assert cfg['metadata']['document_type'] == expected['document_type']


def test_p0_task_registers_each_hrss_column_once():
    task = load_yaml(ROOT / 'config' / 'tasks' / 'guangdong_education_talent_p0.yaml')
    entries = {entry['id']: entry for entry in task['sites']}
    expected = {
        'gd_hrss_national_policy': 'config/sites/gd_hrss_national_policy.yaml',
        'gd_hrss_employment': 'config/sites/gd_hrss_employment.yaml',
        'gd_hrss_policy_explain': 'config/sites/gd_hrss_policy_explain.yaml',
    }
    for site_id, path in expected.items():
        assert entries[site_id]['config'] == path
        assert entries[site_id]['enabled'] is True


def test_hrss_list_and_next_page_use_verified_structure():
    html = (FIXTURES / 'gd_hrss_policy_list.html').read_text(encoding='utf-8')
    cfg = load_yaml(SITE_DIR / 'gd_hrss_employment.yaml')
    current = 'https://hrss.gd.gov.cn/jyzl/zcfg/bszc/index.html'
    items = parse_list_page(html, current, cfg)
    assert len(items) == 1
    assert items[0].url.endswith('/jyzl/zcfg/bszc/content/post_4924456.html')
    assert items[0].publish_time == '2026-07-10'
    assert get_next_url(html, current, cfg, page_no=1).endswith('/jyzl/zcfg/bszc/index_2.html')


def test_national_detail_extracts_only_article_fields():
    html = (FIXTURES / 'gd_hrss_policy_detail.html').read_text(encoding='utf-8')
    cfg = load_yaml(SITE_DIR / 'gd_hrss_national_policy.yaml')
    result = extract_by_rule(html, cfg)
    assert result.extraction_method == 'rule'
    assert result.title == '人力资源社会保障部关于开展就业援助活动的通知'
    assert result.publish_time == '2024-12-22'
    assert '高校毕业生' in (result.content or '')
    assert '关闭窗口' not in (result.content or '')


def test_province_detail_extracts_only_article_fields():
    html = (FIXTURES / 'gd_hrss_province_detail.html').read_text(encoding='utf-8')
    cfg = load_yaml(SITE_DIR / 'gd_hrss_employment.yaml')
    result = extract_by_rule(html, cfg)
    assert result.extraction_method == 'rule'
    assert result.title == '关于开展我省2026年高校毕业生等青年就业服务攻坚行动的通知'
    assert result.publish_time == '2026-07-10'
    assert '高校毕业生' in (result.content or '')
    assert '信息来源' not in (result.content or '')


def test_hrss_attachment_discovery_reads_links_and_file_appendix_once():
    html = (FIXTURES / 'gd_hrss_policy_detail.html').read_text(encoding='utf-8')
    base = 'https://hrss.gd.gov.cn/jyzl/zcfg/bszc/content/post_1.html'
    attachments = find_pdf_attachments(html, base)
    urls = [item['url'] for item in attachments]
    assert urls == [
        'https://hrss.gd.gov.cn/files/employment-policy.pdf',
        'https://hrss.gd.gov.cn/files/second-attachment.pdf',
    ]


class FakeLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass


class FakeHttp:
    def __init__(self, html: str):
        self.html = html

    def get(self, url: str) -> HttpResult:
        return HttpResult(
            url=url,
            final_url=url,
            status_code=200,
            text=self.html,
            encoding='utf-8',
        )


def test_employment_policy_crawler_preserves_direct_attachment(monkeypatch, tmp_path):
    html = (FIXTURES / 'gd_hrss_province_detail.html').read_text(encoding='utf-8')
    cfg = load_yaml(SITE_DIR / 'gd_hrss_employment.yaml')
    monkeypatch.setattr(dcmod, 'extract_pdf_text', lambda url: 'PDF正文')
    # Keep this test hermetic: attachment handling is what is under test, not rendering.
    monkeypatch.setattr(dcmod.DetailCrawler, '_needs_render', lambda self, html, ext: False)
    crawler = dcmod.DetailCrawler(FakeHttp(html), cfg, FakeLogger(), tmp_path)
    raw = crawler.crawl_one(UrlItem(
        url='https://hrss.gd.gov.cn/jyzl/zcfg/bszc/content/post_4924456.html',
        title='列表标题',
    ))
    data_path = tmp_path / 'data' / '01_raw' / 'json' / f'{raw.id}.json'
    data = json.loads(data_path.read_text(encoding='utf-8'))
    assert data['attachmentCount'] == 1
    assert data['attachments'] == [
        {
            'name': '2026年招聘活动计划.pdf',
            'url': 'https://hrss.gd.gov.cn/attachment/0/619/619688/4924456.pdf',
            'contentText': 'PDF正文',
        },
    ]
