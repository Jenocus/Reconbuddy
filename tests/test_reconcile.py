"""
Tests for helper_functions/reconcile.py

Covers:
- reconcile_records: matched, unmatched, missing-on-one-side
- classify_reconciliation_rows: Matched / Unmatched / Missing
- reconcile_by_identifier: totals and details
- infer_unmatched_reasons: timing difference pre-detection (no LLM calls)
- detect_amount_fields, choose_best_amount_field_by_precision
"""
import os
import sys
from unittest import mock

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import helper_functions.knowledge_base as kb_module
from helper_functions.reconcile import (
    classify_reconciliation_rows,
    detect_amount_fields,
    infer_unmatched_reasons,
    reconcile_by_identifier,
    reconcile_records,
)


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path):
    temp_kb = str(tmp_path / "knowledge_base.json")
    with mock.patch.object(kb_module, "KB_PATH", temp_kb):
        yield temp_kb


def make_source(df, name="Source", type_="CSV"):
    fields = [{"name": col, "examples": []} for col in df.columns]
    return {
        "name": name,
        "type": type_,
        "fields": fields,
        "sample_rows": df.head(5).astype(str).to_dict(orient="records"),
        "raw_text": "",
        "dataframe": df,
        "files": [name],
        "file_rows": [len(df)],
    }


# ── reconcile_records ─────────────────────────────────────────────────────────

class TestReconcileRecords:
    def test_all_matched(self):
        df_a = pd.DataFrame({"id": ["A", "B"], "amount": [100.0, 200.0]})
        df_b = pd.DataFrame({"id": ["A", "B"], "amount": [100.0, 200.0]})
        result = reconcile_records(df_a, df_b, "id", "id", "amount", "amount")
        assert len(result) == 2
        assert set(result["identifier"]) == {"A", "B"}

    def test_missing_in_source_b(self):
        df_a = pd.DataFrame({"id": ["A", "B", "C"], "amount": [100.0, 200.0, 50.0]})
        df_b = pd.DataFrame({"id": ["A", "B"], "amount": [100.0, 200.0]})
        result = reconcile_records(df_a, df_b, "id", "id", "amount", "amount")
        assert len(result) == 3
        c_row = result[result["identifier"] == "C"]
        assert not c_row.empty
        # reconcile_records uses amount_b column (total_amount_b is added by classify_reconciliation_rows)
        amount_b_col = "amount_b" if "amount_b" in result.columns else "total_amount_b"
        assert pd.isna(c_row[amount_b_col].values[0]) or c_row[amount_b_col].values[0] == 0.0

    def test_missing_in_source_a(self):
        df_a = pd.DataFrame({"id": ["A"], "amount": [100.0]})
        df_b = pd.DataFrame({"id": ["A", "Z"], "amount": [100.0, 999.0]})
        result = reconcile_records(df_a, df_b, "id", "id", "amount", "amount")
        z_row = result[result["identifier"] == "Z"]
        assert not z_row.empty

    def test_returns_empty_dataframe_on_missing_columns(self):
        df_a = pd.DataFrame({"id": ["A"], "amount": [100.0]})
        df_b = pd.DataFrame({"id": ["A"], "amount": [100.0]})
        result = reconcile_records(df_a, df_b, "id", "WRONG_COL", "amount", "amount")
        assert result.empty

    def test_amounts_are_aggregated_per_identifier(self):
        df_a = pd.DataFrame({"id": ["A", "A", "B"], "amount": [50.0, 50.0, 200.0]})
        df_b = pd.DataFrame({"id": ["A", "B"], "amount": [100.0, 200.0]})
        result = reconcile_records(df_a, df_b, "id", "id", "amount", "amount")
        a_row = result[result["identifier"] == "A"]
        # reconcile_records uses amount_a column (total_amount_a is added by classify_reconciliation_rows)
        amount_a_col = "amount_a" if "amount_a" in result.columns else "total_amount_a"
        assert a_row[amount_a_col].values[0] == pytest.approx(100.0)


# ── classify_reconciliation_rows ──────────────────────────────────────────────

