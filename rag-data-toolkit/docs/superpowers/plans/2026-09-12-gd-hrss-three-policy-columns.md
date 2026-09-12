# Guangdong HRSS Three Policy Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crawl all paginated records from the Guangdong HRSS national-policy, provincial-policy, and policy-explanation columns as independently classified P0 sources, including extractable PDF attachments.

**Architecture:** Keep the existing `gd_hrss_employment` site ID for provincial policy and add one YAML config for each other column. Reuse the site's verified CSS selectors, add a small attachment-discovery enhancement shared by all policy documents, and select only the three HRSS sites for the production rerun so existing P0 outputs remain intact.

**Tech Stack:** Python 3, pytest, BeautifulSoup4, PyYAML, existing crawler/extractor pipeline, PowerShell commands on Windows.

---

## File map

- Create `config/sites/gd_hrss_national_policy.yaml`: national-policy column entry, selectors, metadata, and tags.
- Modify `config/sites/gd_hrss_employment.yaml`: replace automatic discovery with verified provincial-policy selectors and correct classification.
- Create `config/sites/gd_hrss_policy_explain.yaml`: policy-explanation column entry and relationship/attachment mode.
- Modify `config/tasks/guangdong_education_talent_p0.yaml`: register the two new sites and retain the provincial site ID.
- Modify `crawler/policy_relation.py`: discover visible PDF links and PDF URLs embedded in `file_appendix`, with URL deduplication.
- Modify `crawler/detail_crawler.py`: collect direct policy-page attachments for every document and avoid duplicates when following explanation relations.
- Create `tests/fixtures/gd_hrss_policy_list.html`: small stable list-page fixture matching the supplied HTML structure.
- Create `tests/fixtures/gd_hrss_policy_detail.html`: small stable detail-page fixture matching the supplied HTML structure.
- Create `tests/test_gd_hrss_policy_columns.py`: network-free config, list, detail, metadata, task-registration, and attachment regressions.

### Task 1: Lock the three-column configuration contract with failing tests

**Files:**
- Create: `tests/fixtures/gd_hrss_policy_list.html`
- Create: `tests/fixtures/gd_hrss_policy_detail.html`
- Create: `tests/test_gd_hrss_policy_columns.py`
- Test: `tests/test_gd_hrss_policy_columns.py`

- [ ] **Step 1: Create the list fixture**

Add this complete fixture to `tests/fixtures/gd_hrss_policy_list.html`:

```html
<html><body>
  <ul class="list">
    <li>
      <a href="/jyzl/zcfg/bszc/content/post_4924456.html">关于开展就业服务攻坚行动的通知</a>
      <span class="pubDate">2026-07-10</span>
    </li>
  </ul>
  <div class="pages">
    <a class="next" href="/jyzl/zcfg/bszc/index_2.html">下一页</a>
  </div>
</body></html>
```

- [ ] **Step 2: Create the detail fixture**

Add this complete fixture to `tests/fixtures/gd_hrss_policy_detail.html`:

```html
<html><body>
  <div class="insMainConTitle_b">人力资源社会保障部关于开展就业援助活动的通知</div>
  <div class="insMainConTitle_c">发布日期：2024-12-22　打印本页</div>
  <div id="insMainConTxt" class="insMainConTxt_c">
    <div class="TRS_Editor">
      <p>为促进高质量充分就业，现组织开展就业援助活动。</p>
      <p>活动对象包括高校毕业生、登记失业青年和就业困难人员。</p>
      <p>各地应开展岗位归集、职业指导、专场招聘和政策落实工作。</p>
      <p>本段用于保证测试正文超过规则抽取要求的最小长度，并验证不会抽入关闭窗口等页面噪声。</p>
      <a href="/files/employment-policy.pdf">附件：就业政策.pdf</a>
    </div>
    <script>var file_appendix='/files/second-attachment.pdf';</script>
  </div>
  <div class="insMainConTxt_d">【关闭窗口】</div>
</body></html>
```

- [ ] **Step 3: Write tests for the three YAML files and task registration**

