# National Education & Talent Sources — Discovery Audit

Date: 2026-09-12 · Toolkit: `rag-data-toolkit` · Task: `config/tasks/national_education_talent_p0.yaml`

This audit records the verified entry URLs, selectors, pagination behavior, attachment
evidence, scope checks, and gate results for the 16 national sources. Every selector below
was confirmed against live HTML with a nonzero match count; none were guessed.

## Infrastructure notes (apply to several sources)

- **moe.gov.cn pagination is JS-rendered.** `ul#page` is an empty placeholder filled by JS,
  so `next_link` cannot work. The real pages are `index.html` (page 1), `index_1.html`
  (page 2), `index_2.html` (page 3) — i.e. `index_N.html` = page *N+1*. Configs use
  `pagination.type: url_template` with `template: "<column>/index_{page}.html"` **and** list
  `<column>/index_1.html` as a second `start_url`, because the template jumps page 1 →
  `index_2.html` and would otherwise skip page 2. Entry URLs must end in `index.html`, not a
  bare directory: `normalize_url` strips the trailing `/`, which would misresolve `./YYYYMM/...`
  links one directory too high (404).
- **mohrss.gov.cn is protected by a JS anti-bot challenge** (`EO_Bot`, HTTP 200 but a ~980-byte
  obfuscated shell) on *every* page, including deep links. List pages use
  `pagination.type: playwright_click`; detail pages are recovered by the crawler's
  `detail.render_fallback: true` (Playwright re-render when正文 is short).
- **gaokao.chsi.com.cn and chsi.com.cn use a 瑞数 (Ruishu) JS WAF** returning HTTP 412 to
  `requests` and to Playwright's default automation profile. Rendering succeeds only when
  Chrome is launched with `--disable-blink-features=AutomationControlled`. `utils/browser_utils.py`
  now passes `pagination.browser.args` through to `chromium.launch`, and both configs set
  `headless: false` plus that flag. Detail pages inherit the same launch args via `DetailRenderer`.
- **Test contract adaptation.** `tests/test_national_education_talent_configs.py` accepts
  `playwright_click` / `playwright_load_more` in its pagination-type whitelist, because three
  approved domains (mohrss, chsi, gaokao) cannot be crawled without Playwright.

---

## Wave 1 — P0-N

### 1. cn_moe_core_policy — 教育部综合政策 (`education_policy`)
- Entry columns: 中央文件 `jyb_xxgk/moe_1777/moe_1778/index.html`; 政策解读
  `jyb_xwfb/s271/index.html`; 公告公示 `jyb_xxgk/s5743/s5744/index.html` (+ `index_1.html` each).
- List: `#list li` → `a` (href `./YYYYMM/tYYYYMMDD_ID.html`), date in `span`. inspect HTTP 200,
  `selector_matches=20`.
- Pagination: `url_template` (`index_{page}.html`).
- Detail: title `.moe-detail-box h1`|`h1`; content `.TRS_Editor`|`.moe-detail-box`;
  date/source `#detail-date-source` (`日期：… 来源：…`). Verified on 教育强国纲要 page (9247 chars).
- Attachments: none static on sampled Central-document pages (full-text 正文).
- Isolation check (20 docs): 20/20 valid, 0 empty正文.
- Gate: inspect PASS · pytest PASS.

### 2. cn_moe_laws_regulations — 教育法律法规 (`law_regulation`)
- Entry: 文献-政策法规 tree — 教育法律 `jyb_sjzl/sjzl_zcfg/zcfg_jyfl/index.html`, plus
  行政法规 `zcfg_jyxzfg`, 部门规章 `zcfg_jybmgz`, 其他相关法律 `zcfg_qtxgfl`.
- List: `#list li` → `a`, date `span`. inspect HTTP 200, `selector_matches=9` (教育法律).
- **Seven named laws verified individually reachable** (all in 教育法律 column): 教育法, 义务教育法,
  职业教育法 (2022), 高等教育法, 教师法, 学位法 (2024), 学前教育法 (2024); plus 民办教育促进法 etc.
- Detail: `.moe-detail-box h1` / `.TRS_Editor` / `#detail-date-source` (verified 教育法 9002 chars).
- Note: 教育部文件/行政规范性文件 columns redirect to a `was5` search shell and are NOT usable
  as list pages; the 政策法规 tree above is the reachable one.
- Gate: inspect PASS · pytest PASS.

