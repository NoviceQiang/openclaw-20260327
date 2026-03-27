---
name: datasheet-reader
description: Read and extract structured information from electronic component datasheets (MCU, sensors, chips, passive components). Sources: PDF files, web URLs (LCSC, Mouser, Digikey, TI, ST, NXP, manufacturer sites), or part number search. Extracts: IO pin functions and alternate mappings, electrical characteristics (absolute max ratings, recommended conditions, DC/AC specs), recommended peripheral/application circuits, notes/cautions/warnings, timing characteristics, package info. Supports both English and Chinese datasheets. Includes project-level multi-datasheet management: add multiple datasheets to a project, build structured indexes, and search across all chips by pin name, electrical parameter, or note keyword. Use when: user provides a datasheet PDF/URL, asks to read/analyze a chip datasheet, needs pin/electrical/circuit info, wants to extract design notes marked with "Note" / "Caution" / "Warning" / "注意", searches across multiple component datasheets in a project, or requests component design guidelines. Supports netlist cross-checking against extracted datasheet info.
---

# Datasheet Reader

## Quick Start

### Single Datasheet Extraction

```bash
# All sections → Markdown
python3 scripts/datasheet_extract.py <pdf> --sections all --output markdown

# Specific sections
python3 scripts/datasheet_extract.py <pdf> --sections io,electrical,notes --output markdown

# Page range
python3 scripts/datasheet_extract.py <pdf> --sections notes --pages 35-42
```

**Sections:** `io` `electrical` `notes` `circuit` `timing` `package` `all`

### Structured Index (for search)

```bash
# Build index from PDF or raw JSON
python3 scripts/datasheet_index.py <pdf> --part <name> --output-dir ./indexes
python3 scripts/datasheet_index.py <raw.json> --part <name> --output-dir ./indexes
```

Produces `{part}_index.json` with structured pins, electrical params, notes.

## Project-First Workflow

Use a named project as the primary unit of storage and retrieval:

```bash
# 1. Create a project
python3 scripts/project_manager.py init --project motor-controller-v1 --title "Motor Controller V1"

# 2. Add datasheets to the project
python3 scripts/project_manager.py add --project motor-controller-v1 --pdf mcu.pdf --part STM32F103C8T6
python3 scripts/project_manager.py add --project motor-controller-v1 --pdf sensor.pdf --part BMP280

# 3. Show project contents
python3 scripts/project_manager.py show --project motor-controller-v1

# 4. Search within the project
python3 scripts/project_manager.py search --project motor-controller-v1 --query "PA0"
python3 scripts/project_manager.py search --project motor-controller-v1 --query "VCC" --section electrical --mode exact
python3 scripts/project_manager.py search --project motor-controller-v1 --query "decoupling capacitor near VDDA" --section notes --mode hybrid
```

**Project structure:**
```
projects/
└── motor-controller-v1/
    ├── manifest.json
    ├── raw/              # Original PDFs
    ├── parsed/           # Section extraction JSON
    ├── indexes/          # Structured index JSON
    ├── retrieval/        # Retrieval chunk JSON
    └── reports/
```

## Analysis Guide

After extraction, summarize:

1. **IO summary**: pin functions grouped by port, alternate functions
2. **Electrical limits**: absolute max ratings, operating ranges
3. **Key notes**: ALL Note/Caution/Warning items — critical design constraints
4. **Recommended circuits**: decoupling, reset, crystal, power filtering
5. **Special pins**: BOOT, NRST, VDDA/VSSA, VBAT, etc.

Format for the user's platform (no markdown tables on Discord/WhatsApp).

## Netlist Cross-Check

When user provides a netlist, cross-reference against project indexes:
- Power pins have proper decoupling (check notes for capacitor values)
- Reset circuit matches recommendation
- Crystal/clock circuit correct
- Unused pins properly handled
- IO voltage levels compatible across connected devices
- No note/warning violations

## Hybrid Retrieval Upgrade

The skill now supports a retrieval-oriented layer in addition to section extraction:

```bash
# Build structured index
python3 scripts/datasheet_index.py chip.pdf --part STM32F103C8 --output-dir ./indexes

# Build retrieval chunks from the structured index
python3 scripts/build_retrieval_index.py ./indexes/STM32F103C8_index.json --output-dir ./indexes

# Search one chip or a whole project
python3 scripts/search_retrieval.py ./indexes/STM32F103C8_retrieval.json --query "analog supply decoupling" --mode hybrid
python3 scripts/search_retrieval.py ./my_project --query "NRST pull-up requirement" --mode hybrid
```

Search modes:
- `exact` → best for pin names, identifiers, exact parameters
- `semantic` → stronger fuzzy/token-overlap matching for descriptive queries
- `hybrid` → recommended default

## Tips

- Large PDFs: use `--pages` to target sections
- EN and CN datasheets both supported — section extraction keywords are bilingual
- `notes` catches ALL instances of Note/Caution/Warning/注意/注
- Retrieval ranking improves descriptive queries like decoupling, reset behavior, analog supply, boot notes
- Exact mode remains better for identifiers such as `PA0`, `VDD`, `NRST`, `VBAT`
