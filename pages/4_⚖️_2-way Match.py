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
from helper_functions.knowledge_base import record_confirmed_pairing, record_mismatch_reasons, record_user_reasons, record_flagged_reason, load_kb
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
    page_title="2-way Match",
    page_icon="⚖️",
)

if not check_password():
    st.stop()

st.title("⚖️ 2-way Match")
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

                # Compute a hash of only the KB sections that affect LLM output
                # (mismatch_reasons changes every run so is excluded)
                import hashlib, json as _json
                _kb_snapshot = load_kb()
                _kb_for_hash = {
                    "flagged_reasons": _kb_snapshot.get("flagged_reasons", {}),
                    "user_reasons": _kb_snapshot.get("user_reasons", []),
                }
                _current_kb_hash = hashlib.md5(
                    _json.dumps(_kb_for_hash, sort_keys=True).encode()
                ).hexdigest()

                # Warn (but do NOT clear results) if KB has changed since last run
                _cached = st.session_state.get(f"recon_result_{selected_key}")
                if _cached and _cached.get("kb_hash") != _current_kb_hash:
                    st.warning("⚠️ The knowledge base has changed since the last run. Click **Run Reconciliation** again to apply the latest learned patterns and flags.")

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
                        if not details.empty:
                            unmatched = details[details["status"] != "Matched"]
                            matched = details[details["status"] == "Matched"]
                            matched_amount_a = matched["total_amount_a"].sum()
                            matched_amount_b = matched["total_amount_b"].sum()
                            unmatched_total_a = unmatched["total_amount_a"].sum()
                            unmatched_total_b = unmatched["total_amount_b"].sum()
                            unmatched_count = int(unmatched.shape[0])
                            matched_count = int(matched.shape[0])
                            unmatched_difference = unmatched_total_a - unmatched_total_b
                            pct_unmatched_rows_a = unmatched_count / len(source_a["dataframe"]) * 100 if len(source_a["dataframe"]) else 0.0
                            pct_unmatched_rows_b = unmatched_count / len(source_b["dataframe"]) * 100 if len(source_b["dataframe"]) else 0.0
                            pct_unmatched_a = unmatched_total_a / totals["Total A"] * 100 if totals["Total A"] != 0 else 0.0
                            pct_unmatched_b = unmatched_total_b / totals["Total B"] * 100 if totals["Total B"] != 0 else 0.0

                            suggestion_map = infer_unmatched_reasons(
                                unmatched,
                                source_a["name"],
                                source_b["name"],
                                amount_a,
                                amount_b,
                                identifier_field_a=selected["source_a_field"],
                                identifier_field_b=selected["source_b_field"],
                                source_a_df=source_a["dataframe"],
                                source_b_df=source_b["dataframe"],
                                matched_df=matched,
                            )
                            details["suggested_reason"] = details["identifier"].astype(str).map(suggestion_map).fillna("")

                            reason_counts = unmatched["reason"].value_counts().rename_axis("reason").reset_index(name="count")
                            top_reasons = reason_counts.head(3)["reason"].tolist()

                            record_confirmed_pairing(selected["source_a_field"], selected["source_b_field"])
                            suggested_reason_counts = (
                                details[details["suggested_reason"].str.strip() != ""]["suggested_reason"]
                                .value_counts()
                                .rename_axis("reason")
                                .reset_index(name="count")
                            )
                            if not suggested_reason_counts.empty:
                                record_mismatch_reasons(dict(zip(suggested_reason_counts["reason"], suggested_reason_counts["count"])))

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

                            unmatched_ids_a = unmatched[unmatched["total_amount_a"].notna()]["identifier"].astype(str).unique().tolist()
                            unmatched_ids_b = unmatched[unmatched["total_amount_b"].notna()]["identifier"].astype(str).unique().tolist()
                            unmatched_a_rows = source_a["dataframe"][source_a["dataframe"][selected["source_a_field"]].astype(str).isin(unmatched_ids_a)] if selected["source_a_field"] in source_a["dataframe"].columns else pd.DataFrame()
                            unmatched_b_rows = source_b["dataframe"][source_b["dataframe"][selected["source_b_field"]].astype(str).isin(unmatched_ids_b)] if selected["source_b_field"] in source_b["dataframe"].columns else pd.DataFrame()

                            st.session_state[f"recon_result_{selected_key}"] = {
                                "details": details,
                                "totals": totals,
                                "matched_amount_a": matched_amount_a,
                                "matched_amount_b": matched_amount_b,
                                "unmatched_total_a": unmatched_total_a,
                                "unmatched_total_b": unmatched_total_b,
                                "unmatched_difference": unmatched_difference,
                                "matched_count": matched_count,
                                "unmatched_count": unmatched_count,
                                "pct_unmatched_a": pct_unmatched_a,
                                "pct_unmatched_b": pct_unmatched_b,
                                "pct_unmatched_rows_a": pct_unmatched_rows_a,
                                "pct_unmatched_rows_b": pct_unmatched_rows_b,
                                "summary_text": summary_text,
                                "reason_counts": reason_counts,
                                "unmatched_a_rows": unmatched_a_rows,
                                "unmatched_b_rows": unmatched_b_rows,
                                "source_a_len": len(source_a["dataframe"]),
                                "source_b_len": len(source_b["dataframe"]),
                                "source_a_name": source_a["name"],
                                "source_b_name": source_b["name"],
                                "field_a": selected["source_a_field"],
                                "field_b": selected["source_b_field"],
                                "kb_hash": _current_kb_hash,
                            }
                        else:
                            st.session_state.pop(f"recon_result_{selected_key}", None)
                            st.warning("No reconciliation rows were produced.")

                # Render results from session state — persists across reruns including Save button click
                _rr = st.session_state.get(f"recon_result_{selected_key}")
                if _rr:
                    details = _rr["details"]
                    totals = _rr["totals"]
                    matched_amount_a = _rr["matched_amount_a"]
                    matched_amount_b = _rr["matched_amount_b"]
                    unmatched_total_a = _rr["unmatched_total_a"]
                    unmatched_total_b = _rr["unmatched_total_b"]
                    unmatched_difference = _rr["unmatched_difference"]
                    matched_count = _rr["matched_count"]
                    unmatched_count = _rr["unmatched_count"]
                    pct_unmatched_a = _rr["pct_unmatched_a"]
                    pct_unmatched_b = _rr["pct_unmatched_b"]
                    pct_unmatched_rows_a = _rr["pct_unmatched_rows_a"]
                    pct_unmatched_rows_b = _rr["pct_unmatched_rows_b"]
                    summary_text = _rr["summary_text"]
                    reason_counts = _rr["reason_counts"]
                    unmatched_a_rows = _rr["unmatched_a_rows"]
                    unmatched_b_rows = _rr["unmatched_b_rows"]
                    field_a = _rr["field_a"]
                    field_b = _rr["field_b"]

                    def unmatched_badge(pct):
                        color = "green" if pct < 20 else "orange" if pct < 50 else "red"
                        return f"<span style='color:{color};font-size:20px;font-weight:600;'>{pct:.1f}% unmatched</span>"

                    st.subheader("Reconciliation Results")
                    metrics = st.columns(4)
                    metrics[0].metric("Source A total $", f"{totals['Total A']:,.2f}")
                    metrics[1].metric("Source B total $", f"{totals['Total B']:,.2f}")
                    metrics[2].markdown(
                        f"**Matched identifiers**<br><span style='color:green;font-size:24px'>{matched_count:,}</span>",
                        unsafe_allow_html=True,
                    )
                    metrics[3].markdown(
                        f"**Unmatched identifiers**<br><span style='color:red;font-size:24px'>{unmatched_count:,}</span>",
                        unsafe_allow_html=True,
                    )

                    row_metrics = st.columns(2)
                    row_metrics[0].markdown(
                        f"**Rows in Source A**<br>{_rr['source_a_len']:,}<br>Unmatched amount: {unmatched_total_a:,.2f}<br>{unmatched_badge(pct_unmatched_rows_a)}",
                        unsafe_allow_html=True,
                    )
                    row_metrics[1].markdown(
                        f"**Rows in Source B**<br>{_rr['source_b_len']:,}<br>Unmatched amount: {unmatched_total_b:,.2f}<br>{unmatched_badge(pct_unmatched_rows_b)}",
                        unsafe_allow_html=True,
                    )

                    details_styled = format_dataframe_numbers(details)
                    reason_counts_chart = reason_counts.copy()
                    reason_counts_chart.columns = ["Reason", "Count"]
                    exposure_data = pd.DataFrame(
                        {
                            "Source": [_rr["source_a_name"], _rr["source_b_name"], _rr["source_a_name"], _rr["source_b_name"]],
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

                    # Initialize shared reason edits tracking across all tabs
                    reason_edits_key = f"reason_edits_{selected_key}"
                    if reason_edits_key not in st.session_state:
                        st.session_state[reason_edits_key] = {}

                    def apply_reason_edits(df, reason_column_name="suggested_reason"):
                        """Apply tracked edits from session_state to the dataframe"""
                        df = df.copy()
                        for identifier, edited_reason in st.session_state[reason_edits_key].items():
                            mask = df["identifier"].astype(str) == str(identifier)
                            if mask.any():
                                df.loc[mask, reason_column_name] = edited_reason
                        return df

                    all_tab, matched_tab, unmatched_tab = st.tabs([
                        "All",
                        f"Matched ({matched_count})",
                        f"Unmatched ({unmatched_count})",
                    ])
                    with all_tab:
                        all_edit = details[[
                            "identifier", "total_amount_a", "total_amount_b", "difference", "status"
                        ]].copy()
                        all_edit["Reason"] = apply_reason_edits(details, "suggested_reason")["suggested_reason"].fillna("")
                        readonly_cols_all = [c for c in all_edit.columns if c != "Reason"]
                        edited_all = st.data_editor(
                            all_edit,
                            disabled=readonly_cols_all,
                            use_container_width=True,
                            key=f"all_editor_{selected_key}",
                            column_config={
                                "Reason": st.column_config.TextColumn(
                                    "Reason",
                                    help="Edit reasons for any rows, then click Save to train the AI.",
                                )
                            },
                        )
                        # Update session state with edits from this tab
                        for _, row in edited_all.iterrows():
                            identifier = str(row["identifier"])
                            reason = str(row["Reason"]).strip()
                            if reason:
                                st.session_state[reason_edits_key][identifier] = reason
                        if st.button("Save reasons to knowledge base", key=f"save_reasons_all_{selected_key}"):
                            reasons_to_save = {
                                str(row["identifier"]): str(row["Reason"]).strip()
                                for _, row in edited_all.iterrows()
                                if str(row["Reason"]).strip()
                            }
                            if reasons_to_save:
                                record_user_reasons(field_a, field_b, reasons_to_save)
                                st.success(f"Saved {len(reasons_to_save)} reason(s) to knowledge base.")
                            else:
                                st.info("No reasons entered to save.")
                    with matched_tab:
                        matched_edit = details[details["status"] == "Matched"][[
                            "identifier", "total_amount_a", "total_amount_b", "difference"
                        ]].copy()
                        readonly_cols_matched = list(matched_edit.columns)
                        st.dataframe(matched_edit, use_container_width=True)
                    with unmatched_tab:
                        st.markdown(f"### Unmatched rows ({unmatched_count})")
                        st.markdown(
                            f"**Unmatched total in Source A:** {unmatched_total_a:,.2f}  \
                            **Unmatched total in Source B:** {unmatched_total_b:,.2f}"
                        )
                        unmatched_edit = details[details["status"] != "Matched"][
                            ["identifier", "total_amount_a", "total_amount_b", "difference"]
                        ].copy()
                        unmatched_with_edits = apply_reason_edits(details[details["status"] != "Matched"], "suggested_reason")
                        unmatched_edit["Reason"] = unmatched_with_edits["suggested_reason"].values
                        unmatched_edit.insert(0, "Select", False)
                        readonly_cols = [c for c in unmatched_edit.columns if c not in ["Reason", "Select"]]
                        edited_unmatched = st.data_editor(
                            unmatched_edit,
                            disabled=readonly_cols,
                            use_container_width=True,
                            key=f"unmatched_editor_{selected_key}",
                            column_config={
                                "Select": st.column_config.CheckboxColumn(
                                    "Select",
                                    help="Check a row to highlight its corresponding rows in Source A/B",
                                    width="small",
                                ),
                                "Reason": st.column_config.TextColumn(
                                    "Reason",
                                    help="LLM-suggested reason. Edit to correct it, then click Save to train the AI for future runs on this identifier pair.",
                                ),
                            },
                        )
                        # Update session state with edits from this tab
                        for _, row in edited_unmatched.iterrows():
                            identifier = str(row["identifier"])
                            reason = str(row["Reason"]).strip()
                            if reason:
                                st.session_state[reason_edits_key][identifier] = reason
                        if st.button("Save reasons to knowledge base", key=f"save_reasons_{selected_key}"):
                            reasons_to_save = {
                                str(row["identifier"]): str(row["Reason"]).strip()
                                for _, row in edited_unmatched.iterrows()
                                if str(row["Reason"]).strip()
                            }
                            if reasons_to_save:
                                record_user_reasons(field_a, field_b, reasons_to_save)
                                st.success(f"Saved {len(reasons_to_save)} reason(s) to knowledge base.")
                            else:
                                st.info("No reasons entered to save.")

                        # Flagging — use multiselect so state survives reruns reliably
                        st.markdown("**Flag reasons as wrong:**")
                        current_reasons = sorted(set(
                            r for r in unmatched_edit["Reason"].astype(str).tolist() if r.strip()
                        ))
                        reasons_to_flag = st.multiselect(
                            "Select reason(s) to flag as incorrect — the AI will never use these again",
                            options=current_reasons,
                            key=f"flag_multiselect_{selected_key}",
                        )
                        if st.button("Flag selected reasons as wrong", key=f"flag_reasons_{selected_key}", type="secondary"):
                            if reasons_to_flag:
                                for reason in reasons_to_flag:
                                    record_flagged_reason(reason)
                                st.warning(f"Flagged {len(reasons_to_flag)} reason(s) as wrong — the AI will avoid these in future runs.")
                        
                        # Filter Source A/B rows based on selected checkboxes
                        selected_identifiers = edited_unmatched[edited_unmatched["Select"]]["identifier"].astype(str).tolist()
                        
                        if selected_identifiers:
                            filtered_a = unmatched_a_rows[unmatched_a_rows[selected["source_a_field"]].astype(str).isin(selected_identifiers)]
                            filtered_b = unmatched_b_rows[unmatched_b_rows[selected["source_b_field"]].astype(str).isin(selected_identifiers)]
                        else:
                            filtered_a = pd.DataFrame()
                            filtered_b = pd.DataFrame()
                        
                        st.markdown(f"**Unmatched rows from Source A**")
                        if not filtered_a.empty:
                            st.dataframe(format_dataframe_numbers(filtered_a))
                        else:
                            st.info("Select a row above to view corresponding Source A rows")
                        
                        st.markdown(f"**Unmatched rows from Source B**")
                        if not filtered_b.empty:
                            st.dataframe(format_dataframe_numbers(filtered_b))
                        else:
                            st.info("Select a row above to view corresponding Source B rows")

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

                    # LLM Chat about sources
                    st.write("---")
                    st.subheader("💬 Ask about the sources")
                    
                    # Initialize chat history for this reconciliation
                    chat_key = f"chat_history_{selected_key}"
                    if chat_key not in st.session_state:
                        st.session_state[chat_key] = []
                    
                    # Display chat history
                    chat_container = st.container()
                    with chat_container:
                        for message in st.session_state[chat_key]:
                            with st.chat_message(message["role"]):
                                st.markdown(message["content"])
                    
                    # Chat input
                    user_question = st.chat_input("Ask a question about these sources...", key=f"chat_input_{selected_key}")
                    
                    if user_question:
                        # Add user message to history
                        st.session_state[chat_key].append({"role": "user", "content": user_question})
                        
                        # Build comprehensive context about sources including data samples
                        source_context = (
                            f"Source A: {_rr['source_a_name']}\n"
                            f"- Total rows: {_rr['source_a_len']:,}\n"
                            f"- Total amount: {totals['Total A']:,.2f}\n"
                            f"- Matched amount: {matched_amount_a:,.2f}\n"
                            f"- Unmatched amount: {unmatched_total_a:,.2f}\n"
                            f"- Fields: {list(source_a['dataframe'].columns)}\n\n"
                            f"Source A Sample Data (first 10 rows):\n{source_a['dataframe'].head(10).to_string()}\n\n"
                            f"Source B: {_rr['source_b_name']}\n"
                            f"- Total rows: {_rr['source_b_len']:,}\n"
                            f"- Total amount: {totals['Total B']:,.2f}\n"
                            f"- Matched amount: {matched_amount_b:,.2f}\n"
                            f"- Unmatched amount: {unmatched_total_b:,.2f}\n"
                            f"- Fields: {list(source_b['dataframe'].columns)}\n\n"
                            f"Source B Sample Data (first 10 rows):\n{source_b['dataframe'].head(10).to_string()}\n\n"
                            f"Reconciliation Results:\n"
                            f"- Matched identifiers: {matched_count:,}\n"
                            f"- Unmatched identifiers: {unmatched_count:,}\n"
                            f"- Identifier pair: {_rr['field_a']} ↔ {_rr['field_b']}\n"
                        )
                        
                        if not reason_counts.empty:
                            reason_summary = "\nTop unmatched reasons:\n" + "\n".join(
                                [f"- {row['reason']}: {int(row['count'])}" for _, row in reason_counts.head(5).iterrows()]
                            )
                            source_context += reason_summary
                        
                        # Get LLM response
                        from helper_functions.llm import get_completion
                        
                        response = get_completion([
                            {"role": "system", "content": "You are a helpful financial reconciliation analyst. Answer questions about the two sources and reconciliation results based on the provided data. Analyze the uploaded documents and data to provide accurate insights."},
                            {"role": "user", "content": f"Here is the reconciliation data and source documents:\n\n{source_context}\n\nUser question: {user_question}"},
                        ], temperature=0)
                        
                        # Add assistant response to history
                        st.session_state[chat_key].append({"role": "assistant", "content": response})
                        
                        # Rerun to display new messages
                        st.rerun()
        else:
            if "recon_candidates" in st.session_state:
                st.error("No shared identifier candidates were found.")
