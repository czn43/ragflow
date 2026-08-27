from pathlib import Path

from utils import browser_utils


def test_find_system_chrome_explicit_path(tmp_path):
    chrome = tmp_path / 'chrome.exe'
    chrome.write_bytes(b'fake')
    assert browser_utils.find_system_chrome(str(chrome)) == str(chrome)


def test_browser_launch_args_prefers_system_chrome(monkeypatch):
    monkeypatch.setattr(browser_utils, 'find_system_chrome', lambda explicit_path=None: r'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')
    cfg = {
        'pagination': {
            'headless': True,
            'browser': {'prefer_system_chrome': True, 'executable_path': None},
        }
    }
    args, diag = browser_utils.browser_launch_args(cfg)
    assert args['headless'] is True
    assert args['executable_path'].endswith('chrome.exe')
    assert diag['browser_source'] == 'system_chrome'


def test_browser_launch_args_falls_back_to_playwright(monkeypatch):
    monkeypatch.setattr(browser_utils, 'find_system_chrome', lambda explicit_path=None: None)
    cfg = {'pagination': {'headless': False, 'browser': {'prefer_system_chrome': True}}}
    args, diag = browser_utils.browser_launch_args(cfg)
    assert args == {'headless': False}
    assert diag['browser_source'] == 'playwright_chromium'
