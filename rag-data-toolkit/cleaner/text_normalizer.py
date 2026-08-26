import html as html_lib
import re
import unicodedata


def normalize_text(text: str | None) -> str:
    if not text:
        return ''
    text = html_lib.unescape(text)
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\t', ' ')
    lines = []
    for line in text.split('\n'):
        line = re.sub(r'[ \u3000\xa0]+', ' ', line).strip()
        lines.append(line)
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
