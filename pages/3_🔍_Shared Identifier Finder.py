import streamlit as st
from helper_functions.reconcile import analyze_sources, load_source
from helper_functions.utility import check_password

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

uploaded_a = st.file_uploader("Upload first report", type=["pdf", "csv", "xls", "xlsx"], key="source_a")
uploaded_b = st.file_uploader("Upload second report", type=["pdf", "csv", "xls", "xlsx"], key="source_b")
business_context = st.text_area(
    "Optional business context",
    value="Example: Match transaction and audit records to reconcile trace IDs and descriptions.",
    height=100,
)

if uploaded_a and uploaded_b:
    with st.spinner("Parsing uploaded files..."):
        source_a = load_source(uploaded_a)
        source_b = load_source(uploaded_b)

    with st.expander("Source summaries", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**{source_a['name']}**")
            st.write(f"Type: {source_a['type']}")
            if source_a["fields"]:
                st.write("Fields:")
                for field in source_a["fields"]:
                    st.write(f"- {field['name']}: {field['examples']}")
            if source_a["type"] == "PDF":
                st.write("PDF text excerpt:")
                st.write(source_a["raw_text"][:1000])

        with col2:
            st.write(f"**{source_b['name']}**")
            st.write(f"Type: {source_b['type']}")
            if source_b["fields"]:
                st.write("Fields:")
                for field in source_b["fields"]:
                    st.write(f"- {field['name']}: {field['examples']}")
            if source_b["type"] == "PDF":
                st.write("PDF text excerpt:")
                st.write(source_b["raw_text"][:1000])

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
