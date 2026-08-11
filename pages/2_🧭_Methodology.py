import streamlit as st
from helper_functions.utility import check_password

st.set_page_config(
    layout="centered",
    page_title="Methodology",
    page_icon="🧭",
)

if not check_password():
    st.stop()

st.title("🧭 Methodology")
st.write(
    "The workflow is intentionally simple: ingest data, identify likely shared identifiers, reconcile values, and present the results clearly."
)

st.subheader("End-to-end data flow")
st.markdown(
    "1. Upload one or more source files in PDF, Excel, or CSV format.\n"
    "2. Parse the documents and extract tables or text.\n"
    "3. Normalize headers and detect likely amount fields.\n"
    "4. Use LLM-based analysis to suggest shared identifiers and field mappings.\n"
    "5. Reconcile totals by identifier; detect timing differences by comparing dates to matched period.\n"
    "6. Review unmatched rows with LLM-suggested reasons; edit reasons across tabs (All, Matched, Unmatched).\n"
    "7. Save user-corrected reasons to knowledge base for learning.\n"
    "8. Ask questions about sources via LLM chatbox (reads uploaded data and reconciliation metrics).\n"
    "9. Export reconciliation report and use learned patterns for future reconciliations."
)

st.subheader("Implementation detail")
st.write(
    "The implementation uses Streamlit for the UI, pandas for table handling, and LLM-based reasoning to infer relationships when field names differ or are embedded in free text. The LLM is used to interpret the meaning of uploaded fields and descriptions, identify likely shared identifiers, and explain why those mappings are reasonable before reconciliation is performed."
)

st.subheader("Use case 1: Shared identifier discovery")
st.write(
    "This workflow starts with uploaded reports, extracts structured information, and uses the LLM to suggest shared identifiers and field mappings before any reconciliation is performed."
)

st.subheader("Use case 2: Reconciliation")
st.write(
    "This workflow uses the selected identifier pair to reconcile totals across the two sources, then presents matched and unmatched rows with summary insights."
)

st.markdown(
    """
    <svg width="760" height="260" viewBox="0 0 760 260" xmlns="http://www.w3.org/2000/svg">
      <rect x="20" y="90" width="120" height="60" rx="10" fill="#e8f1ff" stroke="#4c78a8"/>
      <text x="80" y="125" text-anchor="middle" font-size="15" fill="#1f2937">Upload files</text>
      <line x1="140" y1="120" x2="200" y2="120" stroke="#4c78a8" stroke-width="2"/>
      <rect x="200" y="90" width="140" height="60" rx="10" fill="#fef3c7" stroke="#f59e0b"/>
      <text x="270" y="125" text-anchor="middle" font-size="15" fill="#1f2937">Parse &amp; normalize</text>
      <line x1="340" y1="120" x2="400" y2="120" stroke="#4c78a8" stroke-width="2"/>
      <rect x="400" y="90" width="150" height="60" rx="10" fill="#fce7f3" stroke="#db2777"/>
      <text x="475" y="125" text-anchor="middle" font-size="15" fill="#1f2937">Find shared IDs</text>
      <line x1="550" y1="120" x2="610" y2="120" stroke="#4c78a8" stroke-width="2"/>
      <rect x="610" y="90" width="130" height="60" rx="10" fill="#dcfce7" stroke="#16a34a"/>
      <text x="675" y="125" text-anchor="middle" font-size="15" fill="#1f2937">Reconcile amounts</text>
      <line x1="675" y1="150" x2="675" y2="190" stroke="#4c78a8" stroke-width="2"/>
      <rect x="610" y="190" width="130" height="50" rx="10" fill="#f3f4f6" stroke="#6b7280"/>
      <text x="675" y="220" text-anchor="middle" font-size="14" fill="#1f2937">Insights &amp; download</text>
    </svg>
    """,
    unsafe_allow_html=True,
)

st.caption("This methodology is intentionally transparent so analysts can inspect each stage and understand why the application made a particular recommendation.")

st.subheader("Knowledge base for learning")
st.write(
    "Reconbuddy maintains a knowledge base (knowledge_base.json) that learns from user corrections across sessions. When you edit a mismatch reason and save it, the system records: "
    "(1) which field pair was reconciled, (2) the reason you confirmed, and (3) the specific identifier. "
    "On future reconciliations with the same field pair, the LLM receives these user-confirmed examples as hints, improving suggestions over time."
)

st.subheader("Timing difference detection")
st.write(
    "Timing differences are automatically detected by comparing transaction dates. The system analyzes the date range of all matched rows (e.g., Jan 1-31), "
    "then flags any unmatched row with a date outside that period as a timing difference. This is the highest-priority unmatched reason and ensures transactions "
    "that belong in a different reporting period are not misclassified as missing or duplicated."
)

st.subheader("Key design choices")
st.table(
    {
        "Decision": [
            "Direct LLM prompting instead of RAG",
            "Knowledge base (JSON) for learning, not a vector store",
            "Session state for cross-tab reason sync",
            "No external database (knowledge base stored locally as JSON)",
            "Timing difference detected in code, not via LLM",
            "LLM used for field mapping and secondary reasons",
            "Full document data sent to chatbox",
            "GPT-4o-mini as the LLM",
            "Streamlit session state for caching",
        ],
        "Reason": [
            "Reconciliation inputs are small structured tables that fit within a single prompt window; retrieval overhead is unnecessary.",
            "Users build patterns over time by confirming reasons for the same field pairs. A simple JSON KB stores examples and aggregates; no vector embeddings needed.",
            "When a user edits a reason in one tab (All, Matched, or Unmatched), session state tracks it so other tabs display the same edit immediately.",
            "No external database is used. Reconciliation session data is not retained after the session ends. User-confirmed mismatch reasons are stored locally in knowledge_base.json, which improves LLM suggestions over time without sending data to an external service.",
            "Date-based logic is deterministic and fast; letting the LLM guess leads to false negatives. Pre-detecting timing differences ensures they are never misclassified.",
            "Column names often differ across systems (e.g. 'InvNum' vs 'invoice_id'). An LLM interprets intent better than brittle keyword rules. For timing differences, detection is deterministic.",
            "The chatbox LLM needs access to uploaded data samples and reconciliation metrics to answer questions accurately (e.g., 'Why are amounts different?').",
            "Balances cost, speed, and reasoning quality for structured data interpretation tasks.",
            "LLM analysis for the same pair of sources is deterministic enough to cache within a session, avoiding redundant API calls when the user revisits settings.",
        ],
    }
)
