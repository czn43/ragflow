# Changelog

## v1.8.0

### New

- Added `pagination.type: playwright_load_more` for list pages where a “加载更多” button appends new article cards to the current DOM.
- Added DOM-growth waiting: the crawler waits until `list.item_selector` count increases after each click.
- Added `pagination.fallback_next_link_selector`; when load-more clicking fails, a hidden/normal next-page href can be used as a fallback.
- Added `config/sites/sznews.yaml` for `https://www.sznews.com/node_31100.htm`.
- Added `config/tasks/shenzhen_news_training.yaml` for SZTV + SZNEWS multi-source practice.
- Added `run_sznews_100.bat`, `run_inspect_sznews.bat`, and `run_shenzhen_news_multi.bat`.
- Added metadata field post-processing with `strip_prefixes` and `regex_extract`.
- Added a full competition-day universal AI site-adaptation prompt to README.

### Validation against supplied SZNEWS HTML

- Before “load more”: 10 article cards detected.
- After “load more”: 20 article cards detected.
- Detail page rule extracted:
  - title: `“贴身管家”爬楼拿药 “果园熟手”2秒摘果`
  - source: `深圳晚报`
  - publish date: `2026-08-27`
  - article body: 337 characters from `.article-content`
- AI sidebar / QR-code area is excluded by the exact content selector.

### Compatibility

- Keeps all v1.7 multi-source functionality.
- Keeps the fixed 8-field competition JSON schema introduced in v1.6.
- Keeps system-Chrome-first Playwright behavior.