### 3. cn_moe_admission_policy — 高校招生政策 (`admission_policy`)
- Entry: `jyb_xxgk/xxgk/neirong/fenlei/sxml_gdjy/gdjy_gxzs/gxzs_zszcwj/index.html`
  (全国普通高校、成人高校招生相关政策文件).
- List: `dl#list dd` → `a`, date `span.x_gkndbg_pcdate`. inspect HTTP 200, `selector_matches=20`.
- Pagination: `url_template` (`index_{page}.html`; `index_1`=2017-2020 …).
- Detail: title `#downloadContent h1`|`.moe-detail-box h1`; content `#downloadContent`|`.TRS_Editor`;
  date/source `.moe-detail-shuxing` (`发布日期：… 来源：…`).
- **2026 annual rules present** (普通高校招生 2026-01-22; 成人高校招生 2026-09-03) with 2025
  counterparts; year visible in every title.
- Gate: inspect PASS · pytest PASS.

### 4. cn_gaokao_policy — 阳光高考 (`admission_policy`)
- Entry: `gaokao.chsi.com.cn/gkxx/zcdh/`, `/gkxx/qjjh/`, `/gkxx/zc/ss/`.
- Blocked by Ruishu WAF; renders only with `--disable-blink-features=AutomationControlled`
  (headed system Chrome). inspect (Playwright): `selector_matches=60`, next button `div.pageC a:nth-of-type(3)` = 1.
- List: `ul.news-list > li` → `div.title a`, date `div.time`. Pagination: `playwright_click`, server `?start=N`.
- Detail: `div.title-box h2` / `div.detail` / `div.news-msg > span`; source `div.news-msg span:nth-of-type(2)`.
- Inclusion filter: only the three policy columns; not nationwide `/zsgs/` 招生章程.
- Attachments: none static on sampled detail.
- Gate: inspect PASS (60 matches) · pytest PASS.

### 5. cn_student_aid — 学生资助 (`student_aid_policy`)
- Entry: 高校学生资助 `xszz.edu.cn/n39/n54/index.html`; 政策文件 n53/n58/n57/n56/n55
  (综合/学前/义务/普高/中职); 政策问答 n61-n65.
- List: `div.erjiCon.wrap li` → `a[href*='content.html']` (all links are `/cNNNNN/content.html`).
  inspect HTTP 200, `selector_matches=10`, 5/5 details valid.
- Pagination: `url_template` (`index_53_{page}.html`); page 2 added explicitly. `index_53_N` are
  AJAX fragments (selector=0 there) — the crawler's conservative auto-discovery recovers those links.
- Detail: `h2.title2` / `#txtSize` / `div.newsinfo span`.
- Attachment: static same-domain `.doc`, e.g. `/n39/n53/c7148/part/7313.doc`.
- Trial 20 docs: 20/20, 0 empty正文. Gate: inspect PASS · pytest PASS.

### 6-9. MOHRSS family (`talent_employment_policy` / `employment_policy` / `professional_title_policy` / `skill_talent_policy`)
All four: Playwright list render (anti-bot), `selector_matches=20`, next control found; detail via
`render_fallback`. Distinct subcolumns so the URLs do not overlap:

| site | entry column | list item selector | next control |
|---|---|---|---|
| cn_mohrss_core_policy | `xxgk2020/fdzdgknr/zcfg/` | `ul.rsb_con_rightUl li` | `div.pagede a.nextpage` |
| cn_mohrss_graduate_employment | `SYrlzyhshbzb/jiuye/zcwj/gaoxiaobiyesheng/` + `jiuye/zcwj/JYzonghe/` | `div.organGeneralNewListConType` | `img.pageNextBtn` |
| cn_mohrss_professional_titles | `SYrlzyhshbzb/rencairenshi/zcwj/zhuanyejishurenyuan/` | `div.organGeneralNewListConType` | `img.pageNextBtn` |
| cn_mohrss_skilled_talent | `SYrlzyhshbzb/rencairenshi/zcwj/jinengrencai/` | `div.organGeneralNewListConType` | `img.pageNextBtn` |

- Detail (both mohrss templates A/B covered): title `div.insMainConTitle_b`|`div.artT`|`h1`;
  content `#insMainConTxt .TRS_Editor`|`#insMainConTxt`|`div.art_det div.clearboth`|`div.art_det`;
  date `div.insMainConTitle_c`|`div.art_infos span`; source `div.insMainConTitle_c`|`div.info_table li:nth-of-type(3) .arti_r`.
