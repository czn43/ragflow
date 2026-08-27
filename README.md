# RAG Data Toolkit v1.6

面向 **RAG 知识库比赛 / 数据治理比赛** 的网页数据采集、正文抽取、清洗、去重、质量校验与标准 JSON 输出工具。

v1.6 的核心目标不是“从零开发 RAG”，而是把互联网网页数据加工成一批：

> **来源明确、正文完整、格式统一、过程可追溯、可以继续批量上传到 RAGFlow 的标准知识库数据。**

当前版本已经针对 **深圳广播电影电视集团第一现场（SZTV）** 做过实战适配，能够处理：

- 普通 HTML 列表页
- JavaScript 点击分页
- 列表项本身就是 `<a href>` 的页面结构
- 普通 `requests` 获取不到正文时，自动使用系统 Chrome + Playwright 渲染详情页
- 精确正文 Selector 抽取
- 评论、相关推荐、版权声明等页面噪声隔离 / 清洗
- URL 去重、正文完全重复去重
- 日期标准化
- 数据质量校验
- 固定 8 字段标准 JSON 输出
- 每个处理阶段留档，方便比赛过程展示和问题追踪

---

## 1. 项目定位

本项目解决的不是“聊天机器人怎么回答”，而是 RAG 上游最重要的数据工程问题：

```text
互联网网页
    ↓
发现文章 URL
    ↓
抓取详情页
    ↓
保留原始 HTML
    ↓
抽取标题 / 正文 / 来源 / 日期
    ↓
标准化 JSON
    ↓
URL 去重
    ↓
正文清洗
    ↓
质量校验
    ↓
正文完全重复去重
    ↓
最终标准数据
    ↓
RAGFlow / 其他知识库平台
```

比赛时最常见的工作不是修改核心 Python，而是：

```text
找到目标网站
→ 分析 DOM
→ 新建 / 修改站点 YAML
→ inspect 验证
→ 小批量抓取
→ 检查 RAW / CLEAN / FINAL
→ 再扩大数据量
```

---

# 2. 当前版本信息

```text
版本：v1.6.0
Python：推荐 3.11 / 3.12
系统：Windows 优先，也可在其他系统运行 Python 主程序
浏览器：优先使用电脑现有 Google Chrome
```

查看版本：

```powershell
.\.venv\Scripts\python.exe main.py --version
```

预期：

```text
1.6.0
```

当前自动测试：

```text
18 passed
```

---

# 3. 标准 JSON 数据契约

v1.6 对比赛侧 / 上传侧数据统一使用 **固定 8 字段**。

```json
{
  "sourceName": "深视新闻",
  "sourceUrl": "https://www.sztv.com.cn/ysz/zx/zw/83852598.shtml",
  "title": "白手起家的深圳年轻人，忙着改写全球富豪榜",
  "contentText": "这里是真正的文章正文……",
  "category": "新闻资讯-新闻资讯",
  "publishTime": "2026-08-25",
  "attachments": [],
  "attachmentCount": 0
}
```

字段说明：

| 字段 | 含义 | 示例 |
| --- | --- | --- |
| `sourceName` | 数据来源 / 发布来源 | `深视新闻` |
| `sourceUrl` | 原始文章 URL | `https://.../83852598.shtml` |
| `title` | 文章标题 | `白手起家的深圳年轻人...` |
| `contentText` | 纯正文文本 | `最近，胡润集团...` |
| `category` | 当前数据分类 | `新闻资讯-新闻资讯` |
| `publishTime` | 标准化发布日期 | `2026-08-25` |
| `attachments` | 附件数组 | `[]` |
| `attachmentCount` | 附件数量 | `0` |

## 3.1 为什么用户侧只保留 8 字段

以下技术信息不会混入最终上传 JSON：

```text
id
quality score
issues
content hash
url hash
cleaning actions
render fallback used
http status
crawl time
```

这些字段仍然会保留，但放到：

```text
data/_internal/
reports/
data/01_raw/meta/
```

这样可以同时满足：

1. 上传数据结构干净；
2. 内部处理过程仍然可追溯。

> 注意：当前 v1.6 的 `attachments` 字段已经保留在标准契约中，但“网页附件自动下载 / PDF、Word、Excel 深度解析”尚未正式接入本版本主流程，所以大多数网页数据仍为 `[]`。

---

# 4. 项目架构

