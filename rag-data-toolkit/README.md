# RAG Data Toolkit v1.9 — 广东省“教育与人才”比赛专用包

> 本包基于 v1.8，新增本次比赛的 P0 数据源配置、任务配置和 100 题盲测 Benchmark。
> **第一次使用请先读：`README_COMPETITION_GD_EDU_TALENT.md`。**

快速开始：

```powershell
.\setup_windows.bat
.\run_guangdong_p0.bat
```

最终合并数据：

```text
data/final/guangdong_education_talent_p0/combined_final.jsonl
```

---

# RAG Data Toolkit v1.8

> 面向 RAG / 知识库比赛的数据采集、清洗、标准化与多来源合并工具。
>
> 当前版本重点支持：**普通 HTML 分页、JavaScript 下一页、JavaScript“加载更多”、系统 Chrome 渲染、标准 8 字段 JSON、多站点独立运行、跨站合并去重。**

---

## 1. 这个项目解决什么问题

比赛拿到一个主题后，通常不是“写一个聊天机器人”就结束，而是要完成下面这条数据链路：

```text
目标主题
  ↓
寻找多个权威/有效数据源
  ↓
分析每个网站的列表页 / 分页 / 详情页 DOM
  ↓
发现文章 URL
  ↓
抓取详情页
  ↓
保存 RAW HTML + RAW 标准 JSON
  ↓
正文抽取
  ↓
URL / 正文去重
  ↓
噪声清洗
  ↓
日期 / 来源 / Metadata 标准化
  ↓
质量校验
  ↓
最终标准 JSON
  ↓
多个网站统一合并
  ↓
跨站去重
  ↓
combined_final.jsonl
  ↓
RAGFlow / 知识库入库
```

v1.8 的核心设计原则是：

```text
Python = 通用引擎
YAML   = 网站适配器
Task YAML = 比赛主题下的数据源编排
```

比赛当天，**优先让 AI 修改 / 新建 YAML，而不是修改 Python 核心代码**。

---

# 2. v1.8 新增内容

相对 v1.7，本版本新增：

- `pagination.type: playwright_load_more`
  - 专门处理“加载更多”按钮。
  - 点击后旧卡片保留，新卡片追加。
  - 程序等待 `item_selector` 数量增加，而不是等待第一页第一条 URL 改变。
- `fallback_next_link_selector`
  - “加载更多”点击失败时，可使用页面隐藏的传统“下一页”链接继续。
- 新增深圳新闻网配置：
  - `config/sites/sznews.yaml`
- 新增 SZTV + 深圳新闻网双来源任务：
  - `config/tasks/shenzhen_news_training.yaml`
- 新增脚本：
  - `run_sznews_100.bat`
  - `run_inspect_sznews.bat`
  - `run_shenzhen_news_multi.bat`
- Metadata 字段支持简单后处理：
  - `strip_prefixes`
  - `regex_extract`
- 新增深圳新闻网真实结构测试。

---

# 3. 最终标准 JSON

所有最终比赛数据统一输出为 **8 个字段**：

```json
{
  "sourceName": "深圳晚报",
  "sourceUrl": "https://wb.sznews.com/PC/content/202608/27/content_3473784.html",
  "title": "“贴身管家”爬楼拿药 “果园熟手”2秒摘果",
  "contentText": "深圳晚报讯……",
  "category": "深圳新闻-深圳新闻网",
  "publishTime": "2026-08-27",
  "attachments": [],
  "attachmentCount": 0
}
```

固定字段：

| 字段 | 含义 |
|---|---|
| `sourceName` | 来源名称 |
| `sourceUrl` | 原始详情页 URL |
| `title` | 标题 |
| `contentText` | 正文纯文本 |
| `category` | 当前比赛的数据分类 |
| `publishTime` | `YYYY-MM-DD` |
| `attachments` | 附件列表 |
| `attachmentCount` | 附件数量 |

技术字段，例如：

```text
quality_score
issues
content_hash
url_hash
extraction_method
```

不会写入最终上传 JSON；它们只用于内部治理和报告。

---

# 4. 项目架构

