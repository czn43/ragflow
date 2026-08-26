# 一、最终要做成什么

最终不是十几个零散 Python 脚本，而是一个统一 CLI 工具。

最终期望使用方式：

```bash
python main.py crawl --config config/sites/demo.yaml
```

完成：

```text
发现 URL
→ 抓网页
→ 保存 RAW HTML
→ 初步解析
```

然后：

```bash
python main.py process
```

完成：

```text
URL标准化
→ 去重
→ 正文提取
→ 正文清洗
→ 时间标准化
→ 异常检测
→ 内容去重
→ Metadata
→ Tag
→ Quality Score
```

然后：

```bash
python main.py analyze
```

生成：

```text
质量统计
异常统计
来源统计
长度统计
日期统计
抽样数据
```

最后：

```bash
python main.py export
```

生成：

```text
final.jsonl
quality_report.json
actions.json
removed.jsonl
```

最好进一步支持：

```bash
python main.py all --config config/sites/demo.yaml
```

一键：

```text
crawl
+
process
+
analyze
+
export
```

---

# 二、第一阶段：建立真正可运行的项目骨架

## 2.1 创建项目

- [ ] 创建：

```text
rag-data-toolkit/
```

---

## 2.2 建立目录

- [ ] 创建：

```text
rag-data-toolkit/
│
├── main.py
├── requirements.txt
├── README.md
│
├── config/
│   ├── app.yaml
│   ├── noise_rules.yaml
│   └── sites/
│       └── demo.yaml
│
├── core/
│   ├── models.py
│   ├── constants.py
│   ├── exceptions.py
│   └── context.py
│
├── crawler/
│   ├── http_client.py
│   ├── url_normalizer.py
│   ├── list_crawler.py
│   ├── detail_crawler.py
│   ├── playwright_crawler.py
│   ├── sitemap_crawler.py
│   └── attachment_downloader.py
│
├── extractor/
│   ├── html_extractor.py
│   ├── generic_extractor.py
│   ├── rule_extractor.py
│   ├── metadata_extractor.py
│   ├── attachment_extractor.py
│   ├── pdf_extractor.py
│   ├── docx_extractor.py
│   └── xlsx_extractor.py
│
├── cleaner/
│   ├── pipeline.py
│   ├── text_normalizer.py
│   ├── noise_cleaner.py
│   ├── date_cleaner.py
│   ├── url_deduplicator.py
│   ├── content_deduplicator.py
│   ├── validator.py
│   ├── metadata_builder.py
│   ├── tagger.py
│   └── quality_scorer.py
│
├── analyzer/
│   ├── statistics.py
│   ├── anomaly_statistics.py
│   ├── sampling.py
│   └── report_builder.py
│
├── exporter/
│   ├── jsonl_exporter.py
│   ├── json_exporter.py
│   └── csv_exporter.py
│
├── utils/
│   ├── file_utils.py
│   ├── hash_utils.py
│   ├── text_utils.py
│   └── logger.py
│
├── tests/
│   ├── fixtures/
│   ├── test_cleaner.py
│   ├── test_date.py
│   ├── test_dedup.py
│   └── test_extractor.py
│
├── data/
│   ├── 00_urls/
│   ├── 01_raw/
│   │   ├── html/
│   │   └── json/
│   ├── 02_extracted/
│   ├── 03_dedup/
│   ├── 04_clean/
│   ├── 05_validated/
│   ├── 06_final/
│   ├── attachments/
│   ├── rejected/
│   └── failed/
│
├── reports/
│   ├── samples/
│   └── charts/
│
└── logs/
```

---

# 三、先把数据模型定死

这一步优先级非常高。

不要边写爬虫边发明字段。

## 3.1 新建 `core/models.py`

- [ ] 建立 `RawDocument`。

核心字段：

```python
@dataclass
class RawDocument:
    id: str
    source_url: str
    final_url: str | None
    crawl_time: str

    http_status: int | None

    raw_title: str | None
    raw_html: str | None

    source_name: str | None
    category: str | None
```

---

## 3.2 建立 `Document`

- [ ] 定义最终文档对象：

```python
@dataclass
class Document:
    id: str

    title: str
    content: str

    source_url: str
    source_name: str

    publish_time: str | None
    crawl_time: str

    category: str | None
    tags: list[str]

    region: str | None
    document_type: str | None

    attachments: list[dict]

    char_count: int
    quality_score: int

    status: str
    issues: list[str]
```

---

## 3.3 增加治理字段

最终最好包含：

```json
{
  "cleaning_version": "v1.0",
  "content_hash": "",
  "url_hash": "",
  "issues": [],
  "quality_score": 90
}
```

理由：

以后你调清洗规则，可以知道：

```text
这条数据是哪一个版本清洗出来的。
```

---

# 四、ID 策略实现

## 4.1 创建 `utils/hash_utils.py`

