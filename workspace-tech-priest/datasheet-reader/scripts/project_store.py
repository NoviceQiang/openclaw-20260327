#!/usr/bin/env python3
"""
project_store.py - Project-first storage helpers for datasheet-reader.

Project layout:
  datasheet-reader/projects/<project-name>/
    manifest.json
    raw/
    parsed/
    indexes/
    retrieval/
    reports/
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from typing import Dict, Optional


PROJECT_SUBDIRS = ["raw", "parsed", "indexes", "retrieval", "reports"]


def slugify(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^0-9A-Za-z._-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-._")
    return name or "unnamed-project"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_projects_root(skill_dir: str) -> str:
    return os.path.join(skill_dir, "projects")


def get_project_dir(skill_dir: str, project_name: str) -> str:
    return os.path.join(get_projects_root(skill_dir), slugify(project_name))


def ensure_project(skill_dir: str, project_name: str, title: Optional[str] = None) -> str:
    project_dir = get_project_dir(skill_dir, project_name)
    os.makedirs(project_dir, exist_ok=True)
    for sub in PROJECT_SUBDIRS:
        os.makedirs(os.path.join(project_dir, sub), exist_ok=True)

    manifest_path = os.path.join(project_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        manifest = {
            "project": slugify(project_name),
            "title": title or project_name,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "parts": {},
            "notes": [],
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    return project_dir


def load_manifest(project_dir: str) -> Dict:
    path = os.path.join(project_dir, "manifest.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Project manifest not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(project_dir: str, manifest: Dict):
    manifest["updated_at"] = now_iso()
    path = os.path.join(project_dir, "manifest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def import_pdf(project_dir: str, pdf_path: str, part_name: str) -> str:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    ext = os.path.splitext(pdf_path)[1] or ".pdf"
    safe_part = slugify(part_name)
    dst = os.path.join(project_dir, "raw", f"{safe_part}{ext}")
    shutil.copy2(pdf_path, dst)
    return dst
