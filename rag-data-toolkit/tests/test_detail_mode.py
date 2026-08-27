from core.models import HttpResult
from crawler.list_crawler import ListCrawler, looks_like_detail_page


class FakeHttp:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        html = self.pages.get(url)
        return HttpResult(url=url, final_url=url, status_code=200 if html else 404, text=html, encoding='utf-8')


class FakeLogger:
    def info(self, *args, **kwargs):
        pass
    def warning(self, *args, **kwargs):
        pass


def make_cfg(url):
    return {
        'site': {'domain': 'www.sztv.com.cn'},
        'crawler': {'start_urls': [url], 'start_mode': 'auto'},
        'list': {'item_selector': '.news-list li'},
        'pagination': {'type': 'none'},
        'discovery': {'min_score': 3, 'detail_url_score': 4},
        'detail': {
            'min_content_chars': 100,
            'title': {'selectors': ['h1']},
            'content': {'selectors': ['.article-content']},
            'publish_time': {'selectors': ['.date']},
            'source': {'selectors': []},
        },
    }


def test_direct_detail_url_is_detected_and_collected():
    url = 'https://www.sztv.com.cn/ysz/zx/tj/83853041.shtml'
    body = '这是用于测试的新闻正文内容。' * 30
    html = f'<html><body><h1>测试详情标题</h1><div class="article-content">{body}</div></body></html>'
    cfg = make_cfg(url)
    ok, info = looks_like_detail_page(html, url, cfg)
    assert ok is True
    assert info['content_chars'] >= 100

    crawler = ListCrawler(FakeHttp({url: html}), cfg, FakeLogger())
    urls = crawler.discover(max_pages=1, max_docs=100)
    assert len(urls) == 1
    assert urls[0].url == url
    assert crawler.diagnostics['start_pages'][0]['mode'] == 'direct_detail'
