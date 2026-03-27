from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(r"C:\Users\Qiang\.openclaw\workspace-lexmechanic")
SOURCE_DIR = WORKSPACE / "memory" / "eeworld-source-code"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def iter_source_files() -> list[Path]:
    if not SOURCE_DIR.exists():
        return []
    return sorted(SOURCE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def mark_in_file(path: Path, *, url: str | None, title: str | None, interested: bool | None, interest_note: str | None) -> dict[str, Any] | None:
    data = load_json(path)
    ranked = data.get("ranked")
    if not isinstance(ranked, list):
        return None

    hit = None
    for item in ranked:
        if not isinstance(item, dict):
            continue
        if url and item.get("url") == url:
            hit = item
            break
        if title and str(item.get("title", "")).strip() == title.strip():
            hit = item
            break

    if hit is None:
        return None

    ts = datetime.now(timezone.utc).isoformat()
    hit["read"] = True
    hit["read_at"] = ts
    if interested is not None:
        hit["interested"] = interested
    if interest_note:
        hit["interest_note"] = interest_note
    data["updated_at"] = ts
    save_json(path, data)
    return {"file": str(path), "title": hit.get("title"), "url": hit.get("url"), "read_at": ts}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--title")
    ap.add_argument("--source-file", help="Optional specific source JSON file to update")
    ap.add_argument("--interested", action=argparse.BooleanOptionalAction, default=None)
    ap.add_argument("--interest-note")
    args = ap.parse_args()

    if not args.url and not args.title:
        raise SystemExit("Need --url or --title")

    files = [Path(args.source_file)] if args.source_file else iter_source_files()
    for path in files:
        if not path.exists():
            continue
        result = mark_in_file(
            path,
            url=args.url,
            title=args.title,
            interested=args.interested,
            interest_note=args.interest_note,
        )
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

    raise SystemExit("No matching article found in source JSON files")


if __name__ == "__main__":
    main()
