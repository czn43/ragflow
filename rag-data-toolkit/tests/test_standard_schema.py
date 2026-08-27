import json
from pathlib import Path

from core.schema import STANDARD_FIELDS, exact_standard_record, make_standard_record
from crawler import detail_crawler as dcmod
from core.models import HttpResult, UrlItem
from cleaner.pipeline import ProcessingPipeline


class FakeLogger:
    def info(self, *args, **kwargs):
        pass
    def warning(self, *args, **kwargs):
        pass


class FakeHttp:
    def __init__(self, html):
        self.html = html
    def get(self, url):
        return HttpResult(url=url, final_url=url, status_code=200, text=self.html, encoding='utf-8')


class FakeRenderer:
    def __init__(self, cfg, logger):
        self.cfg = cfg
    def render(self, url):
        body = '这是通过浏览器渲染后得到的真实正文。' * 20
        return f'''<html><body>
        <h1 id="title-name">渲染后的新闻标题</h1>
        <div id="meta_content"><a class="rich_media_meta_nickname">深视新闻</a><span>2026-08-27 09:00:00</span></div>
        <div id="rich_media_wrp"><div class="js_content" data-module-name="article"><div id="editWrap"><p>{body}</p></div></div></div>
        <div class="comment-container">评论：这不应该进入正文</div>
        </body></html>'''
    def close(self):
        pass


def cfg():
    return {
        'site': {'name': 'SZTV', 'domain': 'sztv.com.cn'},
        'metadata': {'category': '新闻资讯-新闻资讯'},
        'detail': {
            'min_content_chars': 100,
            'render_fallback': True,
            'title': {'selectors': ['#title-name']},
            'content': {'selectors': ['#rich_media_wrp .js_content[data-module-name="article"] #editWrap']},
            'publish_time': {'selectors': ['#meta_content span']},
            'source': {'selectors': ['#meta_content .rich_media_meta_nickname']},
        },
        'pagination': {'headless': True, 'browser': {'prefer_system_chrome': True}},
    }


def test_exact_standard_schema_fields_only():
    record = make_standard_record(source_name='A', source_url='https://a.example/x', title='T', content_text='C')
    assert list(record.keys()) == STANDARD_FIELDS
    assert record['attachmentCount'] == 0
    dirty = dict(record, id='x', quality=100)
    assert list(exact_standard_record(dirty).keys()) == STANDARD_FIELDS


def test_raw_json_contains_rendered_body(monkeypatch, tmp_path):
    # requests HTML intentionally has title only and no article body
    shell = '<html><body><h1 id="title-name">壳页面标题</h1></body></html>'
    monkeypatch.setattr(dcmod, 'DetailRenderer', FakeRenderer)
    crawler = dcmod.DetailCrawler(FakeHttp(shell), cfg(), FakeLogger(), tmp_path)
    item = UrlItem(url='https://www.sztv.com.cn/ysz/zx/tj/12345678.shtml', title='列表标题')
    raw = crawler.crawl_one(item)
    crawler.close()
    doc_id = raw.id
    data = json.loads((tmp_path / f'data/01_raw/json/{doc_id}.json').read_text(encoding='utf-8'))
    assert list(data.keys()) == STANDARD_FIELDS
    assert data['title'] == '渲染后的新闻标题'
    assert len(data['contentText']) >= 100
    assert '评论' not in data['contentText']
    assert data['sourceName'] == '深视新闻'
    assert data['publishTime'] == '2026-08-27'


def test_pipeline_outputs_standard_clean_json(tmp_path):
    raw_dir = tmp_path / 'data/01_raw/json'
    raw_dir.mkdir(parents=True)
    record = make_standard_record(
        source_name='深视新闻',
        source_url='https://www.sztv.com.cn/ysz/zx/zw/12345678.shtml',
        title='测试新闻',
        content_text='这是有效新闻正文。' * 30 + '\n相关推荐\n评论\n还没有人发言，快来抢沙发吧!',
        category='新闻资讯-新闻资讯',
        publish_time='2026-08-27',
    )
    (raw_dir / 'x.json').write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
    noise = {
        'line_remove': ['^相关推荐$', '^评论$', '^还没有人发言.*$'],
        'trailing_markers': ['相关推荐', '评论'],
    }
    pipe = ProcessingPipeline(tmp_path, cfg(), noise, FakeLogger())
    docs, rejected = pipe.run()
    assert not rejected
    assert len(docs) == 1
    out = docs[0]
    assert list(out.keys()) == STANDARD_FIELDS
    assert '相关推荐' not in out['contentText']
    assert '评论' not in out['contentText']
    assert out['publishTime'] == '2026-08-27'
