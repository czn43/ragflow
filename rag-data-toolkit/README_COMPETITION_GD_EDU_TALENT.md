# 广东省“教育与人才”比赛专用操作手册（v1.9）

> 当前目标：围绕 **广东省教育与人才**，优先建设能回答 **事实概念 / 数值统计 / 比较辨析 / 列表列举 / 场景应用** 五种题型的 RAG 知识库。
>
> 这不是“新闻爬虫任务”。第一优先级是：**权威政策、考试招生规则、办事指南、统计数字、政策清单、PDF 附件**。

---

## 1. 本版本已经准备好的东西

v1.9 在 v1.8 的通用爬虫、多数据源、JS 分页、标准 JSON 基础上，加入本次比赛专用配置：

```text
config/sites/
├── gd_edu_policy.yaml             广东省教育厅-教育政策法规
├── gd_edu_explain.yaml            广东省教育厅-政策解读
├── gd_eea_gaokao.yaml             广东省教育考试院-普通高考
├── gd_eea_gzxk.yaml               广东省教育考试院-高中学考
├── gd_hrss_employment.yaml        广东省人社厅-高校毕业生就业政策
├── gd_hrss_skill.yaml             广东省人社厅-技能人才
├── gd_seed_work_report_2026.yaml  2026广东省政府工作报告
├── gd_seed_talent_card.yaml       广东省人才优粤卡实施办法
├── gd_seed_graduate_policy.yaml   高校毕业生就业创业扶持政策清单
└── gd_seed_student_aid.yaml       广东学生资助政策体系

config/tasks/
└── guangdong_education_talent_p0.yaml

benchmarks/
├── Guangdong_Education_Talent_100Q.xlsx
└── 广东省教育与人才_RAG盲狙100题_知识矩阵.xlsx
```

首轮 task 的设计原则不是“数据越多越好”，而是先把高信息密度 P0 证据吃下来。

---

## 2. 首次运行

### 2.1 安装

```powershell
.\setup_windows.bat
```

如果电脑已安装 Chrome，项目优先使用系统 Chrome，不会重复下载 Playwright Chromium。

### 2.2 一键跑 P0 首轮

```powershell
.\run_guangdong_p0.bat
```

等价于：

```powershell
.\.venv\Scripts\python.exe main.py multi `
  --task config\tasks\guangdong_education_talent_p0.yaml `
  --clean-run
```

### 2.3 输出位置

每个来源独立保存：

```text
data/runs/guangdong_education_talent_p0/
├── gd_work_report_2026/
├── gd_talent_card/
├── gd_graduate_policy/
├── gd_student_aid/
├── gd_hrss_employment/
├── gd_hrss_skill/
├── gd_eea_gaokao/
├── gd_eea_gzxk/
├── gd_edu_policy/
└── gd_edu_explain/
```

最终合并：

```text
data/final/guangdong_education_talent_p0/combined_final.jsonl
```

---

## 3. 这次比赛先检查什么，而不是先看数量

每个来源运行后按下面顺序验收：

```text
01_raw/raw.jsonl
↓
04_clean/cleaned.jsonl
↓
06_final/final.jsonl
```

每个来源随机打开 5～10 条，检查：

1. `title` 是否是真正标题；
2. `contentText` 是否是真正正文；
3. 是否混入导航、页脚、推荐、评论；
4. `publishTime` 是否正确；
5. `sourceName` 是否合理；
6. PDF/附件型政策是否只有“附件见下方”而没有正文。

如果 RAW 就抓错了，先修 selector / 渲染策略；不要用 cleaner 去补救错误正文。

---

## 4. 首轮配置为什么有一些 list selector 是空的

例如：

```yaml
list:
  item_selector: ""
```

这是有意设计，不是漏写。

目前我们已经确定了这些官方栏目 URL 和分页规律，但比赛电脑上还需要结合真实 HTML 做一次 DOM 验证。空 selector 会让 v1.9 先走 **auto discovery**，避免在没看 DOM 的情况下写一个错误 selector，把整站导航当文章列表。

### 正确比赛流程

```text
先 inspect / 小批量抓20条
↓
检查发现的URL是不是文章
↓
浏览器F12复制列表HTML + 详情HTML
↓
交给 AI_SITE_ADAPTER_PROMPT.md
↓
让AI只收紧 YAML selector
↓
再扩大到100 / 500条
```

---

## 5. 当前 P0 数据源的作用

### 5.1 2026 广东省政府工作报告

解决：

- 数值统计；
- 列表列举；
- 教育与人才年度重点任务。

重点关键词：

```text
普通高中学位
补贴性职业技能培训
技工院校招生
职业资格 / 技能等级证书
百万英才汇南粤
高校毕业生
就业见习岗位
粤东粤西粤北
公益性岗位
```

### 5.2 广东省教育考试院

解决：

```text
普通高考
春季高考
依学考
3+证书
志愿填报
招生录取
高中学考
教师专项
```

当前已确认普通高考分页：

