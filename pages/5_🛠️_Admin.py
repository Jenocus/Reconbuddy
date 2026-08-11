import json
import os
import pandas as pd
import streamlit as st
from helper_functions.utility import check_password
from helper_functions.knowledge_base import KB_PATH, load_kb, save_kb

st.set_page_config(
    layout="centered",
    page_title="Admin — Knowledge Base",
    page_icon="🛠️",
)

if not check_password():
    st.stop()

st.title("🛠️ Admin — Knowledge Base")
st.write(
    "View, edit, and manage the knowledge base. Changes here affect what the LLM learns and applies during future reconciliations."
)

kb = load_kb()

# ── Stats banner ───────────────────────────────────────────────────────────────
pairings = kb.get("pairings", [])
mismatch_reasons = kb.get("mismatch_reasons", {})
user_reasons = kb.get("user_reasons", [])
flagged_reasons = kb.get("flagged_reasons", {})

col1, col2, col3, col4 = st.columns(4)
col1.metric("Confirmed pairings", len(pairings))
col2.metric("Unique mismatch reasons", len(mismatch_reasons))
col3.metric("User-confirmed examples", len(user_reasons))
col4.metric("Flagged (wrong) reasons", len(flagged_reasons))

st.write("---")

# ── 1. Field Pairings ──────────────────────────────────────────────────────────
st.subheader("1. Field pairings")
st.caption("Tracks which field pairs have been reconciled and how often.")

if pairings:
    pairings_df = pd.DataFrame(pairings).sort_values("use_count", ascending=False)
    edited_pairings = st.data_editor(
        pairings_df,
        use_container_width=True,
        num_rows="dynamic",
        key="pairings_editor",
    )
    col_save, col_clear = st.columns([1, 1])
    with col_save:
        if st.button("Save pairing changes", key="save_pairings"):
            kb["pairings"] = edited_pairings.to_dict(orient="records")
            save_kb(kb)
            st.success("Pairings saved.")
            st.rerun()
    with col_clear:
        if st.button("Clear all pairings", key="clear_pairings", type="secondary"):
            kb["pairings"] = []
            save_kb(kb)
            st.success("All pairings cleared.")
            st.rerun()
else:
    st.info("No pairings recorded yet. Run a reconciliation to start learning.")

st.write("---")

# ── 2. Mismatch Reasons ────────────────────────────────────────────────────────
st.subheader("2. Mismatch reason frequencies")
st.caption("Aggregate counts of all LLM-suggested reasons across past reconciliations.")

if mismatch_reasons:
    reasons_df = (
        pd.DataFrame(list(mismatch_reasons.items()), columns=["reason", "count"])
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )
    edited_reasons = st.data_editor(
        reasons_df,
        use_container_width=True,
        num_rows="dynamic",
        key="reasons_editor",
    )
    col_save_r, col_clear_r = st.columns([1, 1])
    with col_save_r:
        if st.button("Save reason changes", key="save_reasons_admin"):
            kb["mismatch_reasons"] = dict(zip(edited_reasons["reason"], edited_reasons["count"]))
            save_kb(kb)
            st.success("Reasons saved.")
            st.rerun()
    with col_clear_r:
        if st.button("Clear all reasons", key="clear_reasons", type="secondary"):
            kb["mismatch_reasons"] = {}
            save_kb(kb)
            st.success("All mismatch reasons cleared.")
            st.rerun()
else:
    st.info("No mismatch reason frequencies recorded yet.")

st.write("---")

# ── 3. User-confirmed examples ─────────────────────────────────────────────────
st.subheader("3. User-confirmed examples")
st.caption(
    "These are injected into the LLM prompt as few-shot examples during future reconciliations with the same field pair. "
    "Editing or removing entries here directly affects what the LLM learns."
)

if user_reasons:
    user_df = pd.DataFrame(user_reasons).sort_values(
        ["field_a", "field_b", "recorded_at"], ascending=[True, True, False]
    ).reset_index(drop=True)

    # Filter by field pair
    pair_options = ["(All pairs)"] + sorted(
        user_df.apply(lambda r: f"{r['field_a']} ↔ {r['field_b']}", axis=1).unique().tolist()
    )
    selected_pair = st.selectbox("Filter by field pair", pair_options, key="admin_pair_filter")

    if selected_pair != "(All pairs)":
        fa, fb = selected_pair.split(" ↔ ", 1)
        display_df = user_df[(user_df["field_a"] == fa) & (user_df["field_b"] == fb)].copy()
    else:
        display_df = user_df.copy()

    edited_user = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",
        key="user_reasons_editor",
    )

    col_save_u, col_clear_u = st.columns([1, 1])
    with col_save_u:
        if st.button("Save example changes", key="save_user_reasons"):
            if selected_pair != "(All pairs)":
                fa, fb = selected_pair.split(" ↔ ", 1)
                # Replace only the entries for the selected pair, keep others intact
                other_entries = [e for e in user_reasons if not (e["field_a"] == fa and e["field_b"] == fb)]
                kb["user_reasons"] = other_entries + edited_user.to_dict(orient="records")
            else:
                kb["user_reasons"] = edited_user.to_dict(orient="records")
            save_kb(kb)
            st.success("Examples saved.")
            st.rerun()
    with col_clear_u:
        if selected_pair != "(All pairs)":
            clear_label = f"Clear examples for selected pair"
        else:
            clear_label = "Clear all examples"
        if st.button(clear_label, key="clear_user_reasons", type="secondary"):
            if selected_pair != "(All pairs)":
                fa, fb = selected_pair.split(" ↔ ", 1)
                kb["user_reasons"] = [e for e in user_reasons if not (e["field_a"] == fa and e["field_b"] == fb)]
            else:
                kb["user_reasons"] = []
            save_kb(kb)
            st.success("Examples cleared.")
            st.rerun()
