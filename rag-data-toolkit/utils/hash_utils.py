import hashlib


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8', errors='ignore')).hexdigest()


def make_content_hash(content: str) -> str:
    normalized = ''.join(content.split())
    return sha256_text(normalized)