Add the following to `tests/test_gd_hrss_policy_columns.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from core.models import HttpResult, UrlItem
from crawler import detail_crawler as dcmod
from crawler.list_crawler import get_next_url, parse_list_page
from crawler.policy_relation import find_pdf_attachments
from extractor.html_extractor import extract_by_rule

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / 'config' / 'sites'
FIXTURES = Path(__file__).resolve().parent / 'fixtures'

SITES = {
    'gd_hrss_national_policy.yaml': {
        'path': '/jyzl/zcfg/gjzc/',
        'category': '教育与人才-就业政策-国家政策',
        'document_type': 'employment_policy',
    },
    'gd_hrss_employment.yaml': {
        'path': '/jyzl/zcfg/bszc/',
        'category': '教育与人才-就业政策-本省政策',
        'document_type': 'employment_policy',
    },
    'gd_hrss_policy_explain.yaml': {
        'path': '/jyzl/zcfg/zcjd/',
        'category': '教育与人才-就业政策-政策解读',
        'document_type': 'policy_explanation',
    },
}


def load_yaml(path: Path) -> dict:
    with path.open(encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


@pytest.mark.parametrize(('filename', 'expected'), SITES.items())
def test_hrss_column_config_contract(filename: str, expected: dict):
    cfg = load_yaml(SITE_DIR / filename)
    starts = cfg['crawler']['start_urls']
    assert len(starts) == 1
    assert expected['path'] in starts[0]
    assert cfg['crawler']['start_mode'] == 'list'
    assert cfg['list'] == {
        'item_selector': 'ul.list li',
        'link_selector': "a[href*='/content/post_']",
        'title_selector': "a[href*='/content/post_']",
        'date_selector': '.pubDate',
    }
    assert cfg['pagination'] == {
        'type': 'next_link',
        'next_selector': '.pages a.next',
    }
    assert cfg['detail']['title']['selectors'][0] == '.insMainConTitle_b'
    assert cfg['detail']['content']['selectors'][0] == '#insMainConTxt .TRS_Editor'
    assert '.insMainConTitle_c' in cfg['detail']['publish_time']['selectors']
    assert cfg['metadata']['category'] == expected['category']
    assert cfg['metadata']['document_type'] == expected['document_type']


def test_p0_task_registers_each_hrss_column_once():
    task = load_yaml(ROOT / 'config' / 'tasks' / 'guangdong_education_talent_p0.yaml')
    entries = {entry['id']: entry for entry in task['sites']}
    expected = {
        'gd_hrss_national_policy': 'config/sites/gd_hrss_national_policy.yaml',
        'gd_hrss_employment': 'config/sites/gd_hrss_employment.yaml',
        'gd_hrss_policy_explain': 'config/sites/gd_hrss_policy_explain.yaml',
    }
    for site_id, path in expected.items():
        assert entries[site_id]['config'] == path
        assert entries[site_id]['enabled'] is True
```

- [ ] **Step 4: Write tests for list, detail, and attachment parsing**

Append this code to `tests/test_gd_hrss_policy_columns.py`:

```python
def test_hrss_list_and_next_page_use_verified_structure():
    html = (FIXTURES / 'gd_hrss_policy_list.html').read_text(encoding='utf-8')
    cfg = load_yaml(SITE_DIR / 'gd_hrss_employment.yaml')
    current = 'https://hrss.gd.gov.cn/jyzl/zcfg/bszc/index.html'
    items = parse_list_page(html, current, cfg)
    assert len(items) == 1
    assert items[0].url.endswith('/jyzl/zcfg/bszc/content/post_4924456.html')
    assert items[0].publish_time == '2026-07-10'
    assert get_next_url(html, current, cfg, page_no=1).endswith('/jyzl/zcfg/bszc/index_2.html')


def test_hrss_detail_extracts_only_article_fields():
    html = (FIXTURES / 'gd_hrss_policy_detail.html').read_text(encoding='utf-8')
    cfg = load_yaml(SITE_DIR / 'gd_hrss_employment.yaml')
    result = extract_by_rule(html, cfg)
    assert result.extraction_method == 'rule'
    assert result.title == '人力资源社会保障部关于开展就业援助活动的通知'
    assert result.publish_time == '2024-12-22'
    assert '高校毕业生' in (result.content or '')
    assert '关闭窗口' not in (result.content or '')


def test_hrss_attachment_discovery_reads_links_and_file_appendix_once():
    html = (FIXTURES / 'gd_hrss_policy_detail.html').read_text(encoding='utf-8')
    base = 'https://hrss.gd.gov.cn/jyzl/zcfg/bszc/content/post_1.html'
    attachments = find_pdf_attachments(html, base)
    urls = [item['url'] for item in attachments]
    assert urls == [
        'https://hrss.gd.gov.cn/files/employment-policy.pdf',
        'https://hrss.gd.gov.cn/files/second-attachment.pdf',
    ]
```