```text
rag-data-toolkit-v1.8-load-more/
│
├── main.py                         # CLI 总入口
├── requirements.txt
├── setup_windows.bat               # Windows 初始化
├── browser_check.py                # 系统 Chrome 检测
├── AI_SITE_ADAPTER_PROMPT.md      # 比赛当天可直接复制给 AI 的通用适配提示词
│
├── config/
│   ├── app.yaml                    # 通用默认配置
│   ├── noise_rules.yaml            # 通用清洗噪声规则
│   │
│   ├── sites/                      # 每一种网页模板一份 YAML
│   │   ├── demo.yaml               # 比赛站点模板
│   │   ├── sztv.yaml               # SZTV
│   │   ├── sznews.yaml             # 深圳新闻网
│   │   └── sztv_auto.yaml
│   │
│   └── tasks/                      # 多来源比赛任务
│       ├── competition_multi_template.yaml
│       ├── sztv_training.yaml
│       └── shenzhen_news_training.yaml
│
├── crawler/
│   ├── http_client.py              # requests + timeout + retry
│   ├── url_normalizer.py           # URL 标准化
│   ├── article_discovery.py        # Selector 失效后的自动 URL 发现
│   ├── list_crawler.py             # 普通 HTML 列表/分页
│   ├── playwright_list_crawler.py  # JS 下一页 / 加载更多
│   ├── detail_crawler.py           # 详情页抓取 + RAW 保存
│   └── detail_renderer.py          # 详情正文不足时 Chrome 渲染兜底
│
├── extractor/
│   └── html_extractor.py           # Selector 优先 + Trafilatura fallback
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
│   └── report_builder.py
│
├── multi/
│   ├── merger.py                   # 跨站 URL / 正文去重
│   └── output.py
│
├── exporter/
│   ├── jsonl_exporter.py
│   └── csv_exporter.py
│
├── core/
│   ├── models.py
│   └── schema.py                   # 固定 8 字段标准 JSON
│
├── utils/
│   ├── browser_utils.py
│   ├── file_utils.py
│   ├── hash_utils.py
│   ├── logger.py
│   ├── run_utils.py
│   └── workspace.py
│
├── data/
│   ├── 00_urls/
│   ├── 01_raw/
│   ├── 02_extracted/
│   ├── 03_dedup/
│   ├── 04_clean/
│   ├── 05_validated/
│   ├── 06_final/
│   ├── runs/                       # 多来源各站独立目录
│   └── final/                      # 多来源最终合并数据
│
├── reports/
│   └── tasks/
│
└── tests/
```

---

# 5. 数据目录每一层是什么

单站运行时：

```text
data/
├── 00_urls/
│   └── urls.jsonl
│
├── 01_raw/
│   ├── html/       # 原始详情 HTML
│   ├── json/       # 一篇文章一个“未清洗但已有正文”的标准 JSON
│   ├── meta/       # HTTP、渲染方式等内部信息
│   └── raw.jsonl
│
├── 02_extracted/
│   └── extracted.jsonl
│
├── 03_dedup/
│   └── dedup.jsonl
│
├── 04_clean/
│   └── cleaned.jsonl
│
├── 05_validated/
│   └── validated.jsonl
│
└── 06_final/
    ├── final.jsonl
    ├── final_preview.csv
    └── json/        # 一篇文章一个最终标准 JSON
```

检查顺序建议固定为：

```text
01_raw
↓
04_clean
↓
06_final
```

如果 RAW 正文就抓错了，应修改：

```text
site YAML / Selector / Chrome渲染策略
```

而不是依靠清洗脚本强行修。

如果 RAW 正文正确，但 CLEAN 仍有广告/页脚/推荐等噪声，再修改：

```text
config/noise_rules.yaml
```

---

# 6. 安装

推荐：Windows + Python 3.11 / 3.12。

进入项目目录：

```powershell
cd D:\Aproject\gitee\ragflow\rag-data-toolkit-v1.8-load-more
```

执行：

```powershell
.\setup_windows.bat
```

安装脚本会：

```text
检查 Python
↓
创建 .venv
↓
安装 requirements.txt
↓
检测系统 Google Chrome
↓
找到 Chrome：直接使用，不下载 Playwright Chromium
↓
找不到 Chrome：才询问是否下载 Chromium
↓
运行 pytest
```

测试通过应看到：

```text
24 passed
```

---

# 7. 常用 CLI

查看版本：

```powershell
.\.venv\Scripts\python.exe main.py --version
```

诊断网站：

