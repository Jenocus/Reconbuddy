import streamlit as st
from helper_functions.reconcile import (
    analyze_sources,
    detect_amount_fields,
    group_amount_by_identifier,
    get_identifier_candidates,
    load_source,
    reconcile_by_identifier,
)
from helper_functions.utility import check_password

# Page configuration
st.set_page_config(
    layout="centered",
    page_title="ReconBuddy",
    page_icon="🧾",
)

if not check_password():
    st.stop()

st.title("🧾 ReconBuddy")
st.write(
    "Upload two reports and use a shared identifier to reconcile amounts across both sources."
)

with st.expander("How it works"):
    st.write(
        "This page uses the shared identifier mappings discovered by the previous page to perform an amount reconciliation. "
        "You can choose a different identifier candidate and compare totals for each source."
    )

uploaded_a = st.file_uploader("Upload first report", type=["pdf", "csv", "xls", "xlsx"], key="recon_a")
uploaded_b = st.file_uploader("Upload second report", type=["pdf", "csv", "xls", "xlsx"], key="recon_b")
business_context = st.text_area(
    "Optional business context",
    value="Example: Reconcile amounts using the shared transaction or trace identifier.",
    height=100,
)

if uploaded_a and uploaded_b:
    with st.spinner("Parsing uploaded files..."):
        source_a = load_source(uploaded_a)
        source_b = load_source(uploaded_b)

    if source_a.get("dataframe") is None or source_b.get("dataframe") is None:
        st.error("Amount reconciliation requires both files to be CSV or Excel.")
    else:
        with st.expander("Source summaries", expanded=False):
            st.write(f"**{source_a['name']}**")
            st.write(f"Type: {source_a['type']}")
            st.write(f"Fields: {[field['name'] for field in source_a['fields']]}")
            st.write(f"**{source_b['name']}**")
            st.write(f"Type: {source_b['type']}")
            st.write(f"Fields: {[field['name'] for field in source_b['fields']]}" )

        if st.button("Run Reconciliation"):
            with st.spinner("Finding shared identifier candidates..."):
                analysis = analyze_sources(source_a, source_b, business_context)
                candidates = get_identifier_candidates(analysis)

            if not candidates:
                st.error("No shared identifier candidates were found.")
            else:
                selected = st.selectbox(
                    "Select identifier pair to reconcile",
                    options=candidates,
                    format_func=lambda item: item["label"],
                )

                amount_fields_a = detect_amount_fields(source_a["dataframe"])
                amount_fields_b = detect_amount_fields(source_b["dataframe"])

                col1, col2 = st.columns(2)
                with col1:
                    amount_a = st.selectbox("Amount field in first report", amount_fields_a)
                with col2:
                    amount_b = st.selectbox("Amount field in second report", amount_fields_b)

                if st.button("Perform amount reconciliation"):
                    result = reconcile_by_identifier(
                        source_a,
                        source_b,
                        selected,
                        amount_a,
                        amount_b,
                    )

                    st.subheader("Reconcilation Results")
                    st.write(f"Source A total: {result['total_a']}")
                    st.write(f"Source B total: {result['total_b']}")
                    if not result["joined"].empty:
                        st.write("**Reconciliation by identifier**")
                        st.dataframe(result["joined"].head(100))
                    else:
                        st.warning("No matching identifiers were found in both sources.")
