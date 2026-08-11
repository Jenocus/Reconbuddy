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


def record_user_reasons(field_a: str, field_b: str, reasons: dict) -> None:
    """Store user-confirmed mismatch reasons for specific identifiers under a field pair.

    reasons: {identifier_string: reason_string}
    Overwrites any existing entry for the same (field_a, field_b, identifier) triple.
    """
    kb = load_kb()
    user_reasons = kb.setdefault("user_reasons", [])
    today = str(date.today())
    existing = {
        (e["field_a"], e["field_b"], e["identifier"]): i
        for i, e in enumerate(user_reasons)
    }
    for identifier, reason in reasons.items():
        reason = reason.strip()
        if not reason:
            continue
        key = (field_a, field_b, str(identifier))
        if key in existing:
            user_reasons[existing[key]]["reason"] = reason
            user_reasons[existing[key]]["recorded_at"] = today
        else:
            user_reasons.append({
                "field_a": field_a,
                "field_b": field_b,
                "identifier": str(identifier),
                "reason": reason,
                "recorded_at": today,
            })
    save_kb(kb)


def get_user_reason_context(field_a: str, field_b: str, max_examples: int = 15) -> str:
    """Return a prompt hint with user-confirmed reasons for a specific field pair.

    The LLM can use these as labelled examples to apply the same reasoning pattern
    to new, unseen identifiers in the same pair context.
    """
    kb = load_kb()
    user_reasons = kb.get("user_reasons", [])
    relevant = [
        e for e in user_reasons
        if e["field_a"] == field_a and e["field_b"] == field_b
    ]
    if not relevant:
        return ""
    # Most recent first so the LLM sees up-to-date corrections
    relevant.sort(key=lambda e: e.get("recorded_at", ""), reverse=True)
    sample = relevant[:max_examples]
    lines = [f"  - identifier {e['identifier']!r}: {e['reason']}" for e in sample]
    return (
        f"User-confirmed mismatch reasons for identifier pair "
        f"({field_a} ↔ {field_b}) from past reconciliations "
        f"— use these as labelled examples to infer the pattern and apply it to new rows:\n"
        + "\n".join(lines)
    )


def record_flagged_reason(reason: str) -> None:
    """Increment the flag count for a reason marked as wrong by the user."""
    reason = reason.strip()
    if not reason:
        return
    kb = load_kb()
    flagged = kb.setdefault("flagged_reasons", {})
    flagged[reason] = flagged.get(reason, 0) + 1
    save_kb(kb)


def get_flagged_reason_context() -> str:
    """Return a prompt hint listing reasons flagged as wrong by users.

    The more times a reason has been flagged, the stronger the instruction to avoid it.
    """
    kb = load_kb()
    flagged = kb.get("flagged_reasons", {})
    if not flagged:
        return ""
    # Sort by flag count descending so most-flagged appear first
    top = sorted(flagged.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = [f"  - {r!r} (flagged {c} time(s) as incorrect)" for r, c in top]
    return (
        "The following reason labels have been flagged as WRONG by users — "
        "avoid using them unless there is very strong evidence:\n"
        + "\n".join(lines)
    )