```powershell
.\.venv\Scripts\python.exe main.py inspect `
  --site config\sites\demo.yaml `
  --url "https://目标网站/栏目页"
```

单站一键完成：

```powershell
.\.venv\Scripts\python.exe main.py all `
  --site config\sites\xxx.yaml `
  --max-pages 20 `
  --max-docs 100 `
  --clean-run
```

只抓取：

```powershell
.\.venv\Scripts\python.exe main.py crawl `
  --site config\sites\xxx.yaml `
  --max-pages 20 `
  --max-docs 100 `
  --clean-run
```

只处理已有 RAW：

```powershell
.\.venv\Scripts\python.exe main.py process --site config\sites\xxx.yaml
```

只生成报告：

```powershell
.\.venv\Scripts\python.exe main.py analyze --site config\sites\xxx.yaml
```

只导出最终文件：

```powershell
.\.venv\Scripts\python.exe main.py export --site config\sites\xxx.yaml
```

---

# 8. 支持的分页类型

## 8.1 `next_link`

页面存在真实“下一页” `<a href>`：

```yaml
pagination:
  type: next_link
  next_selector: "a.next"
```

适合：

```html
<a class="next" href="list_2.html">下一页</a>
```

---

## 8.2 `url_template`

分页 URL 有明确规律：

```yaml
pagination:
  type: url_template
  template: "https://example.com/news/index_{page}.html"
```

---

## 8.3 `page_parameter`

例如：

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

## 8.4 `playwright_click`

用于：

```text
点击“下一页”
↓
旧列表被替换
↓
新的第一页卡片出现
```

例如 SZTV：

```yaml
pagination:
  type: playwright_click
  next_selector: "#pagination .pagination-next-btn:not(.disabled)"
  ready_selector: "#newsGrid > a.news-card"
  js_function: "window.v3Index.goToPage"
```

程序判断翻页成功的主要条件：

```text
点击前第一条 href
!=
点击后第一条 href
```

---

## 8.5 `playwright_load_more`（v1.8 新增）

用于：

```text
初始10条
↓
点击“加载更多”
↓
旧10条仍在
+ 新10条追加
↓
DOM共20条
↓
继续点击
```

配置：

```yaml
pagination:
  type: playwright_load_more
  load_more_selector: "a.btn-more"
  ready_selector: ".card-list > a.card-list-item"
  wait_timeout_ms: 15000
  settle_ms: 400
```

程序不是固定 `sleep(2)`，而是等待：

```text
点击后的 item_selector 数量
>
点击前的 item_selector 数量
```

如果页面同时藏着传统下一页 URL，可以增加：

```yaml
fallback_next_link_selector: "ul.pages li.page-next a"
```

这样加载更多按钮异常时还能继续。

> `--max-pages` 对 `playwright_load_more` 表示“初始批次 + 最多若干次加载更多轮次”。

---

# 9. SZTV 练习

已有：

```text
config/sites/sztv.yaml
```

一键抓 100 条：

```powershell
.\run_sztv_100.bat
```

SZTV 特点：

```text
列表：#newsGrid > a.news-card
分页：JavaScript“下一页”
详情正文：#rich_media_wrp ... #editWrap
评论区：不会进入正文
```

---

# 10. 深圳新闻网 SZNEWS 练习

目标栏目：

```text
https://www.sznews.com/node_31100.htm
```

配置：

```text
config/sites/sznews.yaml
```

先诊断：

```powershell
.\run_inspect_sznews.bat
```

再抓 100 条：

```powershell
.\run_sznews_100.bat
```

## 10.1 列表结构

当前列表卡片：

```html
<a
  href="https://wb.sznews.com/PC/content/.../content_3473800.html"
  class="waterfall-item card-list-item">

  <div class="card-info">
    <h3>一条河，道尽深圳沧海桑田</h3>
    <span>2026-08-27</span>
  </div>
</a>
```

因此：

```yaml
list:
  item_selector: ".card-list.waterfall-list > a.waterfall-item.card-list-item"
  link_selector: "@self"
  title_selector: ".card-info h3"
  date_selector: ".card-info span"
  source_selector: ".card-info span b"
```

`@self` 表示：

```text
item 自己就是 <a href>
```

而不是在 item 内部继续找 `<a>`。

## 10.2 加载更多

页面按钮：

```html
<a href="javascript:;" class="btn-more">加载更多</a>
```

