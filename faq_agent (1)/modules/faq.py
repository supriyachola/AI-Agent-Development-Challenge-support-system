# modules/faq.py
import json
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

# Paths
FAQ_PATH = Path("data/faq.json")
COUNTS_PATH = Path("data/top_counts.json")
ESCALATIONS_PATH = Path("data/escalations.json")

# Ensure data dir exists
FAQ_PATH.parent.mkdir(parents=True, exist_ok=True)

# Load FAQ
if FAQ_PATH.exists():
    try:
        with FAQ_PATH.open("r", encoding="utf-8") as f:
            FAQ = json.load(f)
            if not isinstance(FAQ, list):
                FAQ = []
    except Exception:
        FAQ = []
else:
    FAQ = []

# Initialize counts and escalations if missing
if not COUNTS_PATH.exists():
    COUNTS_PATH.write_text(json.dumps({}, indent=2), encoding="utf-8")
if not ESCALATIONS_PATH.exists():
    ESCALATIONS_PATH.write_text(json.dumps([], indent=2), encoding="utf-8")

# Optional LLM fallback import (if you have one)
try:
    from modules.llm import llm_fallback  # type: ignore
except Exception:
    llm_fallback = None  # type: ignore

# Internal helpers
def _load_counts() -> Dict[str, Dict[str, Any]]:
    try:
        return json.loads(COUNTS_PATH.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}

def _save_counts(counts: Dict[str, Dict[str, Any]]) -> None:
    COUNTS_PATH.write_text(json.dumps(counts, indent=2, ensure_ascii=False), encoding="utf-8")

def _increment_count(question_text: str) -> None:
    counts = _load_counts()
    entry = counts.get(question_text, {"count": 0, "last_asked": ""})
    entry["count"] = int(entry.get("count", 0)) + 1
    entry["last_asked"] = datetime.utcnow().isoformat() + "Z"
    counts[question_text] = entry
    _save_counts(counts)

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()

def _log_escalation(record: Dict[str, Any]) -> None:
    try:
        existing = json.loads(ESCALATIONS_PATH.read_text(encoding="utf-8") or "[]")
    except Exception:
        existing = []
    existing.append(record)
    ESCALATIONS_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

# Public API
def answer_question(query: str, cutoff: float = 0.55, escalate_threshold: float = 0.40
                   ) -> Tuple[str, Optional[Dict[str, Any]], float, str]:
    """
    Returns: (answer_text, matched_entry_or_None, confidence_float, resolution)
    resolution is 'resolved' or 'escalate'
    """
    q = (query or "").strip()
    if not q:
        return "Please enter a question.", None, 0.0, "escalate"

    # Find best FAQ match
    best = None
    best_score = 0.0
    for item in FAQ:
        score = _similarity(q, item.get("question", ""))
        if score > best_score:
            best_score = score
            best = item

    # Good match => resolved
    if best and best_score >= cutoff:
        matched = best.copy()
        matched["confidence"] = round(best_score, 3)
        _increment_count(matched.get("question", ""))
        return matched.get("answer", ""), matched, matched["confidence"], "resolved"

    # Partial match => recommend escalation (still return matched answer)
    if best and best_score >= escalate_threshold:
        matched = best.copy()
        matched["confidence"] = round(best_score, 3)
        _increment_count(matched.get("question", ""))
        return matched.get("answer", ""), matched, matched["confidence"], "escalate"

    # No good match => try LLM fallback (if available)
    context = "\n".join([f"Q: {it.get('question')}\nA: {it.get('answer')}" for it in FAQ])
    prompt = f"FAQ Context:\n{context}\n\nUser question: {q}\nProvide a short, helpful answer (one paragraph)."

    if llm_fallback:
        try:
            llm_ans = llm_fallback(prompt)
            # log as attempted resolution but mark escalate (human review recommended)
            return llm_ans, None, 0.0, "escalate"
        except Exception:
            pass

    # final fallback
    return "No close FAQ match — please contact support or provide more details.", None, 0.0, "escalate"

def get_faqs_by_tag(tag: Optional[str] = None):
    if not tag:
        return FAQ
    return [it for it in FAQ if tag in it.get("tags", [])]

def get_all_tags():
    tags = set()
    for it in FAQ:
        for t in it.get("tags", []):
            tags.add(t)
    return sorted(tags)

def top_asked(n: int = 10):
    counts = _load_counts()
    # counts is question -> {"count":N, "last_asked":TS}
    items = sorted(
        ((q, data.get("count", 0)) for q, data in counts.items()),
        key=lambda x: x[1],
        reverse=True,
    )
    return items[:n]

def log_escalation(question: str, context: Optional[str] = None,
                   matched: Optional[Dict[str, Any]] = None, confidence: float = 0.0,
                   tags: Optional[list] = None) -> None:
    rec = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "question": question,
        "context": context or "",
        "matched": matched,
        "confidence": float(confidence or 0.0),
        "tags": tags or (matched.get("tags") if matched else []),
    }
    _log_escalation(rec)

def reload_faq():
    global FAQ
    if FAQ_PATH.exists():
        try:
            with FAQ_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    FAQ = data
                else:
                    FAQ = []
        except Exception:
            FAQ = []
    else:
        FAQ = []

__all__ = [
    "answer_question",
    "get_faqs_by_tag",
    "get_all_tags",
    "top_asked",
    "log_escalation",
    "reload_faq",
    "FAQ_PATH",
    "COUNTS_PATH",
    "ESCALATIONS_PATH",
]
