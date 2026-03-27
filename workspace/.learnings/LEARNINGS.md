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