- [ ] 实现：

```python
def sha256_text(value: str) -> str:
```

---

## 4.2 Document ID

采用：

```text
SHA256(normalized_url)
```

实现：

```python
def make_document_id(url: str) -> str:
    normalized = normalize_url(url)
    return sha256_text(normalized)
```

---

## 4.3 Content Hash

- [ ] 实现：

```python
def make_content_hash(content: str) -> str:
```

用于判断：

```text
不同URL
但正文完全一样
```

---

# 五、配置文件设计

这是整个工具能不能在比赛当天快速适配网站的关键。

## 5.1 创建网站配置

例如：

```yaml
site:
  name: 深圳市工业和信息化局
  domain: gxj.sz.gov.cn

crawler:
  start_urls:
    - https://xxx/list.html

  mode: requests

  delay:
    min: 0.5
    max: 1.5

  timeout: 15
  retries: 3

list:
  item_selector: ".news-list li"

  link_selector: "a"

  title_selector: "a"

  date_selector: ".date"

pagination:
  type: next_link
  next_selector: ".next"

detail:
  title:
    selectors:
      - "h1"
      - ".article-title"

  content:
    selectors:
      - ".TRS_Editor"
      - ".article-content"
      - "#content"

  publish_time:
    selectors:
      - ".publish-time"
      - ".date"

  source:
    selectors:
      - ".source"
```

---

## 5.2 网站适配原则

比赛现场首先让 AI Coding 做的应该是：

```text
分析HTML
→
生成/修改 YAML
```

而不是：

```text
重新写crawler.py
```

---

# 六、URL 标准化模块

创建：

```text
crawler/url_normalizer.py
```

## 6.1 实现：

```python
def normalize_url(url: str, base_url: str | None = None) -> str:
```

---

## 6.2 原子规则

- [ ] 相对路径转绝对路径。
- [ ] 删除 `#fragment`。
- [ ] scheme 转小写。
- [ ] host 转小写。
- [ ] 去默认端口。
- [ ] 移除末尾无意义 `/`。
- [ ] 删除常见 tracking 参数：

```text
utm_source
utm_medium
utm_campaign
spm
from
source
```

但：

- [ ] 不得删除明显影响文章 ID 的查询参数。

例如：

```text
?id=1234
```

必须保留。

---

## 6.3 验收

输入：

```text
https://example.com/a?id=123&utm_source=wechat#top
```

输出：

```text
https://example.com/a?id=123
```

---

# 七、统一 HTTP Client

创建：

```text
crawler/http_client.py
```

不要每个 crawler 自己 `requests.get()`。

## 7.1 创建 Session

- [ ] 使用：

```python
requests.Session()
```

---

## 7.2 默认 Header

```python
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 ...",
    "Accept-Language": "zh-CN,zh;q=0.9"
}
```

---

## 7.3 实现

```python
def get(url) -> HttpResult:
```

返回：

```python
@dataclass
class HttpResult:
    url: str
    final_url: str
    status_code: int
    text: str | None
    encoding: str | None
    error: str | None
```

---

## 7.4 Retry

- [ ] 最多 3 次。
- [ ] 只对以下情况重试：

```text
timeout
connection error
429
500
502
503
504
```

---

## 7.5 失败日志

写：

```text
data/failed/http_failed.jsonl
```

每条：

```json
{
  "url": "",
  "status": 503,
  "error": "",
  "retry_count": 3,
  "time": ""
}
```

---

# 八、URL 发现器

创建：

```text
crawler/list_crawler.py
```

## 8.1 原子函数

```python
def parse_list_page(html, config) -> list[UrlItem]:
```

---

## 8.2 UrlItem

```python
@dataclass
class UrlItem:
    url: str
    title: str | None
    publish_time: str | None
    source_page: str
```

---

## 8.3 列表解析

对每个：

```text
item_selector
```

解析：

```text
链接
标题
日期
```

---

## 8.4 翻页

至少支持：

```text
next_link
page_parameter
url_template
```

例如：

```yaml
pagination:
  type: url_template
  template: "index_{page}.html"
  start: 1
  max: 100
```

---

## 8.5 停止条件

必须支持：

- [ ] 找不到下一页。
- [ ] 连续 2 页没有新 URL。
- [ ] 达到 max_pages。
- [ ] 达到 max_documents。
- [ ] 页面返回 404。

防止：

```text
无限爬虫。
```

---

# 九、Sitemap 爬虫备用能力

创建：

```text
crawler/sitemap_crawler.py
```

## 9.1 先尝试：

```text
/sitemap.xml
```

---

## 9.2 支持 sitemap index。

---

## 9.3 输出统一 UrlItem。

这样遇到 sitemap 网站：

```text
甚至不需要解析列表页。
```

---

# 十、Playwright 备用模块

创建：

```text
crawler/playwright_crawler.py
```

只处理：