配置：

```yaml
pagination:
  type: playwright_load_more
  load_more_selector: "a.btn-more"
```

程序会：

```text
打开栏目
↓
统计当前卡片数量
↓
抓当前卡片 URL
↓
点击“加载更多”
↓
等待卡片总数增加
↓
抓新增 URL
↓
继续
```

SZNEWS 页面还存在隐藏传统分页：

```html
<ul class="pages" style="display:none">
  ...
  <li class="page-next">
    <a href="https://www.sznews.com/node_31100_2.htm">下一页</a>
  </li>
</ul>
```

所以配置了：

```yaml
fallback_next_link_selector: "ul.pages li.page-next a"
```

这是保险机制。

## 10.3 详情正文

深圳晚报模板：

```html
<h1 class="article-tit">...</h1>

<div class="article-source">
  <b>来源：深圳晚报</b>
  <span>发布时间：2026-08-27</span>
</div>

<div class="article-content">
  真正正文
</div>
```

因此：

```yaml
detail:
  title:
    selectors:
      - ".article h1.article-tit"

  content:
    selectors:
      - ".article .article-content"

  publish_time:
    selectors:
      - ".article-source span"
    strip_prefixes:
      - "发布时间："

  source:
    selectors:
      - ".article-source b"
    strip_prefixes:
      - "来源："
```

必须只取：

```text
.article-content
```

不要取：

```text
.article
.art-cont
body
```

否则很容易把：

```text
AI视界
二维码
相关推荐
其它功能区域
```

一起送进知识库。

---

# 11. Metadata 字段后处理

v1.8 支持：

```yaml
source:
  selectors:
    - ".article-source b"
  strip_prefixes:
    - "来源："
    - "来源:"
```

输入：

```text
来源：深圳晚报
```

输出：

```text
深圳晚报
```

也支持正则提取：

```yaml
source:
  selectors:
    - ".meta"
  regex_extract: "来源[：:]\\s*(.+)"
```

`regex_extract` 有捕获组时使用第 1 组。

---

# 12. 多数据源运行

这才是比赛正式使用时更推荐的方式。

例如一个比赛题目要同时爬：

```text
SZTV
+
深圳新闻网
+
政府网站
+
行业协会
```

不要把四个域名写进同一份 `site.yaml`。

正确结构：

```text
config/sites/
├── sztv.yaml
├── sznews.yaml
├── szgov.yaml
└── association.yaml

config/tasks/
└── competition_topic.yaml
```

一个站点模板一份 YAML。

一个比赛主题一个 Task YAML。

---

# 13. SZTV + SZNEWS 双来源练习

已经提供：

```text
config/tasks/shenzhen_news_training.yaml
```

直接执行：

```powershell
.\run_shenzhen_news_multi.bat
```

等价于：

```powershell
.\.venv\Scripts\python.exe main.py multi `
  --task config\tasks\shenzhen_news_training.yaml `
  --clean-run
```

运行后：

```text
data/runs/shenzhen_news_training/
├── sztv/
│   ├── 00_urls/
│   ├── 01_raw/
│   ├── 02_extracted/
│   ├── 03_dedup/
│   ├── 04_clean/
│   ├── 05_validated/
│   └── 06_final/
│
└── sznews/
    ├── 00_urls/
    ├── 01_raw/
    ├── 02_extracted/
    ├── 03_dedup/
    ├── 04_clean/
    ├── 05_validated/
    └── 06_final/
```

最终统一数据：

```text
data/final/shenzhen_news_training/combined_final.jsonl
```

跨站重复记录：

```text
data/final/shenzhen_news_training/global_duplicates.jsonl
```

---

# 14. 比赛当天新增一个网站，怎么做

假设比赛题目是：

```text
低空经济
```

你找到一个新网站：

```text
https://example.com/low-altitude/
```

不要直接修改 `sztv.yaml` 或 `sznews.yaml`。

复制：

```text
config/sites/demo.yaml
```

新建：

```text
config/sites/example_low_altitude.yaml
```

然后把：

```text
列表页 URL
列表页 HTML
详情页 HTML
分页 HTML / 点击前后 HTML
```

交给 AI 分析。

优先只让 AI 修改：

```text
site.name
site.domain
crawler.start_urls
list.*
pagination.*
detail.*
metadata.*
tag_rules
```

