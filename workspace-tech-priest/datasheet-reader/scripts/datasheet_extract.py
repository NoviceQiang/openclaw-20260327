#!/usr/bin/env python3
"""
datasheet_extract.py - Extract structured info from electronic component datasheets (EN/CN)

Usage:
  python3 datasheet_extract.py <pdf_path> [--sections ...] [--pages 1-5,10,20-30] [--output json|markdown]

Sections:
  io          - IO pin functions, alternate mappings, pin assignment tables
  electrical  - Electrical characteristics, operating conditions, absolute maximum ratings
  notes       - Notes, cautions, warnings, important remarks marked in the datasheet
  circuit     - Recommended application circuits, typical peripheral connections
  timing      - Timing diagrams / AC characteristics
  package     - Package info, dimensions, land patterns
  all         - All of the above
"""

import sys
import os
import json
import re
import argparse

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip3 install pdfplumber", file=sys.stderr)
    sys.exit(1)


def parse_page_range(pages_str, total_pages):
    if not pages_str:
        return list(range(total_pages))
    pages = set()
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start) - 1, min(int(end), total_pages)))
        else:
            p = int(part) - 1
            if 0 <= p < total_pages:
                pages.add(p)
    return sorted(pages)


# ── keyword banks (EN + CN) ──────────────────────────────────────

KW_IO = [
    # English
    "pin assignment", "pin description", "pin configuration", "pin out",
    "pin function", "pin definition", "alternate function", "multiplexing",
    "pinout diagram", "signal name", "pin map",
    # Chinese
    "引脚定义", "引脚排列", "引脚功能", "引脚配置", "引脚分配",
    "复用功能", "引脚描述", "引脚分配图",
]

KW_ELECTRICAL = [
    # English
    "electrical characteristics", "absolute maximum rating", "absolute maximum",
    "recommended operating condition", "operating conditions",
    "dc characteristics", "ac characteristics",
    "power consumption", "supply current", "quiescent current",
    "voltage characteristics", "current characteristics",
    "input/output characteristics", "i/o characteristics",
    "power supply", "supply voltage",
    # Chinese
    "电气特性", "绝对最大额定值", "推荐工作条件", "工作条件",
    "供电电流", "电源电流", "供电电压", "端口特性",
    "直流特性", "交流特性", "功耗",
]

KW_NOTES = [
    # English — these are inline markers
    "note:", "note :", "notes:", "note1:", "note2:", "note3:",
    "caution:", "caution :", "warning:", "warning :",
    "important:", "important !", "important notice",
    "please note", "be careful", "attention:",
    "note that", "note -", "note –",
    # Chinese
    "注意：", "注意事项", "注意:", "注意：",
    "警告", "重要提示", "注:", "注：",
    "注1:", "注2:", "注3:", "注4:", "注5:",
]

KW_CIRCUIT = [
    # English
    "typical application", "application circuit", "recommended circuit",
    "recommended application", "schematic", "reference design",
    "typical connection", "typical schematic",
    # Chinese
    "推荐电路", "典型应用电路", "推荐应用电路", "外围电路",
    "参考电路", "应用电路图", "参考设计",
]

KW_TIMING = [
    # English
    "timing diagram", "timing chart", "ac characteristics",
    "bus timing", "signal timing", "clock timing",
    # Chinese
    "时序图", "时序特性", "交流特性", "总线时序",
]

KW_PACKAGE = [
    # English — require multi-word phrases to avoid generic "package" hits
    "package information", "package outline", "package dimensions",
    "mechanical data", "land pattern", "soldering footprint",
    "thermal resistance", "marking information", "package drawing",
    "package type", "package thermal",
    # Chinese
    "封装信息", "封装尺寸", "焊盘示意图", "丝印说明",
    "机械数据", "热阻",
]


# ── core extraction ──────────────────────────────────────────────

def find_relevant_pages(pdf, keywords):
    """Scan all pages; return indices whose text matches any keyword."""
    relevant = []
    for i in range(len(pdf.pages)):
        text = (pdf.pages[i].extract_text() or "").lower()
        for kw in keywords:
            if kw in text:
                relevant.append(i)
                break
    return relevant


def build_page_entry(pdf, idx, include_text=True, include_tables=True, text_preview_chars=None):
    entry = {"page": idx + 1}
    if include_text:
        text = pdf.pages[idx].extract_text() or ""
        if text_preview_chars:
            entry["text_preview"] = text.strip()[:text_preview_chars]
        entry["text"] = text.strip()
    if include_tables:
        tables = pdf.pages[idx].extract_tables()
        if tables:
            entry["tables"] = []
            for t_idx, table in enumerate(tables):
                if table and len(table) > 1:
                    entry["tables"].append({"index": t_idx, "rows": table})
    return entry


