#!/usr/bin/env python3
"""
build_retrieval_index.py - Build chunk-level retrieval index from a datasheet index.

Input:
- structured index JSON from datasheet_index.py

Output:
- {part}_retrieval.json with normalized chunks for hybrid search
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Dict, List


def normalize_sentence(text: str) -> str:
    return " ".join((text or "").split())


def chunk_from_pin(part: str, source: str, pin: Dict, idx: int) -> Dict:
    pin_name = pin.get("pin_name", "")
    funcs = pin.get("functions", [])
    text = f"Pin {pin_name}. Functions: {', '.join(funcs[:12])}" if pin_name else ", ".join(funcs[:12])
    return {
        "id": f"{part}_pin_{idx:05d}",
        "part": part,
        "source": source,
        "page": pin.get("page"),
        "section": "io",
        "chunk_type": "pin",
        "pin_name": pin_name,
        "text": normalize_sentence(text),
        "raw": pin,
    }


def chunk_from_param(part: str, source: str, param: Dict, idx: int) -> Dict:
    name = param.get("param", "")
    if "value" in param:
        desc = f"Electrical parameter {name}: value {param.get('value')} {param.get('unit', '')}."
    else:
        desc = f"Electrical parameter {name}: minimum {param.get('min')} maximum {param.get('max')} {param.get('unit', '')}."
    if param.get("source_line"):
        desc += f" Source: {param['source_line']}"
    return {
        "id": f"{part}_elec_{idx:05d}",
        "part": part,
        "source": source,
        "page": param.get("page"),
        "section": "electrical",
        "chunk_type": "electrical_param",
        "param": name,
        "text": normalize_sentence(desc),
        "raw": param,
    }


def chunk_from_note(part: str, source: str, note: Dict, idx: int) -> Dict:
    note_type = note.get("type", "note")
    text = note.get("text", "")
    return {
        "id": f"{part}_note_{idx:05d}",
        "part": part,
        "source": source,
        "page": note.get("page"),
        "section": "notes",
        "chunk_type": "note",
        "type": note_type,
        "text": normalize_sentence(text),
        "raw": note,
    }


def chunk_from_circuit(part: str, source: str, circuit: Dict, idx: int) -> Dict:
    text = circuit.get("description", "")
    return {
        "id": f"{part}_ckt_{idx:05d}",
        "part": part,
        "source": source,
        "page": circuit.get("page"),
        "section": "circuit",
        "chunk_type": "circuit",
        "text": normalize_sentence(text),
        "raw": circuit,
    }


def build_retrieval_chunks(index: Dict) -> Dict:
    part = index.get("part") or os.path.splitext(index.get("source", "unknown"))[0]
    source = index.get("source", "unknown")

    chunks: List[Dict] = []

    for i, pin in enumerate(index.get("pins", []), 1):
        chunks.append(chunk_from_pin(part, source, pin, i))

    for i, param in enumerate(index.get("electrical_params", []), 1):
        item = dict(param)
        chunks.append(chunk_from_param(part, source, item, i))

    for i, note in enumerate(index.get("notes", []), 1):
        chunks.append(chunk_from_note(part, source, note, i))

    for i, circuit in enumerate(index.get("circuits", []), 1):
        chunks.append(chunk_from_circuit(part, source, circuit, i))

    return {
        "part": part,
        "source": source,
        "total_pages": index.get("total_pages"),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def main():
    parser = argparse.ArgumentParser(description="Build retrieval chunks from structured datasheet index")
    parser.add_argument("input", help="Structured index JSON file from datasheet_index.py")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        index = json.load(f)

    retrieval = build_retrieval_chunks(index)
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f"{retrieval['part']}_retrieval.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(retrieval, f, ensure_ascii=False, indent=2)

    print(f"Retrieval index written to: {out_path}")
    print(f"Chunks: {retrieval['chunk_count']}")


if __name__ == "__main__":
    main()