else:
    st.info("No user-confirmed examples recorded yet. Edit reasons on the ReconBuddy page and click Save.")

st.write("---")

# ── 4. Import / Export ─────────────────────────────────────────────────────────
st.subheader("4. Import / Export knowledge base")
st.caption("Export the KB to share it across machines or team members, or import one to load learned patterns.")

col_exp, col_imp = st.columns(2)

with col_exp:
    st.markdown("**Export**")
    kb_json = json.dumps(kb, indent=2)
    st.download_button(
        "Download knowledge_base.json",
        data=kb_json,
        file_name="knowledge_base.json",
        mime="application/json",
    )

with col_imp:
    st.markdown("**Import**")
    uploaded_kb = st.file_uploader("Upload knowledge_base.json", type=["json"], key="kb_upload")
    if uploaded_kb:
        try:
            incoming = json.load(uploaded_kb)
            if st.button("Merge and apply imported KB", key="import_kb"):
                # Merge pairings
                existing_pair_keys = {(p["field_a"], p["field_b"]) for p in kb.get("pairings", [])}
                for p in incoming.get("pairings", []):
                    key = (p["field_a"], p["field_b"])
                    if key in existing_pair_keys:
                        for ep in kb["pairings"]:
                            if ep["field_a"] == p["field_a"] and ep["field_b"] == p["field_b"]:
                                ep["use_count"] = ep.get("use_count", 0) + p.get("use_count", 0)
                    else:
                        kb.setdefault("pairings", []).append(p)
                # Merge mismatch reasons
                for reason, count in incoming.get("mismatch_reasons", {}).items():
                    kb["mismatch_reasons"][reason] = kb["mismatch_reasons"].get(reason, 0) + count
                # Merge user reasons (overwrite same field/identifier triples)
                existing_ur = {(e["field_a"], e["field_b"], e["identifier"]): i for i, e in enumerate(kb.get("user_reasons", []))}
                for entry in incoming.get("user_reasons", []):
                    key = (entry["field_a"], entry["field_b"], entry["identifier"])
                    if key in existing_ur:
                        kb["user_reasons"][existing_ur[key]] = entry
                    else:
                        kb.setdefault("user_reasons", []).append(entry)
                save_kb(kb)
                st.success("Knowledge base merged successfully.")
                st.rerun()
        except (json.JSONDecodeError, KeyError):
            st.error("Invalid knowledge base file. Please upload a valid knowledge_base.json.")

st.write("---")

# ── 5. Flagged reasons ─────────────────────────────────────────────────────────
st.subheader("5. Flagged reasons (negative feedback)")
st.caption(
    "Reasons flagged as wrong by users. The LLM is instructed to avoid these. "
    "Higher flag count = stronger avoidance signal. Remove entries to lift the restriction."
)

flagged_reasons = kb.get("flagged_reasons", {})
if flagged_reasons:
    flagged_df = (
        pd.DataFrame(list(flagged_reasons.items()), columns=["reason", "flag_count"])
        .sort_values("flag_count", ascending=False)
        .reset_index(drop=True)
    )
    edited_flagged = st.data_editor(
        flagged_df,
        use_container_width=True,
        num_rows="dynamic",
        key="flagged_reasons_editor",
    )
    col_save_f, col_clear_f = st.columns([1, 1])
    with col_save_f:
        if st.button("Save flagged reason changes", key="save_flagged"):
            kb["flagged_reasons"] = dict(zip(edited_flagged["reason"], edited_flagged["flag_count"]))
            save_kb(kb)
            st.success("Flagged reasons saved.")
            st.rerun()
    with col_clear_f:
        if st.button("Clear all flagged reasons", key="clear_flagged", type="secondary"):
            kb["flagged_reasons"] = {}
            save_kb(kb)
            st.success("All flagged reasons cleared.")
            st.rerun()
else:
    st.info("No reasons have been flagged yet. Use the 'Flag reason as wrong' checkbox in the 2-way Match page.")

st.write("---")

# ── 6. Danger zone ─────────────────────────────────────────────────────────────
st.subheader("6. Danger zone")
with st.expander("Reset entire knowledge base"):
    st.warning("This will permanently delete all learned pairings, reasons, user examples, and flagged reasons.")
    if st.button("Reset knowledge base", type="primary", key="reset_kb"):
        save_kb({"pairings": [], "mismatch_reasons": {}, "user_reasons": [], "flagged_reasons": {}})
        st.success("Knowledge base has been reset.")
        st.rerun()
