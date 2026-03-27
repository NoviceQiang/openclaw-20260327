#!/usr/bin/env python3
"""
EEWorld latestnews reader utility.

Current scope:
- Fetch latestnews items for specific date(s)
- Rank by reading profile keywords
- Fetch full article markdown
- Save local snapshots by default

Data source (fallback path):
https://r.jina.ai/http://www.eeworld.com.cn/latestnews
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple

LATEST_NEWS_URL = "http://www.eeworld.com.cn/latestnews"
R_JINA_PREFIX = "https://r.jina.ai/"

TITLE_RE = re.compile(r"^Title:\s*(.+)$")
LATEST_ITEM_RE = re.compile(
    r"^\*\s+###\s+\[\[(?P<category>[^\]]+)\]\((?P<category_url>https?://[^\)]+)\)\]"
    r"\[(?P<title>.+?)\]\((?P<url>https?://[^\s\)]+)(?:\s+\"[^\"]*\")?\)\s*(?P<date>20\d{2}-\d{2}-\d{2})\s*$"
)
DATE_TOKEN_RE = re.compile(r"^(?P<y>\d{4})[-/](?P<m>\d{1,2})[-/](?P<d>\d{1,2})$")
DATE_SHORT_RE = re.compile(r"^(?P<m>\d{1,2})[-/](?P<d>\d{1,2})$")

KEYWORD_ALIASES = {
    "射频": ["rf", "无线", "毫米波"],
    "DSP": ["fpga/dsp", "信号处理"],
    "嵌入式系统": ["嵌入式", "mcu", "单片机"],
    "车用传感器": ["传感器", "毫米波雷达", "激光雷达"],
}

CURL_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

MAX_INTEREST_KEYWORDS = 5


# ---------- fetch core ----------

def _url_variants(url: str) -> List[str]:
    variants = [url]
    if url.startswith("http://"):
        variants.append("https://" + url[len("http://") :])
    elif url.startswith("https://"):
        variants.append("http://" + url[len("https://") :])

    out: List[str] = []
    seen: Set[str] = set()
    for v in variants:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def run_curl(
    url: str,
    *,
    attempts: int = 4,
    backoff_seconds: float = 1.0,
    expected_tokens: List[str] | None = None,
) -> str:
    """Fetch by Jina Reader URL prefix, with retries and url-variant fallback."""
    expected_tokens = expected_tokens or []
    errors: List[str] = []

    for target_url in _url_variants(url):
        for attempt in range(1, max(1, attempts) + 1):
            cmd = [
                "curl",
                "-L",
                "-sS",
                "--connect-timeout",
                "10",
                "--max-time",
                "35",
                "-A",
                CURL_USER_AGENT,
                f"{R_JINA_PREFIX}{target_url}",
            ]
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True)

            if proc.returncode == 0 and proc.stdout.strip():
                text = proc.stdout
                if expected_tokens and not any(tok in text for tok in expected_tokens):
                    errors.append(f"{target_url} attempt {attempt}: missing expected tokens")
                else:
                    return text
            else:
                err = proc.stderr.strip() or "no stderr"
                errors.append(f"{target_url} attempt {attempt}: curl failed ({proc.returncode}): {err}")

            if attempt < attempts:
                time.sleep(min(backoff_seconds * attempt, 4.0))

    preview = " | ".join(errors[-4:]) if errors else "unknown error"
    raise RuntimeError(f"Failed to fetch via r.jina.ai. {preview}")


# ---------- article ----------

def extract_markdown_body(raw: str) -> Tuple[str, str]:
    title = ""
    for line in raw.splitlines():
        m = TITLE_RE.match(line.strip())
        if m:
            title = m.group(1).strip()
            break

    marker = "Markdown Content:"
    idx = raw.find(marker)
    if idx < 0:
        body = raw.strip()
    else:
        body = raw[idx + len(marker) :].strip()

    body = clean_article_body(title, body)
    return title, body


def clean_article_body(title: str, body: str) -> str:
    lines = body.splitlines()
    if not lines:
        return body

    start = 0
    pub_indexes = [i for i, ln in enumerate(lines) if "发布者：" in ln]
    if pub_indexes:
        pub_i = pub_indexes[0]
        start = max(0, pub_i - 4)
        if title:
            for j in range(max(0, pub_i - 8), pub_i + 1):
                if title in lines[j]:
                    start = j
                    break
    elif title:
        matches = [i for i, ln in enumerate(lines) if title in ln]
        if matches:
            start = matches[-1]

    end = len(lines)
    tail_markers = ["**上一篇：**", "推荐阅读 最新更新时间", "关注eeworld公众号"]
    for i in range(start, len(lines)):
        s = lines[i].strip()
        if any(m in s for m in tail_markers):
            end = i
            break
        if s.startswith("关键字：") and "引用地址" in s:
            end = i
            break

    cleaned = "\n".join(lines[start:end]).strip()
    return cleaned or body.strip()


def article_cache_key(url: str) -> str:
    m = re.search(r"/([a-z]+\d+)\.html", url)
    if m:
        return m.group(1).lower()
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def article_cache_paths(cache_dir: Path, url: str) -> Tuple[Path, Path]:
    key = article_cache_key(url)
    return cache_dir / f"{key}.json", cache_dir / f"{key}.md"


def load_cached_article(cache_dir: Path, url: str) -> Dict[str, object] | None:
    json_path, md_path = article_cache_paths(cache_dir, url)
    if not json_path.exists() or not md_path.exists():
        return None
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        payload["markdown"] = md_path.read_text(encoding="utf-8")
        payload["cache_hit"] = True
        payload["cache_files"] = {"json": str(json_path), "markdown": str(md_path)}
        return payload
    except (json.JSONDecodeError, OSError):
        return None


def save_article_cache(cache_dir: Path, payload: Dict[str, object]) -> Dict[str, str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = article_cache_paths(cache_dir, str(payload.get("url", "")))

    md_path.write_text(str(payload.get("markdown", "")), encoding="utf-8")
    meta = dict(payload)
    meta.pop("markdown", None)
    meta["cache_saved_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    json_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"json": str(json_path), "markdown": str(md_path)}


def read_article(
    url: str,
    max_chars: int,
    *,
    cache_dir: Path | None = None,
    use_cache: bool = True,
    refresh: bool = False,
    save_cache: bool = True,
) -> Dict[str, object]:
    if cache_dir is not None and use_cache and not refresh:
        cached = load_cached_article(cache_dir, url)
        if cached is not None:
            body = str(cached.get("markdown", ""))
            if max_chars > 0 and len(body) > max_chars:
                cached["markdown"] = body[:max_chars] + "\n\n[Truncated]"
                cached["truncated"] = True
            return cached

    raw = run_curl(url)
    title, body = extract_markdown_body(raw)
    truncated = False
    if max_chars > 0 and len(body) > max_chars:
        body = body[:max_chars] + "\n\n[Truncated]"
        truncated = True

    payload: Dict[str, object] = {
        "url": url,
        "title": title,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "markdown": body,
        "cache_hit": False,
        "truncated": truncated,
    }

    if cache_dir is not None and save_cache:
        cache_files = save_article_cache(cache_dir, payload)
        payload["cache_files"] = cache_files

    return payload


# ---------- profile ----------

def split_keywords(raw_keywords: str) -> List[str]:
    parts = re.split(r"[,，;；\n]+", raw_keywords)
    cleaned: List[str] = []
    seen: Set[str] = set()
    for p in parts:
        k = p.strip()
        if not k:
            continue
        norm = k.lower()
        if norm in seen:
            continue
        seen.add(norm)
        cleaned.append(k)
    return cleaned


def load_profile(path: Path) -> Dict[str, object]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "updated_at": None,
        "total_saved": 0,
        "keyword_counts": {},
        "articles": [],
    }


def save_profile(path: Path, data: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_keywords(profile_path: Path, title: str, url: str, keywords_raw: str) -> Dict[str, object]:
    keywords = split_keywords(keywords_raw)
    if not keywords:
        raise ValueError("No valid keywords provided")

    data = load_profile(profile_path)
    counts = data.setdefault("keyword_counts", {})
    now = dt.datetime.now(dt.timezone.utc).isoformat()

    for kw in keywords:
        key = kw.strip()
        counts[key] = int(counts.get(key, 0)) + 1

    article = {"saved_at": now, "title": title, "url": url, "keywords": keywords}
    articles = data.setdefault("articles", [])
    articles.append(article)
    if len(articles) > 500:
        data["articles"] = articles[-500:]

    data["total_saved"] = int(data.get("total_saved", 0)) + 1
    data["updated_at"] = now

    save_profile(profile_path, data)
    return data


def add_missing_keywords(profile_path: Path, title: str, url: str, keywords_raw: str) -> Dict[str, object]:
    """Only add keywords that do not already exist in profile (case-insensitive)."""
    keywords = split_keywords(keywords_raw)
    if not keywords:
        raise ValueError("No valid keywords provided")

    data = load_profile(profile_path)
    counts = data.setdefault("keyword_counts", {})

    lower_existing = {str(k).strip().lower() for k in counts.keys() if str(k).strip()}
    added: List[str] = []
    skipped: List[str] = []

    for kw in keywords:
        key = kw.strip()
        if not key:
            continue
        if key.lower() in lower_existing:
            skipped.append(key)
            continue
        counts[key] = 1
        lower_existing.add(key.lower())
        added.append(key)

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if added:
        article = {
            "saved_at": now,
            "title": title,
            "url": url,
            "keywords": added,
            "mode": "add-missing",
        }
        articles = data.setdefault("articles", [])
        articles.append(article)
        if len(articles) > 500:
            data["articles"] = articles[-500:]

        data["total_saved"] = int(data.get("total_saved", 0)) + 1
        data["updated_at"] = now
        save_profile(profile_path, data)

    return {
        "profile": data,
        "added_keywords": added,
        "skipped_keywords": skipped,
        "updated": bool(added),
    }


def add_or_increment_keywords(profile_path: Path, title: str, url: str, keywords_raw: str) -> Dict[str, object]:
    """Add missing keywords and increment count for existing ones (case-insensitive)."""
    keywords = split_keywords(keywords_raw)
    if not keywords:
        raise ValueError("No valid keywords provided")

    data = load_profile(profile_path)
    counts = data.setdefault("keyword_counts", {})

    canonical: Dict[str, str] = {}
    for k in list(counts.keys()):
        key = str(k).strip()
        if not key:
            continue
        canonical.setdefault(key.lower(), key)

    added: List[str] = []
    incremented: List[str] = []

    for kw in keywords:
        key = kw.strip()
        if not key:
            continue
        low = key.lower()
        if low in canonical:
            real_key = canonical[low]
            counts[real_key] = int(counts.get(real_key, 0)) + 1
            incremented.append(real_key)
        else:
            counts[key] = 1
            canonical[low] = key
            added.append(key)

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    changed = bool(added or incremented)
    if changed:
        article = {
            "saved_at": now,
            "title": title,
            "url": url,
            "keywords": keywords,
            "mode": "add-or-increment",
        }
        articles = data.setdefault("articles", [])
        articles.append(article)
        if len(articles) > 500:
            data["articles"] = articles[-500:]

        data["total_saved"] = int(data.get("total_saved", 0)) + 1
        data["updated_at"] = now
        save_profile(profile_path, data)

    return {
        "profile": data,
        "added_keywords": added,
        "incremented_keywords": incremented,
        "updated": changed,
    }


def top_keywords(data: Dict[str, object], top_n: int) -> List[Tuple[str, int]]:
    counts = data.get("keyword_counts", {})
    pairs = [(k, int(v)) for k, v in counts.items()]
    pairs.sort(key=lambda kv: (-kv[1], kv[0]))
    return pairs[:top_n]


# ---------- latest-day ----------

def normalize_date_token(raw: str) -> str:
    token = raw.strip()
    if not token:
        raise ValueError("Empty date token")

    m = DATE_TOKEN_RE.match(token)
    if m:
        y, mo, d = int(m.group("y")), int(m.group("m")), int(m.group("d"))
        return dt.date(y, mo, d).isoformat()

    m2 = DATE_SHORT_RE.match(token)
    if m2:
        now = dt.datetime.now(dt.timezone.utc)
        y = now.year
        mo, d = int(m2.group("m")), int(m2.group("d"))
        return dt.date(y, mo, d).isoformat()

    raise ValueError(f"Unsupported date format: {raw}")


def parse_latest_items(page_md: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for line in page_md.splitlines():
        s = line.strip()
        m = LATEST_ITEM_RE.match(s)
        if not m:
            continue
        items.append(
            {
                "category": m.group("category").strip(),
                "category_url": m.group("category_url").strip(),
                "title": m.group("title").strip(),
                "url": m.group("url").strip(),
                "date": m.group("date").strip(),
            }
        )
    return items


def latest_news_page_url(page: int) -> str:
    if page <= 1:
        return LATEST_NEWS_URL
    return f"{LATEST_NEWS_URL}/{page}"


def fetch_latest_by_dates(target_dates: Set[str], max_pages: int) -> Tuple[List[Dict[str, str]], List[Dict[str, object]]]:
    max_pages = max(1, min(max_pages, 100))
    target_dates = set(target_dates)
    if not target_dates:
        return [], []

    items: List[Dict[str, str]] = []
    pages: List[Dict[str, object]] = []
    seen_urls: Set[str] = set()
    min_target = min(target_dates)

    for page in range(1, max_pages + 1):
        page_url = latest_news_page_url(page)
        page_md = run_curl(page_url, expected_tokens=["latestnews", "Markdown Content:"])
        page_items = parse_latest_items(page_md)

        pages.append(
            {
                "page": page,
                "url": page_url,
                "item_count": len(page_items),
                "dates": sorted({it["date"] for it in page_items}),
                "raw_markdown": page_md,
            }
        )

        if not page_items and page > 1:
            break

        page_dates = {it["date"] for it in page_items}

        for it in page_items:
            if it["date"] not in target_dates:
                continue
            if it["url"] in seen_urls:
                continue
            seen_urls.add(it["url"])
            items.append(it)

        if page_dates and max(page_dates) < min_target:
            break

    return items, pages


def token_in_text(token: str, text: str) -> bool:
    t = token.strip().lower()
    if not t:
        return False

    if re.fullmatch(r"[a-z0-9][a-z0-9_\-/+\.]*", t):
        pat = re.compile(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])")
        return bool(pat.search(text))

    return t in text


def score_latest_item(item: Dict[str, str], keyword_counts: Dict[str, int]) -> Tuple[float, List[str]]:
    haystack = f"{item.get('title', '')} {item.get('category', '')} {item.get('url', '')}".lower()
    score = 0.0
    matched: List[str] = []

    for kw, cnt in keyword_counts.items():
        keyword = str(kw).strip()
        if not keyword:
            continue
        weight = max(1, int(cnt))

        direct_hit = token_in_text(keyword, haystack)
        alias_hit = False
        if not direct_hit:
            for alias in KEYWORD_ALIASES.get(keyword, []):
                if token_in_text(alias, haystack):
                    alias_hit = True
                    break

        if direct_hit:
            score += 1.2 * weight
            matched.append(keyword)
        elif alias_hit:
            score += 0.8 * weight
            matched.append(keyword)

    matched.sort(key=lambda k: (-int(keyword_counts.get(k, 1)), k))
    return score, matched


def rank_latest_items(items: List[Dict[str, str]], profile: Dict[str, object]) -> List[Dict[str, object]]:
    counts_raw = profile.get("keyword_counts", {}) if isinstance(profile, dict) else {}
    keyword_counts: Dict[str, int] = {}
    for k, v in counts_raw.items():
        try:
            keyword_counts[str(k)] = int(v)
        except (TypeError, ValueError):
            continue

    ranked: List[Dict[str, object]] = []
    for it in items:
        score, matched = score_latest_item(it, keyword_counts)
        out: Dict[str, object] = dict(it)
        out["score"] = round(score, 2)
        out["matched_keywords"] = matched
        ranked.append(out)

    ranked.sort(
        key=lambda x: (float(x.get("score", 0.0)), str(x.get("date", "")), str(x.get("title", ""))),
        reverse=True,
    )
    return ranked


def render_markdown_latest(payload: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# 获取某天最新文章")
    lines.append(f"日期: {', '.join(payload.get('dates', []))}")
    lines.append(f"来源: {payload.get('source')}")
    lines.append("")

    ranked = payload.get("ranked", [])
    if not ranked:
        lines.append("(指定日期未抓到文章)")
        return "\n".join(lines).rstrip() + "\n"

    by_date: Dict[str, List[Dict[str, object]]] = {}
    for item in ranked:
        day = str(item.get("date", ""))
        by_date.setdefault(day, []).append(item)

    for day in sorted(by_date.keys(), reverse=True):
        lines.append(f"## {day}")
        for i, item in enumerate(by_date[day], 1):
            score = float(item.get("score", 0.0))
            matched = item.get("matched_keywords", [])
            matched_s = "、".join(matched) if matched else "(无命中)"
            lines.append(f"{i}. [{score:.2f}] {item.get('title', '')}")
            lines.append(f"   分类: {item.get('category', '')}")
            lines.append(f"   命中: {matched_s}")
            lines.append(f"   {item.get('url', '')}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def print_markdown_profile(profile: Dict[str, object], top_n: int) -> None:
    print("# 阅读关键词画像")
    print(f"累计保存: {profile.get('total_saved', 0)}")
    print(f"最近更新: {profile.get('updated_at')}")
    print("")
    print(f"## Top {top_n} 关键词")
    pairs = top_keywords(profile, top_n)
    if not pairs:
        print("(暂无关键词)")
        return
    for i, (k, c) in enumerate(pairs, 1):
        print(f"{i}. {k} ({c})")


# ---------- local save ----------

def resolve_workspace_root() -> Path | None:
    env_ws = os.getenv("OPENCLAW_WORKSPACE")
    if env_ws:
        ws = Path(env_ws).expanduser()
        if ws.exists():
            return ws

    cwd = Path.cwd()
    if (cwd / "memory").exists() or (cwd / "skills").exists():
        return cwd

    script_path = Path(__file__).resolve()
    maybe_ws = script_path.parents[3] if len(script_path.parents) >= 4 else None
    if maybe_ws and (maybe_ws / "memory").exists():
        return maybe_ws

    return None


def default_profile_path() -> Path:
    ws = resolve_workspace_root()
    if ws:
        return ws / "memory" / "eeworld-reading-profile.json"
    return Path("memory/eeworld-reading-profile.json")


def default_capture_dir() -> Path:
    ws = resolve_workspace_root()
    if ws:
        return ws / "memory" / "eeworld-captures"
    return Path("memory/eeworld-captures")


def default_article_cache_dir() -> Path:
    return default_capture_dir() / "articles"


def default_interests_dir() -> Path:
    ws = resolve_workspace_root()
    if ws:
        return ws / "memory" / "interests"
    return Path("memory/interests")


def sanitize_token(raw: str) -> str:
    token = re.sub(r"[^0-9A-Za-z_-]+", "-", (raw or "").strip())
    return token.strip("-").lower()


def capture_timestamp(iso_text: str) -> str:
    try:
        ts = dt.datetime.fromisoformat(str(iso_text).replace("Z", "+00:00"))
    except ValueError:
        ts = dt.datetime.now(dt.timezone.utc)

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    ts = ts.astimezone(dt.timezone.utc)
    return ts.strftime("%Y-%m-%dT%H-%M-%SZ")


def save_capture_payload(
    *,
    capture_kind: str,
    payload: Dict[str, object],
    markdown_text: str,
    save_dir: Path,
    hint: str = "",
) -> Dict[str, str]:
    save_dir.mkdir(parents=True, exist_ok=True)

    ts = capture_timestamp(str(payload.get("fetched_at", "")))
    kind = sanitize_token(capture_kind) or "capture"
    hint_token = sanitize_token(hint)

    base_name = f"{ts}-{kind}"
    if hint_token:
        base_name = f"{base_name}-{hint_token}"

    json_path = save_dir / f"{base_name}.json"
    md_path = save_dir / f"{base_name}.md"

    seq = 2
    while json_path.exists() or md_path.exists():
        json_path = save_dir / f"{base_name}-{seq}.json"
        md_path = save_dir / f"{base_name}-{seq}.md"
        seq += 1

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown_text, encoding="utf-8")

    return {"json": str(json_path), "markdown": str(md_path)}


def save_raw_pages(
    *,
    pages: List[Dict[str, object]],
    fetched_at: str,
    save_dir: Path,
    hint: str = "",
) -> List[str]:
    raw_dir = save_dir / "raw-latestnews"
    raw_dir.mkdir(parents=True, exist_ok=True)

    ts = capture_timestamp(fetched_at)
    hint_token = sanitize_token(hint)
    paths: List[str] = []

    for page in pages:
        page_no = int(page.get("page", 0) or 0)
        raw_md = str(page.get("raw_markdown", ""))
        if not raw_md:
            continue

        name = f"{ts}-latestnews-page-{page_no}"
        if hint_token:
            name = f"{name}-{hint_token}"

        out = raw_dir / f"{name}.md"
        seq = 2
        while out.exists():
            out = raw_dir / f"{name}-{seq}.md"
            seq += 1

        out.write_text(raw_md, encoding="utf-8")
        paths.append(str(out))

    return paths


def save_interest_note(
    *,
    title: str,
    url: str,
    summary: str,
    keywords_raw: str,
    interest_dir: Path,
    score: str = "",
    matched_keywords_raw: str = "",
    article_date: str = "",
    focus: str = "",
) -> Dict[str, object]:
    keywords = split_keywords(keywords_raw)[:MAX_INTEREST_KEYWORDS]
    matched_keywords = split_keywords(matched_keywords_raw)

    ts = dt.datetime.now(dt.timezone.utc)
    ts_name = ts.strftime("%Y-%m-%dT%H-%M-%SZ")

    slug = sanitize_token(title)[:80] or "article"
    interest_dir.mkdir(parents=True, exist_ok=True)
    out = interest_dir / f"{ts_name}-{slug}.md"
    seq = 2
    while out.exists():
        out = interest_dir / f"{ts_name}-{slug}-{seq}.md"
        seq += 1

    lines: List[str] = []
    lines.append(f"# 感兴趣文章记录 - {title}")
    lines.append("")
    lines.append(f"- 记录时间(UTC): {ts.isoformat()}")
    if article_date:
        lines.append(f"- 文章日期: {article_date}")
    if score:
        lines.append(f"- 相关度分值: {score}")
    lines.append(f"- URL: {url}")
    lines.append("")

    lines.append("## 技术向摘要")
    lines.append(summary.strip() or "(待补充)")
    lines.append("")

    lines.append("## 关键词")
    lines.append(f"- 新增候选关键词: {'、'.join(keywords) if keywords else '(无)'}")
    lines.append(f"- 列表命中关键词: {'、'.join(matched_keywords) if matched_keywords else '(无)'}")
    lines.append("")

    lines.append("## 后续关注点")
    lines.append(focus.strip() or "- 芯片/方案参数\n- 关键技术路径\n- 典型落地场景")
    lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")

    return {
        "path": str(out),
        "keywords": keywords,
        "matched_keywords": matched_keywords,
    }


# ---------- cli ----------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EEWorld latestnews reader")
    sub = parser.add_subparsers(dest="cmd", required=True)

    default_profile = default_profile_path()
    default_capture = default_capture_dir()
    default_interests = default_interests_dir()
    default_article_cache = default_article_cache_dir()

    p_article = sub.add_parser("article", help="Fetch full article markdown (local cache first)")
    p_article.add_argument("--url", required=True)
    p_article.add_argument("--max-chars", type=int, default=20000)
    p_article.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p_article.add_argument("--cache-dir", default=str(default_article_cache))
    p_article.add_argument(
        "--cache-local",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Read/write local article cache first (default: on)",
    )
    p_article.add_argument(
        "--refresh",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Force refetch and refresh local cache",
    )

    p_add = sub.add_parser("profile-add", help="Save keywords to reading profile")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--url", required=True)
    p_add.add_argument("--keywords", required=True, help="Comma/Chinese-comma separated")
    p_add.add_argument("--profile", default=str(default_profile))
    p_add.add_argument("--format", choices=["markdown", "json"], default="markdown")

    p_add_missing = sub.add_parser("profile-add-missing", help="Add only missing keywords to reading profile")
    p_add_missing.add_argument("--title", required=True)
    p_add_missing.add_argument("--url", required=True)
    p_add_missing.add_argument("--keywords", required=True, help="Comma/Chinese-comma separated")
    p_add_missing.add_argument("--profile", default=str(default_profile))
    p_add_missing.add_argument("--format", choices=["markdown", "json"], default="markdown")

    p_add_count = sub.add_parser("profile-add-count", help="Add keywords and increment count for existing ones")
    p_add_count.add_argument("--title", required=True)
    p_add_count.add_argument("--url", required=True)
    p_add_count.add_argument("--keywords", required=True, help="Comma/Chinese-comma separated")
    p_add_count.add_argument("--profile", default=str(default_profile))
    p_add_count.add_argument("--format", choices=["markdown", "json"], default="markdown")

    p_show = sub.add_parser("profile-show", help="Show profile top keywords")
    p_show.add_argument("--profile", default=str(default_profile))
    p_show.add_argument("--top", type=int, default=20)
    p_show.add_argument("--format", choices=["markdown", "json"], default="markdown")

    p_interest = sub.add_parser("interest-save", help="Save interested article note and optionally sync keywords to profile")
    p_interest.add_argument("--title", required=True)
    p_interest.add_argument("--url", required=True)
    p_interest.add_argument("--summary", required=True, help="Technical summary text")
    p_interest.add_argument("--keywords", required=True, help="New candidate keywords (max 5 kept)")
    p_interest.add_argument("--matched-keywords", default="", help="Matched keywords from ranked list")
    p_interest.add_argument("--score", default="")
    p_interest.add_argument("--date", default="")
    p_interest.add_argument("--focus", default="")
    p_interest.add_argument("--interest-dir", default=str(default_interests))
    p_interest.add_argument("--profile", default=str(default_profile))
    p_interest.add_argument(
        "--sync-profile",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Sync keywords into profile (default: on)",
    )
    p_interest.add_argument(
        "--sync-mode",
        choices=["count", "missing"],
        default="count",
        help="Keyword sync mode: count=叠加计数, missing=只补缺失",
    )
    p_interest.add_argument("--format", choices=["markdown", "json"], default="markdown")

    def add_latest_parser(name: str, help_text: str) -> None:
        p_latest = sub.add_parser(name, help=help_text)
        p_latest.add_argument("--date", action="append", required=True, help="YYYY-MM-DD or M-D")
        p_latest.add_argument("--max-pages", type=int, default=20)
        p_latest.add_argument("--profile", default=str(default_profile))
        p_latest.add_argument("--format", choices=["markdown", "json"], default="markdown")
        p_latest.add_argument(
            "--save-local",
            action=argparse.BooleanOptionalAction,
            default=True,
            help="Auto-save latest-day result and raw pages to local files (default: on)",
        )
        p_latest.add_argument("--save-dir", default=str(default_capture))

    add_latest_parser("latest-day", "Get latestnews articles for specific day(s)")
    add_latest_parser("获取某天最新文章", "获取 latestnews 某日文章")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.cmd == "article":
        payload = read_article(
            args.url,
            int(args.max_chars),
            cache_dir=Path(args.cache_dir).expanduser(),
            use_cache=bool(args.cache_local),
            refresh=bool(args.refresh),
            save_cache=bool(args.cache_local),
        )
        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            title = payload["title"] or "(无标题)"
            print(f"# {title}\n")
            print(payload["markdown"])
            if payload.get("cache_hit"):
                print("\n> 文章来源：本地缓存")
            elif payload.get("cache_files"):
                cf = payload.get("cache_files", {})
                print(f"\n> 已写入本地缓存: {cf.get('markdown')}")
        return

    if args.cmd == "profile-add":
        profile_path = Path(args.profile)
        profile = add_keywords(profile_path, args.title, args.url, args.keywords)
        if args.format == "json":
            print(json.dumps(profile, ensure_ascii=False, indent=2))
        else:
            print(f"已保存关键词到: {profile_path}")
            print_markdown_profile(profile, top_n=20)
        return

    if args.cmd == "profile-add-missing":
        profile_path = Path(args.profile)
        result = add_missing_keywords(profile_path, args.title, args.url, args.keywords)
        profile = result["profile"]
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"已补充缺失关键词到: {profile_path}")
            print(f"新增关键词: {'、'.join(result['added_keywords']) if result['added_keywords'] else '(无新增)'}")
            print(f"已存在关键词: {'、'.join(result['skipped_keywords']) if result['skipped_keywords'] else '(无)'}")
            print_markdown_profile(profile, top_n=20)
        return

    if args.cmd == "profile-add-count":
        profile_path = Path(args.profile)
        result = add_or_increment_keywords(profile_path, args.title, args.url, args.keywords)
        profile = result["profile"]
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"已写入关键词计数到: {profile_path}")
            print(f"新增关键词: {'、'.join(result['added_keywords']) if result['added_keywords'] else '(无)'}")
            print(f"计数+1关键词: {'、'.join(result['incremented_keywords']) if result['incremented_keywords'] else '(无)'}")
            print_markdown_profile(profile, top_n=20)
        return

    if args.cmd == "profile-show":
        profile_path = Path(args.profile)
        profile = load_profile(profile_path)
        if args.format == "json":
            print(json.dumps(profile, ensure_ascii=False, indent=2))
        else:
            print(f"画像文件: {profile_path}")
            print_markdown_profile(profile, top_n=max(1, int(args.top)))
        return

    if args.cmd == "interest-save":
        info = save_interest_note(
            title=args.title,
            url=args.url,
            summary=args.summary,
            keywords_raw=args.keywords,
            interest_dir=Path(args.interest_dir).expanduser(),
            score=str(args.score or ""),
            matched_keywords_raw=str(args.matched_keywords or ""),
            article_date=str(args.date or ""),
            focus=str(args.focus or ""),
        )

        sync_result: Dict[str, object] | None = None
        sync_mode = str(args.sync_mode)
        if bool(args.sync_profile):
            keyword_text = ",".join(info.get("keywords", []))
            profile_path = Path(args.profile).expanduser()
            if sync_mode == "missing":
                sync_result = add_missing_keywords(profile_path, args.title, args.url, keyword_text)
            else:
                sync_result = add_or_increment_keywords(profile_path, args.title, args.url, keyword_text)

        payload = {
            "interest_note": info,
            "profile": str(Path(args.profile).expanduser()),
            "sync_profile": bool(args.sync_profile),
            "sync_mode": sync_mode,
            "profile_sync_result": sync_result,
        }

        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"已保存兴趣记录: {info['path']}")
            if bool(args.sync_profile) and sync_result is not None:
                if sync_mode == "missing":
                    print(
                        "已补充缺失关键词: "
                        f"{'、'.join(sync_result['added_keywords']) if sync_result['added_keywords'] else '(无新增)'}"
                    )
                else:
                    print(
                        "关键词计数更新（+1）: "
                        f"{'、'.join(sync_result.get('incremented_keywords', [])) if sync_result.get('incremented_keywords') else '(无)'}"
                    )
                    print(
                        "关键词新增: "
                        f"{'、'.join(sync_result.get('added_keywords', [])) if sync_result.get('added_keywords') else '(无)'}"
                    )
        return

    if args.cmd in {"latest-day", "获取某天最新文章"}:
        raw_dates: List[str] = list(args.date or [])
        target_dates = sorted({normalize_date_token(x) for x in raw_dates}, reverse=True)
        profile_path = Path(args.profile)
        profile = load_profile(profile_path)

        items, pages = fetch_latest_by_dates(set(target_dates), int(args.max_pages))
        ranked = rank_latest_items(items, profile)

        fetched_at = dt.datetime.now(dt.timezone.utc).isoformat()
        payload: Dict[str, object] = {
            "mode": "latest-day",
            "source": LATEST_NEWS_URL,
            "dates": target_dates,
            "fetched_at": fetched_at,
            "max_pages": max(1, min(int(args.max_pages), 100)),
            "profile": str(profile_path),
            "total_items": len(ranked),
            "ranked": ranked,
            "fetched_pages": [
                {
                    "page": p.get("page"),
                    "url": p.get("url"),
                    "item_count": p.get("item_count"),
                    "dates": p.get("dates"),
                }
                for p in pages
            ],
        }

        markdown_text = render_markdown_latest(payload)
        saved_to: Dict[str, str] | None = None
        raw_saved: List[str] = []

        if bool(args.save_local):
            date_hint = "_".join(target_dates)
            save_dir = Path(args.save_dir).expanduser()

            saved_to = save_capture_payload(
                capture_kind="latest-day",
                payload=payload,
                markdown_text=markdown_text,
                save_dir=save_dir,
                hint=date_hint,
            )
            raw_saved = save_raw_pages(
                pages=pages,
                fetched_at=fetched_at,
                save_dir=save_dir,
                hint=date_hint,
            )

            payload["saved_to"] = saved_to
            payload["saved_raw_pages"] = raw_saved

        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(markdown_text, end="")
            if saved_to:
                print(
                    f"\n> 已保存抓取结果: {saved_to['markdown']}\n"
                    f"> 对应JSON: {saved_to['json']}"
                )
            if raw_saved:
                print(f"> 已保存原始 latestnews 页面: {len(raw_saved)} 份")
        return


if __name__ == "__main__":
    main()
