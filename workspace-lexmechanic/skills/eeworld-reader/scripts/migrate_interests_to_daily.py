from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
from pathlib import Path

WORKSPACE = Path(r"C:\Users\Qiang\.openclaw\workspace-lexmechanic")
INTEREST_DIR = WORKSPACE / "memory" / "interests"
ARCHIVE_ROOT = WORKSPACE / "archive"
DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_first(patterns: list[str], text: str) -> str:
    for pat in patterns:
        m = re.search(pat, text, re.M)
        if m:
            return m.group(1).strip()
    return ""


def resolve_date_token(path: Path, text: str) -> str:
    s = extract_first([
        r"^- 文章日期[:：]\s*(\d{4}-\d{2}-\d{2})",
        r"^- 记录时间\(UTC\)[:：]\s*(\d{4}-\d{2}-\d{2})",
        r"^- 记录时间（UTC）[:：]\s*(\d{4}-\d{2}-\d{2})",
    ], text)
    if s:
        return s
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", path.name)
    if m:
        return m.group(1)
    return dt.date.today().isoformat()


def resolve_title(text: str, path: Path) -> str:
    title = extract_first([
        r"^# 感兴趣文章记录\s*-\s*(.+)$",
        r"^# 感兴趣文章记.*?-\s*(.+)$",
        r"^- 来源文章[:：]\s*(.+)$",
        r"^- 主题[:：]\s*(.+)$",
    ], text)
    return title or path.stem


def resolve_url(text: str) -> str:
    return extract_first([
        r"^- URL[:：]\s*(https?://\S+)$",
        r"^- 链接[:：]\s*(https?://\S+)$",
    ], text)


def strip_root_heading(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    body = "\n".join(lines).strip()
    body = re.sub(r"(?m)^### ", "#### ", body)
    body = re.sub(r"(?m)^## ", "### ", body)
    return body.strip()


def upsert_entry(target: Path, *, title: str, url: str, source_name: str, body: str, date_token: str) -> None:
    marker = url or source_name
    start_marker = f"<!-- interest-entry: {marker} -->"
    end_marker = f"<!-- /interest-entry: {marker} -->"
    entry = [start_marker, f"## {title}", "", body.strip(), "", end_marker]
    entry_block = "\n".join(entry).rstrip() + "\n"

    if target.exists():
        text = read_text(target)
    else:
        text = f"# {date_token} 感兴趣文章\n\n"

    if start_marker in text and end_marker in text:
        pattern = re.compile(rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}\n?", re.S)
        text = pattern.sub(entry_block, text)
    else:
        if not text.endswith("\n"):
            text += "\n"
        if not text.endswith("\n\n"):
            text += "\n"
        text += entry_block + "\n"

    target.write_text(text, encoding="utf-8")


def should_skip(path: Path) -> bool:
    if DATE_FILE_RE.match(path.name):
        return True
    if path.name.startswith("感兴趣文章清单"):
        return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interest-dir", default=str(INTEREST_DIR))
    ap.add_argument("--archive-dir", default="")
    args = ap.parse_args()

    interest_dir = Path(args.interest_dir)
    ts = dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    archive_dir = Path(args.archive_dir) if args.archive_dir else (ARCHIVE_ROOT / f"interests-merge-{ts}")
    archive_dir.mkdir(parents=True, exist_ok=True)

    moved = []
    written = set()
    for path in sorted(interest_dir.glob("*.md")):
        if should_skip(path):
            continue
        text = read_text(path)
        date_token = resolve_date_token(path, text)
        title = resolve_title(text, path)
        url = resolve_url(text)
        body = strip_root_heading(text)
        target = interest_dir / f"{date_token}.md"
        upsert_entry(target, title=title, url=url, source_name=path.name, body=body, date_token=date_token)
        written.add(str(target))
        shutil.move(str(path), str(archive_dir / path.name))
        moved.append(path.name)

    print(f"archive_dir: {archive_dir}")
    print(f"moved_count: {len(moved)}")
    for name in moved:
        print(f"moved: {name}")
    print(f"written_count: {len(written)}")
    for name in sorted(written):
        print(f"written: {name}")


if __name__ == "__main__":
    main()
