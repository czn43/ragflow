# RAG Data Toolkit v1.6 Test Results

## Automated tests

```text
18 passed
```

覆盖：

- URL 标准化
- 日期标准化
- 噪声清洗与误删保护
- SZTV `@self` 列表链接
- SZTV JS 分页模拟
- 系统 Chrome 优先策略
- 标准 8 字段 schema
- 详情页正文为空时 Playwright 渲染兜底
- RAW JSON 必须包含正文 `contentText`
- 清洗结果必须保持标准 8 字段
- 评论/相关推荐不能进入最终正文

## User supplied result diagnosis

针对用户上传的 v1.5 结果检查：

```text
extracted.jsonl: 100 records
EMPTY content:   99
failed extract:  99
final.jsonl:      1 record
```

唯一保留记录仍包含版权声明/相关推荐/评论，因此 v1.5 本轮结果不适合直接入库。v1.6 的实现针对该问题进行了结构性修复。
