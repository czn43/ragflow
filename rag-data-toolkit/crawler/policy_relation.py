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
    arr=[]
    for a in soup.select('.fj a[href],a.pdf[href],a[href$=".pdf"]'):
        arr.append({'name':a.get_text(' ',strip=True),'url':urljoin(base_url,a['href'])})
    return arr
