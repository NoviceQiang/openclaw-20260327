---
name: eeworld-reader
description: Read and archive EEWorld latestnews articles for specific date(s), with ranked reading and keyword count accumulation. Use when users ask for “某天文章/某日文章/按日期抓取 EEWorld 最新文章/抓 latestnews 某天内容/阅读第x篇/对这篇文章感兴趣/关键词计数”. This skill no longer provides “今日电子信息” or “热门文章” board lists.
---

# EEWorld Reader

仅保留 **latestnews 按日期抓取**、**按序号逐篇阅读**、**兴趣记录与关键词计数维护**。

## Mandatory Fetch Path (from WEB_FETCH_FALLBACK.md)

读取并遵循：`WEB_FETCH_FALLBACK.md`

抓取 `latestnews` 时，统一使用 Jina Reader 回退路径：

- 原始页：`http://www.eeworld.com.cn/latestnews`
- 可读页：`https://r.jina.ai/http://www.eeworld.com.cn/latestnews`

## 功能范围（已收敛）

- ✅ 获取 `latestnews` 指定日期文章（支持多日期）
- ✅ 按阅读画像关键词做相关度排序
- ✅ 用户说“阅读第x篇”时，按排序序号读取该文并输出技术向详细说明
- ✅ 用户说“对这篇文章感兴趣”时，写入本地兴趣笔记并做关键词计数叠加
- ✅ 自动保存抓取结果到本地（默认开启）
- ❌ 不再支持“今日电子信息”
- ❌ 不再支持“热门文章”

## Command Mapping

### 1) 获取某天最新文章（主功能）

> 执行前先检查本地是否已有该日期排序文件；有则直接读取本地并继续“阅读第x篇”流程。

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
- `--date` 可重复，支持 `YYYY-MM-DD` 或 `M-D`。
- 会自动翻页抓取：`/latestnews` → `/latestnews/2` → `/latestnews/3` ...，直到覆盖目标日期或达到 `--max-pages`。
- `--max-pages` 默认 20，允许范围 1–100；抓更早日期时请适当调大。
- 默认会本地落盘（`--save-local` 默认开启）。
- 默认保存目录：`memory/eeworld-captures/`。
- 除结果汇总外，还会保存抓取到的原始 `latestnews` 页面文本。

### 2) 读取单篇文章全文（直接抓取并技术总结）

```bash
python3 scripts/eeworld_feed.py article --url "<ARTICLE_URL>" --max-chars 20000 --format markdown --refresh
```

说明：
- 当用户说“阅读第x篇/读这篇”时，默认直接抓取该文章正文（不要求本地缓存优先）。
- 抓取后输出约 **500 字**技术向总结，聚焦：
  - 技术问题与背景
  - 核心技术路径/架构
  - 关键器件/参数/实现要点
  - 应用场景与工程价值
- 同步提取**最多 5 个关键词**（优先技术关键词，去掉宣传词）。
- 如需本地留档，可将正文缓存写入 `memory/eeworld-captures/articles/` 供后续复用。

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

计数叠加（已存在关键词会 +1，便于后续按权重筛选）：

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

### 4) 感兴趣文章落盘（并补齐缺失关键词）

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
- 同步关键词到画像并执行“计数叠加”（`--sync-profile` 默认开启，`--sync-mode` 默认 `count`）
- 如需仅补缺失不叠加：`--sync-mode missing`

## 阅读工作流（必须遵循）

### 0. 数据源优先级（必须）

获取“某日文章”时，按以下优先级执行，避免重复抓取与冲突：

1. **本地已有排序结果优先**：`articles/*-eeworld-latestnews-ranked.md`  
2. **本地抓取缓存其次**：`memory/eeworld-captures/`（含 raw-latestnews 与 latest-day JSON/MD）  
3. **浏览器实时抓取再次**：当本地缺失或日期不全时使用浏览器抓取  
4. **脚本/Jina 回退最后**：仅作补充，不单独作为“是否有该日文章”的唯一判断依据

### A. 列表阶段（按关键词排序）

先返回排序列表（含：序号、分值、命中关键词、标题、URL）。

### B. 用户说“阅读第x篇”

1. 按当前排序定位第 x 篇 URL。  
2. 直接抓取该文章正文（按需使用 `--refresh`，不以本地缓存优先为前提）。  
3. 输出 **约 500 字技术向详细说明**（不是营销复述）：
   - 技术问题与背景
   - 核心技术路径/架构
   - 关键器件/参数/实现要点
   - 适用场景与工程价值
4. 提取并返回**最多 5 个技术关键词**。  
5. 附：标题、URL、相关度分值、命中关键词。

### C. 用户说“对这篇文章感兴趣”

1. 立即写本地兴趣记录（`memory/interests/`，UTC 时间戳命名）。
2. 从文章与摘要提取候选关键词（只保留重点，最多 5 个）。
3. 用 `interest-save` 同步关键词到画像并做计数叠加（自动截断到最多 5 个）。
4. 如用户要求“只补缺失不计数叠加”，改用 `--sync-mode missing`。
5. 明确反馈：
   - 保存路径
   - 新增关键词
   - 计数+1关键词（若有）

## Output Rules

- 列表输出字段：日期、标题、分类、命中关键词、相关度、URL。
- “阅读第x篇”输出：约 500 字，重点放在技术方向，不写空泛宣传语。
- 若 x 超出范围：先提示有效范围，再等待用户重选。
- 若用户提出“今日电子信息/热门文章”，明确说明该功能已下线，并引导改为“按日期抓 latestnews”。

## References

- Web Fetch fallback method: `WEB_FETCH_FALLBACK.md`
