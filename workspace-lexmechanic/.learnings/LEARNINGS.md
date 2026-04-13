## [LRN-20260321-001] correction

**Logged**: 2026-03-21T10:14:00+08:00
**Priority**: high
**Status**: pending
**Area**: docs

### Summary
EEWorld 阅读流程被用户纠正：只有用户明确表示“感兴趣”的文章，才应提取最多 5 个关键词并写入本地画像；单纯“阅读第x篇”不应自动落盘关键词。

### Details
在用户说“我要看3-20号第五篇文章”后，错误地把该文章的 5 个关键词写入了 `memory/eeworld-reading-profile.json`，并新增了一条 `articles` 记录与一份 `memory/interests/` 文件。随后用户明确更正规则：关键词提取与计数只适用于“感兴趣”的文章。

### Suggested Action
1. 回滚本次 TI 边缘 AI MCU 文章的 interest 记录、profile 计数和 article 项。
2. 保留阅读摘要输出逻辑，但将关键词落盘动作改为仅在用户明确表达“感兴趣”时执行。
3. 后续处理“阅读第x篇”请求时，不再默认更新 profile。

### Metadata
- Source: user_feedback
- Related Files: MEMORY.md, memory/2026-03-21.md, memory/eeworld-reading-profile.json, memory/interests/2026-03-21T02-12-11Z-ti-edge-ai-mcu.md
- Tags: eeworld, correction, keyword-counting

---

## [LRN-20260321-002] correction

**Logged**: 2026-03-21T12:53:00+08:00
**Priority**: high
**Status**: pending
**Area**: docs

### Summary
用户将项目方向纠正为“电子信息获取”，目标是订阅并总结电子技术文章，而不是“电子信号获取”。

### Details
在用户要求“进行开发电子信息获取项目”后，错误将其理解为信号采集/ADC/采样链路类工程，并创建了 `projects/electronic-signal-acquisition/` 骨架。这与用户真实意图不符。正确方向应是面向文章/资讯源的订阅、抓取、去重、排序、摘要、归档与索引系统。

### Suggested Action
1. 停止沿“信号采集”方向展开。
2. 新建“电子信息获取”项目骨架，围绕订阅源、抓取、去重、排序、摘要、归档、索引设计。
3. 更新 `memory/projects.md` 与每日日志，记录正确项目方向。

### Metadata
- Source: user_feedback
- Related Files: projects/electronic-signal-acquisition/README.md, projects/electronic-signal-acquisition/docs/requirements.md, memory/projects.md, memory/2026-03-21.md
- Tags: correction, project-scope, electronics, information-acquisition

---

## [LRN-20260321-001] correction

**Logged**: 2026-03-21T07:52:30Z
**Priority**: medium
**Status**: promoted
**Area**: docs

### Summary
User clarified that the issue with answers was loose spacing and overly relaxed visual layout, not insufficient concision or excessive content.

### Details
I over-corrected by shifting to shorter content, while the user's actual preference was to keep the substance but tighten formatting: fewer blank lines, fewer micro-headings, denser structure.

### Suggested Action
Keep content richness when useful, but compress visual layout and grouping in future replies.

### Metadata
- Source: user_feedback
- Related Files: MEMORY.md, memory/2026-03-21.md
- Tags: style, formatting, brevity, correction

### Resolution
- **Resolved**: 2026-03-21T07:52:30Z
- **Notes**: Promoted to workspace memory and daily log.

---
## [LRN-20260410-001] correction

**Logged**: 2026-04-10T01:16:59Z
**Priority**: high
**Status**: pending
**Area**: docs

### Summary
interest-save 的“本篇关注重点”自动细化误触发，导致将不相关的“六层测试项目与指标”插入 ATE 文章记录。

### Details
用户明确给出的关注重点只有 ATE 三类核心卡（V/I、DPS、PE）的职责与取舍。但落盘结果触发了自动“全链路细化”模板，写入了 Camera/LiDAR/IMU 等与文章不相关内容。根因是触发条件过宽：`FULL_CHAIN_HINT_TOKENS` 含“供电/执行”等泛词，且命中任一词即触发。

### Suggested Action
1. 收紧触发词：仅保留“全链路/测试项目与指标/感知层/传输层/决策与控制层/执行层/供电与热管理/功能安全与运维”等明确语义。
2. 触发阈值调整为至少命中 2 个特征词。
3. 对已写错条目立即原地修正后再反馈用户。

### Metadata
- Source: user_feedback
- Related Files: skills/eeworld-reader/scripts/eeworld_feed.py, memory/interests/2026-04-第一周文章.md
- Tags: correction, interest-save, false-positive, focus-points

---
