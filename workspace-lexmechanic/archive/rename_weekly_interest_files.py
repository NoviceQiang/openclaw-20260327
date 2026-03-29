# -*- coding: utf-8 -*-
from pathlib import Path
import re

base = Path(r"C:\Users\Qiang\.openclaw\workspace-lexmechanic\memory\interests")
legacy = {
    "2026-03-16.md","2026-03-17.md","2026-03-18.md","2026-03-19.md","2026-03-20.md",
    "2026-03-22.md","2026-03-23.md","2026-03-24.md","2026-03-25.md","2026-03-26.md",
    "2026-03-27.md","2026-03-28.md"
}

candidates = [p for p in sorted(base.glob("*.md")) if p.name not in legacy and p.name not in {"2026-03-第三周文章.md", "2026-03-第四周文章.md"}]
for p in candidates:
    txt = p.read_text(encoding="utf-8", errors="replace")
    count = txt.count("<!-- interest-entry: ")
    if count == 28:
        target = base / "2026-03-第三周文章.md"
    elif count == 58:
        target = base / "2026-03-第四周文章.md"
    else:
        continue

    if target.exists():
        existing = target.read_text(encoding="utf-8", errors="replace")
        urls = set(re.findall(r"<!-- interest-entry: (.*?) -->", existing))
        for m in re.finditer(r"<!-- interest-entry: (.*?) -->(.*?)<!-- /interest-entry: \1 -->", txt, re.S):
            if m.group(1) in urls:
                continue
            if not existing.endswith("\n\n"):
                existing += "\n\n"
            existing += m.group(0).strip() + "\n\n"
        target.write_text(existing, encoding="utf-8")
        p.unlink()
        print(f"merged into {target.name}")
    else:
        p.rename(target)
        print(f"renamed {p.name} -> {target.name}")
