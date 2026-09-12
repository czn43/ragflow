"""Config regression tests for the national education/talent sources.

These are intentionally network-free: they assert the national task registers
every matrix row exactly once and that each site YAML uses the fields the
crawler and extractor actually read (list -> detail contract).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SITES = {
    'cn_moe_core_policy': ('config/sites/cn_moe_core_policy.yaml', 350, 1),
    'cn_moe_laws_regulations': ('config/sites/cn_moe_laws_regulations.yaml', 60, 1),
    'cn_moe_admission_policy': ('config/sites/cn_moe_admission_policy.yaml', 80, 1),
    'cn_gaokao_policy': ('config/sites/cn_gaokao_policy.yaml', 180, 1),
    'cn_student_aid': ('config/sites/cn_student_aid.yaml', 120, 1),
    'cn_mohrss_core_policy': ('config/sites/cn_mohrss_core_policy.yaml', 280, 1),
    'cn_mohrss_graduate_employment': ('config/sites/cn_mohrss_graduate_employment.yaml', 90, 1),
    'cn_mohrss_professional_titles': ('config/sites/cn_mohrss_professional_titles.yaml', 100, 1),
    'cn_mohrss_skilled_talent': ('config/sites/cn_mohrss_skilled_talent.yaml', 100, 1),
    'cn_gov_top_policy': ('config/sites/cn_gov_top_policy.yaml', 120, 1),
    'cn_education_power_plan': ('config/sites/cn_education_power_plan.yaml', 15, 1),
    'cn_moe_vocational_education': ('config/sites/cn_moe_vocational_education.yaml', 130, 2),
    'cn_moe_education_statistics': ('config/sites/cn_moe_education_statistics.yaml', 30, 2),
    'cn_chsi_rules': ('config/sites/cn_chsi_rules.yaml', 40, 2),
    'cn_neea_exam_rules': ('config/sites/cn_neea_exam_rules.yaml', 60, 2),
    'cn_national_policy_explain': ('config/sites/cn_national_policy_explain.yaml', 80, 3),
}

ALLOWED_DOMAINS = {
    'moe.gov.cn',
    'gaokao.chsi.com.cn',
    'xszz.edu.cn',
    'mohrss.gov.cn',
    'gov.cn',
    'chsi.com.cn',
    'neea.edu.cn',
}


def load_yaml(path: Path) -> dict:
    with path.open(encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def test_national_task_registers_every_matrix_source():
    task = load_yaml(ROOT / 'config/tasks/national_education_talent_p0.yaml')
    assert task['task']['id'] == 'national_education_talent_p0'
    entries = {entry['id']: entry for entry in task['sites']}
    assert set(entries) == set(EXPECTED_SITES)
    for site_id, (config_path, max_docs, priority) in EXPECTED_SITES.items():
        entry = entries[site_id]
        assert entry['config'] == config_path
        assert entry['enabled'] is True
        assert entry['max_docs'] == max_docs
        assert entry['priority'] == priority
    assert task['merge'] == {'dedup_url': True, 'dedup_content': True}


@pytest.mark.parametrize(
    'site_id',
    EXPECTED_SITES,
    ids=list(EXPECTED_SITES),
)
def test_national_site_config_uses_list_to_detail_contract(site_id: str):
    config_path, _, _ = EXPECTED_SITES[site_id]
    cfg = load_yaml(ROOT / config_path)
    assert cfg['site']['domain'] in ALLOWED_DOMAINS
    assert cfg['crawler']['start_mode'] in {'list', 'detail'}
    assert cfg['crawler']['start_urls']
    detail = cfg['detail']
    for field in ('title', 'content', 'publish_time'):
        assert isinstance(detail[field], dict)
        assert detail[field]['selectors']
    if cfg['crawler']['start_mode'] == 'list':
        assert cfg['list']['item_selector']
        assert cfg['list']['link_selector']
        assert cfg['pagination']['type'] in {
            'next_link', 'url_template', 'page_parameter', 'none',
            'playwright_click', 'playwright_load_more',
        }
    assert cfg['metadata']['region'] == '全国'
    assert cfg['metadata']['category'].startswith('教育与人才-国家-')
