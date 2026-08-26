from __future__ import annotations

import random
import time
from dataclasses import replace

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.models import HttpResult


class HttpClient:
    def __init__(self, timeout: int = 15, retries: int = 3,
                 delay_min: float = 0.2, delay_max: float = 0.8,
                 user_agent: str | None = None):
        self.timeout = timeout
        self.retries = retries
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=0.6,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET'],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.headers.update({
            'User-Agent': user_agent or (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0 Safari/537.36'
            ),
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.5',
        })

    def get(self, url: str) -> HttpResult:
        if self.delay_max > 0:
            time.sleep(random.uniform(self.delay_min, self.delay_max))
        try:
            r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if not r.encoding or r.encoding.lower() == 'iso-8859-1':
                r.encoding = r.apparent_encoding or 'utf-8'
            return HttpResult(
                url=url,
                final_url=r.url,
                status_code=r.status_code,
                text=r.text,
                encoding=r.encoding,
                error=None if 200 <= r.status_code < 400 else f'HTTP {r.status_code}',
                retry_count=self.retries,
            )
        except requests.RequestException as e:
            return HttpResult(url=url, error=f'{type(e).__name__}: {e}', retry_count=self.retries)
