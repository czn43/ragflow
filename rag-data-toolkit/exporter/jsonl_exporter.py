from pathlib import Path
from utils.file_utils import read_jsonl, write_jsonl


def export_final_jsonl(root: Path) -> int:
    docs = read_jsonl(root / 'data/05_validated/validated.jsonl')
    # Keep only RAG-relevant fields, while preserving quality and traceability.
    fields = [
        'id', 'title', 'content', 'source_url', 'source_name', 'publish_time',
        'crawl_time', 'category', 'tags', 'region', 'document_type',
        'char_count', 'quality_score', 'quality_level', 'issues',
        'content_hash', 'url_hash', 'cleaning_version', 'extraction_method'
    ]
    final_docs = [{k: d.get(k) for k in fields} for d in docs]
    write_jsonl(root / 'data/06_final/final.jsonl', final_docs)
    return len(final_docs)
