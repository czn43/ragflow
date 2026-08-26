from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from cleaner.content_deduplicator import deduplicate_documents
from cleaner.date_cleaner import parse_date
from cleaner.metadata_builder import build_metadata
from cleaner.noise_cleaner import clean_noise
from cleaner.quality_scorer import score_document
from cleaner.tagger import generate_tags
from cleaner.text_normalizer import normalize_text
from cleaner.url_deduplicator import deduplicate_raw_documents
from cleaner.validator import validate_document
from crawler.url_normalizer import normalize_url
from extractor.html_extractor import extract
from utils.file_utils import dump_json, load_json, write_jsonl
from utils.hash_utils import make_content_hash, sha256_text


class ProcessingPipeline:
    def __init__(self, root: Path, cfg: dict, noise_cfg: dict, logger):
        self.root = root
        self.cfg = cfg
        self.noise_cfg = noise_cfg
        self.logger = logger
        self.stats = {
            'raw': 0,
            'url_duplicate': 0,
            'extract_failed': 0,
            'empty_content': 0,
            'content_duplicate': 0,
            'rejected': 0,
            'warnings': 0,
            'final': 0,
        }
        self.action_counts: dict[str, int] = {}

    def _load_raw(self) -> list[dict]:
        raws = []
        for p in sorted((self.root / 'data/01_raw/json').glob('*.json')):
            d = load_json(p)
            if d:
                raws.append(d)
        return raws

    def run(self) -> tuple[list[dict], list[dict]]:
        raws = self._load_raw()
        self.stats['raw'] = len(raws)
        raws, url_dups = deduplicate_raw_documents(raws)
        self.stats['url_duplicate'] = len(url_dups)
        if url_dups:
            write_jsonl(self.root / 'data/rejected/url_duplicates.jsonl', url_dups)

        processed = []
        prelim_rejected = []
        min_chars = int(self.cfg.get('detail', {}).get('min_content_chars', 100))

        for raw in raws:
            html_path = self.root / (raw.get('raw_html_path') or '')
            if not html_path.exists() or (raw.get('http_status') or 0) >= 400:
                bad = dict(raw)
                bad['reject_reason'] = 'HTTP_ERROR'
                prelim_rejected.append(bad)
                continue
            html = html_path.read_text(encoding='utf-8', errors='ignore')
            ext = extract(html, self.cfg)
            title = normalize_text(ext.title or raw.get('raw_title') or '')
            content = normalize_text(ext.content or '')
            if not content:
                self.stats['extract_failed'] += 1

            content, actions, noise_issues = clean_noise(content, self.noise_cfg)
            for a in actions:
                self.action_counts[a.rule] = self.action_counts.get(a.rule, 0) + 1

            raw_date = ext.publish_time or raw.get('raw_publish_time')
            date_result = parse_date(raw_date)
            issues = list(noise_issues)
            if raw_date and not date_result.valid:
                issues.append(date_result.reason or 'DATE_PARSE_ERROR')
            if not content:
                issues.append('EMPTY_CONTENT')
                self.stats['empty_content'] += 1

            source_url = normalize_url(raw.get('source_url', ''))
            doc = {
                'id': raw['id'],
                'title': title,
                'content': content,
                'source_url': source_url,
                'source_name': ext.source_name or raw.get('source_name') or '',
                'publish_time': date_result.normalized if date_result.normalized else None,
                'crawl_time': raw.get('crawl_time'),
                'category': raw.get('category'),
                'tags': [],
                'region': None,
                'document_type': None,
                'char_count': len(content),
                'quality_score': 0,
                'quality_level': 'LOW',
                'status': 'valid',
                'issues': sorted(set(i for i in issues if i)),
                'cleaning_actions': [asdict(a) for a in actions],
                'content_hash': make_content_hash(content) if content else '',
                'url_hash': sha256_text(source_url) if source_url else '',
                'cleaning_version': 'v1.0',
                'extraction_method': ext.extraction_method,
            }
            doc = build_metadata(doc, self.cfg)
            doc['tags'] = generate_tags(doc, self.cfg)
            vr = validate_document(doc, min_chars=min_chars)
            doc['status'] = vr.status
            doc['issues'] = vr.issues
            score, level = score_document(doc)
            doc['quality_score'] = score
            doc['quality_level'] = level

            if vr.status == 'reject':
                prelim_rejected.append(doc)
                continue
            if vr.status == 'warning':
                self.stats['warnings'] += 1
            processed.append(doc)

        # Content dedup after quality score is available.
        processed, content_dups = deduplicate_documents(processed)
        self.stats['content_duplicate'] = len(content_dups)
        rejected = prelim_rejected + content_dups
        self.stats['rejected'] = len(rejected) + len(url_dups)
        self.stats['final'] = len(processed)

        write_jsonl(self.root / 'data/02_extracted/extracted.jsonl', processed + prelim_rejected)
        write_jsonl(self.root / 'data/04_clean/cleaned.jsonl', processed)
        write_jsonl(self.root / 'data/05_validated/validated.jsonl', processed)
        write_jsonl(self.root / 'data/rejected/rejected.jsonl', rejected)
        dump_json(self.root / 'reports/pipeline_stats.json', self.stats)
        dump_json(self.root / 'reports/actions.json', [
            {'rule': k, 'affected_count': v} for k, v in sorted(self.action_counts.items())
        ])
        self.logger.info('pipeline complete stats=%s', self.stats)
        return processed, rejected
