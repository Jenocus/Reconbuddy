"""
Tests for helper_functions/knowledge_base.py

Covers:
- KB I/O (load/save)
- record_confirmed_pairing (create + increment)
- record_mismatch_reasons (accumulate)
- record_user_reasons (create + overwrite)
- record_flagged_reason (create + increment)
- get_pairing_context (relevant filtering, empty guard)
- get_mismatch_reason_context (top-5, empty guard)
- get_user_reason_context (field pair filter, max_examples, empty guard)
- get_flagged_reason_context (top-10, empty guard)
- End-to-end learning: save reason → context injected on next call
"""
import json
import os
import sys
import tempfile
from unittest import mock

import pytest

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import helper_functions.knowledge_base as kb_module
from helper_functions.knowledge_base import (
    get_flagged_reason_context,
    get_mismatch_reason_context,
    get_pairing_context,
    get_user_reason_context,
    load_kb,
    record_confirmed_pairing,
    record_flagged_reason,
    record_mismatch_reasons,
    record_user_reasons,
    save_kb,
)


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path):
    """Redirect all KB reads/writes to a temp file for test isolation."""
    temp_kb = str(tmp_path / "knowledge_base.json")
    with mock.patch.object(kb_module, "KB_PATH", temp_kb):
        yield temp_kb


# ── load / save ───────────────────────────────────────────────────────────────

class TestLoadSave:
    def test_load_returns_defaults_when_file_missing(self):
        kb = load_kb()
        assert kb["pairings"] == []
        assert kb["mismatch_reasons"] == {}

    def test_save_and_reload_roundtrip(self, isolated_kb):
        data = {"pairings": [{"field_a": "x", "field_b": "y", "use_count": 3}], "mismatch_reasons": {"fees": 2}}
        save_kb(data)
        assert load_kb() == data

    def test_load_handles_corrupt_json(self, isolated_kb):
        with open(isolated_kb, "w") as f:
            f.write("not valid json {{")
        kb = load_kb()
        assert kb["pairings"] == []


# ── record_confirmed_pairing ──────────────────────────────────────────────────

class TestRecordConfirmedPairing:
    def test_creates_new_pairing(self):
        record_confirmed_pairing("invoice_id", "inv_no")
        kb = load_kb()
        assert len(kb["pairings"]) == 1
        assert kb["pairings"][0]["field_a"] == "invoice_id"
        assert kb["pairings"][0]["use_count"] == 1

    def test_increments_existing_pairing(self):
        record_confirmed_pairing("invoice_id", "inv_no")
        record_confirmed_pairing("invoice_id", "inv_no")
        kb = load_kb()
        assert len(kb["pairings"]) == 1
        assert kb["pairings"][0]["use_count"] == 2

    def test_different_pairs_stored_separately(self):
        record_confirmed_pairing("invoice_id", "inv_no")
        record_confirmed_pairing("trace_id", "ref_num")
        kb = load_kb()
        assert len(kb["pairings"]) == 2


# ── record_mismatch_reasons ───────────────────────────────────────────────────

class TestRecordMismatchReasons:
    def test_accumulates_counts(self):
        record_mismatch_reasons({"timing difference": 3, "fees": 1})
        record_mismatch_reasons({"timing difference": 2, "duplicate posting": 5})
        kb = load_kb()
        assert kb["mismatch_reasons"]["timing difference"] == 5
        assert kb["mismatch_reasons"]["fees"] == 1
        assert kb["mismatch_reasons"]["duplicate posting"] == 5

    def test_ignores_empty_reason(self):
        record_mismatch_reasons({"": 10, "fees": 1})
        kb = load_kb()
        assert "" not in kb["mismatch_reasons"]
        assert kb["mismatch_reasons"]["fees"] == 1


# ── record_user_reasons ───────────────────────────────────────────────────────

class TestRecordUserReasons:
    def test_stores_new_reasons(self):
        record_user_reasons("invoice_id", "inv_no", {"TXN-001": "timing difference", "TXN-002": "fees"})
        kb = load_kb()
        assert len(kb["user_reasons"]) == 2

    def test_overwrites_existing_identifier(self):
        record_user_reasons("invoice_id", "inv_no", {"TXN-001": "timing difference"})
        record_user_reasons("invoice_id", "inv_no", {"TXN-001": "fees"})
        kb = load_kb()
        assert len(kb["user_reasons"]) == 1
        assert kb["user_reasons"][0]["reason"] == "fees"

    def test_ignores_blank_reason(self):
        record_user_reasons("invoice_id", "inv_no", {"TXN-001": "  ", "TXN-002": "fees"})
        kb = load_kb()
        assert len(kb["user_reasons"]) == 1
        assert kb["user_reasons"][0]["identifier"] == "TXN-002"

    def test_different_pairs_stored_independently(self):
        record_user_reasons("invoice_id", "inv_no", {"TXN-001": "fees"})
        record_user_reasons("trace_id", "ref_num", {"TXN-001": "timing difference"})
        kb = load_kb()
        assert len(kb["user_reasons"]) == 2


# ── record_flagged_reason ─────────────────────────────────────────────────────

class TestRecordFlaggedReason:
    def test_creates_new_flag(self):
        record_flagged_reason("missing invoice")
        kb = load_kb()
        assert kb["flagged_reasons"]["missing invoice"] == 1

    def test_increments_flag_count(self):
        record_flagged_reason("missing invoice")
        record_flagged_reason("missing invoice")
        kb = load_kb()
        assert kb["flagged_reasons"]["missing invoice"] == 2

    def test_ignores_blank_reason(self):
        record_flagged_reason("   ")
        kb = load_kb()
        assert kb.get("flagged_reasons", {}) == {}


