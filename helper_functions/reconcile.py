import json
from io import BytesIO

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
            source["raw_text"] = parse_pdf(uploaded_file)
            return source
        else:
            source["type"] = "unknown"
            source["raw_text"] = uploaded_file.read().decode(errors="replace")
            return source

        source["raw_text"] = df.head(20).to_csv(index=False)
        source["sample_rows"] = df.head(5).astype(str).to_dict(orient="records")
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
        source_a_field = mapping.get("source_a_field") or ""
        source_b_field = mapping.get("source_b_field") or ""
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


def reconcile_by_identifier(source_a, source_b, identifier_choice, amount_field_a, amount_field_b):
    id_a = identifier_choice["source_a_field"]
    id_b = identifier_choice["source_b_field"]

    grouped_a = group_amount_by_identifier(source_a.get("dataframe"), id_a, amount_field_a)
    grouped_b = group_amount_by_identifier(source_b.get("dataframe"), id_b, amount_field_b)

    if grouped_a.empty or grouped_b.empty:
        return {
            "grouped_a": grouped_a,
            "grouped_b": grouped_b,
            "joined": pd.DataFrame(),
            "total_a": grouped_a["total_amount"].sum() if not grouped_a.empty else 0,
            "total_b": grouped_b["total_amount"].sum() if not grouped_b.empty else 0,
        }

    joined = pd.merge(
        grouped_a,
        grouped_b,
        on="identifier",
        how="outer",
        suffixes=("_a", "_b"),
    )
    joined["total_amount_a"] = joined["total_amount_a"].fillna(0)
    joined["total_amount_b"] = joined["total_amount_b"].fillna(0)
    joined["difference"] = joined["total_amount_a"] - joined["total_amount_b"]
    joined = joined.sort_values(by="difference", key=lambda col: col.abs(), ascending=False)

    return {
        "grouped_a": grouped_a,
        "grouped_b": grouped_b,
        "joined": joined,
        "total_a": grouped_a["total_amount"].sum(),
        "total_b": grouped_b["total_amount"].sum(),
    }
