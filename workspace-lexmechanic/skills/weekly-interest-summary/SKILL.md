---
name: weekly-interest-summary
description: "Summarize one ISO week of interest-marked notes from memory/interests/*.md into a single weekly synthesis file at memory/weekly/YYYY-Www.md. Use when the user asks to create, update, refine, or finalize a weekly summary of previously marked 感兴趣 notes, such as 做本周总结, 把这一周 interests 汇总, 更新 2026-W12 周总结, or 把感兴趣文章做周报. Manual workflow only: first create a local draft, then iterate with the user on the same file until satisfied; do not create separate draft/final files."
---

# Weekly Interest Summary

## Overview
Create one canonical weekly summary from `memory/interests/*.md` only. Interest notes are now stored as weekly merged files rather than daily files, so collection/parsing must support multiple entries inside one weekly note file. Keep note-level substance, group similar topics when helpful, and avoid arbitrary deletion. Write the first draft to `memory/weekly/YYYY-Www.md`, then keep refining that same file through user Q&A until the user is satisfied.

This skill also supports read-status bookkeeping by writing back to source list JSON files under `memory/eeworld-source-code/*.json`. Use it when the user wants to mark an article as read, list unread items more accurately, or keep weekly summaries aware of read/interested state.

## Workflow Decision Tree
- If the user says “这周 / 本周”, use the current ISO week in `Asia/Shanghai`.
- If the user gives a date or week label, resolve it to ISO week `YYYY-Www`.
- If `memory/weekly/YYYY-Www.md` does not exist, create a **draft**.
- If it already exists, update the **same file** in place.
- If the user is still discussing details, keep the file in draft state.
- If the user says the summary is good enough, convert the same file to final form; do not create a second file.

## Step 1 — Resolve the target week
Use ISO week numbering (Monday–Sunday) in `Asia/Shanghai`.

Typical cases:
- “做本周总结” → current ISO week
- “总结 2026-W12” → exact week
- “总结 3 月 22 日那周” → resolve the date to its ISO week

Canonical output path:
- `memory/weekly/YYYY-Www.md`

## Step 2 — Collect source notes
Run the helper script first:

```bash
python skills/weekly-interest-summary/scripts/collect_weekly_interest.py --week 2026-W12 --format json
```

Useful variants:

```bash
python skills/weekly-interest-summary/scripts/collect_weekly_interest.py --date 2026-03-22 --format json
python skills/weekly-interest-summary/scripts/collect_weekly_interest.py --week 2026-W12 --format markdown
python skills/weekly-interest-summary/scripts/collect_weekly_interest.py --week 2026-W12 --format json --output memory/weekly/2026-W12.sources.json
```

The script gives you:
- the resolved ISO week and local date range
- all matching `memory/interests/*.md` notes for that week
- parsed titles, URLs, summaries, keywords, focus points, and discussion blocks
- keyword frequency hints for grouping

If you need the exact writing shape, read `references/weekly-format.md`.

## Step 3 — Write the initial draft
Create `memory/weekly/YYYY-Www.md` and keep it as the canonical file.

Draft rules:
- Synthesize; do not merely concatenate raw notes.
- Do **not** arbitrarily delete material from source notes.
- If themes are similar, place them in the same section, but preserve note-level distinctions.
- Preserve traceability by keeping source note titles, article links, or source file references where useful.
- Carry forward user-confirmed judgments and follow-up Q&A from the source notes.

Default drafting order:
1. Week header and status (`初稿`)
2. Scope and source count
3. Theme groups
4. Per-theme retained details
5. Cross-note technical judgments formed this week
6. Open questions / items to refine with the user
7. Source index

## Step 4 — Iterate with the user on the same file
After saving the draft locally, continue the conversation and patch the same weekly file.

What to add during iteration:
- clarified technical judgments
- distinctions between similar topics
- user-emphasized priorities
- follow-up explanations that improve later reuse
- missing links between notes

Do not:
- create `draft` / `final` sibling files
- create timestamped week files
- silently remove source content the user may still value

## Step 5 — Finalize
When the user says the weekly summary is satisfactory:
- keep the same file path
- update the status from draft to final
- tighten wording if needed, but preserve substance
- make sure the file remains useful as a future reference document, not just a chat recap

## Read-status writeback
When the user says things like:
- “标记我读过的文章”
- “把第 4 篇标记为已读”
- “这篇我看过了”

write the read state back to the matching source list JSON in `memory/eeworld-source-code/*.json`.

Also treat **actually reading a single article** as an implicit read event. Once the assistant has fetched and summarized a specific article, write back `read: true` for that item even if the user never explicitly says “标记已读”, and even if the user does not mark it as interested.

Use:

```bash
python skills/weekly-interest-summary/scripts/mark_read_in_source.py --url "<ARTICLE_URL>"
```

Or, when URL is not convenient:

```bash
python skills/weekly-interest-summary/scripts/mark_read_in_source.py --title "<ARTICLE_TITLE>"
```

Behavior:
- set `read: true`
- set `read_at: <ISO timestamp>`
- optionally set `interested: true/false`
- optionally set `interest_note: <path>`

If the exact source file is already known, prefer passing `--source-file` for deterministic updates.

## List unread articles
When the user asks things like:
- “列出我没看的文章”
- “3-20 文章列表里哪些还没看”
- “列未读文章”

list unread items directly from `memory/eeworld-source-code/*.json` instead of inferring from chat history.

Use:

```bash
python skills/weekly-interest-summary/scripts/list_unread_from_source.py --date 2026-03-20 --format markdown
```

Or, for a known file:

```bash
python skills/weekly-interest-summary/scripts/list_unread_from_source.py --source-file "memory/eeworld-source-code/2026-03-21T06-52-59Z-latest-day-2026-03-20.json" --format markdown
```

Rules:
- Keep the original ranked order.
- Only treat items with `read: true` as read.
- Everything else remains unread.
- Prefer source JSON over conversational memory when the user asks for unread lists.

## Output quality rules
- Prefer structured synthesis over raw accumulation.
- Preserve unique points even when grouping similar themes.
- Treat repeated themes as a signal; summarize the common thread, then keep article-specific deltas.
- Keep future reuse in mind: the file should help with later recall, pattern extraction, and follow-up research.
- When uncertain whether to merge two points, keep them separate under the same theme rather than collapsing them too aggressively.

## Resources
- `scripts/collect_weekly_interest.py` — collect and normalize one week of interest notes
- `references/weekly-format.md` — recommended weekly file structure and update rules