# ── get_pairing_context ───────────────────────────────────────────────────────

class TestGetPairingContext:
    def test_returns_empty_when_no_pairings(self):
        assert get_pairing_context(["invoice_id"], ["inv_no"]) == ""

    def test_returns_relevant_pairing(self):
        record_confirmed_pairing("invoice_id", "inv_no")
        result = get_pairing_context(["invoice_id", "amount"], ["inv_no", "total"])
        assert "invoice_id" in result
        assert "inv_no" in result

    def test_ignores_irrelevant_pairings(self):
        record_confirmed_pairing("trace_id", "ref_num")
        result = get_pairing_context(["invoice_id"], ["inv_no"])
        assert result == ""

    def test_returns_top_3_sorted_by_use_count(self):
        for _ in range(5):
            record_confirmed_pairing("f1", "g1")
        for _ in range(3):
            record_confirmed_pairing("f2", "g2")
        for _ in range(1):
            record_confirmed_pairing("f3", "g3")
        result = get_pairing_context(["f1", "f2", "f3"], ["g1", "g2", "g3"])
        # f1 should appear before f2 (higher use count)
        assert result.index("f1") < result.index("f2")


# ── get_mismatch_reason_context ───────────────────────────────────────────────

class TestGetMismatchReasonContext:
    def test_returns_empty_when_no_reasons(self):
        assert get_mismatch_reason_context() == ""

    def test_returns_top_reasons(self):
        record_mismatch_reasons({"timing difference": 10, "fees": 5, "duplicate posting": 3})
        result = get_mismatch_reason_context()
        assert "timing difference" in result
        assert "fees" in result

    def test_limits_to_five_reasons(self):
        record_mismatch_reasons({f"reason_{i}": i for i in range(10)})
        result = get_mismatch_reason_context()
        # Top 5 reasons should appear; reason_0 (count=0) should not dominate
        lines = [l for l in result.splitlines() if l.strip().startswith("-")]
        assert len(lines) == 5


# ── get_user_reason_context ───────────────────────────────────────────────────

class TestGetUserReasonContext:
    def test_returns_empty_when_no_examples(self):
        assert get_user_reason_context("invoice_id", "inv_no") == ""

    def test_filters_to_correct_pair(self):
        record_user_reasons("invoice_id", "inv_no", {"TXN-001": "fees"})
        record_user_reasons("trace_id", "ref_num", {"TXN-002": "timing difference"})
        result = get_user_reason_context("invoice_id", "inv_no")
        assert "fees" in result
        assert "timing difference" not in result

    def test_respects_max_examples(self):
        reasons = {f"ID-{i}": "fees" for i in range(20)}
        record_user_reasons("invoice_id", "inv_no", reasons)
        result = get_user_reason_context("invoice_id", "inv_no", max_examples=5)
        assert result.count("ID-") == 5

    def test_includes_identifier_in_output(self):
        record_user_reasons("invoice_id", "inv_no", {"TXN-999": "settlement delay"})
        result = get_user_reason_context("invoice_id", "inv_no")
        assert "TXN-999" in result
        assert "settlement delay" in result


# ── get_flagged_reason_context ────────────────────────────────────────────────

class TestGetFlaggedReasonContext:
    def test_returns_empty_when_no_flags(self):
        assert get_flagged_reason_context() == ""

    def test_includes_flagged_reason(self):
        record_flagged_reason("missing invoice")
        result = get_flagged_reason_context()
        assert "missing invoice" in result
        assert "WRONG" in result.upper() or "avoid" in result.lower()

    def test_includes_flag_count(self):
        record_flagged_reason("missing invoice")
        record_flagged_reason("missing invoice")
        result = get_flagged_reason_context()
        assert "2" in result

    def test_limits_to_ten_reasons(self):
        for i in range(15):
            record_flagged_reason(f"bad reason {i}")
        result = get_flagged_reason_context()
        lines = [l for l in result.splitlines() if l.strip().startswith("-")]
        assert len(lines) == 10


# ── End-to-end KB learning ────────────────────────────────────────────────────

class TestEndToEndKBLearning:
    def test_saved_reason_appears_in_future_prompt_context(self):
        """Simulate: user saves a reason → next reconciliation LLM gets it as a hint."""
        record_user_reasons("invoice_id", "inv_no", {"TXN-001": "settlement delay"})
        context = get_user_reason_context("invoice_id", "inv_no")
        assert "settlement delay" in context
        assert "TXN-001" in context

    def test_flagged_reason_appears_in_avoidance_context(self):
        """Simulate: user flags a reason → next LLM call gets a 'avoid this' hint."""
        record_flagged_reason("missing invoice")
        context = get_flagged_reason_context()
        assert "missing invoice" in context

    def test_overwritten_reason_reflects_correction(self):
        """Simulate: user corrects a wrong reason → context shows updated reason."""
        record_user_reasons("invoice_id", "inv_no", {"TXN-001": "timing difference"})
        record_user_reasons("invoice_id", "inv_no", {"TXN-001": "fees"})  # correction
        context = get_user_reason_context("invoice_id", "inv_no")
        assert "fees" in context
        assert context.count("TXN-001") == 1  # only one entry per identifier

    def test_pairing_use_count_grows_across_sessions(self):
        """Simulate: same field pair used across multiple reconciliation sessions."""
        for _ in range(3):
            record_confirmed_pairing("invoice_id", "inv_no")
        kb = load_kb()
        pair = next(p for p in kb["pairings"] if p["field_a"] == "invoice_id")
        assert pair["use_count"] == 3
        context = get_pairing_context(["invoice_id"], ["inv_no"])
        assert "3 time" in context