```text
rag-data-toolkit-v1.6-standard-json/
│
├── main.py                         # CLI 总入口
├── requirements.txt                # Python 依赖
├── setup_windows.bat               # Windows 一键初始化
├── run_100.bat                     # 通用站点抓 100 篇
├── run_sztv_100.bat                # SZTV 实战抓 100 篇
├── run_inspect.bat                 # 页面结构诊断
├── run_tests.bat                   # 自动测试
├── browser_check.py                # 系统 Chrome 检测
│
├── config/
│   ├── app.yaml                    # 全局默认参数
│   ├── noise_rules.yaml            # 通用正文噪声规则
│   └── sites/
│       ├── demo.yaml               # 比赛当天复制的通用模板
│       ├── sztv.yaml               # SZTV 精确站点配置
│       └── sztv_auto.yaml          # SZTV 自动发现示例
│
├── crawler/
│   ├── http_client.py              # requests Session / 超时 / 重试
│   ├── url_normalizer.py           # URL 标准化
│   ├── article_discovery.py        # Selector 失败后的候选文章链接发现
│   ├── list_crawler.py             # 普通列表页 + 普通分页
│   ├── playwright_list_crawler.py  # JS 动态列表 / 点击分页
│   ├── detail_crawler.py           # 详情页抓取 + RAW 留档
│   └── detail_renderer.py          # requests 正文不足时 Chrome 渲染兜底
│
├── extractor/
│   └── html_extractor.py           # Selector 优先 + Trafilatura fallback
│
├── cleaner/
│   ├── pipeline.py                 # 数据处理总流水线
│   ├── text_normalizer.py          # Unicode / 空白 / 换行标准化
│   ├── noise_cleaner.py            # 页面噪声清理
│   ├── date_cleaner.py             # 日期标准化
│   ├── url_deduplicator.py         # URL 去重工具
│   ├── content_deduplicator.py     # 正文 hash 工具
│   ├── validator.py                # 空正文 / 短正文等校验
│   ├── quality_scorer.py           # 质量评分模块（内部能力）
│   ├── metadata_builder.py         # Metadata 扩展模块
│   └── tagger.py                   # 标签扩展模块
│
├── core/
│   ├── models.py                   # 内部数据对象
│   ├── schema.py                   # 固定 8 字段标准契约
│   └── constants.py
│
├── analyzer/
│   ├── statistics.py               # 完整率 / 长度 / 来源等统计
│   └── report_builder.py           # quality_report.json
│
├── exporter/
│   ├── jsonl_exporter.py           # final.jsonl + 单篇 JSON
│   └── csv_exporter.py             # final_preview.csv
│
├── utils/
│   ├── browser_utils.py            # 优先系统 Chrome
│   ├── file_utils.py
│   ├── hash_utils.py
│   ├── logger.py
│   └── run_utils.py                # clean-run 清理本轮产物
│
├── data/                            # 各阶段数据
├── reports/                         # 统计与诊断报告
├── logs/                            # 运行日志
└── tests/                           # 自动测试
```

---

# 5. 数据处理阶段

v1.6 特别强调 **阶段留档**。

```text
00_urls
   ↓
01_raw
   ↓
02_extracted
   ↓
03_dedup
   ↓
04_clean
   ↓
05_validated
   ↓
06_final
```

## 5.1 `data/00_urls/`

列表页发现的文章 URL：

```text
data/00_urls/urls.jsonl
```

用于检查：

- 到底发现了多少条链接；
- 有没有混入栏目页、图片、外链；
- 分页是否真的翻到了第二页、第三页。

---

## 5.2 `data/01_raw/`

### 原始 HTML

```text
data/01_raw/html/*.html
```

这是抓取到的网页 HTML 证据，尽量保留原貌。

### 可读 RAW JSON

```text
data/01_raw/json/*.json
data/01_raw/raw.jsonl
```

这里已经从 HTML 中抽取出正文，但**还没有进入正式清洗阶段**。

也就是说：

```text
RAW HTML = 网页原始证据
RAW JSON = 从网页提取出来、但未清洗的可读正文
```

比赛检查正文是否“抓对了”，首先看这里的 `contentText`。

### 抓取元信息

```text
data/01_raw/meta/*.json
```

这里记录：

- HTTP 状态；
- 抓取时间；
- 原始列表时间；
- 正文提取方式；
- 是否使用 Chrome 渲染兜底；
- RAW 正文字数；
- HTML / JSON 路径。

---

## 5.3 `data/02_extracted/`

```text
data/02_extracted/extracted.jsonl
```

抽取阶段标准数据，仍保持 8 字段契约。

这一层的目的主要是建立明确的“抽取完成”阶段边界。

---

## 5.4 `data/03_dedup/`

```text
data/03_dedup/dedup.jsonl
```

此阶段先进行 **标准化 URL 去重**。

典型情况：

```text
https://xxx/article?id=123&utm_source=wechat
https://xxx/article?id=123&utm_source=app
```

