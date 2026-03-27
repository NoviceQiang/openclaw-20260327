# EEWorld latestnews 日期抓取与阅读流程

> 本 skill 已移除“今日电子信息 / 热门文章”板块抓取。

## 当前数据入口

- 页面：`http://www.eeworld.com.cn/latestnews`
- 分页：`http://www.eeworld.com.cn/latestnews/2`、`/3` ...
- 回退可读入口：`https://r.jina.ai/http://www.eeworld.com.cn/latestnews`（分页同理）

## 当前返回条目结构

每条文章包含：
- `date`
- `title`
- `category`
- `url`
- `score`
- `matched_keywords`

## 逐篇阅读与兴趣记录

- 用户说“阅读第x篇”：
  - 按当前排序序号定位文章
  - 优先读取本地已保存文件（列表与文章缓存），缺失时再联网
  - 拉正文并输出约 500 字技术向说明

- 用户说“对这篇文章感兴趣”：
  - 写兴趣记录到 `memory/interests/`
  - 关键词只保留重点，最多 5 个
  - 同步到 `memory/eeworld-reading-profile.json` 并执行关键词计数叠加（默认）
  - 如需仅补缺失不叠加，使用 `--sync-mode missing`

建议使用：

```bash
python3 scripts/eeworld_feed.py interest-save \
  --title "..." --url "..." --summary "..." --keywords "..."
```

## 默认本地落盘

- 汇总输出（markdown + json）：`memory/eeworld-captures/`
- 原始 latestnews 页面文本：`memory/eeworld-captures/raw-latestnews/`
- 兴趣文章记录：`memory/interests/`
- 文章正文缓存：`memory/eeworld-captures/articles/`

## 推荐流程

1. 用 `latest-day` / `获取某天最新文章` 按日期抓取并排序。
2. 按用户指定序号读取正文（技术向 500 字说明）。
3. 用户确认兴趣后，调用 `interest-save` 落盘并叠加关键词计数（默认）。
