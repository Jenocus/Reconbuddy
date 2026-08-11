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
    "2. Parse documents and extract tables or text.\n"
    "3. Normalize headers and detect likely amount fields.\n"
    "4. Use LLM to suggest shared identifiers and field mappings.\n"
    "5. Reconcile totals by identifier; pre-detect timing differences via date ranges.\n"
    "6. Review matched and unmatched rows in sortable, frozen-header tables.\n"
    "7. Rate each reason inline: 👍 (confirm, saves as positive example) or 👎 (flag as wrong, banned from future runs).\n"
    "8. Review and manage feedback in Admin panel (field pairings, confirmed examples, flagged reasons).\n"
    "9. Ask questions via LLM chatbox; export results; next reconciliation uses updated knowledge base patterns."
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
    "Reconbuddy learns from user feedback via a local knowledge base (knowledge_base.json). When you interact with reasons: "
    "👍 saves that reason as a confirmed example for the field pair (LLM uses as positive hint). "
    "👎 flags the reason as wrong and bans it—the LLM will never suggest it again. "
    "On future reconciliations with the same field pair, the LLM receives confirmed examples and the list of banned reasons, improving quality incrementally without external data sharing."
)

st.subheader("Timing difference detection")
st.write(
    "Timing differences are the **highest-priority** unmatched reason. Detection happens in two stages: "
    "(1) Code-based: the system analyzes the date range of matched rows (e.g., Jan 1–31), then pre-flags unmatched rows with dates outside that period. "
    "(2) LLM-based: for rows without date evidence, the LLM is instructed to consider timing difference first when inferring reasons. "
    "This dual approach ensures timing mismatches are never confused with missing or duplicated transactions."
)

st.subheader("Key design choices")
st.markdown("""
| What we chose | Why |
|---|---|
| **Ask AI directly instead of searching** | The reconciliation data is small structured tables that fit in one prompt. Searching through a database adds unnecessary complexity. We send everything to the AI at once. |
| **Learn from your feedback** | When you click 👍 or 👎, the system saves your correction. Next time with the same field pair, the AI gets your previous examples as hints. 👍 = positive example. 👎 = hard ban. Simple, transparent, no vector embeddings needed. |
| **Rate reasons per row** | Instead of filling out big forms, you just click 👍 or 👎 directly on each row. Instant feedback, no friction. Edits sync across All/Matched/Unmatched tabs in real-time. |
| **Frozen headers & sorting** | Headers stay locked at the top when you scroll. Columns are sortable. This matches what analysts expect from Excel-like interfaces and improves usability for large result sets. |
| **Check dates first, then ask AI** | Timing differences are deterministic—just compare transaction dates to the matched period. Pre-detect timing mismatches in code (fast, reliable) before asking the AI. If no date evidence, AI prioritizes timing difference as reason #1. Ensures timing errors are never missed. |
| **Keep data local & safe** | All your financial data stays on your computer. knowledge_base.json only stores patterns (field pairs, reason labels), not transaction amounts or details. No external API calls, no data leakage risk. |
| **Test everything (54 tests)** | Tests are checkpoints: they verify KB persistence, LLM prompt injection, timing detection, and end-to-end learning. If something breaks, tests catch it immediately. This is especially critical for financial reconciliation. |
| **Use GPT-4o-mini** | It's cost-effective, fast enough for structured data interpretation, and supports JSON parsing + conditional logic. Balances price, speed, and reasoning quality. |
| **Remember & refresh cache** | The app caches LLM results within a session to avoid redundant API calls. Cache is invalidated only when learning changes (new flagged or confirmed reasons). This avoids stale suggestions while reducing costs. |
""")


