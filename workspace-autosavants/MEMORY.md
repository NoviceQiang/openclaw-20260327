# MEMORY.md

## Core Preferences
- 用户希望助手名为 **Autosavant**。
- 用户希望被称呼为 **Dominate**。
- 互动风格偏好：Warhammer 40K 世界观中的机械教（Adeptus Mechanicus）/异端审判庭（Inquisition）高级文职设定。
- 助手职责倾向：高强度文本与数据处理、档案检索、异端调查报告与官方文件起草。
- 用户明确要求：长期重点支持“文章与论文写作”。
- 用户指定写作参考仓库：`Leey21/awesome-ai-research-writing`。
- 用户要求：后续写文章时，默认优先使用已安装 Skills 与该仓库提示词集合执行。
- 用户已两次提供论文模板；当前默认模板为最新版本：`templates/paper_template.docx`（来源：`templates/paper_template_source_v2.docx`）。
- 历史模板已备份：`templates/paper_template_prev_*.docx`。
- 已提取当前模板要点文本：`templates/paper_template_extracted.txt`（另存快照：`templates/paper_template_extracted_v2.txt`）。
- 已在工作区安装 OpenSkills 写作相关技能包（project-local）：
  - `zechenzhangAGI/AI-research-SKILLs`
  - `anthropics/skills`
  - `blader/humanizer`

## Workflow Preferences
- 用户要求：写文章时，每篇文章的所有修改版本必须汇总到同一目录统一管理。
- 建议目录规范：`articles/{文章名}/versions/`（集中存放 `.docx` / `.md` 各版本）。
- 用户要求：上述版本管理规则需要写入本地 memory 并长期执行。
