import pandas as pd
import streamlit as st
from helper_functions.reconcile import (
    analyze_sources,
    build_output_files,
    detect_amount_fields,
    get_identifier_candidates,
    infer_unmatched_reasons,
    load_source,
    reconcile_by_identifier,
)
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

    file_names = []
    file_row_counts = []
    for uploaded_file in uploaded_files:
        source = load_source(uploaded_file)
        if source.get("dataframe") is None:
            return {
                "name": source_label,
                "type": "error",
                "fields": [],
                "sample_rows": [],
                "raw_text": source.get("raw_text", ""),
                "dataframe": None,
                "files": file_names,
                "file_rows": file_row_counts,
            }
        df = source["dataframe"]
        file_names.append(uploaded_file.name)
        file_row_counts.append(len(df))
        dataframes.append(df)
        fields.extend(source["fields"])
        raw_text_parts.append(source.get("raw_text", ""))

    combined_df = pd.concat(dataframes, ignore_index=True)
    combined_fields = []
    seen = set()
    for field in fields:
        if field["name"] not in seen:
            seen.add(field["name"])
            combined_fields.append(field)

    return {
        "name": source_label,
        "type": "Combined",
        "fields": combined_fields,
        "sample_rows": combined_df.head(5).astype(str).to_dict(orient="records"),
        "raw_text": "\n\n".join(raw_text_parts),
        "dataframe": combined_df,
        "files": file_names,
        "file_rows": file_row_counts,
    }

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

uploaded_a = st.file_uploader("Upload first source (1 or 2 files)", type=["pdf", "csv", "xls", "xlsx"], accept_multiple_files=True, key="recon_a")
uploaded_b = st.file_uploader("Upload second source (1 or 2 files)", type=["pdf", "csv", "xls", "xlsx"], accept_multiple_files=True, key="recon_b")
business_context = st.text_area(
    "Optional business context",
    value="Example: Reconcile amounts using the shared transaction or trace identifier.",
    height=100,
)

