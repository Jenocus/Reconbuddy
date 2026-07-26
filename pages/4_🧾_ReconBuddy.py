import streamlit as st
from helper_functions.reconcile import (
    analyze_sources,
    build_output_files,
    detect_amount_fields,
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

        if st.button("Find identifier candidates"):
            with st.spinner("Finding shared identifier candidates..."):
                analysis = analyze_sources(source_a, source_b, business_context)
                st.session_state.recon_analysis = analysis
                st.session_state.recon_candidates = get_identifier_candidates(analysis)

        candidates = st.session_state.get("recon_candidates", [])

        if candidates:
            st.success(f"Found {len(candidates)} identifier candidate(s).")
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
                tolerance = st.number_input(
                    "Amount tolerance",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.01,
                    step=0.01,
                    format="%.4f",
                )
            with col2:
                amount_b = st.selectbox("Amount field in second report", amount_fields_b)

            if st.button("Run Reconciliation"):
                result = reconcile_by_identifier(
                    source_a,
                    source_b,
                    selected,
                    amount_a,
                    amount_b,
                    tolerance=tolerance,
                )

                details = result["details"]
                totals = {
                    "Total A": result["total_a"],
                    "Total B": result["total_b"],
                    "Matched": int(details[details["status"] == "Matched"].shape[0]) if not details.empty else 0,
                    "Unmatched": int(details[details["status"] == "Unmatched"].shape[0]) if not details.empty else 0,
                }

                st.subheader("Reconciliation Results")
                metrics = st.columns(3)
                metrics[0].metric("Source A total", totals["Total A"])
                metrics[1].metric("Source B total", totals["Total B"])
                metrics[2].metric("Matched rows", totals["Matched"])

                if not details.empty:
                    unmatched = details[details["status"] != "Matched"]
                    reason_counts = unmatched["reason"].value_counts().rename_axis("reason").reset_index(name="count")
                    if not reason_counts.empty:
                        st.bar_chart(reason_counts.set_index("reason"))

                    all_tab, matched_tab, unmatched_tab = st.tabs(["All", "Matched", "Unmatched"])
                    with all_tab:
                        st.dataframe(details)
                    with matched_tab:
                        st.dataframe(details[details["status"] == "Matched"])
                    with unmatched_tab:
                        st.dataframe(details[details["status"] != "Matched"])

                    excel_data, csv_data = build_output_files(details, source_a, source_b)
                    st.download_button(
                        "Download reconciliation Excel",
                        data=excel_data,
                        file_name="reconciliation.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    st.download_button(
                        "Download reconciliation CSV",
                        data=csv_data,
                        file_name="reconciliation.csv",
                        mime="text/csv",
                    )
                else:
                    st.warning("No reconciliation rows were produced.")
        else:
            if "recon_candidates" in st.session_state:
                st.error("No shared identifier candidates were found.")