标准化后可能被视为同一地址。

---

## 5.5 `data/04_clean/`

```text
data/04_clean/cleaned.jsonl
```

这是最重要的“清洗后”数据。

目前主要执行：

- 标题空白标准化；
- 正文 Unicode 标准化；
- HTML entity / 空白 / 换行整理；
- 配置化行噪声移除；
- 高置信尾部噪声截断；
- 日期标准化为 `YYYY-MM-DD`；
- URL 再标准化；
- 保持固定 8 字段输出。

---

## 5.6 `data/05_validated/`

```text
data/05_validated/validated.jsonl
```

通过 Validator 后的数据，并在这个阶段之后执行正文完全重复去重。

当前重点检查：

- 标题是否存在；
- 正文是否为空；
- 正文是否过短；
- URL 是否有效；
- 清洗后正文是否完全重复。

---

## 5.7 `data/06_final/`

真正用于后续知识库入库的数据。

### 总文件

```text
data/06_final/final.jsonl
```

### 人工快速检查

```text
data/06_final/final_preview.csv
```

CSV 不放完整正文，重点查看：

- 来源；
- URL；
- 标题；
- 分类；
- 日期；
- 附件数量；
- 正文字数。

### 一篇一个 JSON

```text
data/06_final/json/*.json
```

例如：

```text
0001_白手起家的深圳年轻人_忙着改写全球富豪榜.json
0002_深圳经济特区_46岁生日快乐.json
```

这一目录非常适合后续：

```text
文件批量上传
+ Metadata 绑定
+ RAGFlow 入库
```

---

# 6. 内部审计与报告

## 6.1 单条数据审计

```text
data/_internal/record_audit.jsonl
```

记录：

```text
id
sourceUrl
title
beforeChars
afterChars
status
issues
cleaningActions
contentHash
urlHash
```

当发现：

> “为什么这篇文章最后没进 final？”

应该优先查这里和 `rejected.jsonl`。

---

## 6.2 被拒绝的数据

```text
data/rejected/rejected.jsonl
```

包含：

- URL 重复；
- 正文重复；
- 空正文；
- 校验拒绝等。

用于说明“数据为什么减少”。

---

## 6.3 Pipeline 数量统计

```text
reports/pipeline_stats.json
```

例如：

```json
{
  "raw": 100,
  "url_duplicate": 2,
  "extracted": 100,
  "cleaned": 98,
  "empty_content": 1,
  "short_content": 3,
  "content_duplicate": 4,
  "rejected": 7,
  "warnings": 2,
  "validated": 93,
  "final": 93
}
```

比赛答辩时，这份数据可以直接用于说明处理链路。

---

## 6.4 清洗动作统计

```text
reports/actions.json
```

例如：

```json
[
  {
    "rule": "TRAILING_NOISE",
    "affectedCount": 82
  }
]
```

---

## 6.5 质量报告

```text
reports/quality_report.json
```

当前包括：

- 最终数据数量；
- 字段完整率；
- 正文长度 min / max / mean；
- P50 / P90 / P95；
- 正文长度分桶；
- 来源分布；
- 分类分布；
- 年份分布；
- 缺失 / 无效日期数量；
- Issue 分布。

---

## 6.6 URL 发现诊断

```text
reports/discovery_diagnostics.json
reports/inspect_report.json
reports/crawl_summary.json
```

当出现：

```text
discovered urls=0
```

不要直接改 Python，先看这三份文件。

---

# 7. 当前已经实现的功能

## 7.1 数据发现

- CSS Selector 精确抓文章列表；
- Selector 匹配 0 条时自动扫描 `<a href>`；
- 同域链接过滤；
- 疑似文章 URL 打分；
- `.html / .shtml / article / news / 长数字 ID` 等模式识别；
- 自动判断 start URL 更像列表页还是详情页；
- 支持直接详情页模式。

## 7.2 普通网页分页

支持：

```text
next_link
url_template
page_parameter
none
```

## 7.3 JavaScript 动态分页

支持：

```text
playwright_click
```

用于类似 SZTV：

```html
<button onclick="window.v3Index.goToPage(2)">2</button>
```

Playwright 会：

```text
打开页面
→ 等待列表
→ 读取当前页
→ 点击下一页
→ 等待第一条文章 URL 改变
→ 再读取下一页
```

避免只使用固定 `sleep()` 导致分页不稳定。

## 7.4 详情页正文抽取

优先：

```text
YAML 中配置的精确 CSS Selector
```

失败后：

```text
Trafilatura 通用正文抽取
```

对于 SZTV 这类 JS 详情页：

