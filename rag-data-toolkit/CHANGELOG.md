# Changelog

## v1.6.0 - Standard JSON + detail render fallback

- 固定用户侧 JSON 为 8 字段：`sourceName/sourceUrl/title/contentText/category/publishTime/attachments/attachmentCount`。
- `data/01_raw/json/*.json` 现在直接包含未清洗正文 `contentText`，不再只有抓取元信息。
- 原始 HTTP/调试元信息移动到 `data/01_raw/meta/`。
- SZTV 详情页 requests 抽不到规则正文时，自动复用系统 Chrome + Playwright 渲染详情页。
- 对 SZTV 开启 `render_fallback_on_non_rule`：若只得到 Trafilatura 页面壳结果，也会强制尝试浏览器渲染。
- 清洗阶段增加 SZTV 高置信噪声：版权声明、相关推荐、评论、APP 引导。
- 真正按阶段输出 `02_extracted -> 03_dedup -> 04_clean -> 05_validated -> 06_final`。
- 内部质量/问题/清洗动作独立输出到 `data/_internal/record_audit.jsonl`。
- 新增 `data/06_final/json/`：每篇文章一个标准 JSON 文件，方便目录式批量上传。