公共 Python 代码尽量不要动。

---

# 15. 比赛当天标准站点适配顺序

推荐固定执行：

```text
1. 浏览网站
↓
2. 找到列表页
↓
3. F12 查看一条卡片 DOM
↓
4. 找详情页 HTML
↓
5. 判断分页方式
↓
6. 把材料给 AI
↓
7. AI 新建 site YAML
↓
8. inspect
↓
9. 先抓 10~20 条
↓
10. 检查 01_raw/json
↓
11. 检查 04_clean
↓
12. 检查 06_final
↓
13. 没问题再扩大 100 / 500 / 3000
```

千万不要：

```text
第一次运行就抓3000条
```

如果正文 Selector 错了，会得到 3000 条垃圾。

---

# 16. 通用 AI 站点适配提问模板（比赛当天直接复制）

下面这一整段建议直接保存。比赛当天把 URL 和 HTML 填进去后发给 AI。

```text
你现在是在维护我的 RAG Data Toolkit v1.8 项目。

项目目标：
把互联网网站数据采集后，经过 RAW 留档、正文抽取、去重、清洗、校验，最终输出固定 8 字段 JSON，并支持多数据源 task 合并。

【非常重要的项目约束】

1. 优先只新增/修改 config/sites/*.yaml。
2. 不要修改已经跑通的 cleaner、pipeline、schema、multi merger，除非现有框架确实无法支持这个网站。
3. 如果必须修改 Python，请做成“通用能力”，不能写死当前网站域名。
4. 最终 JSON 必须严格保持以下 8 个字段：

sourceName
sourceUrl
title
contentText
category
publishTime
attachments
attachmentCount

5. RAW 必须保留原始 HTML，同时 RAW JSON 必须有实际正文 contentText。
6. 正文 Selector 必须尽量精准，只抓真正文章正文；不要把导航、评论、相关推荐、AI摘要、二维码、版权区、页脚抓进 contentText。
7. 优先 requests；只有列表页 JavaScript 分页或 requests 得不到正文时才使用 Playwright。
8. Playwright 优先使用本机系统 Chrome。
9. 不要一开始抓大量数据；先给我 10~20 条验证命令。
10. 网站适配成功后要告诉我如何加入 multi-source task。

【我要适配的新网站】

网站名称：<填写>
网站域名：<填写>
目标栏目 URL：<填写>
希望 category：<填写，例如：低空经济-政策法规>
计划抓取数量：<填写，例如 500>

【列表页 HTML】

<把列表页相关 HTML 粘贴在这里，至少包含 2~3 个完整卡片>

【分页区域 HTML】

<把分页/下一页/加载更多按钮 HTML 粘贴在这里>

如果是动态分页，我还会提供：

点击前 HTML：
<填写>

点击一次“下一页/加载更多”后的 HTML：
<填写>

【详情页 HTML】

<粘贴一个完整详情页中：标题、来源、日期、正文，以及正文之后区域的 HTML>

【请你先判断，不要马上乱改代码】

请依次判断：

A. 列表 item_selector 是什么？
B. link_selector 是什么？item 本身是否就是 a 标签，需不需要 @self？
C. title_selector 是什么？
D. date_selector 是什么？
E. source_selector 是什么？
F. 分页属于哪一种：
   - next_link
   - url_template
   - page_parameter
   - playwright_click
   - playwright_load_more
   - none
G. 如果是 JS 分页，应该等待“第一条 URL 改变”还是“卡片数量增加”？
H. 页面是否存在隐藏的真实下一页 href，可作为 fallback_next_link_selector？
I. 详情页 title selector 是什么？
J. 真正正文 content selector 是什么？
K. publish_time selector 是什么？是否需要 strip_prefixes / regex_extract？
L. source selector 是什么？是否需要 strip_prefixes / regex_extract？
M. requests 是否足够？是否需要 detail.render_fallback？
N. 哪些区域明确不能进入正文？

【你必须输出】

第一部分：网页结构分析结论

第二部分：完整的新 site YAML 文件
文件名建议：config/sites/<site_id>.yaml
必须完整输出，不要只给片段。

第三部分：告诉我现有 v1.8 是否已经支持。

如果已经支持：
只使用 YAML，不修改 Python。

如果不支持：
说明缺少的通用能力，然后列出必须修改的 Python 文件；修改不能写死当前网站。

第四部分：给出 inspect 命令。

第五部分：给出只抓 20 条的验证命令。

第六部分：告诉我跑完以后依次检查哪些文件：
01_raw
04_clean
06_final

第七部分：给出加入多数据源 task YAML 的完整 sites 配置片段。

第八部分：给出验收标准，至少包括：
- URL 是否正确
- title 是否正确
- contentText 是否是真正文
- sourceName 是否正确
- publishTime 是否为 YYYY-MM-DD
- 评论/导航/AI摘要/相关推荐是否被排除
- final.jsonl 是否严格只有 8 个标准字段

注意：
不要为了“抓到内容”而把 selector 写成 body、main 或过大的父容器。
宁可正文少一点，也不要把整页脏数据放进知识库。
```

