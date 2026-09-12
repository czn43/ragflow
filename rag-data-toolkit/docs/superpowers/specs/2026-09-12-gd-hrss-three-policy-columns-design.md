# 广东省人社厅就业政策三栏目采集设计

## 目标

将广东省人社厅“广东就业 / 政策法规”下的国家政策、本省政策、政策解读分别作为独立数据源采集，保留准确分类，并纳入广东省“教育与人才”P0 合并任务。

## 已确认页面结构

- 国家政策：`https://hrss.gd.gov.cn/jyzl/zcfg/gjzc/`
- 本省政策：`https://hrss.gd.gov.cn/jyzl/zcfg/bszc/`
- 政策解读：`https://hrss.gd.gov.cn/jyzl/zcfg/zcjd/`
- 列表项：`ul.list li`
- 详情链接：`a[href*='/content/post_']`
- 列表日期：`.pubDate`
- 下一页：`.pages a.next`
- 详情标题：`.insMainConTitle_b`
- 详情信息栏：`.insMainConTitle_c`
- 详情正文：`#insMainConTxt .TRS_Editor`，回退 `#insMainConTxt`

## 架构

保留现有 `gd_hrss_employment` 作为“本省政策”，新增 `gd_hrss_national_policy` 和 `gd_hrss_policy_explain` 两个站点。三份 YAML 使用相同的列表、分页和详情规则，只在入口、站点名、分类与文档类型上区分。

政策页直接出现的 PDF 附件和政策解读关联原文中的 PDF 均进入标准记录的 `attachments`。附件 URL 去重后提取正文；附件失败不阻断政策正文入库。来源字段不从包含脚本和“打印本页”的信息栏强行抽取，无法得到明确来源时按现有框架回落为对应站点名。

## 数据分类

| 站点 ID | category | document_type |
| --- | --- | --- |
| `gd_hrss_national_policy` | `教育与人才-就业政策-国家政策` | `employment_policy` |
| `gd_hrss_employment` | `教育与人才-就业政策-本省政策` | `employment_policy` |
| `gd_hrss_policy_explain` | `教育与人才-就业政策-政策解读` | `policy_explanation` |

## 运行与安全边界

先运行无网络回归测试，再分别执行三站 `inspect`，随后使用 `multi --sites` 定向重跑三站。定向重跑不使用 `--clean-run`，因此其余 P0 数据源的已有结果保持不变；完成后框架会重新合并所有可用站点结果。

## 验收标准

- 三个入口分别命中本栏目详情链接，并能沿 `.pages a.next` 翻页。
- 给定详情 HTML 能以规则方式抽取标题、日期和正文。
- 三类记录的 `category` 与 `document_type` 正确。
- 可见 PDF 和 `file_appendix` 脚本中的 PDF 能被发现且 URL 去重。
- 三站定向运行完成，正文非空，并重新生成 `data/final/guangdong_education_talent_p0/combined_final.jsonl`。
