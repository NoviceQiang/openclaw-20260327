#!/usr/bin/env python3
"""
datasheet_index.py - Parse raw extraction into structured, searchable index

Usage:
  python3 datasheet_index.py <raw_json_or_pdf> [--part HC32L130F8UA] [--output-dir ./index]

Takes the JSON output from datasheet_extract.py and parses it into:
  - index.json: structured metadata (pins, electrical params, notes, circuits)
  - searchable flat index for quick lookups
"""

import sys
import os
import json
import re
import argparse

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


# ── Pin table parser ─────────────────────────────────────────────

def parse_pin_tables(tables):
    """Parse pin function tables into structured list of pin entries."""
    pins = []
    for table_block in tables:
        rows = table_block.get("rows", [])
        if not rows or len(rows) < 2:
            continue

        # Try to detect column structure
        # Common patterns: [Pin#, Name, Type, I/O, Function, Alternate]
        header = [str(c).replace("\n", " ").strip() if c else "" for c in rows[0]]

        for row in rows[1:]:
            cells = [str(c).replace("\n", " ").strip() if c else "" for c in row]
            if not any(cells):
                continue

            pin_entry = {
                "raw": cells,
                "page": table_block.get("page"),
            }

            # Try to extract pin name and functions
            # Heuristic: find cells with known pin name patterns
            for cell in cells:
                cell_upper = cell.upper().strip()
                # Match GPIO pin names: PA0, PB12, PC15, PD00 etc.
                if re.match(r'^P[A-Z]\d{1,2}$', cell_upper):
                    pin_entry["pin_name"] = cell_upper
                # Match power pins
                elif cell_upper in ("VCC", "VDD", "VDDA", "AVCC", "DVCC",
                                    "GND", "VSS", "AVSS", "DVSS",
                                    "VBAT", "VCAP", "VREF", "AREF"):
                    pin_entry["pin_name"] = cell_upper
                # Match reset
                elif cell_upper in ("RESET", "RESETB", "NRST", "RST"):
                    pin_entry["pin_name"] = cell_upper

            # Collect all non-empty function strings
            funcs = [c for c in cells if c and len(c) > 1]
            pin_entry["functions"] = funcs
            pins.append(pin_entry)

    return pins


# ── Electrical params parser ─────────────────────────────────────

def parse_electrical_params(text):
    """Extract key-value electrical parameters from text."""
    params = []

    # Pattern: "Parameter description  min  typ  max  unit"
    # Common in tables: symbol | description | min | typ | max | unit
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for voltage/current specs: e.g. "VCC = 1.8V to 5.5V"
        vm = re.search(r'(V\w*)\s*=\s*([\d.]+)\s*[Vv]\s*(?:to|~|–|-)\s*([\d.]+)\s*[Vv]', line)
        if vm:
            params.append({
                "param": vm.group(1),
                "min": float(vm.group(2)),
                "max": float(vm.group(3)),
                "unit": "V",
                "source_line": line[:200]
            })

        # Look for current specs: e.g. "ICC = 10mA"
        cm = re.search(r'(I\w*)\s*=\s*([\d.]+)\s*(mA|uA|µA|A)', line)
        if cm:
            params.append({
                "param": cm.group(1),
                "value": float(cm.group(2)),
                "unit": cm.group(3),
                "source_line": line[:200]
            })

        # Absolute max patterns: "VCC - VSS  -0.3  5.5  V"
        am = re.search(r'(V\w*|I\w*)\s*.*?\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(V|mA|uA|µA|A|℃|°C)', line)
        if am and abs(float(am.group(2))) < 1000 and abs(float(am.group(3))) < 1000:
            params.append({
                "param": am.group(1),
                "min": float(am.group(2)),
                "max": float(am.group(3)),
                "unit": am.group(4),
                "source_line": line[:200]
            })

    return params


# ── Notes parser ─────────────────────────────────────────────────

NOTE_PATTERN = re.compile(
    r'((?:Note|Caution|Warning|Important|注意|注)\s*[:：\-–]?\s*\d*[.:：]?\s*.+)',
    re.IGNORECASE
)

def extract_note_lines(text, page_num):
    """Extract individual note/warning lines from page text."""
    notes = []
    lines = text.split("\n")
    buffer = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                notes.append({"page": page_num, "text": buffer.strip(), "type": classify_note(buffer)})
                buffer = ""
            continue

        # New note starts
        if NOTE_PATTERN.match(stripped):
            if buffer:
                notes.append({"page": page_num, "text": buffer.strip(), "type": classify_note(buffer)})
            buffer = stripped
        elif buffer:
            # Continuation of previous note
            buffer += " " + stripped
        # else: regular content, skip

    if buffer:
        notes.append({"page": page_num, "text": buffer.strip(), "type": classify_note(buffer)})

    return notes


def classify_note(text):
    text_lower = text.lower()
    if any(w in text_lower for w in ("caution", "警告")):
        return "caution"
    elif any(w in text_lower for w in ("warning", "警告")):
        return "warning"
    elif any(w in text_lower for w in ("important", "重要")):
        return "important"
    return "note"


# ── Main index builder ──────────────────────────────────────────

