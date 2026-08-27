from __future__ import annotations

from utils.browser_utils import browser_launch_args

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:  # pragma: no cover
    sync_playwright = None
    PlaywrightTimeoutError = Exception


class DetailRenderer:
    """Persistent Playwright renderer for JS-driven detail pages.

    A single browser/context/page is reused across all detail URLs so a site with
    100 articles does not launch Chrome 100 times.
    """

    def __init__(self, cfg: dict, logger):
        self.cfg = cfg
        self.logger = logger
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self.diagnostics = {}

    def _start(self) -> None:
        if self._page is not None:
            return
        if sync_playwright is None:
            raise RuntimeError('Playwright is not installed')
        self._pw = sync_playwright().start()
        launch_args, diag = browser_launch_args(self.cfg)
        self.diagnostics.update(diag)
        self._browser = self._pw.chromium.launch(**launch_args)
        p_cfg = self.cfg.get('pagination', {})
        self._context = self._browser.new_context(
            user_agent=self.cfg.get('crawler', {}).get('user_agent') or None,
            locale=p_cfg.get('locale', 'zh-CN'),
        )
        self._page = self._context.new_page()
        self._page.set_default_timeout(int(self.cfg.get('detail', {}).get('render_wait_timeout_ms', 12000)))

    def render(self, url: str) -> str | None:
        self._start()
        detail = self.cfg.get('detail', {})
        timeout = int(detail.get('render_navigation_timeout_ms', 30000))
        wait_until = detail.get('render_wait_until', 'domcontentloaded')
        try:
            self.logger.info('detail playwright render url=%s', url)
            self._page.goto(url, wait_until=wait_until, timeout=timeout)
            selectors = detail.get('content', {}).get('selectors') or []
            if isinstance(selectors, str):
                selectors = [selectors]
            # Wait for the first configured content selector that appears.
            for selector in selectors:
                try:
                    self._page.wait_for_selector(selector, state='attached', timeout=int(detail.get('render_wait_timeout_ms', 12000)))
                    break
                except PlaywrightTimeoutError:
                    continue
            # Give page-side article hydration a very small grace period.
            self._page.wait_for_timeout(int(detail.get('render_settle_ms', 300)))
            return self._page.content()
        except Exception as exc:
            self.logger.warning('detail playwright render failed url=%s error=%s', url, exc)
            return None

    def close(self) -> None:
        for obj in (self._context, self._browser):
            try:
                if obj is not None:
                    obj.close()
            except Exception:
                pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass
        self._pw = self._browser = self._context = self._page = None
