from crawler.url_normalizer import normalize_url


def test_normalize_tracking_params():
    url = 'https://Example.com/a?id=123&utm_source=wechat#top'
    assert normalize_url(url) == 'https://example.com/a?id=123'
