---
name: eeworld-reader
description: Read EEWorld latestnews articles for specific date(s), rank them by profile keywords, read single articles, and save interest notes. Use when users ask for “某天文章 / 某日文章 / 按日期抓取 EEWorld 最新文章 / 抓 latestnews 某天内容 / 阅读第x篇 / 对这篇文章感兴趣 / 关键词计数”. Follow MEMORY.md first for output and storage: latest-day only saves JSON into memory/eeworld-source-code/, article reads do not archive locally by default, on-demand article cache saves JSON into memory/articles/, and interest notes are saved under memory/interests/ as weekly merged files named like `2026-03-第三周文章.md`.
---

# EEWorld Reader

仅保留以下能力：
- latestnews 按日期抓取
- 按阅读画像关键词排序
- 按序号阅读单篇文章
- 感兴趣文章落盘与关键词计数维护

## Mandatory Fetch Path

读取并遵循：`WEB_FETCH_FALLBACK.md`

抓取 `latestnews` 时，统一使用 Jina Reader 回退路径：
- 原始页：`http://www.eeworld.com.cn/latestnews`
- 可读页：`https://r.jina.ai/http://www.eeworld.com.cn/latestnews`

## 功能范围

- ✅ 获取 `latestnews` 指定日期文章（支持多日期）
- ✅ 按阅读画像关键词做相关度排序
- ✅ 用户说“阅读第x篇”时，按排序序号读取该文并输出技术向详细说明
- ✅ 用户说“对这篇文章感兴趣”时，写入本地兴趣笔记并做关键词计数叠加
- ✅ 默认保存列表抓取结果 JSON
- ❌ 不再支持“今日电子信息”
- ❌ 不再支持“热门文章”

## Command Mapping

### 1) 获取某天最新文章（主功能）

```bash
python3 scripts/eeworld_feed.py 获取某天最新文章 \
  --date "2026-03-19" \
  --max-pages 20 \
  --profile "memory/eeworld-reading-profile.json" \
  --format markdown
```

英文别名：

```bash
python3 scripts/eeworld_feed.py latest-day --date "3-19" --max-pages 20 --format markdown
```

说明：
- `--date` 可重复，支持 `YYYY-MM-DD` 或 `M-D`
- 会自动翻页抓取：`/latestnews` → `/latestnews/2` → `/latestnews/3` ...，直到覆盖目标日期或达到 `--max-pages`
- `--max-pages` 默认 20，允许范围 1–100
- 默认会本地落盘（`--save-local` 默认开启）
- 默认只保存 **JSON** 到：`memory/eeworld-source-code/`
- 不再额外保存列表 markdown 或 raw latestnews 页面文本

### 2) 读取单篇文章全文（直接抓取并技术总结）

```bash
python3 scripts/eeworld_feed.py article --url "<ARTICLE_URL>" --max-chars 20000 --format markdown --refresh
```

说明：
- 当用户说“阅读第x篇 / 读这篇”时，默认直接抓取该文章正文
- **默认不本地存档**
- 仅当用户明确要求存档时，再启用本地缓存，并只保存 **JSON** 到 `memory/articles/`
- 输出内容格式优先遵循 `MEMORY.md`
- 摘要输出优先使用以下固定格式：
  - 文章标题 / 链接
  - 关键内容
  - 对用户有价值的点
  - 与用户关注方向的关系
  - 提取的关键词（最多 5 个）

### 3) 阅读画像关键词维护

普通追加（已存在关键词会累加）：

```bash
python3 scripts/eeworld_feed.py profile-add \
  --title "<ARTICLE_TITLE>" \
  --url "<ARTICLE_URL>" \
  --keywords "关键词1,关键词2,关键词3"
```

仅补充缺失关键词（已存在不重复写入）：

```bash
python3 scripts/eeworld_feed.py profile-add-missing \
  --title "<ARTICLE_TITLE>" \
  --url "<ARTICLE_URL>" \
  --keywords "关键词1,关键词2,关键词3"
```

计数叠加（已存在关键词会 +1）：

```bash
python3 scripts/eeworld_feed.py profile-add-count \
  --title "<ARTICLE_TITLE>" \
  --url "<ARTICLE_URL>" \
  --keywords "关键词1,关键词2,关键词3"
```

查看画像：

```bash
python3 scripts/eeworld_feed.py profile-show --top 20 --format markdown
```

### 4) 感兴趣文章落盘

```bash
python3 scripts/eeworld_feed.py interest-save \
  --title "<ARTICLE_TITLE>" \
  --url "<ARTICLE_URL>" \
  --summary "<技术向摘要>" \
  --keywords "关键词1,关键词2,关键词3" \
  --matched-keywords "命中词1,命中词2" \
  --score "2.80" \
  --date "2026-03-19"
```

默认行为：
- 写兴趣笔记到 `memory/interests/`
- 不再按单篇或单天建文件，而是按周合并写入周文件
- 周文件命名格式：`YYYY-MM-第N周文章.md`，例如 `2026-03-第三周文章.md`
- 同步关键词到画像并执行“计数叠加”（`--sync-profile` 默认开启，`--sync-mode` 默认 `count`）
- 如需仅补缺失不叠加：`--sync-mode missing`

## 阅读工作流（必须遵循）

### A. 列表阶段（获取某天最新文章）

按 `MEMORY.md` 优先输出排序列表，字段保持：
- 序号
- 相关度
- 命中关键词
- 标题
- URL

列表抓取结果只保存 JSON 到 `memory/eeworld-source-code/`。

### B. 用户说“阅读第x篇”

1. 按当前排序定位第 x 篇 URL
2. 直接抓取该文章正文
3. 输出约 500 字技术向详细说明，格式优先遵循 `MEMORY.md`：
   - 文章标题 / 链接
   - 关键内容
   - 对用户有价值的点
   - 与用户关注方向的关系
   - 提取的关键词（最多 5 个）
4. 默认不本地存档
5. 如用户明确要求存档，再保存 JSON 到 `memory/articles/`

### C. 用户说“对这篇文章感兴趣”

1. 立即写本地兴趣记录到 `memory/interests/`
2. 不单独新建日文件，而是写入对应周文件：`YYYY-MM-第N周文章.md`
3. 从文章与摘要提取候选关键词（最多 5 个）
4. 同步关键词到画像并做计数叠加
5. 明确反馈：
   - 保存路径
   - 新增关键词
   - 计数 +1 的关键词（若有）

## Output Rules

- 列表输出字段：日期、标题、分类、命中关键词、相关度、URL
- “阅读第x篇”输出格式优先服从 `MEMORY.md`
- 若 x 超出范围：先提示有效范围，再等待用户重选
- 若用户提出“今日电子信息 / 热门文章”，明确说明该功能已下线，并引导改为“按日期抓 latestnews”

## References

- Web Fetch fallback method: `WEB_FETCH_FALLBACK.md`