- [ ] **Step 5: Run the new tests and verify they fail for the missing configs and old selectors**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_gd_hrss_policy_columns.py -q
```

Expected: FAIL because the two new YAML files do not exist, `gd_hrss_employment.yaml` still has an empty `item_selector`, and `file_appendix` is not yet parsed.

- [ ] **Step 6: Commit the regression fixtures and failing tests**

```powershell
git add tests/fixtures/gd_hrss_policy_list.html tests/fixtures/gd_hrss_policy_detail.html tests/test_gd_hrss_policy_columns.py
git commit -m "test: cover Guangdong HRSS policy columns"
```

### Task 2: Add the three independent site configurations

**Files:**
- Create: `config/sites/gd_hrss_national_policy.yaml`
- Modify: `config/sites/gd_hrss_employment.yaml`
- Create: `config/sites/gd_hrss_policy_explain.yaml`
- Test: `tests/test_gd_hrss_policy_columns.py`

- [ ] **Step 1: Replace the provincial config with verified selectors and metadata**

Set `config/sites/gd_hrss_employment.yaml` to:

```yaml
site:
  name: 广东省人力资源和社会保障厅-就业本省政策
  domain: hrss.gd.gov.cn
crawler:
  start_mode: list
  start_urls:
    - https://hrss.gd.gov.cn/jyzl/zcfg/bszc/
  timeout: 20
  retries: 3
  delay: {min: 0.2, max: 0.6}
list:
  item_selector: ul.list li
  link_selector: "a[href*='/content/post_']"
  title_selector: "a[href*='/content/post_']"
  date_selector: .pubDate
pagination:
  type: next_link
  next_selector: .pages a.next
discovery:
  min_score: 3
  detail_url_score: 4
  allow_external: false
detail:
  min_content_chars: 100
  render_fallback: true
  title:
    selectors: [.insMainConTitle_b, h1, .article-title, .title]
  content:
    selectors: ["#insMainConTxt .TRS_Editor", "#insMainConTxt", .article-content]
  publish_time:
    selectors: [.insMainConTitle_c, .time, .date, .publish-time]
    regex_extract: "(\\d{4}-\\d{1,2}-\\d{1,2})"
  source:
    selectors: []
metadata:
  category: 教育与人才-就业政策-本省政策
  region: 广东
  document_type: employment_policy
  max_tags: 7
tag_rules:
  就业见习: [就业见习, 见习岗位]
  高校毕业生: [高校毕业生, 毕业生]
  补贴: [补贴, 社保补贴, 求职补贴, 基层岗位补贴]
  创业: [创业, 创业担保贷款, 创业租金]
```

- [ ] **Step 2: Create the national-policy config**

Create `config/sites/gd_hrss_national_policy.yaml` with the same verified structure and these complete values:

```yaml
site:
  name: 广东省人力资源和社会保障厅-就业国家政策
  domain: hrss.gd.gov.cn
crawler:
  start_mode: list
  start_urls:
    - https://hrss.gd.gov.cn/jyzl/zcfg/gjzc/
  timeout: 20
  retries: 3
  delay: {min: 0.2, max: 0.6}
list:
  item_selector: ul.list li
  link_selector: "a[href*='/content/post_']"
  title_selector: "a[href*='/content/post_']"
  date_selector: .pubDate
pagination:
  type: next_link
  next_selector: .pages a.next
discovery:
  min_score: 3
  detail_url_score: 4
  allow_external: false
detail:
  min_content_chars: 100
  render_fallback: true
  title:
    selectors: [.insMainConTitle_b, h1, .article-title, .title]
  content:
    selectors: ["#insMainConTxt .TRS_Editor", "#insMainConTxt", .article-content]
  publish_time:
    selectors: [.insMainConTitle_c, .time, .date, .publish-time]
    regex_extract: "(\\d{4}-\\d{1,2}-\\d{1,2})"
  source:
    selectors: []
metadata:
  category: 教育与人才-就业政策-国家政策
  region: 广东
  document_type: employment_policy
  max_tags: 7
tag_rules:
  高校毕业生: [高校毕业生, 毕业生]
  就业服务: [公共就业服务, 就业服务, 招聘]
  就业援助: [就业援助, 就业困难人员, 零就业家庭]
  补贴: [补贴, 社保补贴, 求职补贴]
