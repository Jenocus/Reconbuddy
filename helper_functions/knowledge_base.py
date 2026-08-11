import json
import os
from datetime import date

KB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base.json")


def load_kb() -> dict:
    if not os.path.exists(KB_PATH):
        return {"pairings": [], "mismatch_reasons": {}}
    try:
        with open(KB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"pairings": [], "mismatch_reasons": {}}


def save_kb(kb: dict) -> None:
    try:
        with open(KB_PATH, "w", encoding="utf-8") as f:
            json.dump(kb, f, indent=2)
    except OSError:
        pass


def record_confirmed_pairing(field_a: str, field_b: str) -> None:
    """Increment use count for a confirmed field pairing, or create a new entry."""
    kb = load_kb()
    for entry in kb["pairings"]:
        if entry["field_a"] == field_a and entry["field_b"] == field_b:
            entry["use_count"] = entry.get("use_count", 0) + 1
            entry["last_used"] = str(date.today())
            save_kb(kb)
            return
    kb["pairings"].append({
        "field_a": field_a,
        "field_b": field_b,
        "use_count": 1,
        "last_used": str(date.today()),
    })
    save_kb(kb)


def record_mismatch_reasons(reason_counts: dict) -> None:
    """Accumulate mismatch reason frequencies. reason_counts: {reason_string: int_count}"""
    kb = load_kb()
    for reason, count in reason_counts.items():
        if reason:
            kb["mismatch_reasons"][reason] = kb["mismatch_reasons"].get(reason, 0) + int(count)
    save_kb(kb)


def get_pairing_context(fields_a: list, fields_b: list) -> str:
    """Return a prompt hint about confirmed pairings whose fields appear in the current sources."""
    kb = load_kb()
    pairings = kb.get("pairings", [])
    if not pairings:
        return ""
    fields_a_lower = {str(f).lower() for f in fields_a}
    fields_b_lower = {str(f).lower() for f in fields_b}
    relevant = [
        p for p in pairings
        if p["field_a"].lower() in fields_a_lower and p["field_b"].lower() in fields_b_lower
    ]
    if not relevant:
        return ""
    top = sorted(relevant, key=lambda p: p.get("use_count", 0), reverse=True)[:3]
    lines = [
        f"- {p['field_a']} ↔ {p['field_b']} (used {p['use_count']} time(s), last on {p['last_used']})"
        for p in top
    ]
    return "Previously confirmed field pairings from past reconciliations:\n" + "\n".join(lines)


def get_mismatch_reason_context() -> str:
    """Return a prompt hint listing the most common historical mismatch reasons."""
    kb = load_kb()
    reasons = kb.get("mismatch_reasons", {})
    if not reasons:
        return ""
    top = sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:5]
    lines = [f"- {r} ({c} occurrence(s))" for r, c in top]
    return (
        "Historically observed mismatch reasons from past reconciliations (prefer these labels when applicable):\n"
        + "\n".join(lines)
    )