```text
requests
↓
精确正文不足
↓
系统 Chrome + Playwright
↓
再次按精确 Selector 抽取
```

## 7.5 浏览器策略

优先查找电脑已有 Chrome：

```text
C:\Program Files\Google\Chrome\Application\chrome.exe
C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe
```

找到后直接使用。

只有找不到系统 Chrome 时，安装脚本才询问：

```text
Install Playwright Chromium now? [Y/N]
```

避免比赛现场无意义下载约 200 MB 浏览器。

## 7.6 清洗和治理

- URL 标准化；
- URL 去重；
- Unicode 文本标准化；
- 空白 / 换行整理；
- 页面噪声规则清理；
- 尾部噪声截断；
- 日期标准化；
- 空正文检查；
- 短正文检查；
- 正文 SHA256 完全重复去重；
- 被拒数据留档；
- 单条审计信息留档；
- Pipeline 数量统计；
- 质量报告。

---

# 8. 当前未正式实现 / 不要误以为已经完成的功能

v1.6 当前主链路 **尚未完整实现**：

- PDF / Word / Excel 附件自动下载与正文解析；
- 扫描 PDF OCR；
- 近似重复 / 转载相似度去重；
- AI 自动分类；
- AI 自动打标签；
- HTML 可视化质量报告；
- RAGFlow API 自动上传；
- RAGFlow Metadata 自动绑定；
- Chunk / Embedding / Recall 自动调优。

配置文件中存在一些 Metadata / Tag 扩展项，是为后续能力预留；当前比赛侧标准 JSON 仍严格只输出固定 8 字段。

---

# 9. Windows 首次安装

进入项目目录：

```powershell
cd D:\你的目录\rag-data-toolkit-v1.6-standard-json
```

运行：

```powershell
.\setup_windows.bat
```

脚本会完成：

```text
检查 Python
↓
创建 .venv
↓
升级 pip
↓
安装 requirements.txt
↓
检测系统 Chrome
↓
如果没有 Chrome，再询问是否安装 Playwright Chromium
↓
运行 pytest
```

正常结束：

```text
Setup completed. All tests passed.
```

## 9.1 手动运行测试

```powershell
.\run_tests.bat
```

或：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

---

# 10. SZTV 实战快速开始

SZTV 已经有完整配置：

```text
config/sites/sztv.yaml
```

直接抓 100 篇：

```powershell
.\run_sztv_100.bat
```

等价命令：

```powershell
.\.venv\Scripts\python.exe main.py all `
  --site config\sites\sztv.yaml `
  --max-pages 20 `
  --max-docs 100 `
  --clean-run
```

运行完成后先检查：

```text
data\01_raw\raw.jsonl
data\04_clean\cleaned.jsonl
data\06_final\final.jsonl
reports\pipeline_stats.json
reports\quality_report.json
```

---

# 11. CLI 使用方式

总入口：

```powershell
.\.venv\Scripts\python.exe main.py <command> [参数]
```

## 11.1 `inspect` —— 比赛当天第一优先命令

```powershell
.\.venv\Scripts\python.exe main.py inspect `
  --site config\sites\demo.yaml `
  --url "https://目标网站/栏目页"
```

作用：

- 检查 HTTP 是否成功；
- 检查配置 Selector 命中数；
- 判断是否更像详情页；
- Selector 失败时列出候选文章链接；
- Playwright 模式显示浏览器来源；
- 检查下一页按钮是否命中。

报告：

```text
reports/inspect_report.json
```

---

## 11.2 `crawl` —— 只抓数据

```powershell
.\.venv\Scripts\python.exe main.py crawl `
  --site config\sites\xxx.yaml `
  --max-pages 5 `
  --max-docs 100 `
  --clean-run
```

只执行：

```text
URL发现
+ 详情页抓取
+ RAW HTML
+ RAW JSON
```

不会继续清洗。

---

## 11.3 `process` —— 只处理现有 RAW

```powershell
.\.venv\Scripts\python.exe main.py process `
  --site config\sites\xxx.yaml
```

执行：

```text
02_extracted
→ URL 去重
→ 04_clean
→ Validator
→ 正文完全重复去重
→ 05_validated
```

适合比赛时：

> 已经抓完数据，只修改了清洗规则，不想重新请求网站。

---

## 11.4 `analyze` —— 重新生成质量报告

```powershell
.\.venv\Scripts\python.exe main.py analyze `
  --site config\sites\xxx.yaml
```

输出：

```text
reports/quality_report.json
```

---

## 11.5 `export` —— 重新导出 final

```powershell
.\.venv\Scripts\python.exe main.py export `
  --site config\sites\xxx.yaml
