from pathlib import Path

from core.schema import STANDARD_FIELDS, make_standard_record
from multi.merger import SiteBundle, merge_site_records
from utils.workspace import data_path, mark_flat_workspace


def doc(url: str, title: str, content: str, source: str) -> dict:
    return make_standard_record(
        source_name=source,
        source_url=url,
        title=title,
        content_text=content,
        category='测试',
        publish_time='2026-08-27',
    )


def test_global_url_dedup_prefers_lower_priority():
    high = SiteBundle('gov', '政府', 10, [doc('https://a.com/x?id=1&utm_source=x', 'A', '正文A' * 20, '政府')])
    low = SiteBundle('news', '媒体', 30, [doc('https://a.com/x?id=1&utm_source=y', 'A转载', '另一正文' * 20, '媒体')])
    merged, dup, stats = merge_site_records([low, high])
    assert len(merged) == 1
    assert merged[0]['sourceName'] == '政府'
    assert dup[0]['_rejectReason'] == 'GLOBAL_DUPLICATE_URL'
    assert stats['final_count'] == 1


def test_global_content_dedup_across_domains():
    text = '同一篇转载正文。' * 30
    a = SiteBundle('official', '官方', 10, [doc('https://official.test/1.html', '官方稿', text, '官方')])
    b = SiteBundle('media', '媒体', 20, [doc('https://media.test/999.shtml', '转载稿', text, '媒体')])
    merged, dup, stats = merge_site_records([b, a])
    assert len(merged) == 1
    assert merged[0]['sourceName'] == '官方'
    assert dup[0]['_rejectReason'] == 'GLOBAL_DUPLICATE_CONTENT'
    assert stats['duplicate_count'] == 1
    assert list(merged[0].keys()) == STANDARD_FIELDS


def test_flat_workspace_paths(tmp_path: Path):
    normal = tmp_path / 'normal'
    assert data_path(normal, '01_raw') == normal / 'data' / '01_raw'

    flat = tmp_path / 'flat'
    mark_flat_workspace(flat)
    assert data_path(flat, '01_raw') == flat / '01_raw'
