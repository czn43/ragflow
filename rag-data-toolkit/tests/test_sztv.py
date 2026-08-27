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


LIST_PAGE_1 = '''
<html><body>
<div id="newsGrid">
  <a class="news-card" href="https://www.sztv.com.cn/ysz/zx/tj/83852819.shtml">
    <div class="news-card-title">深圳经济特区，46岁生日快乐！</div>
    <span class="news-card-source">第一现场客户端</span>
    <span class="news-card-time">7小时前</span>
  </a>
  <a class="news-card" href="https://www.sztv.com.cn/ysz/zx/tj/83853036.shtml">
    <div class="news-card-title">铁路新增教师积分优惠</div>
    <span class="news-card-source">第一现场客户端</span>
    <span class="news-card-time">1小时前</span>
  </a>
</div>
<div id="pagination"><button class="pagination-btn pagination-next-btn">next</button></div>
<div id="loading-state" style="display:none"></div>
</body></html>
'''

LIST_PAGE_2 = '''
<html><body>
<div id="newsGrid">
  <a class="news-card" href="https://www.sztv.com.cn/ysz/zx/zw/83852907.shtml">
    <div class="news-card-title">串联粤桂五市！这一跨省高铁新进展来了</div>
    <span class="news-card-source">深视新闻</span>
    <span class="news-card-time">3小时前</span>
  </a>
  <a class="news-card" href="https://www.sztv.com.cn/ysz/zx/zw/83852875.shtml">
    <div class="news-card-title">事关6G商用，工信部最新介绍</div>
    <span class="news-card-source">深视新闻</span>
    <span class="news-card-time">5小时前</span>
  </a>
</div>
<div id="pagination"><button class="pagination-btn pagination-next-btn disabled">next</button></div>
<div id="loading-state" style="display:none"></div>
</body></html>
'''


def load_cfg():
    return yaml.safe_load((Path(__file__).resolve().parents[1] / 'config/sites/sztv.yaml').read_text(encoding='utf-8'))


def test_sztv_self_link_selector():
    cfg = load_cfg()
    items = parse_list_page(LIST_PAGE_1, 'https://www.sztv.com.cn/', cfg)
    assert len(items) == 2
    assert items[0].url.endswith('/83852819.shtml')
    assert items[0].title == '深圳经济特区，46岁生日快乐！'
    assert items[0].source_name == '第一现场客户端'
    assert items[0].publish_time == '7小时前'


def test_sztv_detail_rule_excludes_comment_and_license():
    cfg = load_cfg()
    body = '这是文章正文内容。' * 30
    html = f'''
    <main id="rich-content">
      <h1 id="title-name">测试新闻</h1>
      <div id="meta_content"><a class="rich_media_meta_nickname">深视新闻</a><span>2026-08-25 19:47:00</span></div>
      <div id="rich_media_wrp">
        <div class="js_content" data-module-name="article">
          <div id="editWrap"><p>{body}</p></div>
          <div id="license_content">版权声明：不应进入正文</div>
        </div>
      </div>
      <div class="comment-container"><h2>评论</h2><div class="comment-content">厉害👍</div></div>
    </main>
    '''
    result = extract(html, cfg)
    assert result.title == '测试新闻'
    assert result.source_name == '深视新闻'
    assert result.publish_time == '2026-08-25 19:47:00'
    assert '这是文章正文内容' in result.content
    assert '评论' not in result.content
    assert '厉害👍' not in result.content
    assert '版权声明' not in result.content


class FakeNextLocator:
    def __init__(self, page):
        self.page = page

    @property
    def first(self):
        return self

    def count(self):
        return 1 if self.page.index < len(self.page.pages) - 1 else 0

    def get_attribute(self, name):
        if name == 'class':
            return 'pagination-btn pagination-next-btn'
        return None

    def click(self, timeout=None):
        self.page.index += 1


class FakeEmptyLocator(FakeNextLocator):
    def count(self):
        return 0


class FakePage:
    def __init__(self, pages):
        self.pages = pages
        self.index = 0
        self.url = 'https://www.sztv.com.cn/'

    def goto(self, *args, **kwargs):
        return None

    def wait_for_selector(self, *args, **kwargs):
        return None

    def set_default_timeout(self, *args, **kwargs):
        return None

    def content(self):
        return self.pages[self.index]

    def locator(self, selector):
        if 'pagination-next-btn' in selector:
            return FakeNextLocator(self)
        return FakeEmptyLocator(self)

    def wait_for_function(self, *args, **kwargs):
        return None

    def evaluate(self, *args, **kwargs):
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


def test_playwright_click_pagination_collects_second_page(monkeypatch):
    cfg = load_cfg()
    fake_page = FakePage([LIST_PAGE_1, LIST_PAGE_2])
    monkeypatch.setattr(pwmod, 'sync_playwright', lambda: FakePlaywrightManager(fake_page))
    crawler = pwmod.PlaywrightListCrawler(cfg, FakeLogger())
    items = crawler.discover(max_pages=10, max_docs=3)
    assert len(items) == 3
    assert items[0].url.endswith('83852819.shtml')
    assert items[2].url.endswith('83852907.shtml')
    assert len(crawler.diagnostics['pages']) == 2