```text
requests 抓不到正文
+
页面依赖 JS
```

## 10.1 实现

```python
async def render(url: str) -> str:
```

返回最终 HTML。

---

## 10.2 默认策略

优先：

```text
requests
```

失败：

```text
Playwright fallback
```

不要所有页面都 Playwright。

否则：

```text
速度会非常慢。
```

---

# 十一、详情页抓取

创建：

```text
crawler/detail_crawler.py
```

## 11.1 工作流程

```text
UrlItem
↓
HTTP GET
↓
保存HTML
↓
创建RawDocument
↓
保存JSON metadata
```

---

## 11.2 原始 HTML 必须保存

文件：

```text
data/01_raw/html/{id}.html
```

---

## 11.3 原始 Metadata

```text
data/01_raw/json/{id}.json
```

例如：

```json
{
  "id": "...",
  "source_url": "...",
  "final_url": "...",
  "crawl_time": "...",
  "http_status": 200,
  "list_title": "..."
}
```

---

# 十二、正文提取采用“两级策略”

这是必须提前做好的核心模块。

创建：

```text
extractor/html_extractor.py
```

## 12.1 第一优先级：网站规则

```text
RuleExtractor
```

因为比赛找到目标网站后：

```text
针对性 selector
```

通常比通用正文算法更加可靠。

---

## 12.2 第二优先级：Trafilatura

当网站规则不存在或失败：

```text
Trafilatura fallback
```

---

## 12.3 实现统一接口

```python
def extract(html: str, url: str, site_config) -> ExtractResult:
```

---

## 12.4 ExtractResult

```python
@dataclass
class ExtractResult:
    title: str | None
    content: str | None
    publish_time: str | None
    source_name: str | None
    author: str | None
    extraction_method: str
```

---

## 12.5 extraction_method

必须记录：

```text
rule
trafilatura
fallback
failed
```

方便分析：

```text
哪些文章抽取失败。
```

---

# 十三、正文 Selector 容错

不要只写：

```python
soup.select_one(".content")
```

要写：

```python
CONTENT_SELECTORS = [
    ".TRS_Editor",
    ".article-content",
    ".article-detail",
    ".content",
    "#content"
]
```

逐一尝试。

成功条件例如：

```python
len(text) >= 100
```

---

# 十四、正文抽取质量初判

正文抽出来后立刻计算：

```text
char_count
line_count
paragraph_count
```

---

## 14.1 如果：

```text
content为空
```

标记：

```text
EMPTY_CONTENT
```

---

## 14.2 如果：

```text
len(content) < 50
```

标记：

```text
VERY_SHORT_CONTENT
```

---

## 14.3 如果：

```text
50 <= len(content) < 100
```

标记：

```text
SHORT_CONTENT
```

不要立刻全删。

---

# 十五、统一文本标准化

创建：

```text
cleaner/text_normalizer.py
```

## 15.1 实现：

```python
def normalize_text(text: str) -> str:
```

---

## 15.2 顺序固定

### Step 1

HTML entity 解码。

```text
&amp;
&nbsp;
&lt;
```

---

### Step 2

Unicode normalization。

推荐：

```python
unicodedata.normalize("NFKC", text)
```

---

### Step 3

统一换行：

```text
\r\n
\r
```

全部变：

```text
\n
```

---

### Step 4

Tab：

```text
\t → 空格
```

---

### Step 5

连续空格：

```text
"    "
```

缩成：

```text
" "
```

---

### Step 6

连续空行：

```text
最多保留2个换行。
```

---

# 十六、噪声规则改成配置驱动

不要把：

```python
if "上一篇" in text:
```

散落在代码里。

创建：

```text
config/noise_rules.yaml
```

---

## 16.1 示例

```yaml
trailing:
  - name: previous_next
    patterns:
      - "上一篇"
      - "下一篇"

  - name: comment_notice
    patterns:
      - "评论在审核通过后将对所有人可见"

  - name: footer
    patterns:
      - "网站地图"
      - "联系我们"

line_remove:
  - "^分享到"
  - "^责任编辑[:：]"
  - "^打印本页"
  - "^关闭窗口$"
```

---

# 十七、NoiseCleaner 必须返回清洗证据

这是一个非常重要的设计。

不要：

```python
cleaned = clean(text)
```

然后不知道改了什么。

应该：

```python
cleaned, actions = clean(text)
```

---

## 17.1 Action

定义：

```python
@dataclass
class CleaningAction:
    rule: str
    before: str
    after: str
    removed_text: str
```

---

## 17.2 最终每篇数据保存：

```json
{
  "cleaning_actions": [
    {
      "rule": "TRAILING_NOISE",
      "removed_text": "上一篇 下一篇"
    }
  ]
}
```

---

# 十八、尾部噪声要“截断”，不是简单 replace

例如：

