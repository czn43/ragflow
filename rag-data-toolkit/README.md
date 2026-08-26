# RAG Data Toolkit — 比赛 P0 第一版

> **Windows v1.2 note:** the batch files in this package use Windows CRLF line endings and ASCII-only console messages to avoid CMD encoding/line-ending issues.


这是一套面向“互联网数据采集 → 清洗 → 结构化 → RAGFlow 入库前准备”的轻量工具。

## 已实现 P0-1 → P0-16

1. 统一 Document 数据模型
2. HTTP Client（Session / Retry / Timeout / Delay）
3. 列表页 + 自动分页
4. 详情页 RAW HTML/JSON 留档
5. CSS Selector 正文抽取 + Trafilatura fallback
6. URL Normalize + URL 去重
7. 正文 Unicode/空白标准化
8. 配置驱动的尾部/行噪声清洗
9. 日期标准化
10. Content Hash 去重
11. Validator（valid / warning / reject）
12. Metadata Builder
13. Quality Score
14. Statistics
15. `final.jsonl`
16. `quality_report.json`

额外包含：`final_preview.csv`、`actions.json`、`rejected.jsonl`、单元测试。

---

## 1. 安装

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
```

安装依赖：

```bash
python -m pip install -r requirements.txt
```

---

## 2. 比赛当天优先改配置，不改公共代码

复制：

```text
config/sites/demo.yaml
```

例如：

```text
config/sites/topic_a.yaml
```

重点配置：

- `crawler.start_urls`
- `list.item_selector`
- `list.link_selector`
- `list.date_selector`
- `pagination`
- `detail.title.selectors`
- `detail.content.selectors`
- `detail.publish_time.selectors`
- `detail.source.selectors`
- `metadata`
- `tag_rules`

拿到新网站后建议先抓 5 篇验证，再 50 篇，最后 100/3000 篇。

---

## 3. 一键跑 100 篇

```bash
python main.py all --site config/sites/topic_a.yaml --max-pages 20 --max-docs 100
```

也可分阶段运行：

```bash
python main.py crawl --site config/sites/topic_a.yaml --max-pages 20 --max-docs 100
python main.py process --site config/sites/topic_a.yaml
python main.py analyze --site config/sites/topic_a.yaml
python main.py export --site config/sites/topic_a.yaml
```

---

## 4. 产物

### 原始 URL

```text
data/00_urls/urls.jsonl
```

### RAW HTML

```text
data/01_raw/html/{id}.html
```

### RAW 元数据

```text
data/01_raw/json/{id}.json
```

### 清洗后数据

```text
data/04_clean/cleaned.jsonl
```

### 验证后数据

```text
data/05_validated/validated.jsonl
```

### 最终 RAG 数据

```text
data/06_final/final.jsonl
```

### Excel 可查看预览

```text
data/06_final/final_preview.csv
```

### 数据质量报告

```text
reports/quality_report.json
```

### Pipeline 数量变化

```text
reports/pipeline_stats.json
```

### 清洗动作统计

```text
reports/actions.json
```

### 被拒绝/去重数据

```text
data/rejected/
```

---

## 5. final.jsonl 示例

```json
{"id":"...","title":"某政策通知","content":"正文...","source_url":"https://...","source_name":"某政府网站","publish_time":"2026-08-01","category":"产业政策","tags":["政策"],"region":"深圳","document_type":"policy","char_count":2356,"quality_score":95,"quality_level":"HIGH","issues":[]}
```

---

## 6. quality_report.json 包含

- 原始/最终/重复/异常数量
- title/content/date/source/url 完整率
- 正文长度 min/max/mean/P50/P90/P95
- 长度区间分布
- 来源 Top20、Top1/Top3 集中度
- Category 分布
- 年份分布
- issue 污染/异常统计

---

## 7. 新网站适配推荐工作流

1. 浏览一个列表页和一个详情页。
2. 把 HTML 交给 AI Coding，让它只分析 Selector。
3. 修改 `config/sites/xxx.yaml`。
4. `--max-docs 5` 试跑。
5. 打开 RAW HTML 与 `validated.jsonl` 人工核对。
6. `--max-docs 50` 再跑。
7. 检查 `quality_report.json` 和 `rejected.jsonl`。
8. 确认后再放大数据量。

---

## 8. 运行测试

推荐：

```bash
python -m pytest -q
```

Windows 也可以直接运行：

```text
run_tests.bat
```

项目同时提供 `pytest.ini` 与 `tests/conftest.py`，因此直接执行 `pytest -q` 也能正确识别 `crawler`、`cleaner`、`extractor` 等本地包。

---

## 9. 当前第一版边界

这是 P0 版本，因此暂未加入：

- Playwright 动态页渲染
- PDF/Word/Excel 附件解析
- OCR
- 近似重复 RapidFuzz
- 多线程/异步高并发
- HTML 可视化报告

这些建议作为 P1 扩展，不影响第一版完成“100 篇普通政府/新闻网站数据全流程”。


---

## 10. Windows 最省事的启动方式

首次解压后直接双击：

```text
setup_windows.bat
```

它会：

1. 检查 Python；
2. 创建 `.venv`；
3. 升级虚拟环境 pip；
4. 安装 `requirements.txt`；
5. 使用虚拟环境 Python 执行 `python -m pytest -q`。

测试通过后，复制并修改 `config/sites/demo.yaml`，再运行：

```text
run_100.bat config\sites\你的站点.yaml
```

### 如果曾出现 `ModuleNotFoundError: No module named 'cleaner'`

本修正版已增加：

- `pytest.ini`：显式将项目根目录加入测试 Python Path；
- `tests/conftest.py`：在测试收集前再次保证项目根目录进入 `sys.path`；
- 所有业务目录均保留 `__init__.py`；
- Windows BAT 不再依赖 `activate` 后再调用裸 `pytest.exe`，而是直接调用 `.venv\Scripts\python.exe -m pytest`。

因此无需手工设置 `PYTHONPATH`。
