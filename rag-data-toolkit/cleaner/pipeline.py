from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from cleaner.date_cleaner import parse_date
from cleaner.noise_cleaner import clean_noise
from cleaner.text_normalizer import normalize_text
from cleaner.validator import validate_document
from core.schema import coerce_standard_record, exact_standard_record, make_standard_record
from crawler.url_normalizer import normalize_url
from utils.file_utils import dump_json, load_json, write_jsonl
from utils.hash_utils import make_content_hash, sha256_text


class ProcessingPipeline:
    """Stage-oriented pipeline.

    User-facing stage files always use the exact eight-field standard schema:
    sourceName/sourceUrl/title/contentText/category/publishTime/attachments/attachmentCount.
    Technical quality/audit fields are written separately to data/_internal.
    """

    def __init__(self, root: Path, cfg: dict, noise_cfg: dict, logger):
        self.root = root
        self.cfg = cfg
        self.noise_cfg = noise_cfg
        self.logger = logger
        self.stats = {
            'raw': 0,
            'url_duplicate': 0,
            'extracted': 0,
            'cleaned': 0,
            'empty_content': 0,
            'short_content': 0,
            'content_duplicate': 0,
            'rejected': 0,
            'warnings': 0,
            'validated': 0,
            'final': 0,
        }
        self.action_counts: dict[str, int] = {}

    def _load_raw(self) -> list[dict]:
        records = []
        for p in sorted((self.root / 'data/01_raw/json').glob('*.json')):
            d = load_json(p)
            if d:
                records.append(coerce_standard_record(d))
        return records

    @staticmethod
    def _dedup_url(records: list[dict]) -> tuple[list[dict], list[dict]]:
        kept = {}
        duplicates = []
        for record in records:
            url = normalize_url(record.get('sourceUrl') or '')
            if not url:
                bad = dict(record)
                bad['_rejectReason'] = 'INVALID_URL'
                duplicates.append(bad)
                continue
            if url in kept:
                dup = dict(record)
                dup['_rejectReason'] = 'DUPLICATE_URL'
                duplicates.append(dup)
                continue
            record = dict(record)
            record['sourceUrl'] = url
            kept[url] = record
        return list(kept.values()), duplicates

    @staticmethod
    def _dedup_content(records: list[dict], audits: dict[str, dict]) -> tuple[list[dict], list[dict]]:
        kept = {}
        duplicates = []
        for record in records:
            url = record.get('sourceUrl') or ''
            key = make_content_hash(normalize_text(record.get('contentText') or ''))
            if not key:
                key = f'__empty__:{sha256_text(url)}'
            if key not in kept:
                kept[key] = record
                continue
            dup = dict(record)
            dup['_rejectReason'] = 'DUPLICATE_CONTENT'
            duplicates.append(dup)
            audit = audits.get(url)
            if audit:
                audit['status'] = 'reject'
                audit['issues'] = sorted(set((audit.get('issues') or []) + ['DUPLICATE_CONTENT']))
        return list(kept.values()), duplicates

    def run(self) -> tuple[list[dict], list[dict]]:
        raw_records = self._load_raw()
        self.stats['raw'] = len(raw_records)

        # Stage 02: extracted but not cleaned. Exact standard schema.
        extracted = [exact_standard_record(x) for x in raw_records]
        self.stats['extracted'] = len(extracted)
        write_jsonl(self.root / 'data/02_extracted/extracted.jsonl', extracted)

        # Stage 03: URL dedup only; raw text is still unchanged.
        deduped, url_dups = self._dedup_url(extracted)
        self.stats['url_duplicate'] = len(url_dups)
        write_jsonl(self.root / 'data/03_dedup/dedup.jsonl', [exact_standard_record(x) for x in deduped])

        cleaned_records: list[dict] = []
        audits: dict[str, dict] = {}
        rejected: list[dict] = []
        min_chars = int(self.cfg.get('detail', {}).get('min_content_chars', 100))

        for raw in deduped:
            source_url = raw.get('sourceUrl') or ''
            title = normalize_text(raw.get('title') or '')
            content_before = raw.get('contentText') or ''
            content = normalize_text(content_before)
            content, actions, noise_issues = clean_noise(content, self.noise_cfg)
            for action in actions:
                self.action_counts[action.rule] = self.action_counts.get(action.rule, 0) + 1

            date_result = parse_date(raw.get('publishTime') or '')
            publish_time = date_result.normalized or ''
            issues = list(noise_issues)
            if raw.get('publishTime') and not date_result.valid:
                issues.append(date_result.reason or 'DATE_PARSE_ERROR')

            clean = make_standard_record(
                source_name=normalize_text(raw.get('sourceName') or ''),
                source_url=normalize_url(source_url),
                title=title,
                content_text=content,
                category=normalize_text(raw.get('category') or self.cfg.get('metadata', {}).get('category') or ''),
                publish_time=publish_time,
                attachments=raw.get('attachments') or [],
            )
            cleaned_records.append(clean)

            internal_doc = {
                'title': clean['title'],
                'content': clean['contentText'],
                'source_url': clean['sourceUrl'],
                'issues': sorted(set(i for i in issues if i)),
            }
            vr = validate_document(internal_doc, min_chars=min_chars)
            if not clean['contentText']:
                self.stats['empty_content'] += 1
            elif len(clean['contentText']) < min_chars:
                self.stats['short_content'] += 1

            status = vr.status
            if status == 'warning':
                self.stats['warnings'] += 1

            audits[source_url] = {
                'id': sha256_text(clean['sourceUrl']) if clean['sourceUrl'] else '',
                'sourceUrl': clean['sourceUrl'],
                'title': clean['title'],
                'beforeChars': len(content_before),
                'afterChars': len(clean['contentText']),
                'status': status,
                'issues': vr.issues,
                'cleaningActions': [asdict(a) for a in actions],
                'contentHash': make_content_hash(clean['contentText']) if clean['contentText'] else '',
                'urlHash': sha256_text(clean['sourceUrl']) if clean['sourceUrl'] else '',
            }

        self.stats['cleaned'] = len(cleaned_records)
        write_jsonl(self.root / 'data/04_clean/cleaned.jsonl', [exact_standard_record(x) for x in cleaned_records])

        # Exact-content dedup happens after cleaning, because boilerplate differences
        # should not prevent duplicate detection.
        content_ready = []
        for rec in cleaned_records:
            audit = audits.get(rec.get('sourceUrl') or '', {})
            if audit.get('status') == 'reject':
                bad = dict(rec)
                bad['_rejectReason'] = ','.join(audit.get('issues') or ['VALIDATION_REJECT'])
                rejected.append(bad)
            else:
                content_ready.append(rec)

        content_ready, content_dups = self._dedup_content(content_ready, audits)
        self.stats['content_duplicate'] = len(content_dups)
        rejected.extend(content_dups)
        rejected.extend(url_dups)
        self.stats['rejected'] = len(rejected)

        validated = [exact_standard_record(x) for x in content_ready]
        self.stats['validated'] = len(validated)
        self.stats['final'] = len(validated)
        write_jsonl(self.root / 'data/05_validated/validated.jsonl', validated)
        write_jsonl(self.root / 'data/_internal/record_audit.jsonl', list(audits.values()))
        write_jsonl(self.root / 'data/rejected/rejected.jsonl', rejected)

        dump_json(self.root / 'reports/pipeline_stats.json', self.stats)
        dump_json(self.root / 'reports/actions.json', [
            {'rule': k, 'affectedCount': v} for k, v in sorted(self.action_counts.items())
        ])
        self.logger.info('pipeline complete stats=%s', self.stats)
        return validated, rejected