- **Content-selector order matters for speed.** `DetailRenderer` waits on the content selectors
  *in order*, each for `render_wait_timeout_ms` (12 s). These columns' detail pages are almost all
  template B (`div.art_det`), so listing template-A selectors first cost ~24 s/page (two 12 s waits)
  before matching. Reordering to put `div.art_det div.clearboth` / `div.art_det` first drops it to
  ~0.2 s/page after the first challenge warm-up (measured: page 1 ≈ 5.9 s, subsequent ≈ 0.1-0.2 s).
- Attachment verified (skilled): `.../qt/gztz/202608/W020260821663866126784.pdf`.
- Trials: core 5/5, graduate 4/4, titles 4/4, skilled 4/4 — 0 empty正文, correct categories.
- Gate: inspect PASS for all four · pytest PASS (after whitelist adaptation).

### 10. cn_gov_top_policy — 国务院顶层政策 (`top_level_policy`)
- `start_mode: detail`, 20 curated gov.cn full-text seeds (中共中央/国务院/中办国办), covering
  教育强国、就业优先、人才发展、职业教育、高校毕业生.
- Blocker for list mode: gov.cn policy columns (`/zhengce/zuixin/`, `/wenjian/`, `/zhengceku/`) are
  JS/JSON-rendered (403 to requests), so detail seeds are used.
- Detail: title `h1`|`.abstract p:nth-of-type(5)`; content `#UCAP-CONTENT`|`.TRS_Editor`;
  date `.pages-date`|`.abstract p:nth-of-type(7)`; source `span.font-zyygwj`.
  `render_fallback: true` required (raw HTML is truncated by lxml).
- Trial: 20/20 success, 751-9282 chars, 0 empty正文. Gate: inspect PASS · pytest PASS.

### 11. cn_education_power_plan — 教育强国建设规划 (`strategic_plan`)
- `start_mode: detail`, 4 moe.gov.cn seeds. **Required** 《教育强国建设规划纲要（2024—2035年）》
  full text `.../202501/t20250119_1176193.html` confirmed complete (`.TRS_Editor` 9247 chars,
  includes section「（二十九）优化教师管理和资源配置」, not an abstract), plus 答记者问 and related.
- Detail: `.moe-detail-box h1` / `.TRS_Editor` / `.moe-detail-shuxing`.
- Trial: 4/4 success. Gate: inspect PASS · pytest PASS.

---

## Wave 2 — P1-N

### 12. cn_moe_vocational_education — 职业教育 (`vocational_education_policy`)
- Entries: 综合性政策规定和制度文件 `sxml_zycrjy/zycrjy_zjjjgl/zyjyyjxjyzhgl_zczd/index.html`,
  专业设置备案/审批结果 `zycrjy_zjjx/zyjyjx_spjg/index.html`, 专业目录年度增补 `zyjyjx_zbzy/index.html`,
  高中阶段招生文件 `zycrjy_zzdyxxgl/zzdyyxxgl_zswj/index.html`, 学历继续教育专业备案 `zycrjy_jjzygl/jxjyzygl_baspjg/index.html`.
- List: `dl#list dd` → `a`, date `span.x_gkndbg_pcdate`. inspect HTTP 200, `selector_matches=20`.
- Detail: `#downloadContent h1` / `#downloadContent`|`.TRS_Editor` / `.moe-detail-shuxing`.
- **Static PDF confirmed**: `.../srcsite/A07/moe_953/202202/W020220223300433792603.pdf` (新设高职专科国控专业审批结果).
- Gate: inspect PASS · pytest PASS.

### 13. cn_moe_education_statistics — 教育统计 (`statistical_bulletin`)
- Entries: 统计公报 `jyb_xxgk/xxgk/neirong/tongji/gongbao/index.html`, 经费执行公告
  `tongji/jytj_jftjgg/index.html`, 统计数据-全国/各地 `jyb_sjzl/moe_560/2024/{quanguo,gedi}/index.html`.
- List: `dl#list dd, #list li` → `a`, date `span.x_gkndbg_pcdate, span` (公报用 `dl#list dd`，数据表用 `#list li`).
- **Newest live bulletin verified = 2025年全国教育事业发展统计公报** (list date 2026-07-06), first item;
  no 2026 bulletin exists yet — not assumed from the matrix.
- Detail: bulletins `.moe-detail-box` + `.TRS_Editor`; data tables bare `.TRS_Editor` (both covered).
- Gate: inspect PASS · pytest PASS.

