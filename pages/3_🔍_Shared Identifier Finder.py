import pandas as pd
import streamlit as st
from helper_functions.reconcile import analyze_sources, load_source
from helper_functions.utility import check_password


def format_dataframe_numbers(df):
    if df is None or df.empty:
        return df
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) == 0:
        return df
    fmt = {col: "{:,.2f}" for col in numeric_cols}
    return df.style.format(fmt)


def combine_uploaded_sources(uploaded_files, source_label):
    if not uploaded_files:
        return None

    dataframes = []
    fields = []
    raw_text_parts = []
    file_types = []
    file_names = []
    file_rows = []

    for uploaded_file in uploaded_files:
        source = load_source(uploaded_file)
        file_types.append(source.get("type"))
        if source.get("dataframe") is None:
            return {
                "name": source_label,
                "type": "error",
                "fields": [],
                "sample_rows": [],
                "raw_text": source.get("raw_text", ""),
                "dataframe": None,
                "files": file_names,
                "file_rows": file_rows,
                "file_types": file_types,
                "has_pdf": any(t == "PDF" for t in file_types),
            }

        df = source["dataframe"]
        file_names.append(uploaded_file.name)
        file_rows.append(len(df))
        dataframes.append(df)
        fields.extend(source["fields"])
        raw_text_parts.append(source.get("raw_text", ""))

    combined_df = pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()
    combined_fields = []
    seen = set()
    for field in fields:
        if field["name"] not in seen:
            seen.add(field["name"])
            combined_fields.append(field)

    combined_type = file_types[0] if len(set(file_types)) == 1 else "Combined"
    return {
        "name": source_label,
        "type": combined_type,
        "fields": combined_fields,
        "sample_rows": combined_df.head(5).astype(str).to_dict(orient="records"),
        "raw_text": "\n\n".join(raw_text_parts),
        "dataframe": combined_df,
        "files": file_names,
        "file_rows": file_rows,
        "file_types": file_types,
        "has_pdf": any(t == "PDF" for t in file_types),
    }

# Page configuration
st.set_page_config(
    layout="centered",
    page_title="Shared Identifier Finder",
    page_icon="🔍",
)

if not check_password():
    st.stop()

st.title("🔍 Shared Identifier Finder")
st.write(
    "Upload two reports in PDF, Excel, or CSV format and Shared Identifier Finder will identify matching fields or shared identifiers across both sources."
)

with st.expander("How it works"):
    st.write(
        "Shared  Identifier Finder uses semantic analysis and an LLM to map fields across heterogeneous documents. "
        "It does not rely on hard-coded field name matching, so it can detect a shared identifier even when it is embedded inside a description or other text field."
    )

uploaded_a = st.file_uploader("Upload first source (1 or 2 files)", type=["pdf", "csv", "xls", "xlsx"], accept_multiple_files=True, key="source_a")
uploaded_b = st.file_uploader("Upload second source (1 or 2 files)", type=["pdf", "csv", "xls", "xlsx"], accept_multiple_files=True, key="source_b")
business_context = st.text_area(
    "Optional business context",
    value="Example: Match transaction and audit records to reconcile trace IDs and descriptions.",
    height=100,
)

if uploaded_a and uploaded_b:
    with st.spinner("Parsing uploaded files..."):
        source_a = combine_uploaded_sources(uploaded_a, "Source A")
        source_b = combine_uploaded_sources(uploaded_b, "Source B")

    if source_a is None or source_b is None:
        st.error("Unable to read one or both sources. Please upload valid PDF, Excel, or CSV files.")
    elif source_a.get("type") == "error" or source_b.get("type") == "error":
        error_details = []
        if source_a.get("type") == "error":
            error_details.append(f"Source A: {source_a.get('raw_text', 'Unreadable file')}.")
        if source_b.get("type") == "error":
            error_details.append(f"Source B: {source_b.get('raw_text', 'Unreadable file')}.")
        st.error("Unable to read one or both sources. " + " ".join(error_details))
    else:
        with st.expander("Source summaries", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{source_a['name']}**")
                st.write(f"Type: {source_a['type']}")
                if source_a["fields"] and not (source_a.get("dataframe") is not None and not source_a["dataframe"].empty):
                    st.write("Fields:")
                    for field in source_a["fields"]:
                        st.write(f"- {field['name']}: {field['examples']}")
                if source_a.get("dataframe") is not None and not source_a["dataframe"].empty:
                    st.write("Detected headers:")
                    st.write(list(source_a["dataframe"].columns))
                    st.write("Extracted table sample:")
                    st.dataframe(format_dataframe_numbers(source_a["dataframe"].head(5)))
                elif source_a.get("has_pdf"):
                    st.write("PDF text excerpt:")
                    st.write(source_a["raw_text"][:1000])
                elif source_a.get("fields"):
                    st.write("Fields:")
                    for field in source_a["fields"]:
                        st.write(f"- {field['name']}: {field['examples']}")

            with col2:
                st.write(f"**{source_b['name']}**")
                st.write(f"Type: {source_b['type']}")
                if source_b["fields"] and not (source_b.get("dataframe") is not None and not source_b["dataframe"].empty):
                    st.write("Fields:")
                    for field in source_b["fields"]:
                        st.write(f"- {field['name']}: {field['examples']}")
                if source_b.get("dataframe") is not None and not source_b["dataframe"].empty:
                    st.write("Detected headers:")
                    st.write(list(source_b["dataframe"].columns))
                    st.write("Extracted table sample:")
                    st.dataframe(format_dataframe_numbers(source_b["dataframe"].head(5)))
                elif source_b.get("has_pdf"):
                    st.write("PDF text excerpt:")
                    st.write(source_b["raw_text"][:1000])
                elif source_b.get("fields"):
                    st.write("Fields:")
                    for field in source_b["fields"]:
                        st.write(f"- {field['name']}: {field['examples']}")

        if st.button("Shared Identifier Finder"):
            with st.spinner("Analyzing sources with LLM..."):
                analysis = analyze_sources(source_a, source_b, business_context)

            if not analysis:
                st.error("Unable to interpret the reconciliation result.")
            else:
                st.subheader("Shared Identifier Findings")
                if analysis.get("common_identifier"):
                    st.markdown(f"**Common Identifier:** {analysis['common_identifier']}")
                if analysis.get("field_mappings"):
                    st.write("**Field mappings:**")
                    for mapping in analysis["field_mappings"]:
                        score = mapping.get("match_score")
                        score_text = f" (Match: {score}%)" if score is not None else ""
                        st.markdown(
                            f"- `{mapping.get('source_a_field')}` ↔ `{mapping.get('source_b_field')}` — {mapping.get('relationship')}{score_text}\n  \n"
                            f"  Explanation: {mapping.get('explanation')}"
                        )
                if analysis.get("reasoning"):
                    st.write("**Reasoning:**")
                    st.write(analysis["reasoning"])
                if analysis.get("raw_response"):
                    st.write("**Raw LLM response:**")
                    st.code(analysis["raw_response"])