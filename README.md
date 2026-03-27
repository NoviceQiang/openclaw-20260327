# OpenClaw Skills: EEWorld Reader + BOM Manager

这是一个面向电子工程信息流与器件归档的技能仓库，当前包含两类核心能力：

- **EEWorld Reader**：按日期抓取 EEWorld latestnews，多页去重、偏好排序、单篇深读、兴趣记录。
- **BOM Manager**：从 datasheet 抽取器件信息，生成可确认的 BOM 条目并写回表格。

---

## 1) Skills Overview

### A. `eeworld-reader`

**定位**：电子信息文章获取与技术向筛选。

**关键能力**：

- 指定日期抓取 `https://www.eeworld.com.cn/latestnews`
- 支持多页抓取与本地合并去重
- 按阅读画像（category + keyword）加权排序
- 支持“阅读第 x 篇”单篇深读
- 支持“感兴趣文章”落盘和关键词计数维护

**本地数据规范**：

- Source JSON: `memory/eeworld-source-code/`
- 新命名规则：`文章日期-抓取日期.json`（例如：`2026-3-25-2026-3-27.json`）
- 列表输出：`articles/YYYY-MM-DD-eeworld-latestnews-ranked.md`

---

### B. `bom-manager`

**定位**：电子项目 BOM 条目创建与维护。

**关键能力**：

- 输入 datasheet（PDF / URL）
- 抽取器件参数并生成 BOM 字段草案
- 自动建议 `Item No.` 与 `Reference`
- 用户确认后写入 BOM 文件（xlsx/csv）

**典型字段**：

- Item No., Reference, Category, Description, Parameters
- Voltage/Current/Power Rating
- Footprint, Temperature Range, Datasheet, Usage Notes, Modified

---

## 2) Repository Structure

```text
.
├─ skills/
│  ├─ eeworld-reader/
│  │  ├─ SKILL.md
│  │  ├─ WEB_FETCH_FALLBACK.md
│  │  ├─ scripts/
│  │  │  └─ eeworld_feed.py
│  │  └─ references/
│  └─ bom-manager/
│     └─ SKILL.md
├─ memory/
│  ├─ eeworld-reading-profile.json
│  └─ eeworld-source-code/
└─ articles/
```

---

## 3) Quick Start

### EEWorld：按日期抓取

```bash
uv run python skills/eeworld-reader/scripts/eeworld_feed.py 获取某天最新文章 \
  --date 2026-03-27 \
  --max-pages 20 \
  --format markdown
```

### EEWorld：读取单篇文章

```bash
uv run python skills/eeworld-reader/scripts/eeworld_feed.py article \
  --url "<ARTICLE_URL>" \
  --format markdown
```

### BOM：创建器件条目（工作流）

1. 提供 datasheet（PDF 或 URL）
2. 指定 BOM 文件路径
3. 审核字段草案
4. 确认后写入

---

## 4) Design Principles

- **结论优先**：先给可执行结果，再补分析。
- **完整优先**：按日期抓取必须覆盖全部分页，不写不完整 source JSON。
- **可追溯**：所有中间与最终结果落地本地文件，路径清晰。
- **确认写入**：BOM 场景中，未确认不落表。

---

## 5) Roadmap

- [ ] BOM 自动化脚本（extract/update/reference-suggest）
- [ ] EEWorld 单篇缓存与 read 状态自动标记优化
- [ ] 统一导出日报/周报（与兴趣笔记联动）

---

## 6) License

按你的项目策略补充（MIT / Apache-2.0 / 私有）。