def build_index(raw_data, part_name=None):
    """Build structured index from raw extraction data."""
    source = raw_data.get("source", "unknown")
    sections = raw_data.get("sections", {})

    index = {
        "source": source,
        "part": part_name or os.path.splitext(source)[0],
        "total_pages": raw_data.get("total_pages", 0),
        "pins": [],
        "electrical_params": [],
        "notes": [],
        "circuits": [],
        "timing": [],
        "package": [],
        "pin_pages": [],
        "electrical_pages": [],
        "circuit_pages": [],
        "timing_pages": [],
        "package_pages": [],
    }

    # Parse pins
    if "io" in sections:
        io_data = sections["io"]
        all_tables = []
        for item in io_data:
            if "tables" in item:
                for t in item["tables"]:
                    t["page"] = item["page"]
                    all_tables.append(t)
            index["pin_pages"].append(item["page"])
        index["pins"] = parse_pin_tables(all_tables)

    # Parse electrical
    if "electrical" in sections:
        for item in sections["electrical"]:
            index["electrical_pages"].append(item["page"])
            if "text" in item:
                params = parse_electrical_params(item["text"])
                index["electrical_params"].extend(params)

    # Parse notes
    if "notes" in sections:
        for item in sections["notes"]:
            if "text" in item:
                n = extract_note_lines(item["text"], item["page"])
                index["notes"].extend(n)

    # Parse circuits
    if "circuit" in sections:
        for item in sections["circuit"]:
            index["circuit_pages"].append(item["page"])
            if "text" in item:
                index["circuits"].append({
                    "page": item["page"],
                    "description": item["text"][:500]
                })

    # Preserve timing/package text for retrieval-oriented indexing
    if "timing" in sections:
        for item in sections["timing"]:
            index["timing_pages"].append(item["page"])
            if "text" in item:
                index["timing"].append({
                    "page": item["page"],
                    "description": item["text"][:500]
                })

    if "package" in sections:
        for item in sections["package"]:
            index["package_pages"].append(item["page"])
            if "text" in item:
                index["package"].append({
                    "page": item["page"],
                    "description": item["text"][:500]
                })

    return index


def main():
    parser = argparse.ArgumentParser(description="Build structured index from datasheet extraction")
    parser.add_argument("input", help="Raw JSON from datasheet_extract.py, or PDF path")
    parser.add_argument("--part", default=None, help="Part name override")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    parser.add_argument("--output", default="json", choices=["json", "markdown"])
    args = parser.parse_args()

    if args.input.endswith(".json"):
        with open(args.input, "r", encoding="utf-8") as f:
            raw = json.load(f)
    elif args.input.endswith(".pdf"):
        if pdfplumber is None:
            print("ERROR: pdfplumber required for direct PDF input", file=sys.stderr)
            sys.exit(1)
        # Run extraction inline
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from datasheet_extract import main as extract_main
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        tmp.close()
        # Re-run extraction
        pdf = pdfplumber.open(args.input)
        from datasheet_extract import (parse_page_range, extract_section, extract_notes,
                                        KW_IO, KW_ELECTRICAL, KW_NOTES, KW_CIRCUIT,
                                        KW_TIMING, KW_PACKAGE, ALL_SECTIONS)
        total = len(pdf.pages)
        pages = list(range(total))
        raw = {
            "source": os.path.basename(args.input),
            "total_pages": total,
            "page_range": "all",
            "sections": {
                "io": extract_section(pdf, pages, KW_IO),
                "electrical": extract_section(pdf, pages, KW_ELECTRICAL),
                "notes": extract_notes(pdf, pages, KW_NOTES),
                "circuit": extract_section(pdf, pages, KW_CIRCUIT),
                "timing": extract_section(pdf, pages, KW_TIMING),
                "package": extract_section(pdf, pages, KW_PACKAGE),
            }
        }
        pdf.close()
    else:
        print("ERROR: Input must be .json or .pdf", file=sys.stderr)
        sys.exit(1)

    index = build_index(raw, part_name=args.part)

    os.makedirs(args.output_dir, exist_ok=True)

    if args.output == "json":
        out_path = os.path.join(args.output_dir, f"{index['part']}_index.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        print(f"Index written to: {out_path}", file=sys.stderr)
    else:
        lines = []
        lines.append(f"# {index['part']} - Datasheet Index")
        lines.append(f"Source: {index['source']} ({index['total_pages']} pages)")
        lines.append("")

        if index["pins"]:
            lines.append(f"## Pins ({len(index['pins'])} entries)")
            for p in index["pins"][:50]:
                name = p.get("pin_name", "?")
                funcs = ", ".join(p.get("functions", [])[:4])
                lines.append(f"- **{name}**: {funcs}")
            lines.append("")

        if index["electrical_params"]:
            lines.append(f"## Electrical Parameters ({len(index['electrical_params'])} entries)")
            for p in index["electrical_params"][:30]:
                lines.append(f"- {p['param']}: {p.get('min','?')}-{p.get('max',p.get('value','?'))} {p['unit']}")
            lines.append("")

        if index["notes"]:
            lines.append(f"## Notes & Warnings ({len(index['notes'])} entries)")
            for n in index["notes"][:50]:
                lines.append(f"- [{n['type']}] p{n['page']}: {n['text'][:150]}")
            lines.append("")

        if index["circuits"]:
            lines.append(f"## Circuits ({len(index['circuits'])} entries)")
            for c in index["circuits"]:
                lines.append(f"- p{c['page']}: {c['description'][:100]}...")

        out_path = os.path.join(args.output_dir, f"{index['part']}_index.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Index written to: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