```text
真正正文……

责任编辑：张三

上一篇：XXXX
下一篇：XXXX
网站地图
联系我们
```

最佳处理：

发现高置信尾部 marker：

```text
责任编辑
上一篇
网站地图
```

然后：

```text
从marker开始整体截掉。
```

---

## 18.1 实现

```python
def trim_trailing_noise(text, markers):
```

---

## 18.2 安全条件

不要正文任何位置出现：

```text
“上一篇”
```

就直接截断。

建议：

```text
marker出现在正文最后30%区域
```

才允许执行截断。

这能显著降低误杀。

---

# 十九、污染检测与清洗分开

不要只有：

```text
clean()
```

还应该：

```text
detect()
```

---

## 19.1 新建 Issue 类型

```text
TAG_POLLUTION
TRAILING_NOISE
NAVIGATION_NOISE
DATE_PARSE_ERROR
EMPTY_CONTENT
SHORT_CONTENT
IMAGE_NEWS
ENCODING_ERROR
DUPLICATE_URL
DUPLICATE_CONTENT
NEAR_DUPLICATE
```

---

## 19.2 每篇数据：

```json
{
  "issues": [
    "TRAILING_NOISE",
    "TAG_POLLUTION"
  ]
}
```

这样报告可以统计：

```text
TRAILING_NOISE 821篇
TAG_POLLUTION 316篇
```

---

# 二十、日期解析模块单独实现

创建：

```text
cleaner/date_cleaner.py
```

## 20.1 输入

```text
2026-08-26
2026/08/26
2026.08.26
2026年8月26日
发布时间：2026-08-26
2026-8-6
```

---

## 20.2 输出统一：

```text
2026-08-26
```

---

## 20.3 实现：

```python
def parse_date(raw_date: str) -> DateParseResult:
```

---

## 20.4 DateParseResult

```python
@dataclass
class DateParseResult:
    raw: str
    normalized: str | None
    valid: bool
    reason: str | None
```

---

## 20.5 日期校验

例如当前比赛时间是 2026 年：

出现：

```text
2096-08-26
```

标：

```text
FUTURE_DATE
```

出现：

```text
2026-13-44
```

标：

```text
DATE_PARSE_ERROR
```

---

# 二十一、URL 去重必须分两层

创建：

```text
cleaner/url_deduplicator.py
```

## 21.1 第一层

```text
normalized_url 完全一样
```

直接判重复。

---

## 21.2 如果相同 URL 多条记录

保留：

```text
crawl_time 最新
```

---

## 21.3 输出

```text
data/03_dedup/url_duplicates.jsonl
```

不要直接消失。

---

# 二十二、内容完全重复

创建：

```text
cleaner/content_deduplicator.py
```

## 22.1 对 clean content 做 normalization。

例如去掉：

```text
空格
换行差异
```

---

## 22.2 计算：

```text
SHA256(normalized_content)
```

---

## 22.3 同 hash

直接：

```text
DUPLICATE_CONTENT
```

---

## 22.4 保留规则

优先：

```text
authority高
>
发布日期早
>
正文完整
>
质量分高
```

---

# 二十三、近似重复不要对 3000 篇两两比较

错误方式：

```text
3000 × 3000
```

虽然比赛数据量可能还能跑，但没有必要。

---

## 23.1 第一层候选筛选

先按：

```text
title
+
char_count
```

分组。

---

## 23.2 第二层

使用：

```text
RapidFuzz
```

比较候选。

---

## 23.3 阈值建议初始：

```text
>= 97
```

标：

```text
NEAR_DUPLICATE
```

---

## 23.4 不建议比赛前自动删除全部近似重复

先：

```text
标记
+
抽样
```

完全重复才自动删。

---

# 二十四、转载数据的保留策略

为 source 增加：

```text
authority_level
```

例如：

```text
5 政府
4 行业协会/官方机构
4 高校
3 企业官网
2 主流媒体
1 普通网站
0 未知
```

同文多源时：

```text
authority_level 最大者优先。
```

这样你的规则可解释。

---

# 二十五、附件发现实现

创建：

```text
extractor/attachment_extractor.py
```

## 25.1 遍历：

```html
<a href="">
```

---

## 25.2 判断扩展名

支持：

```text
.pdf
.doc
.docx
.xls
.xlsx
.ppt
.pptx
.zip
```

---

## 25.3 保存

```json
{
  "name": "附件1.pdf",
  "url": "...",
  "type": "pdf",
  "local_path": ""
}
```

---

# 二十六、附件下载器

创建：

```text
crawler/attachment_downloader.py
```

下载目录：

```text
data/attachments/{document_id}/
```

---

## 26.1 文件命名不要直接完全相信网页文件名。

建议：

```text
attachment_001.pdf
```

同时 metadata 保存原始名称。

---

## 26.2 文件大小限制

例如：

```text
max_file_size = 100MB
```

超过：

