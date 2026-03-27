#!/usr/bin/env python3
"""
search_retrieval.py - Search retrieval chunks using hybrid ranking.

Input:
- one retrieval json file, or
- a project directory containing indexes/*_index.json or retrieval files
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List

from retrieval_utils import rank_chunks
from build_retrieval_index import build_retrieval_chunks


def load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def gather_chunks_from_project(project_dir: str) -> List[Dict]:
    chunks: List[Dict] = []

    indexes_dir = os.path.join(project_dir, "indexes")
    if not os.path.isdir(indexes_dir):
        raise FileNotFoundError(f"No indexes directory found: {indexes_dir}")

    for name in os.listdir(indexes_dir):
        path = os.path.join(indexes_dir, name)
        if name.endswith("_retrieval.json"):
            data = load_json(path)
            chunks.extend(data.get("chunks", []))
        elif name.endswith("_index.json"):
            data = load_json(path)
            retrieval = build_retrieval_chunks(data)
            chunks.extend(retrieval.get("chunks", []))

    return chunks


def gather_chunks(input_path: str) -> List[Dict]:
    if os.path.isdir(input_path):
        return gather_chunks_from_project(input_path)

    data = load_json(input_path)
    if "chunks" in data:
        return data["chunks"]
    if "pins" in data or "electrical_params" in data or "notes" in data:
        return build_retrieval_chunks(data)["chunks"]
    raise ValueError("Unsupported input JSON format")


def print_results(results: List[Dict], show_meta: bool = False):
    if not results:
        print("No results")
        return

    for i, item in enumerate(results, 1):
        part = item.get("part", "?")
        section = item.get("section", "?")
        page = item.get("page", "?")
        chunk_type = item.get("chunk_type", "?")
        score = item.get("score", 0)
        text = (item.get("text", "") or "")[:240]
        print(f"[{i}] {part} | {section}/{chunk_type} | p{page} | score={score}")
        print(f"    {text}")
        if show_meta:
            print(f"    meta={json.dumps(item.get('score_meta', {}), ensure_ascii=False)}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Search datasheet retrieval chunks")
    parser.add_argument("input", help="retrieval json, index json, or project dir")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--mode", choices=["exact", "semantic", "hybrid"], default="hybrid")
    parser.add_argument("--section", default=None, help="Optional section filter")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--show-meta", action="store_true")
    args = parser.parse_args()

    chunks = gather_chunks(args.input)
    results = rank_chunks(args.query, chunks, mode=args.mode, section_filter=args.section, top_k=args.top_k)
    print_results(results, show_meta=args.show_meta)


if __name__ == "__main__":
    main()
