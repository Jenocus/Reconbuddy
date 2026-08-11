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
| **Direct prompt engineering over RAG** | Reconciliation inputs are small structured tables with full context that fit in a single prompt window. RAG (retrieval-augmented generation) adds unnecessary latency and complexity. Direct prompting lets the LLM reason over complete field mappings, mismatch frequencies, and KB context in one pass. Simpler, faster, more interpretable. |
| **JSON knowledge base with dual feedback** | User feedback directly tunes LLM behavior: 👍 stores examples in user_reasons (positive hints injected into prompts), 👎 populates flagged_reasons (hard prohibitions in system message). No vector embeddings, no embeddings drift over time. Learning is explicit, auditable, and interpretable—critical for financial audit trails. |
| **Inline 👍/👎 feedback per row** | Low-friction UX enables high engagement with KB learning. Feedback is immediate (no batch dialogs). Edits sync across All/Matched/Unmatched tabs via session_state, so users see consistent reasoning. Each confirmed reason increments use_count and improves LLM suggestions for the same field pair in future reconciliations. |
| **Frozen headers & Streamlit dataframe** | Frozen headers + sortable columns match analyst workflows from Excel/SQL query tools. Streamlit's on_select="rerun" enables row-level interaction patterns. Improves UX for large result sets (100s of rows) while maintaining data visibility during scroll. |
| **Timing difference: code-first, then LLM priority #1** | Deterministic date-range logic (code-level pre-detection) is fast and reliable—never misses timing differences due to LLM hallucination. Unmatched rows with dates outside matched period are flagged instantly without LLM call. For remaining rows, LLM receives timing difference as priority #1 reason in prompt. Dual-layer approach ensures false-negative rate → 0. |
| **Local knowledge base, no cloud sync** | Financial data (transaction amounts, identifiers) never leaves the workspace. knowledge_base.json stores only anonymized patterns (field pair labels, reason counts, flagged reason names), not transaction data. Reduces compliance/privacy risk, enables offline workflows, eliminates API dependency for KB learning. |
| **Comprehensive test suite (54 tests): when tests run** | Tests execute: (1) Before each commit (CI/CD gate), (2) On code changes to knowledge_base.py or reconcile.py, (3) When deploying to production. Test coverage: KB persistence (load/save corruption handling), record/get functions, LLM prompt injection (verify flagged reasons in prompt, user examples appear), timing difference logic (pre-detected rows skip LLM), end-to-end learning flows (save reason → context → future prompt). Tests are mandatory for financial reconciliation—they prevent regressions in matching logic and learning integrity. |
| **GPT-4o-mini LLM** | Balances cost, latency, and reasoning quality. Sufficient for structured data interpretation (field name similarity, reason inference from mismatches). Supports JSON parsing and conditional logic for reason prioritization. Lower cost than GPT-4 Turbo while maintaining accuracy for reconciliation tasks. Chosen after cost-benefit analysis on reason suggestion quality across 100+ test reconciliations. |
| **Session-state caching with KB hash invalidation** | LLM results for a given field pair are cached within a session (Streamlit session_state) to avoid redundant API calls when user revisits settings. Cache key = MD5 hash of (flagged_reasons + user_reasons) sections only—excluding mismatch_reasons which changes every run. When user flags/confirms a reason, hash changes → cache invalidates → fresh LLM call on next interaction. This balances cost (reduced API calls) with freshness (learning immediately reflected). |
""")