```text
ATTACHMENT_TOO_LARGE
```

---

# 二十七、PDF 解析

创建：

```text
extractor/pdf_extractor.py
```

## 27.1 PyMuPDF

实现：

```python
def extract_pdf(path) -> AttachmentContent:
```

---

## 27.2 统计：

```text
page_count
text_length
```

---

## 27.3 如果：

```text
page_count > 0
但 text_length < 100
```

标：

```text
SCAN_PDF
```

---

## 27.4 扫描 PDF

不要比赛前强行做复杂 OCR。

先设计接口：

```python
def needs_ocr(pdf) -> bool:
```

需要时再启用 OCR。

---

# 二十八、Word 解析

创建：

```text
extractor/docx_extractor.py
```

需要读取：

```text
paragraph
table
```

---

## 28.1 表格转：

```text
字段A | 字段B | 字段C
值1   | 值2   | 值3
```

而不是：

```text
值1值2值3
```

---

# 二十九、Excel 解析

创建：

```text
extractor/xlsx_extractor.py
```

不要把 Excel 当普通长文本。

输出：

```json
{
  "sheet": "Sheet1",
  "headers": [],
  "rows": []
}
```

后面决定如何转换知识文本。

---

# 三十、Metadata Builder

创建：

```text
cleaner/metadata_builder.py
```

## 30.1 Metadata 来源优先级

### source_name

优先：

```text
页面字段
>
网站配置
>
域名映射
```

---

### category

优先：

```text
栏目
>
site config
>
规则推断
```

---

### region

不要 AI 瞎猜。

初始通过：

```text
site config
```

例如：

```yaml
metadata:
  region: 深圳
```

---

## 30.2 输出 Metadata

```json
{
  "source": "",
  "category": "",
  "publish_time": "",
  "region": "",
  "topic": "",
  "document_type": ""
}
```

---

# 三十一、document_type 分类

先规则化：

```text
URL / 栏目 / 标题
```

识别：

```text
policy
news
company
research
report
notice
standard
qa
other
```

例如标题包含：

```text
通知
办法
意见
规划
实施方案
```

可能标：

```text
policy
```

不要一开始做很复杂模型。

---

# 三十二、Tagger

创建：

```text
cleaner/tagger.py
```

推荐：

```text
规则为主
AI为辅
```

---

## 32.1 建立关键词表

```yaml
tags:

  人工智能:
    - 人工智能
    - AI
    - 大模型
    - 机器学习

  机器人:
    - 机器人
    - 人形机器人
    - 具身智能

  融资:
    - 融资
    - 投资
    - 基金
```

---

## 32.2 标签来源

每篇：

```text
title 权重最高
category 第二
content 第三
```

---

## 32.3 控制标签数：

```text
max_tags = 5
```

---

# 三十三、Validator

创建：

```text
cleaner/validator.py
```

这是是否进入 Final Pool 的核心。

## 33.1 必填验证

```text
id
title
content
source_url
```

---

## 33.2 规则

例如：

```python
if not title:
    issues.add("EMPTY_TITLE")

if not content:
    issues.add("EMPTY_CONTENT")

if len(content) < 100:
    issues.add("SHORT_CONTENT")
```

---

## 33.3 验证不等于删除

Validator 输出：

```text
valid
warning
reject
```

---

## 33.4 示例

```text
EMPTY_CONTENT
→ reject

HTTP_ERROR
→ reject

SHORT_CONTENT
→ warning

DATE_PARSE_ERROR
→ warning

SCAN_PDF
→ warning
```

---

# 三十四、Quality Score 独立实现

创建：

```text
cleaner/quality_scorer.py
```

不要把评分逻辑混在 validator。

## 34.1 第一版就用透明规则

```text
title非空            +15
正文非空             +25
正文 >= 300          +15
正文 >= 800          +5
publish_time有效      +10
source明确            +10
URL正常               +10
没有严重污染          +10
```

最高：

```text
100
```

---

## 34.2 严重问题扣分

例如：

```text
TAG_POLLUTION        -5
DATE_PARSE_ERROR     -5
SHORT_CONTENT        -15
ENCODING_ERROR       -30
```

---

## 34.3 不要：

```text
quality_score < 80
全部删掉。
```

初始：

```text
>=80     HIGH
60-79    MEDIUM
<60      LOW
```

---

# 三十五、整个清洗 Pipeline 固定执行顺序

创建：

```text
cleaner/pipeline.py
```

建议顺序：

```text
RawDocument
    ↓
URL Normalize
    ↓
URL Deduplicate
    ↓
HTML Extract
    ↓
Text Normalize
    ↓
Noise Clean
    ↓
Date Normalize
    ↓
Content Hash
    ↓
Content Deduplicate
    ↓
Validator
    ↓
Metadata Builder
    ↓
Tagger
    ↓
Quality Score
    ↓
Final Document
```