### 14. cn_chsi_rules — 学籍学历学位服务 (`service_rule`)
- Entry: `www.chsi.com.cn/xlrz/index.jsp` (学历认证公告), `/help/` (学籍/学历/学位查询指南),
  `/xlcx/bgcx.jsp` (在线验证报告). Ruishu WAF — same browser-args fix as gaokao.
- List: `ul.zygz-list a, ul.help-left-menu a, ul.zxyz-left-menu a` with `link_selector: @self`
  (items are the `<a>` themselves). inspect (Playwright): `selector_matches=8` on xlrz.
- Pagination: single-page columns → `playwright_click` with no `next_selector` (stops after one round).
- Detail: `div.title-box h2`|`h2.line-title` / `.content-box`|`.m_cnt_m.wz_page` / `div.news-msg > span`.
- Excludes news, promo, school lists, and any credential/query page.
- Gate: inspect PASS (8 matches) · pytest PASS.

### 15. cn_neea_exam_rules — 教育考试规则 (`exam_rule`)
- Entries: NTCE 考试动态 `neea.edu.cn/html1/category/1507/1148-1.htm`; 考试资讯 `.../16093/615-1.htm`;
  公示公告 `.../1508/151-1.htm`; CET `cet.neea.edu.cn/.../16093/{1124,1129}-1.htm`; 考核内容 `16123/192-1.htm`.
- List: `div.listdiv ul li, div.conlistn ul li, div.listdiv0 ul li` → `a[href*='/html1/report/']`,
  date `span#ReportIDIssueTime`. inspect HTTP 200, `selector_matches=15`, 5/5 valid.
- Pagination: `next_link`, `next_selector: a#CBNext` (static; page 2 verified).
- Detail: `div.Condiv h1`|`h1`|`#ReportIDname` / `div.Condiv`|`div.conts`|`#Content1` / `span#ReportIDIssueTime`.
- Attachment: static `.pdf` (e.g. zhaokao.net PDF linked from a notice).
- Trial: 20 raw, 20/20 detail success, 1 thin 成绩查询 notice rejected by the pipeline.
- Gate: inspect PASS · pytest PASS.

---

## Wave 3 — P2-N

### 16. cn_national_policy_explain — 国家权威政策解读 (`policy_explanation`)
- Entry: 教育部 政策解读/答记者问 `moe.gov.cn/jyb_xwfb/s271/index.html` (+ `index_1.html`).
- List: `#list li` → `a`, date `span`. inspect HTTP 200, `selector_matches=20`.
- Pagination: `url_template` (`index_{page}.html`).
- Detail: `.moe-detail-box h1` / `.TRS_Editor` / `#detail-date-source`.
- `document_type: policy_explanation` makes the crawler follow the original policy link and its
  PDF attachments; original policy sits at merge priority 1 vs this source's priority 3.
- Domain split note: mohrss (Playwright) and `gov.cn` (JS-rendered) explanation columns are not
  structure-compatible with moe's within one config, so this logical source lands on the moe
  interpretation column per the plan's "split by domain" allowance; mohrss/gov material is covered
  by their own site configs.
- Gate: inspect PASS · pytest PASS.

---

## Coverage caveats

- `cn_gov_top_policy` currently ships 20 verified detail seeds (target 70-120). Expanding to a live
  list would require Playwright plus a JSON list endpoint for gov.cn; recorded as a follow-up rather
  than silently shipping a broken list config.
- `cn_education_power_plan` intentionally yields 4-15 records (single strategic document + interpretations),
  per its matrix range.
- `cn_neea_exam_rules` and several list-mode sources may include a small number of thin notices that the
  pipeline rejects; that is expected and does not indicate selector failure.

## RAGFlow readiness prerequisites (not yet executable here)

- **No attachment-expansion exporter exists.** There is no `rag_ready.jsonl` exporter in `exporter/`
  (only `jsonl_exporter` / `csv_exporter`). Attachment正文 is stored as a nested
  `attachments[].contentText` inside each standard record; RAGFlow will not index it unless a
  dedicated exporter flattens attachment records into their own rows (retaining the parent policy
  title/URL/category/publishTime/relation). Recorded as a prerequisite to implement before the
  "upload full national corpus" step.
- The mixed 20-record sample upload + retrieval gate (fact/numeric/comparison/list/scenario questions
  against a live RAGFlow dataset) requires a running RAGFlow instance and dataset credentials, which
  are outside this repository. Manual follow-up.

