# 比赛当天：通用 AI 站点适配提示词

> 复制下面整段给 AI，再补充目标网站 URL、列表页 HTML、分页区域 HTML、详情页 HTML。

```text
你现在是在维护我的 RAG Data Toolkit v1.8 项目。

项目目标：
把互联网网站数据采集后，经过 RAW 留档、正文抽取、去重、清洗、校验，最终输出固定 8 字段 JSON，并支持多数据源 task 合并。

【非常重要的项目约束】
1. 优先只新增/修改 config/sites/*.yaml。
2. 不要修改已经跑通的 cleaner、pipeline、schema、multi merger，除非现有框架确实无法支持这个网站。
3. 如果必须修改 Python，请做成“通用能力”，不能写死当前网站域名。
4. 最终 JSON 必须严格保持：sourceName/sourceUrl/title/contentText/category/publishTime/attachments/attachmentCount。
5. RAW 必须保留原始 HTML，同时 RAW JSON 必须有实际正文 contentText。
6. 正文 Selector 必须尽量精准；不要把导航、评论、相关推荐、AI摘要、二维码、版权区、页脚抓进 contentText。
7. 优先 requests；只有列表页 JavaScript 分页或 requests 得不到正文时才使用 Playwright。
8. Playwright 优先使用本机系统 Chrome。
9. 先给 10~20 条验证方案，不要直接抓大量数据。
10. 适配成功后告诉我如何加入 multi-source task。

【我要适配的新网站】
网站名称：<填写>
网站域名：<填写>
目标栏目 URL：<填写>
希望 category：<填写>
计划抓取数量：<填写>

【列表页 HTML】
<粘贴至少 2~3 个完整卡片>

【分页区域 HTML】
<粘贴下一页/页码/加载更多按钮>

【如果是动态分页】
点击前 HTML：<填写>
点击一次后的 HTML：<填写>

【详情页 HTML】
<粘贴标题、来源、时间、正文，以及正文后面的部分>

请依次判断：
A. item_selector
B. link_selector，是否应使用 @self
C. title_selector
D. date_selector
E. source_selector
F. pagination.type：next_link / url_template / page_parameter / playwright_click / playwright_load_more / none
G. JS 分页应等待“第一条 URL 改变”还是“卡片数量增加”
H. 是否有隐藏真实下一页 href，可配置 fallback_next_link_selector
I. detail.title selector
J. detail.content selector
K. publish_time selector，是否需 strip_prefixes / regex_extract
L. source selector，是否需 strip_prefixes / regex_extract
M. requests 是否足够，是否需要 render_fallback
N. 哪些区域绝不能进入正文

你必须输出：
1. 网页结构分析结论。
2. 完整 config/sites/<site_id>.yaml，不要只给片段。
3. 明确现有 v1.8 是否已支持；支持则不要改 Python。
4. 若不支持，说明缺少的通用能力，并给出完整代码修改；禁止写死域名。
5. inspect 命令。
6. 只抓 20 条的验证命令。
7. 01_raw → 04_clean → 06_final 的验收方法。
8. 加入 task YAML 的完整 sites 配置片段。
9. 验收标准：URL/title/content/source/date/噪声排除/8字段 schema。

不要为了抓到内容而把正文 selector 写成 body、main 或过大的父容器。
宁可正文少一点，也不要把整页脏数据放进知识库。
```
