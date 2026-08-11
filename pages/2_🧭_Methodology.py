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
| **Ask AI directly** | The data is small enough to show the AI everything at once. No need to search for pieces. |
| **Learn & remember** | When you say 👍 or 👎, the app remembers your choice. Next time, the AI uses what you taught it. |
| **Rate each row** | Instead of big popup forms, you just click 👍 or 👎 right on the row. Fast and easy. |
| **Nice tables** | Headers stay at the top so you can always see what each column means, even when scrolling. |
| **Check dates first** | If a transaction is in a different month, that's why it doesn't match. Check dates before asking the AI. |
| **Keep data safe** | All your secret data stays on your computer. We only save labels and patterns, not your numbers. |
| **Test everything** | We have checkpoints that test if learning works, if AI suggestions are right, and if timing checks work. |
| **Use GPT-4o-mini** | It's smart enough for what we need and costs just the right amount. |
| **Remember and reset** | The app memorizes answers to avoid asking the same question twice. When you teach it something new, it forgets the old answer to learn fresh. |
""")