def extract_section(pdf, page_indices, keywords):
    """Generic section extractor: find pages matching keywords, return full content."""
    matched = find_relevant_pages(pdf, keywords)
    # Use matched pages if any; otherwise fall back to provided page_indices
    target = matched if matched else page_indices
    result = []
    for i in target:
        entry = build_page_entry(pdf, i)
        if entry.get("text") or entry.get("tables"):
            result.append(entry)
    return result


def extract_notes(pdf, page_indices, keywords):
    """Extract pages/lines that contain note/warning markers."""
    # First pass: find pages containing note markers
    note_pages = []
    for i in range(len(pdf.pages)):
        text = (pdf.pages[i].extract_text() or "").lower()
        for kw in keywords:
            if kw in text:
                note_pages.append(i)
                break

    result = []
    for i in note_pages:
        entry = build_page_entry(pdf, i)
        if entry.get("text") or entry.get("tables"):
            result.append(entry)
    return result


# ── output formatters ────────────────────────────────────────────

SECTION_META = {
    "io":         ("IO Pin Functions",         "IO引脚功能"),
    "electrical": ("Electrical Characteristics","电气特性"),
    "notes":      ("Notes & Warnings",         "注意事项与警告"),
    "circuit":    ("Recommended Circuits",      "推荐外围电路"),
    "timing":     ("Timing Characteristics",    "时序特性"),
    "package":    ("Package Information",       "封装信息"),
}


def to_markdown(data, sections):
    lines = []
    lines.append(f"# Datasheet Extraction: {data['source']}")
    lines.append(f"- Pages: {data['total_pages']}")
    lines.append(f"- Range: {data.get('page_range', 'all')}")
    lines.append(f"- Sections: {', '.join(sections)}")
    lines.append("")

    for section in sections:
        if section not in data.get("sections", {}):
            continue
        sec_data = data["sections"][section]
        en_title, _ = SECTION_META.get(section, (section, section))
        lines.append(f"## {en_title}")
        lines.append("")

        if not sec_data:
            lines.append("_No content found._")
            lines.append("")
            continue

        for item in sec_data:
            lines.append(f"### Page {item['page']}")
            lines.append("")
            if "text" in item:
                lines.append(item["text"])
                lines.append("")
            if "tables" in item:
                for t in item["tables"]:
                    lines.append(f"**Table {t['index'] + 1}:**")
                    lines.append("")
                    rows = t["rows"]
                    if rows and len(rows) > 0:
                        header = [str(c).replace("\n", " ") if c else "" for c in rows[0]]
                        lines.append("| " + " | ".join(header) + " |")
                        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                        for row in rows[1:]:
                            cells = [str(c).replace("\n", " ") if c else "" for c in row]
                            lines.append("| " + " | ".join(cells) + " |")
                    lines.append("")

    return "\n".join(lines)


# ── main ─────────────────────────────────────────────────────────

ALL_SECTIONS = ["io", "electrical", "notes", "circuit", "timing", "package"]

KW_MAP = {
    "io":         KW_IO,
    "electrical": KW_ELECTRICAL,
    "notes":      KW_NOTES,
    "circuit":    KW_CIRCUIT,
    "timing":     KW_TIMING,
    "package":    KW_PACKAGE,
}


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured info from electronic component datasheets (EN/CN)")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--sections", default="all",
                        help=f"Sections to extract (comma-separated): {','.join(ALL_SECTIONS)},all")
    parser.add_argument("--pages", default=None,
                        help="Page range, e.g. '1-5,10,20-30'. Default: all")
    parser.add_argument("--output", default="json", choices=["json", "markdown"],
                        help="Output format")
    parser.add_argument("--output-file", default=None,
                        help="Output file path (default: stdout)")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"ERROR: File not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    pdf = pdfplumber.open(args.pdf_path)
    total_pages = len(pdf.pages)
    page_indices = parse_page_range(args.pages, total_pages)

    sections = [s.strip() for s in args.sections.split(",")]
    if "all" in sections:
        sections = ALL_SECTIONS

    result = {
        "source": os.path.basename(args.pdf_path),
        "total_pages": total_pages,
        "page_range": args.pages or "all",
        "sections": {}
    }

    for section in sections:
        kw = KW_MAP.get(section, [])
        if section == "notes":
            result["sections"]["notes"] = extract_notes(pdf, page_indices, kw)
        else:
            result["sections"][section] = extract_section(pdf, page_indices, kw)

    pdf.close()

    if args.output == "markdown":
        output = to_markdown(result, sections)
    else:
        output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Result written to: {args.output_file}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
