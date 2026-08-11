import altair as alt
import pandas as pd
import re
import streamlit as st
from helper_functions.reconcile import (
    analyze_sources,
    amount_field_match_score,
    build_output_files,
    choose_amount_field,
    choose_best_amount_field_by_precision,
    detect_amount_fields,
    get_identifier_candidates,
    infer_unmatched_reasons,
    load_source,
    reconcile_by_identifier,
    summarize_reconciliation_insights,
    _infer_decimal_precision,
)
from helper_functions.knowledge_base import record_confirmed_pairing, record_mismatch_reasons
from helper_functions.utility import check_password


def format_dataframe_numbers(df):
    if df is None or df.empty:
        return df
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) == 0:
        return df
    fmt = {col: "{:,.2f}" for col in numeric_cols}
    return df.style.format(fmt)


def normalize_column_name(name: str) -> str:
    if name is None:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def combine_uploaded_sources(uploaded_files, source_label):
    if not uploaded_files:
        return None

    dataframes = []
    fields = []
    raw_text_parts = []
    file_types = []

    file_names = []
    file_row_counts = []
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
                "file_rows": file_row_counts,
                "file_types": file_types,
                "has_pdf": any(t == "PDF" for t in file_types),
            }
        df = source["dataframe"]
        file_names.append(uploaded_file.name)
        file_row_counts.append(len(df))
        dataframes.append(df)
        fields.extend(source["fields"])
        raw_text_parts.append(source.get("raw_text", ""))

    # Normalize column names across uploaded files so totals reflect all joined sources.
    normalized_frames = []
    normalized_order = []
    display_names = {}
    for df in dataframes:
        renamed_columns = {}
        for col in df.columns:
            normalized_name = normalize_column_name(col)
            renamed_columns[col] = normalized_name
            if normalized_name not in display_names:
                display_names[normalized_name] = col
            if normalized_name not in normalized_order:
                normalized_order.append(normalized_name)
        normalized_frames.append(df.rename(columns=renamed_columns))

    combined_df = pd.concat(normalized_frames, ignore_index=True, sort=False)

    # If a source has both a main amount column and a refund column, create a Net amount column.
    if "net_amount" not in combined_df.columns:
        amount_field_candidates = [
            col for col in combined_df.columns
            if any(token in normalize_column_name(col) for token in ["amount", "amt", "total", "value", "price", "cost", "charge"])
            and not any(ref in normalize_column_name(col) for ref in ["refund", "refunded", "rebate", "chargeback", "return"])
        ]
        refund_field_candidates = [
            col for col in combined_df.columns
            if any(ref in normalize_column_name(col) for ref in ["refund", "refunded", "rebate", "chargeback", "return"])
        ]
        if amount_field_candidates and refund_field_candidates:
            amount_col = max(amount_field_candidates, key=lambda col: _infer_decimal_precision(combined_df[col]) or 0)
            refund_col = max(refund_field_candidates, key=lambda col: _infer_decimal_precision(combined_df[col]) or 0)
            combined_df["net_amount"] = (
                pd.to_numeric(combined_df[amount_col], errors="coerce").fillna(0)
                - pd.to_numeric(combined_df[refund_col], errors="coerce").fillna(0)
            )
            if "net_amount" not in normalized_order:
                normalized_order.append("net_amount")
            if "net_amount" not in display_names:
                display_names["net_amount"] = "Net amount"

    # Convert normalized column names back to the original display labels so downstream
    # code works with the same field names that were shown in the source summary.
    combined_df = combined_df.rename(columns=display_names)
    canonical_columns = [display_names[norm] for norm in normalized_order if norm in display_names]
    combined_df = combined_df.reindex(columns=canonical_columns)

    combined_fields = [{"name": display_names[norm], "examples": []} for norm in normalized_order if norm in combined_df.columns]
    normalization_map = {display_names[norm]: norm for norm in normalized_order if norm in combined_df.columns}

    combined_type = file_types[0] if len(set(file_types)) == 1 else "Combined"
    return {
        "name": source_label,
        "type": combined_type,
        "fields": combined_fields,
        "sample_rows": combined_df.head(5).astype(str).to_dict(orient="records"),
        "raw_text": "\n\n".join(raw_text_parts),
        "dataframe": combined_df,
        "files": file_names,
        "file_rows": file_row_counts,
        "file_types": file_types,
        "has_pdf": any(t == "PDF" for t in file_types),
        "normalization_map": normalization_map,
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

uploaded_a = st.file_uploader("Upload Source A (1 or 2 files)", type=["pdf", "csv", "xls", "xlsx"], accept_multiple_files=True, key="recon_a")
uploaded_b = st.file_uploader("Upload Source B (1 or 2 files)", type=["pdf", "csv", "xls", "xlsx"], accept_multiple_files=True, key="recon_b")
business_context = st.text_area(
    "Optional business context",
    value="Example: Reconcile amounts using the shared transaction or trace identifier.",
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
            st.write(f"**{source_a['name']}**")
            st.write(f"Type: {source_a['type']}")
            st.markdown(
                f"<span title='This count includes all files uploaded into Source A.'>Combined rows: {len(source_a['dataframe']):,}</span>",
                unsafe_allow_html=True,
            )
            if source_a.get("files"):
                source_a_files = [f"{name} ({rows} rows)" for name, rows in zip(source_a['files'], source_a.get('file_rows', []))]
                st.write(f"Combined from: {', '.join(source_a_files)}")
            if source_a.get('dataframe') is not None and not source_a['dataframe'].empty:
                st.write(f"Detected headers: {list(source_a['dataframe'].columns)}")
                if source_a.get('normalization_map'):
                    st.write("Header normalization map:")
                    st.write(source_a['normalization_map'])
                if "Net amount" in source_a['dataframe'].columns:
                    net_total_a = pd.to_numeric(source_a['dataframe']["Net amount"], errors="coerce").sum()
                    st.write(f"Total Net amount: {net_total_a:,.2f}")
                st.write("Extracted table sample:")
                st.dataframe(format_dataframe_numbers(source_a['dataframe'].head(5)))
            elif source_a.get('has_pdf'):
                st.write("PDF text excerpt (table extraction failed):")
                st.write(source_a['raw_text'][:1000])
            else:
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
            if source_b['type'] == 'PDF':
                if source_b.get('dataframe') is not None and not source_b['dataframe'].empty:
                    st.write(f"Detected headers: {list(source_b['dataframe'].columns)}")
                    if source_b.get('normalization_map'):
                        st.write("Header normalization map:")
                        st.write(source_b['normalization_map'])
                    if "Net amount" in source_b['dataframe'].columns:
                        net_total_b = pd.to_numeric(source_b['dataframe']["Net amount"], errors="coerce").sum()
                        st.write(f"Total Net amount: {net_total_b:,.2f}")
                    st.write("Extracted table sample:")
                    st.dataframe(format_dataframe_numbers(source_b['dataframe'].head(5)))
                else:
                    st.write("PDF text excerpt (table extraction failed):")
                    st.write(source_b['raw_text'][:1000])
            else:
                if source_b.get('dataframe') is not None and not source_b['dataframe'].empty:
                    st.write(f"Detected headers: {list(source_b['dataframe'].columns)}")
                    if source_b.get('normalization_map'):
                        st.write("Header normalization map:")
                        st.write(source_b['normalization_map'])
                    if "Net amount" in source_b['dataframe'].columns:
                        net_total_b = pd.to_numeric(source_b['dataframe']["Net amount"], errors="coerce").sum()
                        st.write(f"Total Net amount: {net_total_b:,.2f}")
                    st.write("Extracted table sample:")
                    st.dataframe(format_dataframe_numbers(source_b['dataframe'].head(5)))
                else:
                    st.write(f"Fields: {[field['name'] for field in source_b['fields']]}")

        if (
            "recon_candidates" not in st.session_state
            or st.session_state.get("recon_a_files") != source_a.get("files")
            or st.session_state.get("recon_b_files") != source_b.get("files")
            or st.session_state.get("recon_business_context") != business_context
        ):
            with st.spinner("Finding shared identifier candidates..."):
                analysis = analyze_sources(source_a, source_b, business_context)
                st.session_state.recon_analysis = analysis
                st.session_state.recon_candidates = get_identifier_candidates(analysis)
                st.session_state.recon_a_files = source_a.get("files")
                st.session_state.recon_b_files = source_b.get("files")
                st.session_state.recon_business_context = business_context

        candidates = st.session_state.get("recon_candidates", [])

        def field_present_in_source(source, field_name):
            # Check dataframe columns first
            try:
                if field_name in source.get("dataframe", pd.DataFrame()).columns:
                    return True
            except Exception:
                pass
            # Check fields metadata
            for f in source.get("fields", []):
                if str(f.get("name")) == str(field_name):
                    return True
            # Fallback: search the raw text for the field name
            raw = source.get("raw_text", "") or ""
            if raw and str(field_name).lower() in raw.lower():
                return True
            return False

        valid_candidates = [
            c for c in candidates
            if field_present_in_source(source_a, c["source_a_field"]) 
            and field_present_in_source(source_b, c["source_b_field"]) 
        ]

        if valid_candidates:
            st.success(f"Found {len(valid_candidates)} identifier candidate(s).")
            selected = st.selectbox(
                "Select identifier pair to reconcile",
                options=valid_candidates,
                format_func=lambda item: item["label"],
            )
            if selected.get("score") is not None:
                st.markdown(f"**Identifier pair match:** {selected['score']}%")

            selected_key = f"{selected['source_a_field']}|{selected['source_b_field']}"
            remembered_amounts = st.session_state.get("recon_last_amount_by_identifier", {}).get(selected_key, {})

            analysis = st.session_state.get("recon_analysis", {})
            selected_mapping = next(
                (
                    m for m in analysis.get("field_mappings", [])
                    if m.get("source_a_field") == selected["source_a_field"]
                    and m.get("source_b_field") == selected["source_b_field"]
                ),
                None,
            )
            if selected_mapping:
                st.markdown("**Detected shared identifier relationship:**")
                st.write(
                    f"`{selected_mapping['source_a_field']}` ↔ `{selected_mapping['source_b_field']}` — {selected_mapping.get('relationship', 'direct relationship')}"
                )
                if selected_mapping.get("explanation"):
                    st.write(selected_mapping["explanation"])
            st.caption(
                "This reconciler supports embedded identifier matches, including cases where the Source B trace_id appears inside a longer Description field in Source A."
            )

            amount_fields_a = list(source_a["dataframe"].columns)
            amount_fields_b = list(source_b["dataframe"].columns)

            if not amount_fields_a or not amount_fields_b:
                st.error(
                    "No amount columns were detected in one or both sources. "
                    "Please verify the uploaded files and the extracted headers."
                )
            else:
                default_amount_a = detect_amount_fields(source_a["dataframe"])
                default_amount_b = detect_amount_fields(source_b["dataframe"])
                default_a = None
                default_b = None

                if remembered_amounts.get("amount_a") in amount_fields_a:
                    default_a = remembered_amounts["amount_a"]
                else:
                    default_a = choose_best_amount_field_by_precision(source_a["dataframe"], default_amount_a)

                if remembered_amounts.get("amount_b") in amount_fields_b:
                    default_b = remembered_amounts["amount_b"]
                else:
                    default_b = choose_amount_field(source_a["dataframe"], source_b["dataframe"], default_a)

                if default_a not in amount_fields_a:
                    default_a = choose_best_amount_field_by_precision(source_a["dataframe"], default_amount_a)
                if default_a not in amount_fields_a and amount_fields_a:
                    default_a = amount_fields_a[0]

                if default_b not in amount_fields_b:
                    default_b = choose_best_amount_field_by_precision(source_b["dataframe"], default_amount_b)
                if default_b not in amount_fields_b and amount_fields_b:
                    default_b = amount_fields_b[0]

                col1, col2 = st.columns(2)
                with col1:
                    amount_a_index = amount_fields_a.index(default_a) if default_a in amount_fields_a else 0
                    amount_a = st.selectbox("Select amount field in Source A", amount_fields_a, index=amount_a_index)
                with col2:
                    amount_b_index = amount_fields_b.index(default_b) if default_b in amount_fields_b else 0
                    amount_b = st.selectbox("Select amount field in Source B", amount_fields_b, index=amount_b_index)

                if st.button("Run Reconciliation"):
                    missing_fields = []
                    for field_name, source_df, source_label in [
                        (selected["source_a_field"], source_a["dataframe"], "Source A"),
                        (selected["source_b_field"], source_b["dataframe"], "Source B"),
                        (amount_a, source_a["dataframe"], "Source A"),
                        (amount_b, source_b["dataframe"], "Source B"),
                    ]:
                        if field_name not in source_df.columns:
                            missing_fields.append(f"{field_name} ({source_label})")

                    if missing_fields:
                        st.error(
                            "Unable to reconcile because the selected identifier or amount field is not present in the parsed columns: "
                            + ", ".join(missing_fields)
                        )
                    else:
                        st.session_state.setdefault("recon_last_amount_by_identifier", {})[selected_key] = {
                            "amount_a": amount_a,
                            "amount_b": amount_b,
                        }
                        result = reconcile_by_identifier(
                            source_a,
                            source_b,
                            selected,
                            amount_a,
                            amount_b,
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

                            unmatched_total_a = unmatched["total_amount_a"].sum()
                            unmatched_total_b = unmatched["total_amount_b"].sum()
                    unmatched_count = int(unmatched.shape[0])

                    if len(source_a["dataframe"]):
                        pct_unmatched_rows_a = unmatched_count / len(source_a["dataframe"]) * 100
                    else:
                        pct_unmatched_rows_a = 0.0
                    if len(source_b["dataframe"]):
                        pct_unmatched_rows_b = unmatched_count / len(source_b["dataframe"]) * 100
                    else:
                        pct_unmatched_rows_b = 0.0

                    def unmatched_badge(pct):
                        color = "green" if pct < 20 else "orange" if pct < 50 else "red"
                        return f"<span style='color:{color};font-size:20px;font-weight:600;'>{pct:.1f}% unmatched</span>"

                    row_metrics = st.columns(2)
                    row_metrics[0].markdown(
                        f"**Rows in Source A**<br>{len(source_a['dataframe']):,}<br>Unmatched amount: {unmatched_total_a:,.2f}<br>{unmatched_badge(pct_unmatched_rows_a)}",
                        unsafe_allow_html=True,
                    )
                    row_metrics[1].markdown(
                        f"**Rows in Source B**<br>{len(source_b['dataframe']):,}<br>Unmatched amount: {unmatched_total_b:,.2f}<br>{unmatched_badge(pct_unmatched_rows_b)}",
                        unsafe_allow_html=True,
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
                        summary_lines.append("All reconciled identifiers matched.")
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

                    # Persist confirmed pairing and mismatch reasons to the knowledge base
                    record_confirmed_pairing(selected["source_a_field"], selected["source_b_field"])
                    if not reason_counts.empty:
                        record_mismatch_reasons(dict(zip(reason_counts["reason"], reason_counts["count"])))

                    summary_text = summarize_reconciliation_insights(
                        source_a,
                        source_b,
                        matched_amount_a,
                        matched_amount_b,
                        unmatched_total_a,
                        unmatched_total_b,
                        totals["Total A"],
                        totals["Total B"],
                        matched_count,
                        unmatched_count,
                        reason_counts,
                        top_reasons,
                    )

                    reason_counts_chart = reason_counts.copy()
                    reason_counts_chart.columns = ["Reason", "Count"]
                    exposure_data = pd.DataFrame(
                        {
                            "Source": [source_a["name"], source_b["name"], source_a["name"], source_b["name"]],
                            "Type": ["Matched", "Matched", "Unmatched", "Unmatched"],
                            "Amount": [matched_amount_a, matched_amount_b, unmatched_total_a, unmatched_total_b],
                        }
                    )

                    if not reason_counts.empty:
                        st.subheader("Unmatched reason counts")
                        reason_chart = alt.Chart(reason_counts_chart).mark_bar().encode(
                            x=alt.X("Count:Q", title="Count"),
                            y=alt.Y("Reason:N", sort="-x", title="Reason"),
                            tooltip=["Reason", "Count"],
                        ).properties(height=300)
                        st.altair_chart(reason_chart, use_container_width=True)
                    else:
                        st.info("No unmatched reason counts available.")

                    st.write("---")
                    st.subheader("Amount exposure by source")
                    exposure_chart = alt.Chart(exposure_data).mark_bar().encode(
                        x=alt.X("Amount:Q", title="Amount"),
                        y=alt.Y("Source:N", sort="-x", title="Source"),
                        color=alt.Color("Type:N", title="Type", scale=alt.Scale(range=["#1f77b4", "#ff7f0e"])),
                        tooltip=["Source", "Type", "Amount"],
                    ).properties(height=300)
                    st.altair_chart(exposure_chart, use_container_width=True)

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

                    st.write("---")
                    st.subheader("Executive Summary")
                    st.info(summary_text)

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
