from pathlib import Path
from collections import defaultdict
from datetime import date
import re

base = Path(r"C:\Users\Qiang\.openclaw\workspace-lexmechanic\memory\interests")
week_map = {1: "第一周", 2: "第二周", 3: "第三周", 4: "第四周", 5: "第五周"}
entry_re = re.compile(r"<!-- interest-entry: (.*?) -->(.*?)<!-- /interest-entry: \1 -->", re.S)
date_re = re.compile(r"文章日期[:：]\s*(\d{4}-\d{2}-\d{2})")
recorded_re_1 = re.compile(r"记录时间\(UTC\):\s*([^\n]+)")
recorded_re_2 = re.compile(r"记录时间（UTC）：\s*([^\n]+)")
weekly = defaultdict(list)
legacy_files = []

for path in sorted(base.glob("*.md")):
    if re.match(r"\d{4}-\d{2}-第[一二三四五六七八九十\d]+周文章\.md$", path.name):
        continue
    legacy_files.append(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(entry_re.finditer(text))
    if not matches:
        continue
    for m in matches:
        full = m.group(0).strip() + "\n"
        body = m.group(2)
        date_m = date_re.search(body)
        if date_m:
            d = date.fromisoformat(date_m.group(1))
        else:
            rec = recorded_re_1.search(body) or recorded_re_2.search(body)
            if not rec:
                continue
            raw = (rec.group(1) or "").strip()
            try:
                d = date.fromisoformat(raw[:10])
            except Exception:
                continue
        week_in_month = ((d.day - 1) // 7) + 1
        week_label = week_map.get(week_in_month, f"第{week_in_month}周")
        week_file = f"{d.strftime('%Y-%m')}-{week_label}文章.md"
        weekly[week_file].append(full)

created = []
for week_file, items in weekly.items():
    out = base / week_file
    existing = out.read_text(encoding="utf-8", errors="replace") if out.exists() else f"# {week_file[:-3]}\n\n"
    existing_urls = set(re.findall(r"<!-- interest-entry: (.*?) -->", existing))
    appended = 0
    for full in items:
        url_m = re.search(r"<!-- interest-entry: (.*?) -->", full)
        if not url_m:
            continue
        url = url_m.group(1)
        if url in existing_urls:
            continue
        if not existing.endswith("\n"):
            existing += "\n"
        if not existing.endswith("\n\n"):
            existing += "\n"
        existing += full + "\n"
        existing_urls.add(url)
        appended += 1
    out.write_text(existing, encoding="utf-8")
    created.append((week_file, appended))

print("迁移完成")
print("旧日文件数:", len(legacy_files))
for week_file, appended in sorted(created):
    print(f"{week_file}: 新增 {appended} 条")
