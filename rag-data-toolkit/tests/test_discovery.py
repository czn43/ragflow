from core.models import HttpResult
from crawler.article_discovery import discover_links
from crawler.list_crawler import ListCrawler


class FakeHttp:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        html = self.pages.get(url)
        if html is None:
            return HttpResult(url=url, status_code=404, error='HTTP 404')
        return HttpResult(url=url, final_url=url, status_code=200, text=html, encoding='utf-8')


class FakeLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass


def test_auto_discovery_when_selector_matches_zero():
    html = '''
    <html><body>
      <div class="not-news-list">
        <a href="/ysz/zx/tj/83853041.shtml">这是第一篇测试新闻标题</a>
        <a href="/ysz/zx/tj/83853042.shtml">这是第二篇测试新闻标题</a>
        <a href="/about/index.html">关于我们</a>
      </div>
    </body></html>
    '''
    cfg = {
        'site': {'domain': 'www.sztv.com.cn'},
        'crawler': {'start_urls': ['https://www.sztv.com.cn/'], 'start_mode': 'list'},
        'list': {'item_selector': '.news-list li', 'link_selector': 'a'},
        'pagination': {'type': 'none'},
        'discovery': {'min_score': 3, 'detail_url_score': 4},
        'detail': {'min_content_chars': 100, 'title': {'selectors': ['h1']}, 'content': {'selectors': ['.article-content']}},
    }
    crawler = ListCrawler(FakeHttp({'https://www.sztv.com.cn/': html}), cfg, FakeLogger())
    urls = crawler.discover(max_pages=1, max_docs=100)
    assert len(urls) == 2
    assert urls[0].url.endswith('.shtml')
    assert crawler.diagnostics['fallback_used'] is True


def test_stale_demo_domain_does_not_filter_real_site_links():
    html = '<a href="/ysz/zx/tj/83853041.shtml">真实新闻标题足够长</a>'
    cfg = {
        'site': {'domain': 'example.gov.cn'},  # stale copied demo value
        'discovery': {'min_score': 3},
    }
    links = discover_links(html, 'https://www.sztv.com.cn/', cfg)
    assert len(links) == 1
    assert links[0].url == 'https://www.sztv.com.cn/ysz/zx/tj/83853041.shtml'


def test_invalid_selector_falls_back_instead_of_crashing():
    html = '<a href="/news/83853041.shtml">一条有效的测试新闻标题</a>'
    cfg = {
        'site': {'domain': 'example.com'},
        'crawler': {'start_urls': ['https://example.com/'], 'start_mode': 'list'},
        'list': {'item_selector': '[invalid'},
        'pagination': {'type': 'none'},
        'discovery': {'min_score': 3},
        'detail': {'min_content_chars': 100, 'title': {'selectors': ['h1']}, 'content': {'selectors': ['.article-content']}},
    }
    crawler = ListCrawler(FakeHttp({'https://example.com/': html}), cfg, FakeLogger())
    urls = crawler.discover(max_pages=1, max_docs=10)
    assert len(urls) == 1
    assert crawler.diagnostics['fallback_used'] is True