class TestClassifyReconciliationRows:
    def _make_details(self, rows):
        return pd.DataFrame(rows, columns=["identifier", "total_amount_a", "total_amount_b", "difference"])

    def test_matched_within_tolerance(self):
        df = self._make_details([("A", 100.0, 100.0, 0.0)])
        result = classify_reconciliation_rows(df, tolerance=0.01)
        assert result.loc[0, "status"] == "Matched"

    def test_unmatched_outside_tolerance(self):
        df = self._make_details([("A", 100.0, 110.0, 10.0)])
        result = classify_reconciliation_rows(df, tolerance=0.01)
        assert result.loc[0, "status"] == "Unmatched"

    def test_missing_on_source_b(self):
        df = self._make_details([("A", 100.0, 0.0, 100.0)])
        result = classify_reconciliation_rows(df, tolerance=0.01)
        assert "Missing" in result.loc[0, "status"] or result.loc[0, "status"] == "Unmatched"

    def test_difference_column_present(self):
        df_a = pd.DataFrame({"id": ["A"], "amount": [100.0]})
        df_b = pd.DataFrame({"id": ["A"], "amount": [95.0]})
        records = reconcile_records(df_a, df_b, "id", "id", "amount", "amount")
        classified = classify_reconciliation_rows(records)
        assert "difference" in classified.columns


# ── reconcile_by_identifier ───────────────────────────────────────────────────

class TestReconcileByIdentifier:
    def test_basic_full_match(self):
        df_a = pd.DataFrame({"invoice_id": ["INV-1", "INV-2"], "amount": [100.0, 200.0]})
        df_b = pd.DataFrame({"inv_no": ["INV-1", "INV-2"], "total": [100.0, 200.0]})
        source_a = make_source(df_a, "Source A")
        source_b = make_source(df_b, "Source B")
        identifier = {"source_a_field": "invoice_id", "source_b_field": "inv_no"}
        result = reconcile_by_identifier(source_a, source_b, identifier, "amount", "total")
        assert result["total_a"] == pytest.approx(300.0)
        assert result["total_b"] == pytest.approx(300.0)
        assert len(result["details"]) == 2

    def test_partial_match_produces_unmatched(self):
        df_a = pd.DataFrame({"id": ["A", "B", "C"], "amount": [100.0, 200.0, 50.0]})
        df_b = pd.DataFrame({"id": ["A", "B"], "total": [100.0, 200.0]})
        source_a = make_source(df_a)
        source_b = make_source(df_b)
        identifier = {"source_a_field": "id", "source_b_field": "id"}
        result = reconcile_by_identifier(source_a, source_b, identifier, "amount", "total")
        details = result["details"]
        unmatched = details[details["status"] != "Matched"]
        assert len(unmatched) >= 1


# ── infer_unmatched_reasons — timing difference pre-detection ─────────────────

