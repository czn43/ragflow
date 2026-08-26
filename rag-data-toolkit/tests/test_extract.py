from extractor.html_extractor import extract


def test_rule_extract():
    body = '这是正文。' * 40
    html = f'<html><body><h1>测试标题</h1><div class="date">2026-08-20</div><div class="article-content">{body}</div></body></html>'
    cfg = {
        'detail': {
            'min_content_chars': 100,
            'title': {'selectors': ['h1']},
            'content': {'selectors': ['.article-content']},
            'publish_time': {'selectors': ['.date']},
            'source': {'selectors': []},
        }
    }
    r = extract(html, cfg)
    assert r.title == '测试标题'
    assert r.extraction_method == 'rule'
    assert len(r.content) >= 100