---

# 17. 如果 AI 判断需要 `playwright_load_more`

标准配置模板：

```yaml
list:
  item_selector: ".你的列表 > a.item"
  link_selector: "@self"
  title_selector: ".title"
  date_selector: ".date"

pagination:
  type: playwright_load_more
  load_more_selector: "a.btn-more"
  ready_selector: ".你的列表 > a.item"
  wait_timeout_ms: 15000
  settle_ms: 400
  fallback_next_link_selector: "ul.pages li.page-next a"
  browser:
    prefer_system_chrome: true
    executable_path: null
```

如果按钮点击后旧列表被替换，而不是追加，则应该改成：

```yaml
pagination:
  type: playwright_click
```

两者区别：

```text
playwright_click
旧10条消失 → 新10条出现

playwright_load_more
旧10条保留 → 新10条追加 → 共20条
```

---

# 18. 多来源比赛 Task 模板

复制：

```text
config/tasks/competition_multi_template.yaml
```

例如：

```yaml
task:
  id: low_altitude
  name: 低空经济
  fail_fast: false

sites:
  - id: gov
    name: 政府来源
    config: config/sites/gov.yaml
    enabled: true
    priority: 10
    max_pages: 30
    max_docs: 1000
    overrides:
      metadata:
        category: 低空经济-政策法规

  - id: media
    name: 新闻来源
    config: config/sites/media.yaml
    enabled: true
    priority: 30
    max_pages: 20
    max_docs: 500
    overrides:
      metadata:
        category: 低空经济-新闻动态

merge:
  dedup_url: true
  dedup_content: true
```

数字越小，来源优先级越高。

例如：

```text
政府 10
行业协会 20
权威媒体 30
普通来源 50
```

不同来源转载同一正文时，优先保留 priority 更小的来源。

---

# 19. 多来源命令

完整运行：

```powershell
.\.venv\Scripts\python.exe main.py multi `
  --task config\tasks\low_altitude.yaml `
  --clean-run
```

断点续跑：

```powershell
.\.venv\Scripts\python.exe main.py multi `
  --task config\tasks\low_altitude.yaml `
  --resume
```

只重跑一个站：

```powershell
.\.venv\Scripts\python.exe main.py multi `
  --task config\tasks\low_altitude.yaml `
  --sites sznews
```

多个指定站：

```powershell
--sites sznews,sztv
```

只重新合并，不重新爬：

```powershell
.\.venv\Scripts\python.exe main.py merge `
  --task config\tasks\low_altitude.yaml
