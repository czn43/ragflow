from pathlib import Path
import io, requests

def extract_pdf_text(url_or_path):
    data=None
    try:
        if str(url_or_path).startswith('http'):
            resp=requests.get(url_or_path,timeout=30,headers={'User-Agent':'Mozilla/5.0'})
            resp.raise_for_status(); data=resp.content
        else:
            data=Path(url_or_path).read_bytes()
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text='\n'.join((page.extract_text() or '') for page in pdf.pages)
        return text.strip()
    except Exception:
        return ''