```

生成：

```text
data/06_final/final.jsonl
data/06_final/final_preview.csv
data/06_final/json/*.json
```

---

## 11.6 `all` —— 一键完整流程

```powershell
.\.venv\Scripts\python.exe main.py all `
  --site config\sites\xxx.yaml `
  --max-pages 20 `
  --max-docs 100 `
  --clean-run
```

相当于：

```text
crawl
→ process
→ analyze
→ export
```

---

# 12. `--clean-run` 是什么

```text
--clean-run
```

表示运行前删除上一轮：

- URL；
- RAW；
- extracted；
- dedup；
- clean；
- validated；
- final；
- rejected；
- internal audit；
- 本轮 reports。

**单网站重新测试时强烈建议开启。**

否则上一次网站的数据可能混入本次 Pipeline。

---

# 13. 比赛当天：怎么新建一个网站配置

不要直接大改 Python。

推荐：

```text
config/sites/demo.yaml
↓ 复制
config/sites/competition_xxx.yaml
```

例如：

```powershell
Copy-Item config\sites\demo.yaml config\sites\competition_xxx.yaml
```

然后主要修改 YAML。

---

# 14. 比赛当天最重要的 YAML 字段

一个站点配置大致分成：

```yaml
site:
crawler:
list:
pagination:
discovery:
detail:
metadata:
```

---

## 14.1 `site`

```yaml
site:
  name: 深圳市工业和信息化局
  domain: gxj.sz.gov.cn
```

比赛当天必须根据真实站点修改。

`domain` 建议写主域，不要继续保留 `example.gov.cn`。

---

## 14.2 `crawler.start_mode`

```yaml
crawler:
  start_mode: auto
```

支持：

### `auto`

自动判断 start URL 是列表页还是文章详情页。

比赛默认推荐。

### `list`

明确告诉程序这是列表页。

例如 SZTV：首页一定作为新闻列表入口。

### `detail`

明确告诉程序 start URL 就是一篇文章。

适合快速验证详情页正文 Selector。

---

## 14.3 `crawler.start_urls`

```yaml
crawler:
  start_urls:
    - https://xxx.gov.cn/xxgk/zcwj/
```

这里必须放：

> 真正需要采集的栏目页 / 数据入口页。

不要随便把一个详情页放进去，然后期待程序自动翻栏目。

---

# 15. 列表页 Selector 怎么修改

假设页面：

```html
<ul class="news-list">
  <li>
    <a href="/article/123.html">政策标题</a>
    <span class="date">2026-08-27</span>
  </li>
</ul>
```

YAML：

```yaml
list:
  item_selector: ".news-list li"
  link_selector: "a"
  title_selector: "a"
  date_selector: ".date"
```

---

## 15.1 如果 item 自己就是 `<a>`

SZTV：

```html
<a class="news-card" href="https://.../83852819.shtml">
  <div class="news-card-title">标题</div>
</a>
```

应该写：

```yaml
list:
  item_selector: "#newsGrid > a.news-card"
  link_selector: "@self"
  title_selector: ".news-card-title"
```

`@self` 表示：

> `href` 就取当前 item 自身，而不是再向下找子 `<a>`。

---

# 16. 分页怎么配置

当前支持五种分页类型。

---

## 16.1 普通“下一页”链接：`next_link`

网页：

```html
<a class="next" href="list_2.html">下一页</a>
```

配置：

```yaml
pagination:
  type: next_link
  next_selector: "a.next"
```

---

## 16.2 URL 模板：`url_template`

如果页面规律是：

```text
/list_1.html
/list_2.html
/list_3.html
```

配置：

```yaml
pagination:
  type: url_template
  template: "https://example.com/list_{page}.html"
```

---

## 16.3 Query 参数：`page_parameter`

如果页面规律是：

```text
/news?page=1
/news?page=2
```

配置：

```yaml
pagination:
  type: page_parameter
  param: page
```

---

## 16.4 JavaScript 点击分页：`playwright_click`

例如：

```html
<button onclick="window.v3Index.goToPage(2)">2</button>
```

配置：

```yaml
pagination:
  type: playwright_click
  next_selector: "#pagination .pagination-next-btn:not(.disabled)"
  ready_selector: "#newsGrid > a.news-card"
  wait_timeout_ms: 15000
  navigation_timeout_ms: 30000
  headless: true
  browser:
    prefer_system_chrome: true
```

如果站点 click 不稳定，并且你已经知道页面 JS 函数，还可以配置：

```yaml
  js_function: "window.v3Index.goToPage"
```

---

## 16.5 不分页：`none`

```yaml
pagination:
  type: none
```

---

# 17. 详情页 Selector 怎么修改

比赛当天详情页最重要的是四个字段：

```text
标题
正文
发布日期
来源
```

例如：

```yaml
detail:
  min_content_chars: 100

  title:
    selectors:
      - "h1.article-title"
      - "h1"

  content:
    selectors:
      - ".article-content"
      - ".TRS_Editor"
      - "#content"

  publish_time:
    selectors:
      - ".publish-time"
      - ".date"

  source:
    selectors:
      - ".source"
```

Selector 按顺序尝试。

所以：

> **最精准的 Selector 放第一位，通用 Selector 放后面。**

---

# 18. 正文抽取原则

比赛现场最重要的原则之一：

> **不要先抓整个页面，再靠清洗删除一大堆无关内容。优先把正文 Selector 配准。**

错误：

```yaml
content:
  selectors:
    - "body"
```

这很容易抓入：

- 导航；
- 页脚；
- 推荐；
- 评论；
- 作者卡片；
- APP 引导。

正确思路：

```yaml
content:
  selectors:
    - "真正的文章正文节点"
```

SZTV 当前使用：

```yaml
content:
  selectors:
    - '#rich_media_wrp .js_content[data-module-name="article"] #editWrap'
    - '#rich_media_wrp .js_content[data-module-name="article"]'
    - '#rich_media_wrp .js_content'
    - '#rich_media_wrp'
```

因此评论区从源头就不会进入正文。

---

# 19. 什么时候开启详情页 Chrome 渲染兜底

有些网站：

```text
浏览器里能看到正文
requests 返回 HTML 却没有正文
```

配置：

```yaml
detail:
  render_fallback: true
  render_fallback_on_non_rule: true
  render_wait_timeout_ms: 12000
  render_navigation_timeout_ms: 30000
```

程序流程：

```text
requests
↓
正文不足 min_content_chars
或者没有命中规则提取
↓
系统 Chrome + Playwright
↓
等待正文节点
↓
重新抽取
```

日志可能出现：

```text
detail playwright render url=https://...
detail id=xxxx chars=1582 render=True
```

`render=True` 表示 Chrome 兜底成功。

---

# 20. 如何修改噪声清洗规则

配置：

```text
config/noise_rules.yaml
```

当前示例：

```yaml
line_remove:
  - '^责任编辑[:：]'
  - '^版权声明[:：]'
  - '^相关推荐$'
  - '^评论$'
  - '^打开第一现场APP.*$'

trailing_markers:
  - '上一篇'
  - '下一篇'
  - '网站地图'
  - '相关推荐'
  - '评论'
```

## 比赛当天不要看到一条噪声就立即写规则

建议：

```text
先抽 10～20 篇
↓
观察重复出现的噪声
↓
确认不是正文
↓
再加入 noise_rules.yaml
↓
重新执行 process
```

修改清洗规则后不需要重新爬网页：

```powershell
.\.venv\Scripts\python.exe main.py process --site config\sites\xxx.yaml
.\.venv\Scripts\python.exe main.py analyze --site config\sites\xxx.yaml
.\.venv\Scripts\python.exe main.py export --site config\sites\xxx.yaml
```

---

# 21. 比赛当天推荐完整操作流程

这是最推荐实际照着执行的一套流程。

## 第 1 步：确认题目和数据方向

先明确：

```text
要采什么？
政策？
企业？
科研？
行业新闻？
投融资？
```

然后找 3～5 个高价值数据来源。

---

## 第 2 步：先适配一个网站，不要同时开很多

复制：

```text
demo.yaml
```

为：

```text
competition_site_01.yaml
```

先修改：

```text
site.name
site.domain
crawler.start_urls
```

---

## 第 3 步：先跑 inspect

```powershell
.\.venv\Scripts\python.exe main.py inspect `
  --site config\sites\competition_site_01.yaml `
  --url "https://目标网站/栏目"
```

重点看：

```text
HTTP 是否 200
Configured selector matches
Auto-discovery candidates
Next selector matches
```

---

## 第 4 步：浏览器 F12 分析 DOM

先找：

### 列表页

```text
item selector
link selector
title selector
date selector
下一页规则
```

### 详情页

```text
title selector
content selector
publish time selector
source selector
```

---

## 第 5 步：只抓 10～20 篇

不要一开始就 3000 篇。

```powershell
.\.venv\Scripts\python.exe main.py all `
  --site config\sites\competition_site_01.yaml `
  --max-pages 2 `
  --max-docs 20 `
  --clean-run
```

---

## 第 6 步：检查 RAW

随机打开：

```text
data/01_raw/json/*.json
```

重点检查：

```text
title 对不对？
contentText 有没有正文？
正文有没有缺开头？
正文有没有缺结尾？
sourceName 对不对？
publishTime 对不对？
```

如果 RAW 正文就是错的：

> **不要继续调 noise_rules，先修 detail.content Selector / render fallback。**

---

## 第 7 步：检查 CLEAN

看：

```text
data/04_clean/cleaned.jsonl
```

重点检查：

```text
评论有没有？
版权声明有没有？
上一篇 / 下一篇有没有？
相关推荐有没有？
正文有没有被误删？
日期有没有标准化？
```

---

## 第 8 步：检查 FINAL

看：

```text
data/06_final/final.jsonl
```

同时：

```text
data/06_final/final_preview.csv
```

至少人工抽查 20 条。

---

## 第 9 步：看数量变化

```text
reports/pipeline_stats.json
```

如果：

```text
raw=100
final=10
```

不要觉得“清洗很厉害”。

这更可能意味着：

- 正文 Selector 错；
- 页面需要 JS；
- 校验阈值不合适；
- 数据类型本来是视频 / 图片新闻；
- URL 发现混入了非文章页。

---

## 第 10 步：确认没问题后再扩大

```text
20
↓
100
↓
300
↓
1000+
```

例如：

```powershell
.\.venv\Scripts\python.exe main.py all `
  --site config\sites\competition_site_01.yaml `
  --max-pages 50 `
  --max-docs 3000 `
  --clean-run
```

---

# 22. 比赛当天 AI Coding 应该怎么用

不要让 AI 一上来重构整个项目。

推荐给 AI：

```text
这是目标网站的列表页 HTML。

请只分析：
1. item_selector
2. link_selector
3. title_selector
4. date_selector
5. 分页类型
6. next_selector

目标是修改 config/sites/competition_xxx.yaml。
不要修改 crawler/pipeline 等公共 Python 代码。
```

详情页：

```text
这是文章详情页 HTML。

请只分析：
1. title selector
2. content selector
3. publish_time selector
4. source selector

正文 selector 必须尽量只包含文章内容，
不要包含评论、相关推荐、导航和页脚。
然后只修改站点 YAML。
```

现场优先级：

```text
改 YAML
>
加站点特殊规则
>
最后才改公共 Python
```

---

# 23. 多网站采集怎么做

比赛很可能需要多个来源。

例如：

```text
site_01 政府政策
site_02 行业协会
site_03 企业官网
site_04 新闻媒体
```

当前 v1.6 如果希望把多个站点最终汇总到同一个数据池，推荐：

### 第一个站点

```powershell
python main.py crawl --site config\sites\site_01.yaml --max-docs 500 --clean-run
```

### 后续站点

不要再 `--clean-run`：

```powershell
python main.py crawl --site config\sites\site_02.yaml --max-docs 500
python main.py crawl --site config\sites\site_03.yaml --max-docs 500
```

这样 `data/01_raw/json/` 会保留前面已抓的数据。

所有站点抓完后统一：

```powershell
python main.py process --site config\sites\site_01.yaml
python main.py analyze --site config\sites\site_01.yaml
python main.py export --site config\sites\site_01.yaml
```

> 注意：当前 Pipeline 的 category / 清洗配置来自执行 `process` 时传入的 YAML。不同站点如果需要不同 category / noise rules，比赛时更稳的方式仍是“各站点单独生成 final，再做合并”，或者后续为工具增加真正的多数据源批次模式。

---

# 24. 常见问题排查

## 24.1 `discovered urls=0`

说明网页可能访问成功，但文章入口没有识别出来。

先：

```powershell
python main.py inspect --site ... --url ...
```

检查：

```text
selector_matches
candidate_count
```

常见原因：

- item_selector 错；
- 页面是 JS 动态加载；
- URL 入口不是你想的栏目页；
- domain 配错；
- 页面需要特殊分页。

---

## 24.2 RAW 有 100 条，但 `contentText` 大量为空

先看：

```text
data/01_raw/meta/*.json
logs/app.log
```

可能原因：

- detail.content Selector 错；
- requests 只拿到页面壳；
- 页面需要 JS 渲染；
- Chrome 没找到；
- 正文真正存在于 iframe / API 中。

如果浏览器能看到正文而 requests 看不到，优先开启：

```yaml
detail:
  render_fallback: true
```

---

## 24.3 评论 / 推荐内容进入正文

优先修：

```yaml
detail:
  content:
    selectors:
```

让正文节点更精确。

只有网页正文节点自身确实带固定尾部噪声时，再修改：

```text
config/noise_rules.yaml
```

---

## 24.4 下一页点不动

如果页面是：

```html
<button onclick="goToPage(2)">
```

不要使用：

```yaml
pagination:
  type: next_link
```

而应该：

```yaml
pagination:
  type: playwright_click
```

同时检查：

```text
next_selector
ready_selector
js_function
```

---

## 24.5 系统 Chrome 没识别到

执行：

```powershell
.\.venv\Scripts\python.exe browser_check.py
```

如果 Chrome 在自定义目录，可以 YAML 手工指定：

```yaml
pagination:
  browser:
    prefer_system_chrome: true
    executable_path: "D:\\Chrome\\Application\\chrome.exe"
```

---

## 24.6 final 数量异常少

按顺序查：

```text
reports/pipeline_stats.json
↓
data/rejected/rejected.jsonl
↓
data/_internal/record_audit.jsonl
```

不要只看 final。

---

## 24.7 PowerShell 找不到 `.bat`

PowerShell 当前目录执行文件要写：

```powershell
.\run_sztv_100.bat
```

而不是：

```powershell
run_sztv_100.bat
```

---

# 25. SZTV 当前配置为什么这样写

SZTV 首页新闻卡片：

```yaml
list:
  item_selector: "#newsGrid > a.news-card"
  link_selector: "@self"
  title_selector: ".news-card-title"
  date_selector: ".news-card-time"
  source_selector: ".news-card-source"
```

分页：

```yaml
pagination:
  type: playwright_click
  next_selector: "#pagination .pagination-next-btn:not(.disabled)"
  ready_selector: "#newsGrid > a.news-card"
  js_function: "window.v3Index.goToPage"
```

详情正文：

```yaml
detail:
  content:
    selectors:
      - '#rich_media_wrp .js_content[data-module-name="article"] #editWrap'
      - '#rich_media_wrp .js_content[data-module-name="article"]'
      - '#rich_media_wrp .js_content'
      - '#rich_media_wrp'
```

这样正文节点不会直接包含：

```text
comment-container
作者卡片
相关推荐区
APP评论区
```

---

# 26. 比赛当天最低验收清单

正式把数据交给 RAGFlow 以前，至少确认：

- [ ] `urls.jsonl` 里的 URL 基本都是目标文章；
- [ ] RAW HTML 已保存；
- [ ] RAW JSON 的 `contentText` 有真实正文；
- [ ] 随机抽 20 条 RAW，没有大量正文为空；
- [ ] `cleaned.jsonl` 没有导航、评论、相关推荐；
- [ ] 清洗没有明显误删正文；
- [ ] `publishTime` 已变成 `YYYY-MM-DD`；
- [ ] sourceName / sourceUrl / title 正常；
- [ ] URL 重复已处理；
- [ ] 正文完全重复已处理；
- [ ] `rejected.jsonl` 能解释被删除的数据；
- [ ] `pipeline_stats.json` 数量逻辑正常；
- [ ] `quality_report.json` 已生成；
- [ ] final 数据全部是固定 8 字段；
- [ ] `final_preview.csv` 人工抽查正常；
- [ ] 最终再开始 RAGFlow 上传与召回测试。

---

# 27. 推荐的比赛执行节奏

```text
0～15 分钟
找数据源 + 建 YAML

15～30 分钟
inspect + DOM 分析

30～45 分钟
抓 20 条 + 检查 RAW

45～60 分钟
修正文 Selector / 清洗规则

60 分钟以后
扩大到 100 / 500 / 3000

数据稳定后
生成 final + quality_report

最后
RAGFlow 入库 → Parse → Chunk → Recall Test
```

核心原则：

> **先保证抓到的是正确正文，再谈清洗；先保证数据干净完整，再谈 RAG 调参。**

---

# 28. 最重要的三个文件

比赛现场如果时间紧，只记住：

```text
config/sites/xxx.yaml
```

决定：**怎么抓。**

```text
data/04_clean/cleaned.jsonl
```

决定：**清洗成什么样。**

```text
data/06_final/final.jsonl
```

决定：**最终拿什么入库。**

同时用：

```text
reports/pipeline_stats.json
reports/quality_report.json
```

证明数据处理过程是可解释、可追溯的。

---

# 29. 一句话总结

RAG Data Toolkit v1.6 的使用逻辑可以记成：

```text
陌生网站
↓
inspect
↓
改 YAML
↓
先抓 20 条
↓
检查 RAW
↓
修 Selector
↓
检查 CLEAN
↓
扩大采集
↓
FINAL 标准 JSON
↓
RAGFlow
```

**比赛当天优先修改站点 YAML，不要轻易修改已经验证过的公共采集、清洗和 Pipeline 代码。**
