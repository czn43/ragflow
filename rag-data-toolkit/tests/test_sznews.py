from pathlib import Path

import yaml

from crawler.list_crawler import parse_list_page
from crawler import playwright_list_crawler as pwmod
from extractor.html_extractor import extract


class FakeLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass


LIST_INITIAL = '''
<html><body>
<div class="card-list waterfall-list">
  <a href="https://wb.sznews.com/PC/content/202608/27/content_3473800.html" class="waterfall-item card-list-item">
    <div class="card-info"><h3>一条河，道尽深圳沧海桑田</h3><h4></h4><span>2026-08-27</span></div>
  </a>
  <a href="https://www.sznews.com/news/content/2026-08/27/content_32157228.htm" class="waterfall-item card-list-item">
    <div class="card-info"><h3>问政深圳</h3><h4>摘要</h4><span><b>深圳特区报</b> 2026-08-27</span></div>
  </a>
</div>
<a href="javascript:;" class="btn-more">加载更多</a>
<ul class="pages" style="display:none"><li class="page-next"><a href="https://www.sznews.com/node_31100_2.htm">下一页</a></li></ul>
</body></html>
'''

LIST_AFTER_MORE = '''
<html><body>
<div class="card-list waterfall-list">
  <a href="https://wb.sznews.com/PC/content/202608/27/content_3473800.html" class="waterfall-item card-list-item">
    <div class="card-info"><h3>一条河，道尽深圳沧海桑田</h3><span>2026-08-27</span></div>
  </a>
  <a href="https://www.sznews.com/news/content/2026-08/27/content_32157228.htm" class="waterfall-item card-list-item">
    <div class="card-info"><h3>问政深圳</h3><span><b>深圳特区报</b> 2026-08-27</span></div>
  </a>
  <a href="https://wb.sznews.com/PC/content/202608/27/content_3473789.html" class="waterfall-item card-list-item">
    <div class="card-info"><h3>文明实践系列活动启幕</h3><span>2026-08-27</span></div>
  </a>
  <a href="https://wb.sznews.com/PC/content/202608/27/content_3473788.html" class="waterfall-item card-list-item">
    <div class="card-info"><h3>深港技术标准互认落地</h3><span>2026-08-27</span></div>
  </a>
</div>
</body></html>
'''


def load_cfg():
    return yaml.safe_load((Path(__file__).resolve().parents[1] / 'config/sites/sznews.yaml').read_text(encoding='utf-8'))


def test_sznews_list_self_link_and_subdomain_urls():
    cfg = load_cfg()
    items = parse_list_page(LIST_INITIAL, 'https://www.sznews.com/node_31100.htm', cfg)
    assert len(items) == 2
    assert items[0].url == 'https://wb.sznews.com/PC/content/202608/27/content_3473800.html'
    assert items[0].title == '一条河，道尽深圳沧海桑田'
    assert items[0].publish_time == '2026-08-27'
    assert items[1].source_name == '深圳特区报'


def test_sznews_detail_extracts_only_article_and_strips_prefixes():
    cfg = load_cfg()
    body = '这是深圳晚报真实正文内容。' * 20
    html = f'''
    <html><body>
      <div class="article">
        <h1 class="article-tit">“贴身管家”爬楼拿药</h1>
        <div class="article-info"><div class="article-source"><b>来源：深圳晚报</b><span>发布时间：2026-08-27</span></div></div>
        <div class="mb-ai"><p>以下内容由AI生成，仅供参考</p></div>
        <div class="article-txt"><div class="article-content"><p>{body}</p></div><div class="author-info">二维码</div></div>
      </div>
      <div class="article-mod-ai"><p>AI视界分析，不应进入正文</p></div>
    </body></html>
    '''
    result = extract(html, cfg)
    assert result.extraction_method == 'rule'
    assert result.title == '“贴身管家”爬楼拿药'
    assert result.source_name == '深圳晚报'
    assert result.publish_time == '2026-08-27'
    assert '真实正文内容' in result.content
    assert 'AI视界' not in result.content
    assert '二维码' not in result.content


class FakeLocator:
    def __init__(self, page, kind):
        self.page = page
        self.kind = kind

    @property
    def first(self):
        return self

    def count(self):
        if self.kind == 'items':
            return 2 if self.page.index == 0 else 4
        if self.kind == 'load_more':
            return 1 if self.page.index == 0 else 0
        if self.kind == 'fallback':
            return 1 if self.page.index == 0 else 0
        return 0

    def get_attribute(self, name):
        if self.kind == 'load_more' and name == 'class':
            return 'btn-more'
        if self.kind == 'fallback' and name == 'href':
            return 'https://www.sznews.com/node_31100_2.htm'
        return None

    def is_visible(self):
        return True

    def click(self, timeout=None):
        if self.kind != 'load_more':
            raise RuntimeError('unexpected click')
        self.page.index = 1


class FakePage:
    def __init__(self):
        self.index = 0
        self.url = 'https://www.sznews.com/node_31100.htm'

    def goto(self, url, **kwargs):
        self.url = url
        return None

    def wait_for_selector(self, *args, **kwargs):
        return None

    def set_default_timeout(self, *args, **kwargs):
        return None

    def content(self):
        return LIST_INITIAL if self.index == 0 else LIST_AFTER_MORE

    def locator(self, selector):
        if selector == '.card-list.waterfall-list > a.waterfall-item.card-list-item':
            return FakeLocator(self, 'items')
        if selector == 'a.btn-more':
            return FakeLocator(self, 'load_more')
        if selector == 'ul.pages li.page-next a':
            return FakeLocator(self, 'fallback')
        return FakeLocator(self, 'empty')

    def wait_for_function(self, *args, **kwargs):
        return None

    def wait_for_timeout(self, *args, **kwargs):
        return None


class FakeContext:
    def __init__(self, page):
        self.page = page

    def new_page(self):
        return self.page

    def close(self):
        pass


class FakeBrowser:
    def __init__(self, page):
        self.page = page

    def new_context(self, **kwargs):
        return FakeContext(self.page)

    def close(self):
        pass


class FakeChromium:
    def __init__(self, page):
        self.page = page

    def launch(self, **kwargs):
        return FakeBrowser(self.page)


class FakePlaywright:
    def __init__(self, page):
        self.chromium = FakeChromium(page)


class FakePlaywrightManager:
    def __init__(self, page):
        self.obj = FakePlaywright(page)

    def __enter__(self):
        return self.obj

    def __exit__(self, exc_type, exc, tb):
        return False


def test_playwright_load_more_collects_appended_cards(monkeypatch):
    cfg = load_cfg()
    page = FakePage()
    monkeypatch.setattr(pwmod, 'sync_playwright', lambda: FakePlaywrightManager(page))
    crawler = pwmod.PlaywrightListCrawler(cfg, FakeLogger())
    items = crawler.discover(max_pages=5, max_docs=4)
    assert len(items) == 4
    assert items[2].url.endswith('content_3473789.html')
    assert crawler.diagnostics['mode'] == 'playwright_load_more'
    assert len(crawler.diagnostics['pages']) == 2