if uploaded_a and uploaded_b:
    with st.spinner("Parsing uploaded files..."):
        source_a = combine_uploaded_sources(uploaded_a, "Source A")
        source_b = combine_uploaded_sources(uploaded_b, "Source B")

    if source_a.get("dataframe") is None or source_b.get("dataframe") is None:
        st.error("Amount reconciliation requires each source to be CSV or Excel files.")
    else:
        with st.expander("Source summaries", expanded=False):
            st.write(f"**{source_a['name']}**")
            st.write(f"Type: {source_a['type']}")
            st.markdown(
                f"<span title='This count includes all files uploaded into Source A.'>Combined rows: {len(source_a['dataframe']):,}</span>",
                unsafe_allow_html=True,
            )
            if source_a.get("files"):
                source_a_files = [f"{name} ({rows} rows)" for name, rows in zip(source_a['files'], source_a.get('file_rows', []))]
                st.write(f"Combined from: {', '.join(source_a_files)}")
            st.write(f"Fields: {[field['name'] for field in source_a['fields']]}")
            st.write(f"**{source_b['name']}**")
            st.write(f"Type: {source_b['type']}")
            st.markdown(
                f"<span title='This count includes all files uploaded into Source B.'>Combined rows: {len(source_b['dataframe']):,}</span>",
                unsafe_allow_html=True,
            )
            if source_b.get("files"):
                source_b_files = [f"{name} ({rows} rows)" for name, rows in zip(source_b['files'], source_b.get('file_rows', []))]
                st.write(f"Combined from: {', '.join(source_b_files)}")
            st.write(f"Fields: {[field['name'] for field in source_b['fields']]}" )

        if (
            "recon_candidates" not in st.session_state
            or st.session_state.get("recon_a_name") != source_a["name"]
            or st.session_state.get("recon_b_name") != source_b["name"]
        ):
            with st.spinner("Finding shared identifier candidates..."):
                analysis = analyze_sources(source_a, source_b, business_context)
                st.session_state.recon_analysis = analysis
                st.session_state.recon_candidates = get_identifier_candidates(analysis)
                st.session_state.recon_a_name = source_a["name"]
                st.session_state.recon_b_name = source_b["name"]

        candidates = st.session_state.get("recon_candidates", [])

        if candidates:
            st.success(f"Found {len(candidates)} identifier candidate(s).")
            selected = st.selectbox(
                "Select identifier pair to reconcile",
                options=candidates,
                format_func=lambda item: item["label"],
            )

            amount_fields_a = list(source_a["dataframe"].columns)
            amount_fields_b = list(source_b["dataframe"].columns)

            default_amount_a = detect_amount_fields(source_a["dataframe"])
            default_amount_b = detect_amount_fields(source_b["dataframe"])
            default_a = default_amount_a[0] if default_amount_a else amount_fields_a[0]
            default_b = default_amount_b[0] if default_amount_b else amount_fields_b[0]

            col1, col2 = st.columns(2)
            with col1:
                amount_a = st.selectbox("Amount field in first report", amount_fields_a, index=amount_fields_a.index(default_a))
                tolerance = st.number_input(
                    "Amount tolerance",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.01,
                    step=0.01,
                    format="%.4f",
                )
            with col2:
                amount_b = st.selectbox("Amount field in second report", amount_fields_b, index=amount_fields_b.index(default_b))

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
                metrics = st.columns(4)
                metrics[0].metric("Source A total $", f"{totals['Total A']:,.2f}")
                metrics[1].metric("Source B total $", f"{totals['Total B']:,.2f}")
                metrics[2].markdown(
                    f"**Matched identifiers**<br><span style='color:green;font-size:24px'>{totals['Matched']:,}</span>",
                    unsafe_allow_html=True,
                )
                metrics[3].markdown(
                    f"**Unmatched identifiers**<br><span style='color:red;font-size:24px'>{totals['Unmatched']:,}</span>",
                    unsafe_allow_html=True,
                )

                if not details.empty:
                    unmatched = details[details["status"] != "Matched"]
                    matched = details[details["status"] == "Matched"]
                    matched_amount_a = matched["total_amount_a"].sum()
                    matched_amount_b = matched["total_amount_b"].sum()
                    if totals["Total A"] != 0:
                        pct_matched_a = matched_amount_a / totals["Total A"] * 100
                    else:
                        pct_matched_a = 0.0
                    if totals["Total B"] != 0:
                        pct_matched_b = matched_amount_b / totals["Total B"] * 100
                    else:
                        pct_matched_b = 0.0
                    row_metrics = st.columns(2)
                    row_metrics[0].metric(
                        "Rows in Source A",
                        f"{len(source_a['dataframe']):,}",
                        f"{pct_matched_a:.1f}% matched",
                    )
                    row_metrics[1].metric(
                        "Rows in Source B",
                        f"{len(source_b['dataframe']):,}",
                        f"{pct_matched_b:.1f}% matched",
                    )

                    suggestion_map = infer_unmatched_reasons(
                        unmatched,
                        source_a["name"],
                        source_b["name"],
                        amount_a,
                        amount_b,
                    )
                    details["suggested_reason"] = details["identifier"].astype(str).map(suggestion_map).fillna("")
                    details_styled = format_dataframe_numbers(details)

                    unmatched_total_a = unmatched["total_amount_a"].sum()
                    unmatched_total_b = unmatched["total_amount_b"].sum()
                    unmatched_difference = unmatched_total_a - unmatched_total_b
                    matched_count = int(details[details["status"] == "Matched"].shape[0])
                    unmatched_count = int(unmatched.shape[0])

                    if totals["Total A"] != 0:
                        pct_unmatched_a = unmatched_total_a / totals["Total A"] * 100
                    else:
                        pct_unmatched_a = 0.0
                    if totals["Total B"] != 0:
                        pct_unmatched_b = unmatched_total_b / totals["Total B"] * 100
                    else:
                        pct_unmatched_b = 0.0

                    summary_lines = [
                        f"**Executive Summary**",
                        f"{unmatched_count:,} unmatched identifier(s) were found, representing {unmatched_total_a:,.2f} in Source A and {unmatched_total_b:,.2f} in Source B.",
                        f"This is {pct_unmatched_a:.1f}% of Source A total and {pct_unmatched_b:.1f}% of Source B total.",
                    ]

                    if unmatched_count == 0:
                        summary_lines.append("All reconciled identifiers matched within the tolerance.")
                    else:
                        if abs(unmatched_difference) > 0:
                            diff_text = f"Source A is {'higher' if unmatched_difference > 0 else 'lower'} by {abs(unmatched_difference):,.2f} for unmatched amounts."
                            summary_lines.append(diff_text)
                        if pct_unmatched_a > pct_unmatched_b:
                            summary_lines.append("Source A has a larger unmatched exposure proportionally.")
                        elif pct_unmatched_b > pct_unmatched_a:
                            summary_lines.append("Source B has a larger unmatched exposure proportionally.")
                        else:
                            summary_lines.append("Both sources have similar unmatched exposure proportions.")

                    reason_counts = unmatched["reason"].value_counts().rename_axis("reason").reset_index(name="count")
                    top_reasons = reason_counts.head(3)["reason"].tolist()
                    if top_reasons:
                        summary_lines.append(f"Top unmatched reasons: {', '.join(top_reasons)}.")

                    st.info("\n\n".join(summary_lines))

                    chart_cols = st.columns(2)
                    exposure_data = pd.DataFrame(
                        {
                            "Source": [source_a["name"], source_b["name"]],
                            "Matched Amount": [matched_amount_a, matched_amount_b],
                            "Unmatched Amount": [unmatched_total_a, unmatched_total_b],
                        }
                    ).set_index("Source")

                    if not reason_counts.empty:
                        chart_cols[0].subheader("Unmatched reason counts")
                        chart_cols[0].bar_chart(reason_counts.set_index("reason"))
                    else:
                        chart_cols[0].info("No unmatched reason counts available.")

                    chart_cols[1].subheader("Amount exposure by source")
                    chart_cols[1].bar_chart(exposure_data)

                    unmatched_ids_a = unmatched[unmatched["total_amount_a"].notna()]["identifier"].astype(str).unique().tolist()
                    unmatched_ids_b = unmatched[unmatched["total_amount_b"].notna()]["identifier"].astype(str).unique().tolist()
                    unmatched_a_rows = source_a["dataframe"][source_a["dataframe"][selected["source_a_field"]].astype(str).isin(unmatched_ids_a)] if selected["source_a_field"] in source_a["dataframe"].columns else pd.DataFrame()
                    unmatched_b_rows = source_b["dataframe"][source_b["dataframe"][selected["source_b_field"]].astype(str).isin(unmatched_ids_b)] if selected["source_b_field"] in source_b["dataframe"].columns else pd.DataFrame()

                    all_tab, matched_tab, unmatched_tab = st.tabs([
                        "All",
                        f"Matched ({matched_count})",
                        f"Unmatched ({unmatched_count})",
                    ])
                    with all_tab:
                        st.dataframe(details_styled)
                    with matched_tab:
                        st.dataframe(format_dataframe_numbers(details[details["status"] == "Matched"]))
                    with unmatched_tab:
                        st.markdown(f"### Unmatched rows ({unmatched_count})")
                        st.markdown(
                            f"**Unmatched total in Source A:** {unmatched_total_a:,.2f}  \
                            **Unmatched total in Source B:** {unmatched_total_b:,.2f}"
                        )
                        st.dataframe(format_dataframe_numbers(details[details["status"] != "Matched"]))
                        st.markdown(f"**Unmatched rows from Source A (total {unmatched_total_a:,.2f})**")
                        st.dataframe(format_dataframe_numbers(unmatched_a_rows))
                        st.markdown(f"**Unmatched rows from Source B (total {unmatched_total_b:,.2f})**")
                        st.dataframe(format_dataframe_numbers(unmatched_b_rows))

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
