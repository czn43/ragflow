import re

from bs4 import BeautifulSoup
from urllib.parse import urljoin

KEYWORDS=('原文','印发','通知','关于','附件')

def find_policy_links(html, base_url):
    soup=BeautifulSoup(html,'lxml')
    result=[]
    for a in soup.select('a[href]'):
        text=a.get_text(' ',strip=True)
        href=urljoin(base_url,a.get('href'))
        if any(k in text for k in KEYWORDS) and href not in result:
            result.append(href)
    return result

def find_pdf_attachments(html, base_url):
    soup=BeautifulSoup(html,'lxml')
    found={}
    for anchor in soup.select('.fj a[href], a.pdf[href], a[href]'):
        raw=(anchor.get('href') or '').strip()
        if not raw.lower().split('?',1)[0].endswith('.pdf'):
            continue
        url=urljoin(base_url,raw)
        found.setdefault(url,{
            'name':anchor.get_text(' ',strip=True) or raw.rsplit('/',1)[-1],
            'url':url,
        })

    # Some templates only expose the attachment path in a JS variable.
    pattern=r"file_appendix\s*=\s*(['\"])(.*?)\1"
    for match in re.finditer(pattern,html or '',flags=re.I|re.S):
        value=match.group(2)
        for raw in re.findall(r"(?:https?://|/|\.\.?/)[^'\"<>\s]+?\.pdf(?:\?[^'\"<>\s]*)?",value,flags=re.I):
            url=urljoin(base_url,raw)
            found.setdefault(url,{'name':raw.rsplit('/',1)[-1],'url':url})
    return list(found.values())
