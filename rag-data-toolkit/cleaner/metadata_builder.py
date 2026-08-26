from __future__ import annotations

import re


def infer_document_type(title: str, category: str | None) -> str:
    text = f'{title} {category or ""}'
    if re.search(r'办法|意见|规划|政策|条例|规定|实施方案|行动计划', text):
        return 'policy'
    if re.search(r'通知|公告|公示', text):
        return 'notice'
    if re.search(r'报告|白皮书|蓝皮书', text):
        return 'report'
    if re.search(r'标准|规范', text):
        return 'standard'
    return 'news'


def build_metadata(doc: dict, cfg: dict) -> dict:
    metadata_cfg = cfg.get('metadata', {})
    site_cfg = cfg.get('site', {})
    doc['source_name'] = doc.get('source_name') or site_cfg.get('name') or site_cfg.get('domain') or 'UNKNOWN'
    doc['category'] = doc.get('category') or metadata_cfg.get('category')
    doc['region'] = doc.get('region') or metadata_cfg.get('region')
    doc['document_type'] = doc.get('document_type') or infer_document_type(doc.get('title', ''), doc.get('category'))
    return doc