```text
https://eea.gd.gov.cn/ptgk/index.html
https://eea.gd.gov.cn/ptgk/index_2.html
https://eea.gd.gov.cn/ptgk/index_3.html
...
```

高中学考类似：

```text
https://eea.gd.gov.cn/gzxk/index.html
https://eea.gd.gov.cn/gzxk/index_2.html
...
```

### 5.3 广东省人社厅-就业政策

解决：

```text
高校毕业生就业创业
小微企业社保补贴
就业见习
求职创业
基层岗位
粤东粤西粤北就业
创业培训
创业租金
创业担保贷款
```

当前栏目：

```text
https://hrss.gd.gov.cn/jyzl/zcfg/bszc/
```

分页：

```text
index_2.html
```

### 5.4 广东技能人才

解决：

```text
职业技能等级
新八级工
高级技师
特级技师
首席技师
技能人才评价
```

### 5.5 人才优粤卡

一份政策同时适合：

```text
事实概念
数值统计
比较辨析
列表列举
场景应用
```

务必完整入库。

---

## 6. 用 100 道盲测题反向补数据

打开：

```text
benchmarks/Guangdong_Education_Talent_100Q.xlsx
```

它不是预测正式题，而是覆盖测试。

正式入 RAGFlow 后，每题至少检查：

```text
Top5 里有没有正确证据？
```

推荐记录：

```text
问题
题型
正确资料是否存在
Top1是否命中
Top5是否命中
正确Chunk排名
答案是否完整
失败原因
```

### 失败归因顺序

```text
1. 知识库根本没这条数据
2. 数据抓取/清洗错误
3. Chunk切坏
4. Metadata不合理
5. TopK / 阈值问题
6. 最后才是Prompt / LLM问题
```

---

## 7. 当天拿到新的广东官方网站怎么办

不要让 AI 重写整个爬虫。

执行：

```text
复制 config/sites/demo.yaml
↓
改名 gd_xxx.yaml
↓
把列表页HTML + 分页HTML + 详情页HTML 发给AI
↓
附 AI_SITE_ADAPTER_PROMPT.md
↓
让AI只修改/新增 YAML
↓
inspect
↓
抓20条
↓
人工抽查
↓
加入 task.yaml
```

### AI 提问的最简版

```text
这是 RAG Data Toolkit v1.9。
请基于现有 config/sites/demo.yaml 为这个网站新增独立 site YAML。

任务主题：广东省教育与人才。

我会提供：
1. 列表页URL与HTML
2. 分页区域HTML
3. 一个详情页URL与HTML

请先判断：
- item_selector
- link_selector
- title_selector
- date_selector
- source_selector
- pagination.type
- 下一页规则
- detail.title
- detail.content
- detail.publish_time
- detail.source
- requests 是否足够，是否需要 Playwright

要求：
1. 优先只新增/修改 YAML，不改公共 Python；
2. 正文 selector 必须精准，禁止直接使用 body/main 这种大容器；
3. 如果是 PDF/附件型政策，需要明确指出；
4. category 必须属于“教育与人才-xxx”；
5. 给出 inspect 命令和 20 条试跑命令；
6. 最后告诉我如何加入 config/tasks/guangdong_education_talent_p0.yaml。
```

完整版模板仍在：

```text
AI_SITE_ADAPTER_PROMPT.md
```

---

## 8. 建议当天时间分配

### 第一阶段：15～30分钟

先保证以下四份高密度材料成功入库：

```text
2026广东省政府工作报告
人才优粤卡
高校毕业生就业创业扶持政策清单
学生资助政策体系
```

### 第二阶段：30～90分钟

跑：

```text
教育厅政策法规
教育厅政策解读
教育考试院普通高考
高中学考
人社就业政策
技能人才
```

每个站先 20 条，再扩大。

### 第三阶段

入 RAGFlow 后跑 100 道盲测题。

按照错题补：

```text
招生规则不足 → 补教育考试院
就业场景不足 → 补人社办事指南
技能人才不足 → 补技能人才政策
资助不足 → 补最新资助政策
比较题不足 → 同时补政策原文 + 政策解读
```

---

## 9. 当前版本的一个重要提醒

现有 v1.9 已经能处理 HTML 网页正文、多源合并、JS 列表分页、标准 JSON。

但 **PDF / DOC / DOCX 附件自动下载与正文解析还不是本次版本的完整主链路**。

而广东教育、人社的很多高价值政策会把评价标准、招生规定、附件名单放在 PDF/DOCX 中。

因此运行后如果发现：

```text
正文只有：详见附件
```

不要把它当作已覆盖。

应将这类记录标记为“附件待解析”，作为下一阶段最高优先级补强项。

---

## 10. 最终目标

不要追求：

```text
我爬了5000篇
```

应该追求：

```text
P0知识板块都有权威证据
↓
100题Benchmark的Top5召回率持续提高
↓
数值题使用最新政策
↓
场景题能回答对象/条件/材料/流程/期限
↓
正式100题即使完全看不到，也尽量落在已有知识覆盖范围内
```
