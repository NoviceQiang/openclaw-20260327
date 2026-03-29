from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional

WORKSPACE = Path(r"C:\Users\Qiang\.openclaw\workspace-lexmechanic")
INTEREST_DIR = WORKSPACE / "memory" / "interests"


@dataclass
class InterestNote:
    path: str
    title: str
    recorded_at: Optional[str]
    article_date: Optional[str]
    score: Optional[str]
    url: Optional[str]
    summary: str
    keywords: List[str]
    focus: List[str]
    discussions: List[str]
    week: str


def iso_week_bounds(iso_week: str) -> tuple[date, date]:
    year_s, week_s = iso_week.split("-W")
    d = date.fromisocalendar(int(year_s), int(week_s), 1)
    return d, d + timedelta(days=6)


def week_from_date(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def parse_time_to_week(text: str) -> Optional[str]:
    text = text.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(text, fmt)
            return week_from_date(dt.date())
        except ValueError:
            continue
    return None


def extract_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", re.M | re.S)
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def extract_bullets(text: str) -> List[str]:
    out: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            out.append(line[2:].strip())
    return out


def parse_entry(raw: str, path: Path) -> Optional[InterestNote]:
    title = ""
    m = re.search(r"^##\s+(.+)$", raw, re.M)
    if m:
        title = m.group(1).strip()
    if not title:
        m = re.search(r"来源文章[:：]\s*(.+)", raw)
        if m:
            title = m.group(1).strip()
    if not title:
        m = re.search(r"主题[:：]\s*(.+)", raw)
        if m:
            title = m.group(1).strip()

    recorded_at = None
    for pat in [r"记录时间\(UTC\):\s*(.+)", r"记录时间（UTC）：\s*(.+)"]:
        m = re.search(pat, raw)
        if m:
            recorded_at = m.group(1).strip()
            break

    week = parse_time_to_week(recorded_at) if recorded_at else None
    if not week:
        return None

    article_date = None
    m = re.search(r"文章日期[:：]\s*(.+)", raw)
    if m:
        article_date = m.group(1).strip()

    score = None
    for pat in [r"相关度分值[:：]\s*(.+)", r"相关度[:：]\s*(.+)"]:
        m = re.search(pat, raw)
        if m:
            score = m.group(1).strip()
            break

    url = None
    for pat in [r"URL[:：]\s*(.+)", r"链接[:：]\s*(.+)"]:
        m = re.search(pat, raw)
        if m:
            url = m.group(1).strip()
            break

    summary = extract_section(raw, "技术向摘要")

    keywords: List[str] = []
    kw_block = extract_section(raw, "关键词")
    if kw_block:
        for line in kw_block.splitlines():
            line = line.strip()
            if "新增候选关键词" in line:
                _, rhs = re.split(r"[:：]", line, maxsplit=1)
                keywords.extend([x.strip() for x in rhs.split("、") if x.strip()])
    if not keywords:
        m = re.search(r"命中关键词[:：]\s*(.+)", raw)
        if m:
            keywords.extend([x.strip() for x in m.group(1).split("、") if x.strip()])

    focus = extract_bullets(extract_section(raw, "本篇关注重点"))
    if not focus:
        focus = extract_bullets(extract_section(raw, "关注点"))
    if not focus:
        focus = extract_bullets(extract_section(raw, "主人关注点（本次）"))
    if not focus:
        focus = [re.sub(r"^\d+\.\s*", "", line.strip()) for line in extract_section(raw, "关注点").splitlines() if line.strip()]
    if not focus:
        focus = [re.sub(r"^\d+\.\s*", "", line.strip()) for line in extract_section(raw, "主人关注点（本次）").splitlines() if line.strip()]

    discussions = [line.strip() for line in extract_section(raw, "讨论记录（用户提问与回答）").splitlines() if line.strip()]

    return InterestNote(
        path=str(path),
        title=title,
        recorded_at=recorded_at,
        article_date=article_date,
        score=score,
        url=url,
        summary=summary,
        keywords=keywords,
        focus=focus,
        discussions=discussions,
        week=week,
    )


def parse_note(path: Path) -> List[InterestNote]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    notes: List[InterestNote] = []
    matches = list(re.finditer(r"<!-- interest-entry: (.*?) -->(.*?)<!-- /interest-entry: \1 -->", raw, re.S))
    if matches:
        for m in matches:
            note = parse_entry(m.group(2), path)
            if note:
                notes.append(note)
        return notes

    single = parse_entry(raw, path)
    return [single] if single else []


def collect_notes(target_week: str) -> List[InterestNote]:
    notes: List[InterestNote] = []
    if not INTEREST_DIR.exists():
        return notes
    for path in sorted(INTEREST_DIR.glob("*.md")):
        for note in parse_note(path):
            if note and note.week == target_week:
                notes.append(note)
    return notes


def to_markdown(target_week: str, notes: List[InterestNote]) -> str:
    start, end = iso_week_bounds(target_week)
    lines = [
        f"# {target_week} interest sources",
        "",
        f"- period: {start.isoformat()} ~ {end.isoformat()}",
        f"- note_count: {len(notes)}",
        "",
    ]
    for idx, note in enumerate(notes, start=1):
        lines.append(f"## {idx}. {note.title}")
        lines.append(f"- path: {note.path}")
        if note.url:
            lines.append(f"- url: {note.url}")
        if note.keywords:
            lines.append(f"- keywords: {', '.join(note.keywords)}")
        if note.summary:
            lines.append(f"- summary: {note.summary}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--week", help="ISO week like 2026-W12")
    g.add_argument("--date", help="Date like 2026-03-22")
    ap.add_argument("--format", choices=["json", "markdown"], default="json")
    ap.add_argument("--output", help="Optional output path")
    args = ap.parse_args()

    if args.week:
        target_week = args.week
    else:
        d = datetime.strptime(args.date, "%Y-%m-%d").date()
        target_week = week_from_date(d)

    notes = collect_notes(target_week)
    start, end = iso_week_bounds(target_week)
    payload = {
        "week": target_week,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "note_count": len(notes),
        "notes": [asdict(n) for n in notes],
    }

    if args.format == "json":
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        text = to_markdown(target_week, notes)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout.write(text + "\n")
        except Exception:
            sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
