from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from core.models import RawDocument, UrlItem
from crawler.url_normalizer import normalize_url
from utils.file_utils import dump_json
from utils.hash_utils import sha256_text


class DetailCrawler:
    def __init__(self, http_client, cfg: dict, logger, project_root: Path):
        self.http = http_client
        self.cfg = cfg
        self.logger = logger
        self.root = project_root

    def crawl_one(self, item: UrlItem) -> RawDocument:
        normalized = normalize_url(item.url)
        doc_id = sha256_text(normalized)
        result = self.http.get(normalized)
        now = datetime.now(timezone.utc).isoformat()
        html_rel = f'data/01_raw/html/{doc_id}.html'
        if result.text:
            html_path = self.root / html_rel
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(result.text, encoding='utf-8', errors='ignore')
        raw = RawDocument(
            id=doc_id,
            source_url=normalized,
            final_url=normalize_url(result.final_url or normalized),
            crawl_time=now,
            http_status=result.status_code,
            raw_title=item.title,
            raw_publish_time=item.publish_time,
            source_name=self.cfg.get('site', {}).get('name'),
            category=self.cfg.get('metadata', {}).get('category'),
            raw_html_path=html_rel if result.text else None,
            error=result.error,
        )
        dump_json(self.root / f'data/01_raw/json/{doc_id}.json', asdict(raw))
        self.logger.info('detail id=%s status=%s url=%s', doc_id[:10], result.status_code, normalized)
        return raw
