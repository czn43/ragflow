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


class PlaywrightListCrawler:
    """Discover article URLs from JS-driven list pages by clicking pagination controls.

    The first version targets the common case represented by SZTV:
    - article cards already exist in the rendered DOM
    - next page is a JS button instead of an href
    - clicking next replaces the list contents without full-page navigation

    Detail pages are intentionally NOT fetched with Playwright; the normal requests-based
    DetailCrawler remains faster and simpler for that stage.
    """

    def __init__(self, cfg: dict, logger):
        self.cfg = cfg
        self.logger = logger
        self.diagnostics: dict[str, Any] = {
            'mode': 'playwright_click',
            'pages': [],
            'fallback_used': False,
            'browser_source': None,
            'browser_executable': None,
        }

    def _require_playwright(self) -> None:
        if sync_playwright is None:
            raise RuntimeError(
                'pagination.type=playwright_click requires Playwright. '
                'Run: pip install playwright && python -m playwright install chromium'
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
            # bundled Chromium as a last-resort fallback. This is useful when Chrome
            # is installed but blocked or corrupted.
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

    def _wait_list_ready(self, page) -> None:
        p = self.cfg.get('pagination', {})
        item_selector = self.cfg.get('list', {}).get('item_selector')
        timeout = int(p.get('wait_timeout_ms', 15000))
        ready_selector = p.get('ready_selector') or item_selector
        if ready_selector:
            page.wait_for_selector(ready_selector, timeout=timeout)

        # Some JS pages render a loading mask briefly. Waiting for hidden is helpful but
        # optional and non-fatal because many pages never show it at all.
        loading_selector = p.get('loading_selector')
        if loading_selector:
            try:
                page.wait_for_selector(loading_selector, state='hidden', timeout=timeout)
            except PlaywrightTimeoutError:
                self.logger.warning('loading selector did not become hidden: %s', loading_selector)

    def _click_next(self, page, page_no: int, old_first_href: str | None) -> bool:
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

        # Defensive checks for generic buttons where the selector itself may not exclude disabled.
        try:
            classes = btn.first.get_attribute('class') or ''
            disabled_attr = btn.first.get_attribute('disabled')
            aria_disabled = (btn.first.get_attribute('aria-disabled') or '').lower()
            if 'disabled' in classes.split() or disabled_attr is not None or aria_disabled == 'true':
                return False
        except Exception:
            pass

        try:
            btn.first.click(timeout=timeout)
        except Exception as click_error:
            # Optional JS function fallback. Example: window.v3Index.goToPage
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

        # The strongest signal for AJAX pagination is that the first article link changed.
        if old_first_href and item_selector:
            try:
                page.wait_for_function(
                    self._link_changed_script(),
                    arg=[item_selector, link_selector, old_first_href],
                    timeout=timeout,
                )
            except PlaywrightTimeoutError:
                # Fallback to the configured loading/ready state before deciding the click failed.
                self.logger.warning('first article href did not change within timeout; checking DOM readiness')

        self._wait_list_ready(page)
        return True


    def inspect_url(self, url: str) -> dict:
        """Render one JS page and report exact selector/pagination matches."""
        self._require_playwright()
        p_cfg = self.cfg.get('pagination', {})
        target = normalize_url(url)
        with sync_playwright() as p:
            browser = self._launch_browser(p)
            context = browser.new_context(locale=p_cfg.get('locale', 'zh-CN'))
            page = context.new_page()
            page.goto(target, wait_until=p_cfg.get('wait_until', 'domcontentloaded'), timeout=int(p_cfg.get('navigation_timeout_ms', 30000)))
            self._wait_list_ready(page)
            html = page.content()
            items = parse_list_page(html, page.url, self.cfg)
            next_selector = p_cfg.get('next_selector')
            next_count = page.locator(next_selector).count() if next_selector else 0
            report = {
                'url': target,
                'final_url': page.url,
                'render_engine': 'playwright',
                'selector_matches': len(items),
                'sample_items': [asdict(x) for x in items[:10]],
                'next_selector': next_selector,
                'next_selector_matches': next_count,
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
            raise ValueError('playwright_click requires list.item_selector')

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
                self.logger.info('playwright list open url=%s', current)
                page.goto(current, wait_until=p_cfg.get('wait_until', 'domcontentloaded'), timeout=navigation_timeout)
                self._wait_list_ready(page)

                for page_no in range(1, max_pages + 1):
                    html = page.content()
                    items = parse_list_page(html, page.url, self.cfg)
                    first_href = items[0].url if items else None

                    new_count = 0
                    for item in items:
                        if item.url not in collected:
                            collected[item.url] = item
                            new_count += 1
                            if len(collected) >= max_docs:
                                break

                    page_diag = {
                        'page': page_no,
                        'url': page.url,
                        'selector_matches': len(items),
                        'new_urls': new_count,
                        'total_urls': len(collected),
                        'first_href': first_href,
                    }
                    self.diagnostics['pages'].append(page_diag)
                    self.logger.info(
                        'playwright page=%s selector_matches=%s new=%s total=%s',
                        page_no,
                        len(items),
                        new_count,
                        len(collected),
                    )

                    if len(collected) >= max_docs:
                        break
                    if not items:
                        self.logger.warning('playwright page=%s has no matching list items; stopping', page_no)
                        break
                    if not self._click_next(page, page_no, first_href):
                        self.logger.info('playwright pagination finished at page=%s', page_no)
                        break

            context.close()
            browser.close()

        self.diagnostics['discovered_urls'] = len(collected)
        return list(collected.values())[:max_docs]