```

- [ ] **Step 3: Create the policy-explanation config**

Create `config/sites/gd_hrss_policy_explain.yaml` with:

```yaml
site:
  name: 广东省人力资源和社会保障厅-就业政策解读
  domain: hrss.gd.gov.cn
crawler:
  start_mode: list
  start_urls:
    - https://hrss.gd.gov.cn/jyzl/zcfg/zcjd/
  timeout: 20
  retries: 3
  delay: {min: 0.2, max: 0.6}
list:
  item_selector: ul.list li
  link_selector: "a[href*='/content/post_']"
  title_selector: "a[href*='/content/post_']"
  date_selector: .pubDate
pagination:
  type: next_link
  next_selector: .pages a.next
discovery:
  min_score: 3
  detail_url_score: 4
  allow_external: false
detail:
  min_content_chars: 100
  render_fallback: true
  title:
    selectors: [.insMainConTitle_b, h1, .article-title, .title]
  content:
    selectors: ["#insMainConTxt .TRS_Editor", "#insMainConTxt", .article-content]
  publish_time:
    selectors: [.insMainConTitle_c, .time, .date, .publish-time]
    regex_extract: "(\\d{4}-\\d{1,2}-\\d{1,2})"
  source:
    selectors: []
metadata:
  category: 教育与人才-就业政策-政策解读
  region: 广东
  document_type: policy_explanation
  max_tags: 7
tag_rules:
  政策解读: [政策解读, 图解, 问答]
  高校毕业生: [高校毕业生, 毕业生]
  就业服务: [公共就业服务, 就业服务, 招聘]
  补贴: [补贴, 社保补贴, 求职补贴]
```

- [ ] **Step 4: Run the config, list, and detail tests**

Run the configuration and HTML parsing subset:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_gd_hrss_policy_columns.py -q -k "not attachment and not p0_task"
```

Expected: the selected configuration, list, and detail tests PASS. Attachment and task-registration tests remain intentionally deferred.

- [ ] **Step 5: Commit the three site configurations**

```powershell
git add config/sites/gd_hrss_national_policy.yaml config/sites/gd_hrss_employment.yaml config/sites/gd_hrss_policy_explain.yaml
git commit -m "feat: configure Guangdong HRSS policy columns"
```

### Task 3: Collect direct and scripted PDF attachments without duplicates

**Files:**
- Modify: `crawler/policy_relation.py`
- Modify: `crawler/detail_crawler.py`
- Modify: `tests/test_gd_hrss_policy_columns.py`
- Test: `tests/test_gd_hrss_policy_columns.py`

- [ ] **Step 1: Extend PDF discovery for `file_appendix`**

Replace `find_pdf_attachments` in `crawler/policy_relation.py` and add the `re` import:

```python
import re


def find_pdf_attachments(html, base_url):
    soup = BeautifulSoup(html, 'lxml')
    found = {}
    for anchor in soup.select('.fj a[href], a.pdf[href], a[href]'):
        raw = (anchor.get('href') or '').strip()
        if not raw.lower().split('?', 1)[0].endswith('.pdf'):
            continue
        url = urljoin(base_url, raw)
        found.setdefault(url, {
            'name': anchor.get_text(' ', strip=True) or raw.rsplit('/', 1)[-1],
            'url': url,
        })

    pattern = r"file_appendix\s*=\s*(['\"])(.*?)\1"
    for match in re.finditer(pattern, html or '', flags=re.I | re.S):
        value = match.group(2)
        for raw in re.findall(r"(?:https?://|/|\.\.?/)[^'\"<>\s]+?\.pdf(?:\?[^'\"<>\s]*)?", value, flags=re.I):
            url = urljoin(base_url, raw)
            found.setdefault(url, {'name': raw.rsplit('/', 1)[-1], 'url': url})
    return list(found.values())
```

- [ ] **Step 2: Verify PDF discovery passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_gd_hrss_policy_columns.py::test_hrss_attachment_discovery_reads_links_and_file_appendix_once -q
```

Expected: `1 passed`.

- [ ] **Step 3: Add a failing crawler test for direct attachments**

Append this complete test support and test to `tests/test_gd_hrss_policy_columns.py`:

```python
class FakeLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass


class FakeHttp:
    def __init__(self, html: str):
        self.html = html

    def get(self, url: str) -> HttpResult:
        return HttpResult(
            url=url,
            final_url=url,
            status_code=200,
            text=self.html,
            encoding='utf-8',
        )


