from __future__ import annotations

from dataclasses import asdict
from typing import Any

from core.models import UrlItem
from crawler.list_crawler import parse_list_page
from crawler.url_normalizer import normalize_url
from utils.browser_utils import browser_launch_args

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - friendly runtime error handled below
    PlaywrightTimeoutError = Exception
    sync_playwright = None


PLAYWRIGHT_PAGINATION_TYPES = {'playwright_click', 'playwright_load_more'}


class PlaywrightListCrawler:
    """Discover article URLs from JavaScript-driven list pages.

    Supported modes:

    ``playwright_click``
        The page has a next-page button. Clicking it replaces the current list,
        so the crawler waits for the first article URL to change. This is the
        SZTV style.

    ``playwright_load_more``
        The page has a "load more" button. Clicking it appends new cards while
        keeping old cards in the DOM, so the crawler waits for the number of
        matching cards to increase. This is the SZNEWS style.

    Detail pages are intentionally fetched by the normal DetailCrawler. That
    keeps bulk article fetching fast; Playwright is only used when the list page
    actually needs browser-side JavaScript.
    """

    def __init__(self, cfg: dict, logger):
        self.cfg = cfg
        self.logger = logger
        self.pagination_type = str(cfg.get('pagination', {}).get('type', 'playwright_click')).lower()
        if self.pagination_type not in PLAYWRIGHT_PAGINATION_TYPES:
            raise ValueError(
                f'PlaywrightListCrawler does not support pagination.type={self.pagination_type!r}; '
                f'expected one of {sorted(PLAYWRIGHT_PAGINATION_TYPES)}'
            )
        self.diagnostics: dict[str, Any] = {
            'mode': self.pagination_type,
            'pages': [],
            'fallback_used': False,
            'browser_source': None,
            'browser_executable': None,
        }

    def _require_playwright(self) -> None:
        if sync_playwright is None:
            raise RuntimeError(
                f'pagination.type={self.pagination_type} requires Playwright. '
                'Run setup_windows.bat. The project prefers an existing system Chrome; '
                'Playwright Chromium is only needed when no usable Chrome exists.'
            )

    def _browser_launch_args(self) -> dict:
        args, browser_diag = browser_launch_args(self.cfg)
        self.diagnostics.update(browser_diag)
        return args

    def _launch_browser(self, playwright):
        args = self._browser_launch_args()
        try:
            browser = playwright.chromium.launch(**args)
            self.logger.info(
                'playwright browser source=%s executable=%s',
                self.diagnostics.get('browser_source'),
                self.diagnostics.get('browser_executable'),
            )
            return browser
        except Exception as exc:
            # If system Chrome was selected but failed to launch, try Playwright's
            # bundled Chromium as a last-resort fallback.
            if args.get('executable_path'):
                self.logger.warning('system Chrome launch failed; trying Playwright Chromium: %s', exc)
                try:
                    browser = playwright.chromium.launch(headless=args.get('headless', True))
                    self.diagnostics['browser_source'] = 'playwright_chromium'
                    self.diagnostics['browser_executable'] = None
                    self.diagnostics['fallback_used'] = True
                    return browser
                except Exception as fallback_exc:
                    raise RuntimeError(
                        'System Chrome was found but could not be launched, and Playwright Chromium is not available. '
                        'Run setup_windows.bat and choose Y when prompted to install Chromium, or run: '
                        '.venv\\Scripts\\python.exe -m playwright install chromium'
                    ) from fallback_exc

            raise RuntimeError(
                'No usable system Chrome was found and Playwright Chromium is not installed. '
                'Run setup_windows.bat and choose Y when prompted to install Chromium, or run: '
                '.venv\\Scripts\\python.exe -m playwright install chromium'
            ) from exc

    @staticmethod
    def _link_changed_script() -> str:
        return """
        ([itemSelector, linkSelector, oldHref]) => {
            const item = document.querySelector(itemSelector);
            if (!item) return false;
            const link = linkSelector === '@self' ? item : item.querySelector(linkSelector);
            if (!link || !link.href) return false;
            return link.href !== oldHref;
        }
        """

    @staticmethod
    def _item_count_increased_script() -> str:
        return """
        ([itemSelector, oldCount]) => {
            return document.querySelectorAll(itemSelector).length > oldCount;
        }
        """

    @staticmethod
    def _locator_is_disabled(locator) -> bool:
        try:
            classes = (locator.get_attribute('class') or '').split()
            disabled_attr = locator.get_attribute('disabled')
            aria_disabled = (locator.get_attribute('aria-disabled') or '').lower()
            return 'disabled' in classes or disabled_attr is not None or aria_disabled == 'true'
        except Exception:
            return False

    def _wait_list_ready(self, page) -> None:
        p = self.cfg.get('pagination', {})
        item_selector = self.cfg.get('list', {}).get('item_selector')
        timeout = int(p.get('wait_timeout_ms', 15000))
        ready_selector = p.get('ready_selector') or item_selector
        if ready_selector:
            page.wait_for_selector(ready_selector, timeout=timeout)

        loading_selector = p.get('loading_selector')
        if loading_selector:
            try:
                page.wait_for_selector(loading_selector, state='hidden', timeout=timeout)
            except PlaywrightTimeoutError:
                self.logger.warning('loading selector did not become hidden: %s', loading_selector)

    def _click_next_replace(self, page, page_no: int, old_first_href: str | None) -> bool:
        p = self.cfg.get('pagination', {})
        next_selector = p.get('next_selector')
        timeout = int(p.get('wait_timeout_ms', 15000))
        item_selector = self.cfg.get('list', {}).get('item_selector')
        link_selector = self.cfg.get('list', {}).get('link_selector', 'a')

        if not next_selector:
            return False

        btn = page.locator(next_selector)
        if btn.count() == 0:
            return False
        btn = btn.first
        if self._locator_is_disabled(btn):
            return False

        try:
            btn.click(timeout=timeout)
        except Exception as click_error:
            # Optional JavaScript function fallback. Example: window.v3Index.goToPage
            fn_path = p.get('js_function')
            if not fn_path:
                raise RuntimeError(f'failed to click next page selector {next_selector}: {click_error}') from click_error
            next_page = page_no + 1
            page.evaluate(
                """
                ([path, pageNo]) => {
                    const parts = path.split('.');
                    let obj = window;
                    if (parts[0] === 'window') parts.shift();
                    for (let i = 0; i < parts.length - 1; i++) {
                        obj = obj[parts[i]];
                        if (!obj) throw new Error(`Cannot resolve ${path}`);
                    }
                    const fn = obj[parts[parts.length - 1]];
                    if (typeof fn !== 'function') throw new Error(`${path} is not a function`);
                    fn.call(obj, pageNo);
                }
                """,
                [fn_path, next_page],
            )

        if old_first_href and item_selector:
            try:
                page.wait_for_function(
                    self._link_changed_script(),
                    arg=[item_selector, link_selector, old_first_href],
                    timeout=timeout,
                )
            except PlaywrightTimeoutError:
                self.logger.warning('first article href did not change within timeout; checking DOM readiness')

        self._wait_list_ready(page)
        settle_ms = int(p.get('settle_ms', 0))
        if settle_ms > 0:
            page.wait_for_timeout(settle_ms)
        return True

    def _goto_fallback_next_link(self, page) -> bool:
        """Navigate using a hidden/normal next-page href when load-more clicking fails.

        Several news sites render a friendly "加载更多" button while also keeping a
        traditional hidden pagination list in the DOM. SZNEWS is one such example.
        Supporting this optional fallback makes the site adapter much more robust.
        """
        p = self.cfg.get('pagination', {})
        selector = p.get('fallback_next_link_selector')
        if not selector:
            return False
        node = page.locator(selector)
        if node.count() == 0:
            return False
        href = node.first.get_attribute('href')
        if not href or href.lower().startswith('javascript:'):
            return False
        target = normalize_url(href, page.url)
        if not target or target == normalize_url(page.url):
            return False
        self.logger.warning('load-more fallback: navigating hidden next link url=%s', target)
        page.goto(
            target,
            wait_until=p.get('wait_until', 'domcontentloaded'),
            timeout=int(p.get('navigation_timeout_ms', 30000)),
        )
        self._wait_list_ready(page)
        self.diagnostics['fallback_used'] = True
        return True

    def _click_load_more(self, page, old_item_count: int) -> bool:
        p = self.cfg.get('pagination', {})
        selector = p.get('load_more_selector') or p.get('next_selector')
        timeout = int(p.get('wait_timeout_ms', 15000))
        item_selector = self.cfg.get('list', {}).get('item_selector')

        if not selector or not item_selector:
            return False

        btn = page.locator(selector)
        if btn.count() == 0:
            return self._goto_fallback_next_link(page)
        btn = btn.first
        if self._locator_is_disabled(btn):
            return self._goto_fallback_next_link(page)

        try:
            # is_visible() is not implemented by older fakes/tests, so treat errors
            # as "unknown" rather than as a hard failure.
            try:
                if hasattr(btn, 'is_visible') and not btn.is_visible():
                    return self._goto_fallback_next_link(page)
            except Exception:
                pass

            btn.click(timeout=timeout)
        except Exception as click_error:
            self.logger.warning('load-more click failed selector=%s error=%s', selector, click_error)
            if self._goto_fallback_next_link(page):
                return True
            raise RuntimeError(f'failed to click load-more selector {selector}: {click_error}') from click_error

        try:
            page.wait_for_function(
                self._item_count_increased_script(),
                arg=[item_selector, old_item_count],
                timeout=timeout,
            )
        except PlaywrightTimeoutError:
            # Some sites replace the list instead of appending it despite using a
            # "load more" button. Do a defensive count check before giving up.
            try:
                current_count = page.locator(item_selector).count()
            except Exception:
                current_count = old_item_count
            if current_count <= old_item_count:
                self.logger.warning(
                    'load-more did not increase item count old=%s current=%s',
                    old_item_count,
                    current_count,
                )
                return self._goto_fallback_next_link(page)

        self._wait_list_ready(page)
        settle_ms = int(p.get('settle_ms', 300))
        if settle_ms > 0:
            page.wait_for_timeout(settle_ms)
        return True

    def inspect_url(self, url: str) -> dict:
        """Render one JS list page and report exact selector/pagination matches."""
        self._require_playwright()
        p_cfg = self.cfg.get('pagination', {})
        target = normalize_url(url)
        with sync_playwright() as p:
            browser = self._launch_browser(p)
            context = browser.new_context(locale=p_cfg.get('locale', 'zh-CN'))
            page = context.new_page()
            page.goto(
                target,
                wait_until=p_cfg.get('wait_until', 'domcontentloaded'),
                timeout=int(p_cfg.get('navigation_timeout_ms', 30000)),
            )
            self._wait_list_ready(page)
            html = page.content()
            items = parse_list_page(html, page.url, self.cfg)

            control_selector = (
                p_cfg.get('load_more_selector')
                if self.pagination_type == 'playwright_load_more'
                else p_cfg.get('next_selector')
            )
            control_count = page.locator(control_selector).count() if control_selector else 0
            fallback_selector = p_cfg.get('fallback_next_link_selector')
            fallback_count = page.locator(fallback_selector).count() if fallback_selector else 0

            report = {
                'url': target,
                'final_url': page.url,
                'render_engine': 'playwright',
                'pagination_type': self.pagination_type,
                'selector_matches': len(items),
                'sample_items': [asdict(x) for x in items[:10]],
                'control_selector': control_selector,
                'control_selector_matches': control_count,
                # Backward-compatible keys used by older README/log expectations.
                'next_selector': p_cfg.get('next_selector'),
                'next_selector_matches': control_count if self.pagination_type == 'playwright_click' else 0,
                'load_more_selector': p_cfg.get('load_more_selector'),
                'load_more_selector_matches': control_count if self.pagination_type == 'playwright_load_more' else 0,
                'fallback_next_link_selector': fallback_selector,
                'fallback_next_link_matches': fallback_count,
                'browser_source': self.diagnostics.get('browser_source'),
                'browser_executable': self.diagnostics.get('browser_executable'),
            }
            context.close()
            browser.close()
            return report

    def discover(self, max_pages: int = 20, max_docs: int = 100) -> list[UrlItem]:
        self._require_playwright()
        starts = self.cfg.get('crawler', {}).get('start_urls') or []
        if not starts:
            raise ValueError('crawler.start_urls is empty')

        list_cfg = self.cfg.get('list', {})
        item_selector = list_cfg.get('item_selector')
        if not item_selector:
            raise ValueError(f'{self.pagination_type} requires list.item_selector')

        collected: dict[str, UrlItem] = {}
        p_cfg = self.cfg.get('pagination', {})
        navigation_timeout = int(p_cfg.get('navigation_timeout_ms', 30000))

        with sync_playwright() as p:
            browser = self._launch_browser(p)
            context = browser.new_context(
                user_agent=self.cfg.get('crawler', {}).get('user_agent') or None,
                locale=p_cfg.get('locale', 'zh-CN'),
            )
            page = context.new_page()
            page.set_default_timeout(int(p_cfg.get('wait_timeout_ms', 15000)))

            for start in starts:
                if len(collected) >= max_docs:
                    break
                current = normalize_url(start)
                self.logger.info('playwright list open mode=%s url=%s', self.pagination_type, current)
                page.goto(
                    current,
                    wait_until=p_cfg.get('wait_until', 'domcontentloaded'),
                    timeout=navigation_timeout,
                )
                self._wait_list_ready(page)

                # max_pages means "initial rendered batch + at most max_pages-1
                # pagination actions" for both replacement and load-more modes.
                for page_no in range(1, max_pages + 1):
                    html = page.content()
                    items = parse_list_page(html, page.url, self.cfg)
                    first_href = items[0].url if items else None
                    try:
                        dom_item_count = page.locator(item_selector).count()
                    except Exception:
                        dom_item_count = len(items)

                    new_count = 0
                    for item in items:
                        if item.url not in collected:
                            collected[item.url] = item
                            new_count += 1
                            if len(collected) >= max_docs:
                                break

                    page_diag = {
                        'round': page_no,
                        'page': page_no,  # backward compatibility
                        'url': page.url,
                        'pagination_type': self.pagination_type,
                        'selector_matches': len(items),
                        'dom_item_count': dom_item_count,
                        'new_urls': new_count,
                        'total_urls': len(collected),
                        'first_href': first_href,
                    }
                    self.diagnostics['pages'].append(page_diag)
                    self.logger.info(
                        'playwright mode=%s round=%s selector_matches=%s new=%s total=%s',
                        self.pagination_type,
                        page_no,
                        len(items),
                        new_count,
                        len(collected),
                    )

                    if len(collected) >= max_docs:
                        break
                    if not items:
                        self.logger.warning('playwright round=%s has no matching list items; stopping', page_no)
                        break

                    if self.pagination_type == 'playwright_load_more':
                        moved = self._click_load_more(page, dom_item_count)
                    else:
                        moved = self._click_next_replace(page, page_no, first_href)

                    if not moved:
                        self.logger.info('playwright pagination finished at round=%s', page_no)
                        break

            context.close()
            browser.close()

        self.diagnostics['discovered_urls'] = len(collected)
        return list(collected.values())[:max_docs]
