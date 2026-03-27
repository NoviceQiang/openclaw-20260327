from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WORKSPACE = Path(r"C:\Users\Qiang\.openclaw\workspace-lexmechanic")
SOURCE_DIR = WORKSPACE / "memory" / "eeworld-source-code"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_source_file(date_hint: str | None, explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise SystemExit(f"Source file not found: {p}")
        return p

    files = sorted(SOURCE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise SystemExit("No source JSON files found")

    if date_hint:
        for p in files:
            if date_hint in p.name:
                return p
        raise SystemExit(f"No source JSON file matched date hint: {date_hint}")

    return files[0]


def extract_unread(data: dict[str, Any]) -> list[dict[str, Any]]:
    ranked = data.get("ranked")
    if not isinstance(ranked, list):
        return []

    unread: list[dict[str, Any]] = []
    for idx, item in enumerate(ranked, start=1):
        if not isinstance(item, dict):
            continue
        if item.get("read") is True:
            continue
        unread.append(
            {
                "index": idx,
                "date": item.get("date"),
                "category": item.get("category"),
                "title": item.get("title"),
                "url": item.get("url"),
                "score": item.get("score"),
                "matched_keywords": item.get("matched_keywords", []),
            }
        )
    return unread


def render_markdown(path: Path, unread: list[dict[str, Any]]) -> str:
    lines = [
        f"# 未读文章列表",
        "",
        f"- source: {path}",
        f"- unread_count: {len(unread)}",
        "",
    ]
    for item in unread:
        kw = "、".join(item.get("matched_keywords") or [])
        score = item.get("score")
        lines.append(f"{item['index']}. [{item.get('category')}] {item.get('title')}")
        if score is not None:
            lines.append(f"   - 相关度: {score}")
        if kw:
            lines.append(f"   - 命中关键词: {kw}")
        if item.get("url"):
            lines.append(f"   - 链接: {item['url']}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="Date hint like 2026-03-20")
    ap.add_argument("--source-file", help="Explicit source JSON path")
    ap.add_argument("--format", choices=["json", "markdown"], default="json")
    args = ap.parse_args()

    path = find_source_file(args.date, args.source_file)
    data = load_json(path)
    unread = extract_unread(data)

    payload = {
        "source_file": str(path),
        "unread_count": len(unread),
        "items": unread,
    }
    if args.format == "json":
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        text = render_markdown(path, unread)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text + "\n")
    except Exception:
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