def test_employment_policy_crawler_preserves_direct_attachment(monkeypatch, tmp_path):
    html = (FIXTURES / 'gd_hrss_policy_detail.html').read_text(encoding='utf-8')
    cfg = load_yaml(SITE_DIR / 'gd_hrss_employment.yaml')
    monkeypatch.setattr(dcmod, 'extract_pdf_text', lambda url: 'PDF正文')
    crawler = dcmod.DetailCrawler(FakeHttp(html), cfg, FakeLogger(), tmp_path)
    raw = crawler.crawl_one(UrlItem(
        url='https://hrss.gd.gov.cn/jyzl/zcfg/bszc/content/post_1.html',
        title='列表标题',
    ))
    data_path = tmp_path / 'data' / '01_raw' / 'json' / f'{raw.id}.json'
    data = json.loads(data_path.read_text(encoding='utf-8'))
    assert data['attachmentCount'] == 2
    assert data['attachments'] == [
        {
            'name': '附件：就业政策.pdf',
            'url': 'https://hrss.gd.gov.cn/files/employment-policy.pdf',
            'contentText': 'PDF正文',
        },
        {
            'name': 'second-attachment.pdf',
            'url': 'https://hrss.gd.gov.cn/files/second-attachment.pdf',
            'contentText': 'PDF正文',
        },
    ]
```

- [ ] **Step 4: Run the direct-attachment crawler test and verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_gd_hrss_policy_columns.py -k direct_attachment -q
```

Expected: FAIL because `DetailCrawler` currently initializes an empty attachment list for ordinary policy documents.

- [ ] **Step 5: Collect direct PDFs before explanation-specific relation traversal**

In `crawler/detail_crawler.py`, replace the `attachments = []` initialization with:

```python
        attachments = []
        attachment_urls = set()
        for direct_pdf in find_pdf_attachments(html, normalized):
            pdf_url = direct_pdf.get('url')
            if not pdf_url or pdf_url in attachment_urls:
                continue
            direct_pdf['contentText'] = extract_pdf_text(pdf_url)
            attachments.append(direct_pdf)
            attachment_urls.add(pdf_url)
```

Inside the existing related-policy PDF loop, replace the unconditional append with:

```python
                        for item_pdf in rel_pdf:
                            pdf_url = item_pdf.get('url')
                            if not pdf_url or pdf_url in attachment_urls:
                                continue
                            item_pdf['contentText'] = extract_pdf_text(pdf_url)
                            attachments.append(item_pdf)
                            attachment_urls.add(pdf_url)
```

- [ ] **Step 6: Run all HRSS tests**

Run all HRSS tests except the task-registration test, which belongs to Task 4:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_gd_hrss_policy_columns.py -q -k "not p0_task"
```

Expected: all selected tests PASS.

- [ ] **Step 7: Commit the attachment enhancement**

```powershell
git add crawler/policy_relation.py crawler/detail_crawler.py tests/test_gd_hrss_policy_columns.py
git commit -m "feat: preserve policy PDF attachments"
```

### Task 4: Register all three sources in the Guangdong P0 task

**Files:**
- Modify: `config/tasks/guangdong_education_talent_p0.yaml`
- Test: `tests/test_gd_hrss_policy_columns.py`

- [ ] **Step 1: Add the national policy entry before the existing provincial entry**

Insert:

```yaml
  - id: gd_hrss_national_policy
    name: 广东就业国家政策
    config: config/sites/gd_hrss_national_policy.yaml
    enabled: true
    priority: 4
    max_pages: 100
    max_docs: 1000
```

- [ ] **Step 2: Update the existing provincial entry to crawl until pagination ends**

Keep its ID and config path, but set:

```yaml
  - id: gd_hrss_employment
    name: 广东就业本省政策
    config: config/sites/gd_hrss_employment.yaml
    enabled: true
    priority: 4
    max_pages: 100
    max_docs: 1000
```

- [ ] **Step 3: Add the policy-explanation entry after the provincial entry**

Insert:

```yaml
  - id: gd_hrss_policy_explain
    name: 广东就业政策解读
    config: config/sites/gd_hrss_policy_explain.yaml
    enabled: true
    priority: 4
    max_pages: 100
    max_docs: 1000
