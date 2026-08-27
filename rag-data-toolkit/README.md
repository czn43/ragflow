# RAG Data Toolkit v1.6

面向 RAG 知识库比赛的数据采集、清洗与标准化工具。v1.6 重点修复 SZTV 实战中暴露的两个问题：

1. `requests` 抓到详情页壳页面时正文为空；现在会自动使用系统 Chrome + Playwright 渲染详情页兜底。
2. 所有面向比赛/上传的数据文件统一为固定 8 字段 JSON，不再混入 `id/quality_score/issues` 等内部技术字段。

## 标准 JSON 契约

所有 RAW、抽取、去重、清洗、校验、最终数据都使用完全相同的字段：

```json
{
  "sourceName": "深视新闻",
  "sourceUrl": "https://www.sztv.com.cn/ysz/zx/zw/83852598.shtml",
  "title": "白手起家的深圳年轻人，忙着改写全球富豪榜",
  "contentText": "这里是正文……",
  "category": "新闻资讯-新闻资讯",
  "publishTime": "2026-08-25",
  "attachments": [],
  "attachmentCount": 0
}
```

用户可见的数据 JSON 不会再出现额外字段。质量分、问题标签、清洗动作、hash 等技术信息单独放在 `data/_internal/record_audit.jsonl` 和 `reports/` 下。

## 目录含义

```text
data/
├── 00_urls/                     列表页发现的文章 URL
├── 01_raw/
│   ├── html/                    最原始/渲染后的完整 HTML 证据
│   ├── json/                    未清洗的标准 JSON，已经包含正文 contentText
│   └── meta/                    HTTP、抓取时间、是否用 Chrome 渲染等内部元数据
├── 02_extracted/extracted.jsonl 抽取阶段，标准 8 字段
├── 03_dedup/dedup.jsonl         URL 去重后，标准 8 字段
├── 04_clean/cleaned.jsonl       清洗后，标准 8 字段
├── 05_validated/validated.jsonl 校验通过后，标准 8 字段
├── 06_final/
│   ├── final.jsonl              最终批量数据
│   ├── final_preview.csv        人工抽查
│   └── json/                    每篇文章一个独立 JSON 文件
├── _internal/                   内部审计字段，不用于 RAG 上传
└── rejected/                    被拒绝/去重的数据
```

## SZTV 正文抓取策略

SZTV 首页新闻列表使用 Playwright JS 分页。详情页先尝试 `requests`：

```text
requests 详情页
    ↓
精确 selector 能拿到 >=100 字正文？
    ├─ 是 → 直接保存
    └─ 否 → 系统 Chrome 渲染详情页
                ↓
          再次执行精确 selector
                ↓
          保存带正文的 RAW JSON + HTML
```

SZTV 当前精确正文优先级：

```css
#rich_media_wrp .js_content[data-module-name="article"] #editWrap
#rich_media_wrp .js_content[data-module-name="article"]
#rich_media_wrp .js_content
#rich_media_wrp
```

评论区 `.comment-container` 不在这些节点内，因此正常情况下不会进入正文。对于通用抽取器兜底产生的页面噪声，清洗阶段还会移除“版权声明、相关推荐、评论、打开第一现场APP”等高置信噪声。

## Windows 安装

```powershell
.\setup_windows.bat
```

优先使用电脑已有 Google Chrome；只有找不到系统 Chrome 时才提示安装 Playwright Chromium。

## SZTV 100 篇实战

```powershell
.\run_sztv_100.bat
```

或者：

```powershell
.\.venv\Scripts\python.exe main.py all `
  --site config\sites\sztv.yaml `
  --max-pages 10 `
  --max-docs 100 `
  --clean-run
```

先重点检查：

```text
data\01_raw\json\*.json
```

这里现在应该已经有 `contentText`。然后检查：

```text
data\04_clean\cleaned.jsonl
data\06_final\final.jsonl
data\06_final\json\*.json
reports\pipeline_stats.json
reports\quality_report.json
```

## 正常运行时的关键日志

如果 requests 页面正文不足，会出现：

```text
detail playwright render url=https://...
detail id=... chars=1582 render=True ...
```

说明系统 Chrome 已经作为详情页正文兜底生效。
