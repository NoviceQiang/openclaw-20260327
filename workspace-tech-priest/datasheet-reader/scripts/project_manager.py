#!/usr/bin/env python3
"""
project_manager.py - Project-first datasheet knowledge base manager.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from project_store import ensure_project, get_project_dir, get_projects_root, import_pdf, load_manifest, save_manifest, slugify
from build_retrieval_index import build_retrieval_chunks
from retrieval_utils import rank_chunks
from datasheet_extract import extract_section, extract_notes, KW_IO, KW_ELECTRICAL, KW_NOTES, KW_CIRCUIT, KW_TIMING, KW_PACKAGE
from datasheet_index import build_index


try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Use uv run --with pdfplumber ...", file=sys.stderr)
    sys.exit(1)


SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_pdf_to_raw(pdf_path: str) -> dict:
    pdf = pdfplumber.open(pdf_path)
    total = len(pdf.pages)
    pages = list(range(total))
    raw = {
        "source": os.path.basename(pdf_path),
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
    return raw


def add_part(project_name: str, pdf_path: str, part_name: str, title: str | None = None):
    project_dir = ensure_project(SKILL_DIR, project_name, title=title or project_name)
    manifest = load_manifest(project_dir)

    imported_pdf = import_pdf(project_dir, pdf_path, part_name)
    raw = parse_pdf_to_raw(imported_pdf)
    index = build_index(raw, part_name=part_name)
    retrieval = build_retrieval_chunks(index)

    safe_part = slugify(part_name)
    parsed_path = os.path.join(project_dir, "parsed", f"{safe_part}_raw.json")
    index_path = os.path.join(project_dir, "indexes", f"{safe_part}_index.json")
    retrieval_path = os.path.join(project_dir, "retrieval", f"{safe_part}_retrieval.json")

    with open(parsed_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    with open(retrieval_path, "w", encoding="utf-8") as f:
        json.dump(retrieval, f, ensure_ascii=False, indent=2)

    manifest["parts"][safe_part] = {
        "name": part_name,
        "pdf": os.path.relpath(imported_pdf, project_dir),
        "parsed": os.path.relpath(parsed_path, project_dir),
        "index": os.path.relpath(index_path, project_dir),
        "retrieval": os.path.relpath(retrieval_path, project_dir),
        "pages": raw.get("total_pages", 0),
        "pins_count": len(index.get("pins", [])),
        "notes_count": len(index.get("notes", [])),
        "chunks_count": len(retrieval.get("chunks", [])),
    }
    save_manifest(project_dir, manifest)

    print(f"Project: {manifest['project']}")
    print(f"Added part: {part_name}")
    print(f"Pages: {raw.get('total_pages', 0)}")
    print(f"Pins: {len(index.get('pins', []))}")
    print(f"Notes: {len(index.get('notes', []))}")
    print(f"Chunks: {len(retrieval.get('chunks', []))}")


def list_projects():
    root = get_projects_root(SKILL_DIR)
    os.makedirs(root, exist_ok=True)
    names = sorted([n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n))])
    if not names:
        print("No projects.")
        return
    for name in names:
        print(name)


def show_project(project_name: str):
    project_dir = get_project_dir(SKILL_DIR, project_name)
    manifest = load_manifest(project_dir)
    print(f"Project: {manifest['project']}")
    print(f"Title: {manifest.get('title', manifest['project'])}")
    print(f"Parts: {len(manifest.get('parts', {}))}")
    print()
    for key, info in manifest.get("parts", {}).items():
        print(f"- {info.get('name', key)}")
        print(f"  pages={info.get('pages', 0)} pins={info.get('pins_count', 0)} notes={info.get('notes_count', 0)} chunks={info.get('chunks_count', 0)}")


def gather_project_chunks(project_name: str):
    project_dir = get_project_dir(SKILL_DIR, project_name)
    manifest = load_manifest(project_dir)
    all_chunks = []
    for _, info in manifest.get("parts", {}).items():
        rel = info.get("retrieval")
        if not rel:
            continue
        path = os.path.join(project_dir, rel)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            retrieval = json.load(f)
        all_chunks.extend(retrieval.get("chunks", []))
    return all_chunks


def search_project(project_name: str, query: str, section: str | None = None, mode: str = "hybrid", top_k: int = 10):
    chunks = gather_project_chunks(project_name)
    results = rank_chunks(query, chunks, mode=mode, section_filter=section, top_k=top_k)
    if not results:
        print("No results")
        return
    print(f"Project: {slugify(project_name)} | Query: {query} | Mode: {mode}")
    print()
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r.get('part','?')} | {r.get('section','?')}/{r.get('chunk_type','?')} | p{r.get('page','?')} | score={r.get('score',0)}")
        print(f"    {r.get('text','')[:220]}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Project-first datasheet knowledge base manager")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Create a project")
    p_init.add_argument("--project", required=True)
    p_init.add_argument("--title", default=None)

    p_add = sub.add_parser("add", help="Add a datasheet PDF into a project and index it")
    p_add.add_argument("--project", required=True)
    p_add.add_argument("--pdf", required=True)
    p_add.add_argument("--part", required=True)

    p_list = sub.add_parser("list", help="List all projects")

    p_show = sub.add_parser("show", help="Show project contents")
    p_show.add_argument("--project", required=True)

    p_search = sub.add_parser("search", help="Search within one project")
    p_search.add_argument("--project", required=True)
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--section", default=None, choices=["io", "electrical", "notes", "circuit", "timing", "package"])
    p_search.add_argument("--mode", default="hybrid", choices=["exact", "semantic", "hybrid"])
    p_search.add_argument("--top-k", type=int, default=10)

    args = parser.parse_args()

    if args.command == "init":
        project_dir = ensure_project(SKILL_DIR, args.project, title=args.title or args.project)
        print(f"Project created: {project_dir}")
    elif args.command == "add":
        add_part(args.project, args.pdf, args.part)
    elif args.command == "list":
        list_projects()
    elif args.command == "show":
        show_project(args.project)
    elif args.command == "search":
        search_project(args.project, args.query, section=args.section, mode=args.mode, top_k=args.top_k)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