```

The 100-page/1000-document values are safety ceilings; `.pages a.next` terminates naturally at the last page.

- [ ] **Step 4: Run task-registration and full regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_gd_hrss_policy_columns.py tests/test_gd_p0_site_configs.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: the focused tests PASS, followed by the complete suite PASS with no new failures.

- [ ] **Step 5: Commit task registration**

```powershell
git add config/tasks/guangdong_education_talent_p0.yaml
git commit -m "feat: add HRSS policy sources to Guangdong P0"
```

### Task 5: Validate live structure, run only the three sources, and verify merged output

**Files:**
- Inspect: `reports/inspect_report.json`
- Generate: `data/runs/guangdong_education_talent_p0/*`
- Generate: `data/final/guangdong_education_talent_p0/combined_final.jsonl`
- Generate: `reports/tasks/guangdong_education_talent_p0/multi_summary.json`

- [ ] **Step 1: Inspect the national-policy column**

Run:

```powershell
.\.venv\Scripts\python.exe main.py inspect --site config/sites/gd_hrss_national_policy.yaml --validate-top 3
```

Expected: HTTP status below 400, `selector_matches` greater than zero, and validated details with `extraction_method: rule` and `valid_article: true`.

- [ ] **Step 2: Inspect the provincial-policy column**

Run:

```powershell
.\.venv\Scripts\python.exe main.py inspect --site config/sites/gd_hrss_employment.yaml --validate-top 3
```

Expected: HTTP status below 400, `selector_matches` greater than zero, and validated details with nonempty titles and bodies.

- [ ] **Step 3: Inspect the policy-explanation column**

Run:

```powershell
.\.venv\Scripts\python.exe main.py inspect --site config/sites/gd_hrss_policy_explain.yaml --validate-top 3
```

Expected: HTTP status below 400, `selector_matches` greater than zero, and validated details with nonempty titles and bodies.

- [ ] **Step 4: Review each inspect result immediately**

After each command, open `reports/inspect_report.json` and verify the URL belongs to the intended `gjzc`, `bszc`, or `zcjd` path. If any selector has zero matches, stop before the production crawl and adjust only that site's selector using the returned HTML evidence.

- [ ] **Step 5: Rerun only the three HRSS sources without cleaning other P0 outputs**

Run:

```powershell
.\.venv\Scripts\python.exe main.py multi --task config/tasks/guangdong_education_talent_p0.yaml --sites gd_hrss_national_policy,gd_hrss_employment,gd_hrss_policy_explain
```

Expected: all three sites complete; the command does not use `--clean-run`; all available enabled site outputs are merged afterward.

- [ ] **Step 6: Verify per-site and merged record invariants**

Run this read-only PowerShell check:

```powershell
@'
import json
from pathlib import Path

run_root = Path('data/runs/guangdong_education_talent_p0')
final_root = Path('data/final/guangdong_education_talent_p0')
expected = {
    'gd_hrss_national_policy': '教育与人才-就业政策-国家政策',
    'gd_hrss_employment': '教育与人才-就业政策-本省政策',
    'gd_hrss_policy_explain': '教育与人才-就业政策-政策解读',
}
for site_id, category in expected.items():
    path = run_root / site_id / '06_final' / 'final.jsonl'
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert rows, f'{site_id}: no records'
    assert all(row.get('contentText', '').strip() for row in rows), f'{site_id}: empty body'
    assert all(row.get('category') == category for row in rows), f'{site_id}: wrong category'
    assert all('/jyzl/zcfg/' in row.get('sourceUrl', '') for row in rows), f'{site_id}: wrong URL'
    print(site_id, len(rows), sum(row.get('attachmentCount', 0) for row in rows))

combined = final_root / 'combined_final.jsonl'
assert combined.exists() and combined.stat().st_size > 0
print('combined_bytes', combined.stat().st_size)
'@ | .\.venv\Scripts\python.exe -
```

Expected: each site prints a positive record count, no assertion fails, and `combined_bytes` is positive.

- [ ] **Step 7: Run the final test suite and capture evidence**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git status --short
git diff --check
```

Expected: full test suite PASS; `git diff --check` prints nothing. Review `git status` and preserve any pre-existing user changes rather than including them in this feature's commit.

- [ ] **Step 8: Commit only intended source changes if generated reports are intentionally versioned**

```powershell
git add reports/inspect_report.json reports/tasks/guangdong_education_talent_p0/multi_summary.json
git commit -m "chore: validate Guangdong HRSS policy crawl"
```

Skip this commit if those generated paths are ignored or the repository convention is to keep crawl outputs uncommitted. Never add `data/**` or log files.
