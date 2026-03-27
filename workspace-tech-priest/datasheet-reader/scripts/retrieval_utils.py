#!/usr/bin/env python3
"""
retrieval_utils.py - Hybrid retrieval helpers for datasheet chunks.

Goal:
- improve beyond simple heading keyword matching
- combine exact matching, token overlap, domain synonym expansion,
  and fuzzy character n-gram similarity
- stay dependency-light (stdlib only)
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Dict, Iterable, List, Sequence, Set, Tuple


DOMAIN_SYNONYMS: Dict[str, Sequence[str]] = {
    "decoupling": ["bypass", "capacitor", "capacitors", "去耦", "旁路", "滤波", "电容"],
    "bypass": ["decoupling", "去耦", "旁路", "电容"],
    "reset": ["nrst", "rst", "resetb", "复位"],
    "boot": ["boot0", "boot1", "启动", "引导"],
    "power": ["vdd", "vcc", "vdda", "vbat", "supply", "电源", "供电"],
    "ground": ["gnd", "vss", "vssa", "地"],
    "analog": ["adc", "analog", "vdda", "vssa", "模拟"],
    "digital": ["gpio", "digital", "数字"],
    "clock": ["osc", "xtal", "crystal", "clock", "时钟", "晶振"],
    "warning": ["warning", "caution", "important", "警告", "注意", "重要"],
    "note": ["note", "remark", "注", "注意"],
    "package": ["footprint", "land", "package", "封装", "焊盘"],
    "timing": ["timing", "latency", "时序", "建立时间", "保持时间"],
    "uart": ["usart", "serial", "串口"],
    "i2c": ["twi", "i2c", "scl", "sda"],
    "spi": ["mosi", "miso", "sck", "nss", "spi"],
    "current": ["icc", "idd", "current", "电流"],
    "voltage": ["vdd", "vcc", "voltage", "电压"],
}

PIN_RE = re.compile(r"\bP[A-Z]\d{1,2}\b", re.IGNORECASE)
ELECTRICAL_HINT_RE = re.compile(
    r"\b(VDD|VCC|VDDA|VSSA|VBAT|ICC|IDD|IOH|IOL|VIL|VIH|current|voltage|电压|电流)\b",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("µ", "u").replace("μ", "u")
    text = text.lower()
    text = re.sub(r"[\t\r\n]+", " ", text)
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff_./+\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    text = normalize_text(text)
    tokens = re.findall(r"p[a-z]\d{1,2}|[a-z][a-z0-9_./+\-]*|\d+(?:\.\d+)?|[\u4e00-\u9fff]{1,8}", text)
    return [t for t in tokens if t]


def expand_query_tokens(query: str) -> Set[str]:
    base = set(tokenize(query))
    expanded = set(base)
    normalized_query = normalize_text(query)

    for token in list(base):
        if token in DOMAIN_SYNONYMS:
            expanded.update(DOMAIN_SYNONYMS[token])

    for root, synonyms in DOMAIN_SYNONYMS.items():
        if root in normalized_query or any(s in normalized_query for s in synonyms):
            expanded.add(root)
            expanded.update(synonyms)

    # normalize expansions too
    return {normalize_text(t) for t in expanded if normalize_text(t)}


def char_ngrams(text: str, n: int = 3) -> Counter:
    compact = normalize_text(text).replace(" ", "")
    if not compact:
        return Counter()
    if len(compact) < n:
        return Counter([compact])
    return Counter(compact[i:i + n] for i in range(len(compact) - n + 1))


def cosine_counter(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0) for k in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def infer_query_intent(query: str) -> str:
    q = normalize_text(query)
    if PIN_RE.search(q):
        return "pin"
    if ELECTRICAL_HINT_RE.search(q) or re.search(r"\b\d+(?:\.\d+)?\s*(v|a|ma|ua|ns|us|ms|mhz|khz)\b", q):
        return "electrical"
    if any(w in q for w in ["note", "warning", "caution", "注意", "警告", "important"]):
        return "note"
    if any(w in q for w in ["decoupling", "bypass", "reset", "boot", "crystal", "xtal", "clock", "circuit", "schematic", "去耦", "晶振", "复位"]):
        return "circuit"
    if any(w in q for w in ["package", "footprint", "land pattern", "封装", "焊盘"]):
        return "package"
    if any(w in q for w in ["timing", "setup", "hold", "latency", "时序", "建立", "保持"]):
        return "timing"
    return "general"


def section_intent_bonus(intent: str, chunk: Dict) -> float:
    section = normalize_text(chunk.get("section", ""))
    chunk_type = normalize_text(chunk.get("chunk_type", ""))

    if intent == "pin" and (section == "io" or chunk_type == "pin"):
        return 1.5
    if intent == "electrical" and (section == "electrical" or chunk_type in ("electrical_param", "electrical_paragraph")):
        return 1.2
    if intent == "note" and chunk_type == "note":
        return 1.2
    if intent == "circuit" and section in ("circuit", "notes"):
        return 1.0
    if intent == "package" and section == "package":
        return 1.0
    if intent == "timing" and section == "timing":
        return 1.0
    return 0.0


def build_search_blob(chunk: Dict) -> str:
    fields = [
        chunk.get("part", ""),
        chunk.get("section", ""),
        chunk.get("chunk_type", ""),
        chunk.get("heading", ""),
        chunk.get("pin_name", ""),
        chunk.get("param", ""),
        chunk.get("type", ""),
        chunk.get("text", ""),
    ]
    return " ".join(str(x) for x in fields if x)


def score_chunk(query: str, chunk: Dict, mode: str = "hybrid") -> Tuple[float, Dict]:
    q_norm = normalize_text(query)
    blob = build_search_blob(chunk)
    blob_norm = normalize_text(blob)

    q_tokens = expand_query_tokens(query)
    r_tokens = set(tokenize(blob_norm))

    exact_phrase = 1.0 if q_norm and q_norm in blob_norm else 0.0
    exact_token_hits = len(q_tokens & r_tokens)
    token_overlap = exact_token_hits / max(len(q_tokens), 1)

    q_ngrams = char_ngrams(q_norm)
    r_ngrams = char_ngrams(blob_norm)
    fuzzy = cosine_counter(q_ngrams, r_ngrams)

    intent = infer_query_intent(query)
    intent_bonus = section_intent_bonus(intent, chunk)

    if mode == "exact":
        score = 5.0 * exact_phrase + 3.0 * token_overlap + 0.25 * fuzzy + intent_bonus
    elif mode == "semantic":
        score = 1.0 * exact_phrase + 2.2 * token_overlap + 2.0 * fuzzy + intent_bonus
    else:  # hybrid
        score = 3.5 * exact_phrase + 2.6 * token_overlap + 1.2 * fuzzy + intent_bonus

    if q_norm and blob_norm.startswith(q_norm):
        score += 0.4
    if chunk.get("chunk_type") == "note" and any(w in q_norm for w in ["note", "warning", "caution", "注意", "警告"]):
        score += 0.5

    meta = {
        "exact_phrase": exact_phrase,
        "exact_token_hits": exact_token_hits,
        "token_overlap": round(token_overlap, 4),
        "fuzzy": round(fuzzy, 4),
        "intent": intent,
        "intent_bonus": round(intent_bonus, 4),
    }
    return score, meta


def rank_chunks(
    query: str,
    chunks: Iterable[Dict],
    mode: str = "hybrid",
    section_filter: str | None = None,
    top_k: int = 20,
) -> List[Dict]:
    ranked = []
    for chunk in chunks:
        if section_filter and normalize_text(chunk.get("section", "")) != normalize_text(section_filter):
            continue
        score, meta = score_chunk(query, chunk, mode=mode)
        if score <= 0:
            continue
        item = dict(chunk)
        item["score"] = round(score, 4)
        item["score_meta"] = meta
        ranked.append(item)

    ranked.sort(key=lambda x: (x.get("score", 0), x.get("page", 0)), reverse=True)
    return ranked[:top_k]