这个顺序不要随便改。

---

# 三十六、Pipeline 每一步必须统计

建立：

```python
PipelineStats
```

例如：

```json
{
  "raw": 3500,
  "url_duplicate": 150,
  "extract_failed": 25,
  "empty_content": 12,
  "content_duplicate": 185,
  "final": 3128
}
```

---

# 三十七、任何“删除”都必须进入 rejected

文件：

```text
data/rejected/rejected.jsonl
```

每条：

```json
{
  "id": "",
  "title": "",
  "url": "",
  "reason": [
    "EMPTY_CONTENT"
  ]
}
```

必须做到：

> **数据为什么少了，可以追溯。**

---

# 三十八、清洗前后保存 Sample

每个污染类型自动保存最多：

```text
20条
```

到：

```text
reports/samples/
```

例如：

```text
reports/samples/TRAILING_NOISE.json
reports/samples/TAG_POLLUTION.json
reports/samples/SHORT_CONTENT.json
```

每个样本：

```json
{
  "id": "",
  "before": "",
  "after": "",
  "rule": ""
}
```

---

# 三十九、数据统计模块

创建：

```text
analyzer/statistics.py
```

## 39.1 计算：

```text
raw_count
final_count
reject_count
duplicate_count
```

---

## 39.2 字段完整率

```text
title completeness
content completeness
publish_time completeness
source completeness
```

---

# 四十、正文长度统计

计算：

```text
min
max
mean
median
P50
P90
P95
```

---

## 40.1 分桶

```text
0-99
100-499
500-999
1000-1999
2000-4999
5000+
```

---

# 四十一、来源分布

输出：

```json
[
  {
    "source": "深圳市工信局",
    "count": 621,
    "ratio": 0.21
  }
]
```

---

## 41.1 额外计算：

```text
top1_source_ratio
top3_source_ratio
```

用于判断：

```text
数据是否严重集中在一个网站。
```

---

# 四十二、Category 分布

输出：

```text
政策：500
企业：700
科研：300
新闻：1200
融资：200
```

这样可以快速发现：

```text
某一类覆盖不足。
```

---

# 四十三、日期统计

至少：

```text
year
month
missing
invalid
```

输出：

```text
2024  500
2025  1200
2026  1000
```

---

# 四十四、污染统计

根据：

```text
issues
```

统计：

```text
TRAILING_NOISE  821
TAG_POLLUTION   321
DATE_PARSE_ERROR 32
SHORT_CONTENT   121
```

这是答辩很有价值的数据。

---

# 四十五、自动异常抽样

创建：

```text
analyzer/sampling.py
```

实现：

```python
def sample_by_issue(documents, issue, n=20)
```

---

## 45.1 抽样需要随机种子

```python
random.seed(42)
```

这样每次报告一致。

---

# 四十六、REPORT 自动生成

创建：

```text
analyzer/report_builder.py
```

必须生成：

```text
reports/quality_report.json
```

结构：

```json
{
  "summary": {},
  "completeness": {},
  "length_distribution": {},
  "source_distribution": {},
  "category_distribution": {},
  "date_distribution": {},
  "issues": {}
}
```

---

# 四十七、最好提前把 HTML 报告做好

生成：

```text
reports/quality_report.html
```

页面不用漂亮。

只需要：

```text
数据总览

原始：
3500

最终：
3128

删除：
372
```

以及：

```text
字段完整率
来源分布
长度分布
异常统计
清洗样例
```

比赛现场这个东西非常适合截图。

---

# 四十八、ACTION Report

创建：

```text
reports/actions.json
```

不是每篇文章一条。

而是对规则汇总：

```json
[
  {
    "rule": "URL_DUPLICATE",
    "description": "标准化URL后去重",
    "affected_count": 150
  },
  {
    "rule": "TRAILING_NOISE",
    "description": "移除网页正文后的功能性尾部文本",
    "affected_count": 821
  }
]
```

---

# 四十九、Final JSONL 输出

输出：

```text
data/06_final/final.jsonl
```

每一行：

```json
{
  "id": "xxx",
  "title": "深圳市人工智能产业发展行动计划",
  "content": "……",
  "source_url": "https://...",
  "source_name": "深圳市工业和信息化局",
  "publish_time": "2026-08-01",
  "category": "产业政策",
  "region": "深圳",
  "document_type": "policy",
  "tags": [
    "人工智能",
    "产业政策"
  ],
  "attachments": [],
  "char_count": 2356,
  "quality_score": 95
}
```

---

# 五十、同时输出 CSV

用于：

```text
Excel人工检查
```

创建：

```text
data/06_final/final_preview.csv
```

字段：

```text
id
title
publish_time
source
category
char_count
quality_score
url
```

不要把完整正文塞 CSV。

---

# 五十一、最终 CLI

`main.py` 至少提供：

```bash
python main.py crawl
```

