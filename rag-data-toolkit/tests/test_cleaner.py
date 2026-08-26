from cleaner.noise_cleaner import clean_noise
from cleaner.text_normalizer import normalize_text


def test_trailing_noise():
    cfg = {'line_remove': [], 'trailing_markers': ['责任编辑：', '上一篇', '网站地图']}
    text = '这是文章正文。\n\n责任编辑：张三\n上一篇：文章A\n网站地图'
    cleaned, actions, issues = clean_noise(normalize_text(text), cfg)
    assert cleaned == '这是文章正文。'
    assert 'TRAILING_NOISE' in issues


def test_do_not_trim_early_marker():
    cfg = {'line_remove': [], 'trailing_markers': ['上一篇']}
    text = '上一篇报告中指出，人工智能产业增长。\n这是正文的后续内容，而且还有很多重要说明。' * 5
    cleaned, _, _ = clean_noise(normalize_text(text), cfg)
    assert '上一篇报告中指出' in cleaned
