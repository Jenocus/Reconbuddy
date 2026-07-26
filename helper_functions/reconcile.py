import json
import re
from collections import Counter
from io import BytesIO
from itertools import zip_longest

import pandas as pd
import streamlit as st
from PyPDF2 import PdfReader

from helper_functions.llm import get_completion


def parse_pdf(file) -> str:
    file.seek(0)
    reader = PdfReader(BytesIO(file.read()))
    text_pages = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text:
            text_pages.append(page_text)
    return "\n\n".join(text_pages)


def parse_pdf_text_table(raw_text: str) -> pd.DataFrame:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return pd.DataFrame()

    splitter = re.compile(r"\s{2,}")
    split_lines = [splitter.split(line) for line in lines]

    if len(split_lines) >= 2:
        header = split_lines[0]
        data_rows = [row for row in split_lines[1:] if len(row) == len(header)]
        if len(header) >= 2 and len(data_rows) >= max(2, len(split_lines) // 3):
            header_tokens = [cell.strip() for cell in header]
            non_numeric_header = sum(1 for cell in header_tokens if not re.fullmatch(r"[\d\W_]+", cell))
            if non_numeric_header >= len(header) / 2:
                columns = [col or f"column_{i+1}" for i, col in enumerate(header_tokens)]
                return pd.DataFrame(data_rows, columns=columns)

    lengths = [len(row) for row in split_lines]
    most_common = Counter(lengths).most_common(1)
    if most_common and most_common[0][0] > 1 and most_common[0][1] >= 3:
        expected = most_common[0][0]
        rows = [row for row in split_lines if len(row) == expected]
        if len(rows) >= 3:
            columns = [f"column_{i+1}" for i in range(expected)]
            return pd.DataFrame(rows, columns=columns)

    return pd.DataFrame()


def parse_table(file, file_type: str):
    file.seek(0)
    if file_type == "csv":
        return pd.read_csv(file)
    return pd.read_excel(file, engine="openpyxl", sheet_name=0)


def load_source(uploaded_file):
    name = uploaded_file.name
    lower = name.lower()
    source = {
        "name": name,
        "type": None,
        "fields": [],
        "sample_rows": [],
        "raw_text": "",
        "dataframe": None,
    }

    try:
        if lower.endswith(".csv"):
            df = parse_table(uploaded_file, "csv")
            source["type"] = "CSV"
            source["dataframe"] = df
        elif lower.endswith(('.xls', '.xlsx')):
            df = parse_table(uploaded_file, "excel")
            source["type"] = "Excel"
            source["dataframe"] = df
        elif lower.endswith(".pdf"):
            source["type"] = "PDF"
            raw_text = parse_pdf(uploaded_file)
            source["raw_text"] = raw_text
            df = parse_pdf_text_table(raw_text)
            source["dataframe"] = df
        else:
            source["type"] = "unknown"
            source["raw_text"] = uploaded_file.read().decode(errors="replace")
            return source

        source["raw_text"] = df.head(20).to_csv(index=False) if not df.empty else raw_text
        source["sample_rows"] = df.head(5).astype(str).to_dict(orient="records") if not df.empty else []
        source["fields"] = []
        for col in df.columns:
            values = df[col].dropna().astype(str).unique()[:4].tolist()
            source["fields"].append({
                "name": str(col),
                "examples": values,
            })
    except Exception as exc:
        source["type"] = "error"
        source["raw_text"] = f"Unable to parse file: {exc}"

    return source


def build_reconciliation_prompt(source_a, source_b, business_context: str = "") -> str:
    def describe(source):
        if source["type"] == "PDF":
            raw = source["raw_text"][:1200].replace('"', "'")
            return (
                f"Source '{source['name']}' is a PDF.\n" 
                f"Raw text excerpt:\n{raw}\n"
            )

        fields = source["fields"]
        fields_text = "\n".join(
            f"- {field['name']}: examples={field['examples']}" for field in fields
        )
        sample_text = json.dumps(source["sample_rows"], indent=2) if source["sample_rows"] else "No sample rows available."
        return (
            f"Source '{source['name']}' is a {source['type']} file.\n"
            f"Fields:\n{fields_text}\n"
            f"Sample rows:\n{sample_text}\n"
        )

    prompt = [
        "You are a data reconciliation assistant. Given two sources with different formats, identify which fields or identifiers across both documents should be matched for reconciliation.",
        "Focus on semantic matching instead of exact field name equality. If a common identifier appears inside a longer text field such as a description, identify that relationship explicitly.",
        "Produce output in strict JSON with the keys: field_mappings, common_identifier, and reasoning.",
        "field_mappings should be a list of objects with source_a_field, source_b_field, relationship, explanation, and match_score.",
        "common_identifier should be the best shared unique identifier or reconciliation key across both sources.",
        "reasoning should explain why that key or match is likely the best reconciliation anchor.",
        "match_score should be a percentage between 0 and 100 representing how well the fields align semantically.",
        "If a source has no column names, use the raw text clues to identify fields.",
    ]
    if business_context:
        prompt.append(f"Business context: {business_context}")
    prompt.append("Source A:\n" + describe(source_a))
    prompt.append("Source B:\n" + describe(source_b))
    prompt.append(
        "Return only valid JSON. Do not add any Markdown or extra text."
    )
    return "\n\n".join(prompt)


def parse_reconciliation_response(response_text: str):
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(response_text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return {"raw_response": response_text}


def analyze_sources(source_a, source_b, business_context: str = ""):
    prompt = build_reconciliation_prompt(source_a, source_b, business_context)
    result_text = get_completion([
        {"role": "system", "content": "You are a reconciliation and data-mapping expert."},
        {"role": "user", "content": prompt},
    ], temperature=0)
    return parse_reconciliation_response(result_text)


def parse_json_response(response_text: str):
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(response_text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return None


def infer_unmatched_reasons(
    unmatched_df,
    source_a_name: str,
    source_b_name: str,
    amount_field_a: str,
    amount_field_b: str,
    max_rows: int = 20,
):
    if unmatched_df is None or unmatched_df.empty:
        return {}

    sample = unmatched_df.head(max_rows)[[
        "identifier",
        "total_amount_a",
        "total_amount_b",
        "status",
        "reason",
    ]].fillna("")

    rows = sample.to_dict(orient="records")
    prompt = (
        "You are a financial reconciliation analyst. Review the following unmatched reconciliation rows from two sources. "
        "For each row, infer the most likely reason the amounts do not align, focusing on timing and period differences. "
        "Assume the sources may represent different reporting windows (monthly batches, rolling periods, or statement dates). "
        "Identify date-related fields in the samples and use them to determine whether one report is outside the other report's period. "
        "If one source appears to include a date outside the other source's reporting period, label it as a timing difference. "
        "Prefer explanations such as timing difference, period mismatch, settlement delay, duplicate posting, currency variation, fees, or data extraction mismatches. "
        "Do not use missing invoice as a reason. "
        "Respond only with valid JSON in this format: [\n"
        "  { \"identifier\": ..., \"suggested_reason\": ... },\n"
        "]\n"
        "Do not add any markdown or extra text."
    )
    prompt += "\n\n" + json.dumps(rows, indent=2)

    response_text = get_completion([
        {"role": "system", "content": "You are a concise and accurate reconciliation analyst."},
        {"role": "user", "content": prompt},
    ], temperature=0)

    suggestions = parse_json_response(response_text)
    if not isinstance(suggestions, list):
        return {}

    output = {}
    for item in suggestions:
        identifier = item.get("identifier")
        reason = item.get("suggested_reason")
        if identifier is not None and reason is not None:
            output[str(identifier)] = str(reason)
    return output


def describe_source_for_summary(source):
    if source is None:
        return "Source information is unavailable."

    fields = [field["name"] for field in source.get("fields", [])][:8]
    field_list = ", ".join(fields) if fields else "no detected field names"
    file_names = source.get("files") or [source.get("name", "Unnamed source")]
    file_summary = ", ".join(file_names)
    row_count = len(source.get("dataframe", pd.DataFrame())) if source.get("dataframe") is not None else 0
    return (
        f"{source.get('name', 'Source')} is a {source.get('type', 'unknown')} source containing {row_count:,} rows, "
        f"parsed from {file_summary}. Key fields include {field_list}."
    )


def summarize_reconciliation_insights(
    source_a,
    source_b,
    matched_amount_a,
    matched_amount_b,
    unmatched_total_a,
    unmatched_total_b,
    total_a,
    total_b,
    matched_count,
    unmatched_count,
    reason_counts,
    top_reasons,
):
    prompt = [
        {"role": "system", "content": "You are a factual financial reconciliation analyst. Produce a concise executive summary using only the data provided."},
        {
            "role": "user",
            "content": (
                "Review the two sources and the reconciliation results below. "
                "Explain what each source is, why the two sources should or should not match, and highlight the main patterns and risks. "
                "Do not invent details that are not present in the source descriptions. "
                "Include specific facts about source type, row counts, matched amounts, unmatched exposure, and the top unmatched reasons. "
                "Use clear language suitable for a business executive."
            ),
        },
        {
            "role": "user",
            "content": (
                "Source A description:\n" + describe_source_for_summary(source_a) + "\n\n"
                "Source B description:\n" + describe_source_for_summary(source_b) + "\n\n"
                "Reconciliation metrics:\n"
                f"- Source A total amount: {total_a:,.2f}, matched amount: {matched_amount_a:,.2f}.\n"
                f"- Source B total amount: {total_b:,.2f}, matched amount: {matched_amount_b:,.2f}.\n"
                f"- Matched identifiers: {matched_count:,}, unmatched identifiers: {unmatched_count:,}.\n"
                f"- Unmatched exposure in Source A: {unmatched_total_a:,.2f}; Source B: {unmatched_total_b:,.2f}.\n"
            ),
        },
    ]

    if not reason_counts.empty:
        reason_lines = []
        for _, row in reason_counts.head(5).iterrows():
            reason_lines.append(f"- {row['reason']}: {int(row['count'])}")
        prompt.append({
            "role": "user",
            "content": "Top unmatched reasons:\n" + "\n".join(reason_lines) + "\n",
        })

    if top_reasons:
        prompt.append({
            "role": "user",
            "content": "Top reason labels: " + ", ".join(top_reasons) + ".\n",
        })

    prompt.append({"role": "user", "content": "Return a single concise executive summary. Do not add numbered JSON or markdown formatting."})

    response_text = get_completion(prompt, temperature=0.2)
    return response_text.strip()


def normalize_score(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(round(value))
    text = str(value).strip().rstrip("%")
    try:
        return int(round(float(text)))
    except ValueError:
        return None


def get_identifier_candidates(analysis):
    candidates = []
    for mapping in analysis.get("field_mappings", []):
        source_a_field = (mapping.get("source_a_field") or "").strip()
        source_b_field = (mapping.get("source_b_field") or "").strip()
        if not source_a_field or not source_b_field:
            continue
        score = normalize_score(mapping.get("match_score"))
        label = f"{source_a_field} ↔ {source_b_field}"
        if score is not None:
            label = f"{label} ({score}%)"
        candidates.append({
            "label": label,
            "source_a_field": source_a_field,
            "source_b_field": source_b_field,
            "score": score,
        })
    return candidates


def detect_amount_fields(df):
    if df is None:
        return []
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    candidates = [
        c for c in numeric_cols
        if any(token in c.lower() for token in ["amount", "amt", "total", "value", "price", "cost", "charge"])
    ]
    if candidates:
        return candidates
    if numeric_cols:
        return numeric_cols
    return df.columns.tolist()


def group_amount_by_identifier(df, id_field, amount_field):
    if df is None or id_field not in df.columns or amount_field not in df.columns:
        return pd.DataFrame()

    grouped = df[[id_field, amount_field]].copy()
    grouped = grouped.dropna(subset=[id_field])
    grouped[amount_field] = pd.to_numeric(grouped[amount_field], errors="coerce").fillna(0)
    grouped = grouped.groupby(id_field, dropna=False)[amount_field].sum().reset_index()
    grouped = grouped.sort_values(by=amount_field, ascending=False)
    grouped.columns = ["identifier", "total_amount"]
    return grouped


def reconcile_by_identifier(source_a, source_b, identifier_choice, amount_field_a, amount_field_b, tolerance=0.01):
    id_a = identifier_choice["source_a_field"]
    id_b = identifier_choice["source_b_field"]

    grouped_a = group_amount_by_identifier(source_a.get("dataframe"), id_a, amount_field_a)
    grouped_b = group_amount_by_identifier(source_b.get("dataframe"), id_b, amount_field_b)
    details = reconcile_records(
        source_a.get("dataframe"),
        source_b.get("dataframe"),
        id_a,
        id_b,
        amount_field_a,
        amount_field_b,
    )
    details = classify_reconciliation_rows(details, tolerance=tolerance)

    return {
        "grouped_a": grouped_a,
        "grouped_b": grouped_b,
        "details": details,
        "total_a": grouped_a["total_amount"].sum(),
        "total_b": grouped_b["total_amount"].sum(),
    }


def reconcile_records(df_a, df_b, key_a, key_b, amount_a, amount_b):
    if (
        df_a is None
        or df_b is None
        or key_a not in df_a.columns
        or amount_a not in df_a.columns
        or key_b not in df_b.columns
        or amount_b not in df_b.columns
    ):
        return pd.DataFrame(columns=["identifier", "amount_a", "amount_b", "left_present", "right_present"])

    a = df_a[[key_a, amount_a]].copy()
    b = df_b[[key_b, amount_b]].copy()
    a.columns = ["identifier", "amount_a"]
    b.columns = ["identifier", "amount_b"]
    a["amount_a"] = pd.to_numeric(a["amount_a"], errors="coerce")
    b["amount_b"] = pd.to_numeric(b["amount_b"], errors="coerce")

    a = a.dropna(subset=["identifier"]).astype({"identifier": str})
    b = b.dropna(subset=["identifier"]).astype({"identifier": str})

    agg_a = a.groupby("identifier", dropna=False, sort=False)["amount_a"].sum().reset_index()
    agg_b = b.groupby("identifier", dropna=False, sort=False)["amount_b"].sum().reset_index()

    rows = []
    used_a = set()
    used_b = set()

    for idx_b, row_b in agg_b.iterrows():
        b_id = str(row_b["identifier"])
        match_idx_a = None
        for idx_a, row_a in agg_a.iterrows():
            if idx_a in used_a:
                continue
            a_id = str(row_a["identifier"])
            if a_id == b_id or (b_id and a_id and b_id.lower() in a_id.lower()) or (a_id and b_id and a_id.lower() in b_id.lower()):
                match_idx_a = idx_a
                break

        if match_idx_a is not None:
            used_a.add(match_idx_a)
            used_b.add(idx_b)
            matched_a = agg_a.loc[match_idx_a]
            rows.append({
                "identifier": matched_a["identifier"],
                "amount_a": float(matched_a["amount_a"]),
                "amount_b": float(row_b["amount_b"]),
                "left_present": True,
                "right_present": True,
            })
        else:
            rows.append({
                "identifier": b_id,
                "amount_a": None,
                "amount_b": float(row_b["amount_b"]),
                "left_present": False,
                "right_present": True,
            })

    for idx_a, row_a in agg_a.iterrows():
        if idx_a in used_a:
            continue
        rows.append({
            "identifier": row_a["identifier"],
            "amount_a": float(row_a["amount_a"]),
            "amount_b": None,
            "left_present": True,
            "right_present": False,
        })

    if not rows:
        return pd.DataFrame(columns=["identifier", "amount_a", "amount_b", "left_present", "right_present"])

    return pd.DataFrame(rows)


def merge_identifier_groups(grouped_a, grouped_b):
    if grouped_a.empty and grouped_b.empty:
        return pd.DataFrame(columns=["identifier", "total_amount_a", "total_amount_b", "difference"])

    grouped_a = grouped_a.copy().reset_index(drop=True)
    grouped_b = grouped_b.copy().reset_index(drop=True)
    grouped_a["total_amount_a"] = grouped_a["total_amount"]
    grouped_b["total_amount_b"] = grouped_b["total_amount"]
    grouped_a = grouped_a[["identifier", "total_amount_a"]]
    grouped_b = grouped_b[["identifier", "total_amount_b"]]

    exact_ids = set(grouped_a["identifier"].astype(str).unique()) & set(grouped_b["identifier"].astype(str).unique())
    if exact_ids:
        joined = pd.merge(
            grouped_a,
            grouped_b,
            on="identifier",
            how="outer",
        )
        joined["total_amount_a"] = joined["total_amount_a"].fillna(0)
        joined["total_amount_b"] = joined["total_amount_b"].fillna(0)
        joined["difference"] = joined["total_amount_a"] - joined["total_amount_b"]
        return joined

    joined_rows = []
    used_a = set()
    used_b = set()
    for index_b, row_b in grouped_b.iterrows():
        b_id = str(row_b["identifier"])
        match_index_a = None
        for index_a, row_a in grouped_a.iterrows():
            if index_a in used_a:
                continue
            a_id = str(row_a["identifier"])
            if b_id and a_id and (b_id.lower() in a_id.lower() or a_id.lower() in b_id.lower()):
                match_index_a = index_a
                break

        if match_index_a is not None:
            used_a.add(match_index_a)
            used_b.add(index_b)
            joined_rows.append({
                "identifier": grouped_a.loc[match_index_a, "identifier"],
                "total_amount_a": grouped_a.loc[match_index_a, "total_amount_a"],
                "total_amount_b": row_b["total_amount_b"],
            })
        else:
            joined_rows.append({
                "identifier": b_id,
                "total_amount_a": 0,
                "total_amount_b": row_b["total_amount_b"],
            })

    for index_a, row_a in grouped_a.iterrows():
        if index_a in used_a:
            continue
        joined_rows.append({
            "identifier": row_a["identifier"],
            "total_amount_a": row_a["total_amount_a"],
            "total_amount_b": 0,
        })

    joined = pd.DataFrame(joined_rows)
    joined["difference"] = joined["total_amount_a"] - joined["total_amount_b"]
    return joined


def classify_reconciliation_rows(joined, tolerance=0.01):
    rows = []
    for _, row in joined.iterrows():
        a = row.get("total_amount_a") if "total_amount_a" in row else row.get("amount_a")
        b = row.get("total_amount_b") if "total_amount_b" in row else row.get("amount_b")
        diff = None
        try:
            diff = a - b if a is not None and b is not None else None
        except Exception:
            diff = None

        if pd.isna(a) and pd.isna(b):
            status = "Missing on both sides"
            reason = "No amounts available"
        elif a is None or pd.isna(a) or a == 0:
            status = "Unmatched"
            reason = "Missing on source A"
        elif b is None or pd.isna(b) or b == 0:
            status = "Unmatched"
            reason = "Missing on source B"
        elif diff is not None and abs(diff) <= tolerance:
            status = "Matched"
            reason = ""
        else:
            status = "Unmatched"
            reason = "Mismatch"

        rows.append({
            "identifier": row.get("identifier"),
            "total_amount_a": a,
            "total_amount_b": b,
            "difference": diff,
            "status": status,
            "reason": reason,
        })
    return pd.DataFrame(rows)


def build_output_files(recon_df, source_a, source_b):
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        source_a["dataframe"].to_excel(writer, sheet_name="Source A", index=False)
        source_b["dataframe"].to_excel(writer, sheet_name="Source B", index=False)
        recon_df.to_excel(writer, sheet_name="Reconciliation", index=False)
    excel_buffer.seek(0)

    csv_buffer = BytesIO()
    recon_df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return excel_buffer, csv_buffer
