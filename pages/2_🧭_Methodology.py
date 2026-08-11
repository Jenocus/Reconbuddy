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

st.subheader("Use case 2: Reconciliation workflow")
st.write(
    "The reconciliation workflow is a multi-phase process involving deterministic matching, LLM-assisted reason inference, user feedback loops, and knowledge base updates. Below is the swimlane diagram showing interactions between the Analyst, System, and AI/KB components."
)

st.markdown(
    """
    <svg width="100%" height="auto" viewBox="0 0 1100 750" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
          <polygon points="0 0, 10 3, 0 6" fill="#4c78a8"/>
        </marker>
        <marker id="arrowhead-purple" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
          <polygon points="0 0, 10 3, 0 6" fill="#c026d3"/>
        </marker>
      </defs>
      
      <!-- Swimlane backgrounds -->
      <rect x="0" y="50" width="250" height="700" fill="#f0f4f8" stroke="#999" stroke-width="1"/>
      <rect x="250" y="50" width="400" height="700" fill="#f9fafb" stroke="#999" stroke-width="1"/>
      <rect x="650" y="50" width="450" height="700" fill="#fffbf0" stroke="#999" stroke-width="1"/>
      
      <!-- Swimlane headers -->
      <text x="125" y="35" text-anchor="middle" font-weight="bold" font-size="14" fill="#1f2937">ANALYST</text>
      <text x="450" y="35" text-anchor="middle" font-weight="bold" font-size="14" fill="#1f2937">SYSTEM</text>
      <text x="875" y="35" text-anchor="middle" font-weight="bold" font-size="14" fill="#1f2937">AI / KB</text>
      
      <!-- Swimlane dividers -->
      <line x1="250" y1="50" x2="250" y2="750" stroke="#666" stroke-width="2"/>
      <line x1="650" y1="50" x2="650" y2="750" stroke="#666" stroke-width="2"/>
      
      <!-- PHASE 1: Select Identifier (y=80) -->
      <rect x="15" y="70" width="220" height="55" rx="5" fill="#dbeafe" stroke="#0ea5e9" stroke-width="2"/>
      <text x="125" y="95" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">1. Select Identifier Pair</text>
      <text x="125" y="112" text-anchor="middle" font-size="10" fill="#666">(e.g., invoice_id)</text>
      
      <line x="235" y1="97" x2="250" y2="97" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- PHASE 2: Aggregate (y=80) -->
      <rect x="265" y="70" width="220" height="55" rx="5" fill="#fef3c7" stroke="#f59e0b" stroke-width="2"/>
      <text x="375" y="95" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">2. Aggregate &amp; Reconcile</text>
      <text x="375" y="112" text-anchor="middle" font-size="10" fill="#666">(Group by ID, sum amounts)</text>
      
      <line x="485" y1="97" x2="650" y2="97" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- PHASE 3: Pre-detect Timing (y=80) -->
      <rect x="665" y="70" width="220" height="55" rx="5" fill="#fce7f3" stroke="#db2777" stroke-width="2"/>
      <text x="775" y="95" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">3. Pre-detect Timing Diffs</text>
      <text x="775" y="112" text-anchor="middle" font-size="10" fill="#666">(Code: check date ranges)</text>
      
      <!-- Feedback arrow to KB -->
      <line x1="885" y1="95" x2="900" y2="95" stroke="#c026d3" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrowhead-purple)"/>
      <text x="885" y="88" font-size="9" fill="#c026d3">load</text>
      
      <!-- PHASE 3b: Load KB (y=80) -->
      <rect x="915" y="70" width="170" height="55" rx="5" fill="#fef08a" stroke="#ca8a04" stroke-width="2"/>
      <text x="1000" y="95" text-anchor="middle" font-size="11" font-weight="bold" fill="#1f2937">Load KB Context</text>
      <text x="1000" y="112" text-anchor="middle" font-size="9" fill="#666">(user reasons, bans)</text>
      
      <!-- PHASE 4: Classify Rows (y=180) -->
      <line x1="125" y1="125" x2="125" y2="150" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <rect x="15" y="150" width="220" height="55" rx="5" fill="#e0e7ff" stroke="#6366f1" stroke-width="2"/>
      <text x="125" y="175" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">4. Classify Rows</text>
      <text x="125" y="192" text-anchor="middle" font-size="10" fill="#666">(Matched / Unmatched)</text>
      
      <line x="235" y1="177" x2="250" y2="177" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- PHASE 5: Infer Reasons (y=180) -->
      <rect x="265" y="150" width="220" height="55" rx="5" fill="#fbf8f3" stroke="#f97316" stroke-width="2"/>
      <text x="375" y="175" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">5. Infer Unmatched Reasons</text>
      <text x="375" y="192" text-anchor="middle" font-size="10" fill="#666">(LLM: timing priority #1)</text>
      
      <line x="485" y1="177" x2="650" y2="177" stroke="#c026d3" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrowhead-purple)"/>
      <text x="550" y="170" font-size="9" fill="#c026d3">query KB</text>
      
      <!-- KB: Suggest Reasons -->
      <rect x="665" y="150" width="220" height="55" rx="5" fill="#f5f3ff" stroke="#a78bfa" stroke-width="2"/>
      <text x="775" y="175" text-anchor="middle" font-size="11" font-weight="bold" fill="#1f2937">Suggest Reasons</text>
      <text x="775" y="192" text-anchor="middle" font-size="9" fill="#666">(inject KB examples/bans)</text>
      
      <line x="665" y1="177" x2="650" y2="177" stroke="#c026d3" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrowhead-purple)"/>
      <text x="650" y="170" font-size="9" fill="#c026d3" text-anchor="end">return</text>
      
      <!-- PHASE 6: Display Tables (y=260) -->
      <line x1="125" y1="205" x2="125" y2="230" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <rect x="15" y="230" width="220" height="55" rx="5" fill="#dcfce7" stroke="#16a34a" stroke-width="2"/>
      <text x="125" y="255" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">6. Display Tables</text>
      <text x="125" y="272" text-anchor="middle" font-size="10" fill="#666">(All / Matched / Unmatched)</text>
      
      <line x="235" y1="257" x2="250" y2="257" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- System: Show Results -->
      <rect x="265" y="230" width="220" height="55" rx="5" fill="#f0fdfa" stroke="#14b8a6" stroke-width="2"/>
      <text x="375" y="255" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">Display with Reasons</text>
      <text x="375" y="272" text-anchor="middle" font-size="10" fill="#666">(frozen headers, sortable)</text>
      
      <!-- PHASE 7: Rate Inline (y=340) -->
      <line x1="125" y1="285" x2="125" y2="310" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <rect x="15" y="310" width="220" height="55" rx="5" fill="#fef3c7" stroke="#f59e0b" stroke-width="2"/>
      <text x="125" y="335" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">7. Rate Inline</text>
      <text x="125" y="352" text-anchor="middle" font-size="10" fill="#666">👍 confirm | 👎 flag wrong</text>
      
      <line x="235" y1="337" x2="250" y2="337" stroke="#c026d3" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrowhead-purple)"/>
      <text x="240" y="330" font-size="9" fill="#c026d3">feedback</text>
      
      <!-- System: Record Feedback -->
      <rect x="265" y="310" width="220" height="55" rx="5" fill="#dbeafe" stroke="#0ea5e9" stroke-width="2"/>
      <text x="375" y="335" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">Record Feedback</text>
      <text x="375" y="352" text-anchor="middle" font-size="10" fill="#666">👍→user_reasons|👎→flagged</text>
      
      <line x="485" y1="337" x2="650" y2="337" stroke="#c026d3" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrowhead-purple)"/>
      <text x="550" y="330" font-size="9" fill="#c026d3">submit</text>
      
      <!-- KB: Persist Updates -->
      <rect x="665" y="310" width="220" height="55" rx="5" fill="#fef08a" stroke="#ca8a04" stroke-width="2"/>
      <text x="775" y="335" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">8. Update KB</text>
      <text x="775" y="352" text-anchor="middle" font-size="10" fill="#666">(recalc hash, invalidate cache)</text>
      
      <!-- PHASE 9: (Optional) Admin Review (y=420) -->
      <line x1="125" y1="365" x2="125" y2="390" stroke="#9ca3af" stroke-width="2" marker-end="url(#arrowhead)" opacity="0.6"/>
      <text x="125" y="385" text-anchor="middle" font-size="9" fill="#999">(optional)</text>
      
      <rect x="15" y="390" width="220" height="50" rx="5" fill="#e5e7eb" stroke="#6b7280" stroke-width="2" opacity="0.7"/>
      <text x="125" y="413" text-anchor="middle" font-size="11" font-weight="bold" fill="#4b5563">9. Admin Review</text>
      <text x="125" y="428" text-anchor="middle" font-size="9" fill="#666">(edit KB)</text>
      
      <!-- PHASE 10: Export (y=500) -->
      <line x1="125" y1="440" x2="125" y2="460" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <rect x="15" y="460" width="220" height="50" rx="5" fill="#dcfce7" stroke="#16a34a" stroke-width="2"/>
      <text x="125" y="483" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">10. Export Report</text>
      <text x="125" y="498" text-anchor="middle" font-size="9" fill="#666">(Excel / CSV)</text>
      
      <line x="235" y1="485" x2="250" y2="485" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- System: Download -->
      <rect x="265" y="460" width="220" height="50" rx="5" fill="#f0fdfa" stroke="#14b8a6" stroke-width="2"/>
      <text x="375" y="483" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937">Save &amp; Download</text>
      <text x="375" y="498" text-anchor="middle" font-size="9" fill="#666">(details + reasons)</text>
      
      <!-- Feedback Loop: Next Reconciliation -->
      <path d="M 485 485 Q 575 600 825 380" stroke="#c026d3" stroke-width="2" stroke-dasharray="4" fill="none" marker-end="url(#arrowhead-purple)"/>
      <text x="600" y="620" font-size="10" fill="#c026d3" font-weight="bold">↻ Next reconciliation</text>
      <text x="600" y="635" font-size="9" fill="#c026d3">uses learned KB patterns</text>
    </svg>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "**Swimlane flow**: Analyst (left) interacts with System (center) to review and rate results. "
    "System queries AI/KB (right) for suggestions and learning. Dashed arrows show KB interactions. "
    "Feedback loop ensures next reconciliation benefits from user corrections."
)



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