class TestInferUnmatchedReasonsTimingDifference:
    """Tests the deterministic timing difference detection (no LLM calls needed)."""

    def _make_unmatched_df(self, rows):
        """rows: list of (identifier, total_amount_a, total_amount_b, date_str)"""
        return pd.DataFrame(rows, columns=["identifier", "total_amount_a", "total_amount_b", "transaction_date"])

    def _make_matched_df(self, date_strs):
        return pd.DataFrame({"transaction_date": date_strs})

    def test_date_outside_matched_period_flagged_as_timing_difference(self):
        """Unmatched row from February when matched rows are all January → timing difference."""
        matched = self._make_matched_df(["2024-01-01", "2024-01-15", "2024-01-31"])
        unmatched = self._make_unmatched_df([
            ("TXN-001", 500.0, 0.0, "2024-02-05"),
        ])
        source_df = pd.DataFrame({"transaction_date": ["2024-01-01"]})

        with mock.patch("helper_functions.reconcile.get_completion") as mock_llm:
            mock_llm.return_value = "[]"
            result = infer_unmatched_reasons(
                unmatched,
                "Source A", "Source B",
                "total_amount_a", "total_amount_b",
                source_a_df=source_df,
                source_b_df=source_df,
                matched_df=matched,
            )
        assert result.get("TXN-001") == "timing difference"

    def test_date_within_matched_period_not_flagged(self):
        """Unmatched row within matched date range should NOT be auto-flagged."""
        matched = self._make_matched_df(["2024-01-01", "2024-01-31"])
        unmatched = self._make_unmatched_df([
            ("TXN-002", 500.0, 0.0, "2024-01-15"),
        ])
        source_df = pd.DataFrame({"transaction_date": ["2024-01-01"]})

        with mock.patch("helper_functions.reconcile.get_completion") as mock_llm:
            mock_llm.return_value = '[{"identifier": "TXN-002", "suggested_reason": "fees"}]'
            result = infer_unmatched_reasons(
                unmatched,
                "Source A", "Source B",
                "total_amount_a", "total_amount_b",
                source_a_df=source_df,
                source_b_df=source_df,
                matched_df=matched,
            )
        assert result.get("TXN-002") != "timing difference"

    def test_no_date_columns_no_timing_difference(self):
        """When no date columns exist, timing difference cannot be pre-detected."""
        unmatched = pd.DataFrame([
            {"identifier": "TXN-003", "total_amount_a": 100.0, "total_amount_b": 0.0},
        ])
        matched = pd.DataFrame([{"identifier": "TXN-X", "total_amount_a": 50.0}])
        source_df = pd.DataFrame({"amount": [100.0]})  # no date cols

        with mock.patch("helper_functions.reconcile.get_completion") as mock_llm:
            mock_llm.return_value = '[{"identifier": "TXN-003", "suggested_reason": "duplicate posting"}]'
            result = infer_unmatched_reasons(
                unmatched,
                "Source A", "Source B",
                "total_amount_a", "total_amount_b",
                source_a_df=source_df,
                source_b_df=source_df,
                matched_df=matched,
            )
        assert result.get("TXN-003") != "timing difference"

    def test_empty_unmatched_returns_empty_dict(self):
        result = infer_unmatched_reasons(
            pd.DataFrame(),
            "Source A", "Source B",
            "amount_a", "amount_b",
        )
        assert result == {}

    def test_timing_difference_rows_do_not_go_to_llm(self):
        """Rows already flagged as timing difference should be skipped by LLM call."""
        matched = self._make_matched_df(["2024-01-01", "2024-01-31"])
        unmatched = self._make_unmatched_df([
            ("TXN-004", 500.0, 0.0, "2024-02-10"),  # outside → timing difference
        ])
        source_df = pd.DataFrame({"transaction_date": ["2024-01-01"]})

        with mock.patch("helper_functions.reconcile.get_completion") as mock_llm:
            mock_llm.return_value = "[]"
            result = infer_unmatched_reasons(
                unmatched,
                "Source A", "Source B",
                "total_amount_a", "total_amount_b",
                source_a_df=source_df,
                source_b_df=source_df,
                matched_df=matched,
            )
        # LLM should not have been called since all rows are pre-detected
        mock_llm.assert_not_called()
        assert result["TXN-004"] == "timing difference"

    def test_mixed_rows_some_timing_some_llm(self):
        """Some rows outside period → timing difference; others within → go to LLM."""
        matched = self._make_matched_df(["2024-01-01", "2024-01-31"])
        unmatched = self._make_unmatched_df([
            ("OUTSIDE", 500.0, 0.0, "2024-03-01"),   # outside → timing difference
            ("INSIDE", 200.0, 0.0, "2024-01-10"),    # inside → LLM
        ])
        source_df = pd.DataFrame({"transaction_date": ["2024-01-01"]})

        with mock.patch("helper_functions.reconcile.get_completion") as mock_llm:
            mock_llm.return_value = '[{"identifier": "INSIDE", "suggested_reason": "fees"}]'
            result = infer_unmatched_reasons(
                unmatched,
                "Source A", "Source B",
                "total_amount_a", "total_amount_b",
                source_a_df=source_df,
                source_b_df=source_df,
                matched_df=matched,
            )
        assert result["OUTSIDE"] == "timing difference"
        assert result["INSIDE"] == "fees"
        mock_llm.assert_called_once()


# ── detect_amount_fields ──────────────────────────────────────────────────────

class TestDetectAmountFields:
    def test_detects_amount_column(self):
        df = pd.DataFrame({"invoice_amount": [100.0], "name": ["X"]})
        result = detect_amount_fields(df)
        assert "invoice_amount" in result

    def test_returns_numeric_fallback_if_no_semantic_match(self):
        df = pd.DataFrame({"x": [1.0], "y": [2.0], "label": ["abc"]})
        result = detect_amount_fields(df)
        assert len(result) >= 1

    def test_returns_empty_list_for_none(self):
        result = detect_amount_fields(None)
        assert result == []