```

---

# 20. 多来源数据目录

假设 Task ID：

```text
low_altitude
```

每个网站单独存：

```text
data/runs/low_altitude/
├── gov/
├── association/
├── sztv/
└── sznews/
```

每个目录内部都有完整：

```text
00_urls
01_raw
02_extracted
03_dedup
04_clean
05_validated
06_final
reports
```

最终合并：

```text
data/final/low_altitude/
├── combined_final.jsonl
├── final_preview.csv
├── global_duplicates.jsonl
└── json/
```

---

# 21. 比赛当天如何检查抓取质量

## 第一关：URL

看：

```text
00_urls/urls.jsonl
```

确认：

```text
不是栏目页
不是图片
不是JS
不是登录页
确实是文章详情URL
```

## 第二关：RAW

随机打开：

```text
01_raw/json/*.json
```

重点看：

```text
title
contentText
sourceName
publishTime
```

如果 `contentText` 为空或整页都是菜单，先停下来修 YAML。

## 第三关：CLEAN

看：

```text
04_clean/cleaned.jsonl
```

重点查：

```text
上一篇
下一篇
相关推荐
评论
网站地图
APP引导
版权声明
导航
```

## 第四关：FINAL

看：

```text
06_final/final.jsonl
```

确认严格为固定 8 字段。

---

# 22. 常见错误

## `status=200` 但 `discovered urls=0`

含义：

```text
网页拿到了
但 list.item_selector / link_selector 没匹配到文章
```

处理：

```text
inspect
↓
检查 DOM
↓
修 site YAML
```

---

## RAW 里面 `contentText` 为空

原因通常是：

```text
详情 content selector 错
或者 requests 只拿到 JS 壳页面
```

先修 Selector。

如果浏览器里正文存在、requests HTML 中不存在：

```yaml
detail:
  render_fallback: true
```

---

## “加载更多”点了以后一直停在第一批

检查：

```yaml
pagination:
  type: playwright_load_more
  load_more_selector: "正确按钮 selector"
  ready_selector: "正确文章 item selector"
```

再检查：

```text
点击之后 item_selector 数量是否真的增加
```

如果页面有隐藏下一页 href，建议配置：

```yaml
fallback_next_link_selector: "..."
```

---

## 内容把 AI 摘要也抓进去了

说明正文 Selector 太大。

例如深圳新闻网应该抓：

```css
.article-content
```

而不是：

```css
.article
```

---

# 23. 当前已经实现的能力

```text
✅ requests HTTP 抓取
✅ timeout / retry
✅ URL 标准化
✅ URL 去重
✅ Selector 列表发现
✅ 自动文章 URL 发现 fallback
✅ 直接详情 URL 模式
✅ next_link
✅ url_template
✅ page_parameter
✅ playwright_click
✅ playwright_load_more
✅ load-more 隐藏 href fallback
✅ 系统 Chrome 优先
✅ 详情页 Chrome 渲染 fallback
✅ Selector 正文提取
✅ Trafilatura fallback
✅ Metadata strip_prefixes
✅ Metadata regex_extract
✅ 原始 HTML 留档
✅ RAW 标准 JSON 正文
✅ 正文 normalize
✅ 通用噪声清洗
✅ Content Hash 去重
✅ Validator
✅ Quality Score
✅ 8字段 final JSON
✅ 多数据源独立目录
✅ 跨站 URL 去重
✅ 跨站正文转载去重
✅ priority 权威来源优先
✅ 单站重跑
✅ resume
✅ 只重新 merge
```

---

# 24. 当前尚未重点实现的能力

以下不是当前 P0/P1 主链路：

```text
OCR扫描PDF
复杂PDF表格恢复
Word/PPT附件深度解析
登录态网站
验证码
强反爬绕过
无限滚动无按钮页面
复杂API签名
图片文字识别
```

比赛当天如果确实遇到，再针对性扩展。

---

# 25. 推荐比赛执行节奏

```text
0~15分钟
确定主题 + 数据类别 + 数据源

15~30分钟
第一个权威网站：AI生成site YAML

30~45分钟
inspect + 20条试跑 + RAW验收

45分钟以后
扩到100/500条，同时适配第二、第三个来源

中后段
multi合并 + 跨站去重 + 质量报告

最后
combined_final.jsonl → RAGFlow
```

---

# 26. 最终比赛最低验收

正式上传 RAGFlow 前至少确认：

```text
[ ] 不止一个有效来源（题目需要多来源时）
[ ] 01_raw 原始数据留档
[ ] RAW contentText 有真实正文
[ ] 标题正确
[ ] 来源正确
[ ] 日期正确
[ ] 评论未进入正文
[ ] AI摘要未进入正文
[ ] 导航/相关推荐未进入正文
[ ] URL已去重
[ ] 正文已去重
[ ] final.jsonl只有8个标准字段
[ ] 多站合并完成
[ ] global_duplicates.jsonl可追溯
[ ] combined_final.jsonl可正常逐行解析
```

---

# 27. 一句话记住 v1.8 的使用方式

```text
一个页面模板 = 一个 site.yaml

一个比赛主题 = 一个 task.yaml

陌生网站先让 AI 分析 DOM → 新建 YAML → 20条验证 → 再批量

最后：多个 site final → task merge → combined_final.jsonl → RAGFlow
```