```bash
python main.py process
```

```bash
python main.py analyze
```

```bash
python main.py export
```

```bash
python main.py all
```

---

# 五十二、比赛最实用的参数

例如：

```bash
python main.py all \
  --site config/sites/shenzhen_ai.yaml \
  --max-pages 50 \
  --max-docs 3000
```

---

# 五十三、日志必须提前做好

日志：

```text
logs/app.log
```

格式：

```text
2026-08-26 10:00:01 INFO crawl url=xxx status=200
2026-08-26 10:00:02 INFO extracted id=xxx chars=2356
2026-08-26 10:00:02 INFO cleaned id=xxx rules=TRAILING_NOISE
```

不要比赛现场靠：

```python
print()
```

排错。

---

# 五十四、控制台进度

使用：

```text
tqdm
```

显示：

```text
抓取文章：1721 / 3000

成功：1699
失败：22
```

---

# 五十五、Checkpoint

非常建议提前实现。

每抓完一篇就把状态写入：

```text
data/checkpoint.json
```

或者通过已存在 raw 文件判断。

这样比赛现场程序中断：

```text
重新执行
```

不会重新爬 2000 篇。

---

# 五十六、支持 Resume

命令：

```bash
python main.py crawl --resume
```

跳过：

```text
已经成功保存的数据。
```

---

# 五十七、批量处理不要一次全部放内存

JSONL：

```text
一行一篇文章。
```

Pipeline 尽量：

```text
逐条处理
```

而不是：

```python
documents = load_all_30000()
```

虽然比赛规模未必很大，但这样设计更稳。

---

# 五十八、必须准备自动化测试样本

建立：

```text
tests/fixtures/
```

至少准备：

```text
normal_article.html
trailing_noise.html
empty_content.html
weird_date.html
duplicate_article.html
attachment_article.html
```

---

# 五十九、日期测试

`test_date.py`

必须验证：

```text
2026年8月26日
2026/08/26
2026.08.26
2026-8-6
```

最终都正确。

---

# 六十、噪声测试

输入：

```text
这是文章正文。

责任编辑：张三
上一篇：文章A
下一篇：文章B
网站地图
```

期望：

```text
这是文章正文。
```

---

# 六十一、误删测试

正文：

```text
“上一篇报告中指出，人工智能产业规模持续增长。”
```

不能因为出现：

```text
上一篇
```

把正文截断。

这个单测很重要。

---

# 六十二、重复测试

以下 URL：

```text
https://a.com/article?id=1&utm_source=x
https://a.com/article?id=1&utm_source=y
```

必须判同 URL。

---

# 六十三、最小验收数据集

比赛前自己找一个公开网站。

至少：

```text
抓 100 篇。
```

全流程必须跑通：

```text
URL
↓
RAW
↓
EXTRACT
↓
CLEAN
↓
DEDUP
↓
VALIDATE
↓
FINAL
↓
REPORT
```

---

# 六十四、比赛当天最关键的 AI Coding 工作流

你拿到网站后第一步：

把：

```text
列表页HTML
+
详情页HTML
```

给 AI。

让它：

```text
只分析DOM结构。

输出：

item_selector
link_selector
date_selector
next_selector
title_selector
content_selector
publish_time_selector
source_selector
```

---

# 六十五、AI 不允许直接破坏公共框架

当天优先修改：

```text
config/sites/xxx.yaml
```

必要时新增：

```text
site_adapter.py
```

尽量不要改：

```text
pipeline.py
validator.py
quality_scorer.py
report_builder.py
```

这样才能保证你提前准备的框架不会现场被 AI 改坏。

---

# 六十六、针对新网站的标准适配流程

固定执行：

```text
1. 人工浏览网站

2. 找列表页

3. 找详情页

4. 给AI分析HTML

5. 生成site yaml

6. 先抓5篇

7. 人工检查

8. 抓50篇

9. 跑清洗

10. 看异常

11. 修selector

12. 再开始大批量
```

---

# 六十七、不要一开始爬3000篇

必须：

```text
5
↓
50
↓
300
↓
3000
```

逐级扩大。

否则 selector 错一次：

```text
3000篇垃圾。
```

---

# 六十八、最终应该留下的“比赛证据链”

最终目录里必须能找到：

```text
01 原始URL
02 原始HTML
03 原始JSON
04 清洗数据
05 异常数据
06 被删除数据
07 最终JSONL
08 质量报告
09 清洗规则
10 清洗动作统计
```

答辩时你就可以说：

> 所有数据处理过程可追溯，并不是直接把网页内容抓下来后丢进知识库。

---

# 六十九、项目完成验收标准

只有以下全部满足，才算这套“备赛工具”真正做完。

## 采集

