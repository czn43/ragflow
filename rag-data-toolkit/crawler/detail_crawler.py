from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from cleaner.date_cleaner import parse_date
from core.models import RawDocument, UrlItem
from core.schema import make_standard_record
from crawler.detail_renderer import DetailRenderer
from crawler.url_normalizer import normalize_url
from extractor.html_extractor import extract
from utils.file_utils import dump_json
from utils.hash_utils import sha256_text


class DetailCrawler:
    def __init__(self, http_client, cfg: dict, logger, project_root: Path):
        self.http = http_client
        self.cfg = cfg
        self.logger = logger
        self.root = project_root
        self._renderer: DetailRenderer | None = None

    def _needs_render(self, html: str | None, ext) -> bool:
        detail = self.cfg.get('detail', {})
        enabled = bool(detail.get('render_fallback', True))
        if not enabled:
            return False
        min_chars = int(detail.get('min_content_chars', 100))
        if not html or ext is None:
            return True
        # On sites with a known detail selector (such as SZTV), a generic
        # Trafilatura result often means requests only received the page shell.
        if bool(detail.get('render_fallback_on_non_rule', False)) and ext.extraction_method != 'rule':
            return True
        return len((ext.content or '').strip()) < min_chars

    def _renderer_instance(self) -> DetailRenderer:
        if self._renderer is None:
            self._renderer = DetailRenderer(self.cfg, self.logger)
        return self._renderer

    def crawl_one(self, item: UrlItem) -> RawDocument:
        normalized = normalize_url(item.url)
        doc_id = sha256_text(normalized)
        result = self.http.get(normalized)
        now = datetime.now(timezone.utc).isoformat()

        html = result.text or ''
        ext = extract(html, self.cfg) if html else None
        render_used = False

        if self._needs_render(html, ext):
            rendered = self._renderer_instance().render(normalized)
            if rendered:
                rendered_ext = extract(rendered, self.cfg)
                # Prefer rendered page if it yields more actual article text.
                if len((rendered_ext.content or '').strip()) > len((ext.content or '').strip() if ext else ''):
                    html = rendered
                    ext = rendered_ext
                    render_used = True

        html_rel = f'data/01_raw/html/{doc_id}.html'
        if html:
            html_path = self.root / html_rel
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(html, encoding='utf-8', errors='ignore')

        # The RAW JSON is already an extracted text record, but is intentionally
        # NOT cleaned. This gives the user a readable raw article body while the
        # original HTML remains archived separately.
        ext = ext or extract('', self.cfg)
        title = (ext.title or item.title or '').strip()
        raw_content = ext.content or ''
        raw_date = ext.publish_time or item.publish_time or ''
        date_result = parse_date(raw_date)
        publish_time = date_result.normalized or ''
        source_name = (ext.source_name or item.source_name or self.cfg.get('site', {}).get('name') or '').strip()
        category = str(self.cfg.get('metadata', {}).get('category') or '')

        standard_raw = make_standard_record(
            source_name=source_name,
            source_url=normalized,
            title=title,
            content_text=raw_content,
            category=category,
            publish_time=publish_time,
            attachments=[],
        )
        dump_json(self.root / f'data/01_raw/json/{doc_id}.json', standard_raw)

        raw = RawDocument(
            id=doc_id,
            source_url=normalized,
            final_url=normalize_url(result.final_url or normalized),
            crawl_time=now,
            http_status=result.status_code,
            raw_title=title,
            raw_publish_time=raw_date,
            source_name=source_name,
            category=category,
            raw_html_path=html_rel if html else None,
            error=result.error,
        )

        meta = asdict(raw)
        meta.update({
            'extraction_method': ext.extraction_method,
            'render_fallback_used': render_used,
            'raw_content_chars': len(raw_content.strip()),
            'standard_json_path': f'data/01_raw/json/{doc_id}.json',
        })
        dump_json(self.root / f'data/01_raw/meta/{doc_id}.json', meta)
        self.logger.info(
            'detail id=%s status=%s chars=%s render=%s url=%s',
            doc_id[:10], result.status_code, len(raw_content.strip()), render_used, normalized
        )
        return raw

    def close(self) -> None:
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