- [ ] 能解析普通列表页。
- [ ] 能自动分页。
- [ ] 能抓详情页。
- [ ] 能自动重试。
- [ ] 能恢复执行。
- [ ] 能限制最大页数。
- [ ] 能限制最大文章数。
- [ ] 能保存原始 HTML。
- [ ] JS 页面有 Playwright fallback。

## 提取

- [ ] 能提取 title。
- [ ] 能提取 content。
- [ ] 能提取 date。
- [ ] 能提取 source。
- [ ] 支持 selector 优先。
- [ ] 支持 Trafilatura fallback。

## 清洗

- [ ] Unicode 标准化。
- [ ] HTML entity 清洗。
- [ ] 空格标准化。
- [ ] 换行标准化。
- [ ] 常见尾部噪声清洗。
- [ ] 清洗动作可追踪。

## 去重

- [ ] URL 去重。
- [ ] Content Hash 去重。
- [ ] 近似重复检测。

## 附件

- [ ] PDF 发现。
- [ ] Word 发现。
- [ ] Excel 发现。
- [ ] 附件与原文关联。
- [ ] PDF 文本可以提取。

## Metadata

- [ ] source。
- [ ] category。
- [ ] region。
- [ ] document_type。
- [ ] tags。

## 质量

- [ ] issue 检测。
- [ ] validator。
- [ ] quality score。
- [ ] rejected 数据可追踪。

## 分析

- [ ] 总数量。
- [ ] 去重数量。
- [ ] 删除数量。
- [ ] 字段完整率。
- [ ] 长度 P50/P90/P95。
- [ ] 来源分布。
- [ ] 类别分布。
- [ ] 日期分布。
- [ ] 污染类型统计。
- [ ] 异常抽样。

## 输出

- [ ] final.jsonl。
- [ ] preview.csv。
- [ ] quality_report.json。
- [ ] quality_report.html。
- [ ] actions.json。
- [ ] rejected.jsonl。

---

# 七十、真正最优先开发的 P0

如果时间有限，严格按这个顺序实现。

## P0-1

```text
统一Document数据模型
```

## P0-2

```text
HTTP Client
```

## P0-3

```text
列表页 + 分页
```

## P0-4

```text
详情页保存RAW HTML
```

## P0-5

```text
Selector正文抽取
+
Trafilatura fallback
```

## P0-6

```text
URL Normalize + 去重
```

## P0-7

```text
正文 Normalize
```

## P0-8

```text
尾部噪声清理
```

## P0-9

```text
日期标准化
```

## P0-10

```text
Content Hash去重
```

## P0-11

```text
Validator
```

## P0-12

```text
Metadata
```

## P0-13

```text
Quality Score
```

## P0-14

```text
Statistics
```

## P0-15

```text
final.jsonl
```

## P0-16

```text
quality_report.json
```

---

# 七十一、P1 能力

P0 跑通以后再实现：

```text
Playwright
附件下载
PDF解析
Word解析
Excel解析
近似重复
标签自动生成
HTML质量报告
异常自动抽样
```

---

# 七十二、P2 能力

还有时间才做：

```text
AI自动判断标签
AI自动识别document_type
OCR
复杂表格恢复
自动寻找更多网站
自动判断网页模板
多进程/异步高速爬虫
可视化管理界面
```

这些不是当前备赛第一优先级。

---

# 七十三、最终一句话架构

最终工具应该严格保持：

```text
                    Site YAML
                       │
                       ▼
Internet ──► URL Discovery
                       │
                       ▼
                  HTTP Client
                       │
                       ▼
                  RAW Archive
                       │
                       ▼
            Rule Extractor
                 │
                 ├────失败────► Trafilatura
                 │
                 ▼
             Normalization
                 │
                 ▼
              Cleaning
                 │
                 ▼
              Dedup
                 │
                 ▼
             Validation
                 │
                 ▼
              Metadata
                 │
                 ▼
                Tags
                 │
                 ▼
            Quality Score
                 │
          ┌──────┴──────┐
          ▼             ▼
       Reject          Final
                         │
                         ▼
                     Analyzer
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
           DATA        REPORT       ACTION
```

# 七十四、这套工具最核心的设计思想

**第一：RAW 永远不覆盖。**

原始数据始终能找回来。

**第二：所有删除都有理由。**

不是：

```text
3500 → 2800
```

而是：

```text
3500
- URL重复 150
- 正文重复 185
- 空正文 12
- 抓取失败 25
- 低质量 128

最终 3000
```

**第三：所有清洗都有证据。**

比如：

```text
TRAILING_NOISE
命中821篇
```

可以随机打开 20 篇：

```text
清洗前
VS
清洗后
```

**第四：网站差异配置化。**

换考试题时主要改：

```text
site.yaml
```

而不是重写系统。

**第五：最终目标不是“数据看起来干净”。**

而是：

> **得到一批结构统一、来源明确、内容完整、污染可控、质量可量化、能够直接送入 RAGFlow 的知识库数据。**