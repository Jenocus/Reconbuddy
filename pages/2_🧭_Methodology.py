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
    <svg width="1000" height="700" viewBox="0 0 1000 700" xmlns="http://www.w3.org/2000/svg" style="overflow: auto;">
      <!-- Swimlane Headers -->
      <rect x="0" y="0" width="200" height="700" fill="#f0f4f8" stroke="#ccc"/>
      <rect x="200" y="0" width="400" height="700" fill="#f9fafb" stroke="#ccc"/>
      <rect x="600" y="0" width="400" height="700" fill="#fffbf0" stroke="#ccc"/>
      
      <text x="100" y="30" text-anchor="middle" font-weight="bold" font-size="14" fill="#1f2937">Analyst</text>
      <text x="400" y="30" text-anchor="middle" font-weight="bold" font-size="14" fill="#1f2937">System</text>
      <text x="800" y="30" text-anchor="middle" font-weight="bold" font-size="14" fill="#1f2937">AI / Knowledge Base</text>
      
      <!-- Horizontal lanes -->
      <line x1="0" y1="50" x2="1000" y2="50" stroke="#ccc" stroke-width="1"/>
      <line x1="0" y1="150" x2="1000" y2="150" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="5"/>
      <line x1="0" y1="250" x2="1000" y2="250" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="5"/>
      <line x1="0" y1="350" x2="1000" y2="350" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="5"/>
      <line x1="0" y1="450" x2="1000" y2="450" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="5"/>
      <line x1="0" y1="550" x2="1000" y2="550" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="5"/>
      <line x1="0" y1="650" x2="1000" y2="650" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="5"/>
      
      <!-- Vertical swimlane separators -->
      <line x1="200" y1="0" x2="200" y2="700" stroke="#aaa" stroke-width="2"/>
      <line x1="600" y1="0" x2="600" y2="700" stroke="#aaa" stroke-width="2"/>
      
      <!-- Phase 1: Select identifier pair (y=80) -->
      <rect x="20" y="65" width="160" height="60" rx="8" fill="#e8f1ff" stroke="#4c78a8" stroke-width="2"/>
      <text x="100" y="97" text-anchor="middle" font-size="13" fill="#1f2937">1. Select identifier</text>
      <text x="100" y="115" text-anchor="middle" font-size="12" fill="#666">(e.g., invoice_id)</text>
      
      <arrow x1="180" y1="95" x2="220" y2="95" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- Phase 2: Reconcile amounts (y=80) -->
      <rect x="220" y="65" width="160" height="60" rx="8" fill="#fef3c7" stroke="#f59e0b" stroke-width="2"/>
      <text x="300" y="90" text-anchor="middle" font-size="12" fill="#1f2937">2. Aggregate &amp;</text>
      <text x="300" y="108" text-anchor="middle" font-size="12" fill="#1f2937">reconcile totals</text>
      <text x="300" y="120" text-anchor="middle" font-size="10" fill="#666">(Group by ID)</text>
      
      <arrow x1="380" y1="95" x2="420" y2="95" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- Phase 3: Pre-detect timing (y=80) -->
      <rect x="420" y="65" width="170" height="60" rx="8" fill="#fce7f3" stroke="#db2777" stroke-width="2"/>
      <text x="505" y="90" text-anchor="middle" font-size="12" fill="#1f2937">3. Pre-detect timing</text>
      <text x="505" y="108" text-anchor="middle" font-size="12" fill="#1f2937">differences (code)</text>
      <text x="505" y="120" text-anchor="middle" font-size="10" fill="#666">(Check date ranges)</text>
      
      <arrow x1="590" y1="95" x2="630" y2="95" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- Phase 3b: Load KB context -->
      <rect x="620" y="65" width="150" height="60" rx="8" fill="#fef08a" stroke="#eab308" stroke-width="2"/>
      <text x="695" y="90" text-anchor="middle" font-size="12" fill="#1f2937">Load KB context</text>
      <text x="695" y="108" text-anchor="middle" font-size="12" fill="#1f2937">(user reasons,</text>
      <text x="695" y="120" text-anchor="middle" font-size="10" fill="#666">flagged bans)</text>
      
      <!-- Phase 4: Classify rows (y=170) -->
      <rect x="220" y="165" width="160" height="60" rx="8" fill="#dbeafe" stroke="#0ea5e9" stroke-width="2"/>
      <text x="300" y="190" text-anchor="middle" font-size="12" fill="#1f2937">4. Classify rows:</text>
      <text x="300" y="208" text-anchor="middle" font-size="11" fill="#666">Matched / Unmatched</text>
      
      <arrow x1="300" y1="150" x2="300" y2="165" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      <arrow x1="380" y1="195" x2="420" y2="195" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- Phase 5: Infer reasons (y=170) -->
      <rect x="420" y="165" width="170" height="60" rx="8" fill="#fbf8f3" stroke="#f97316" stroke-width="2"/>
      <text x="505" y="190" text-anchor="middle" font-size="12" fill="#1f2937">5. Infer unmatched</text>
      <text x="505" y="208" text-anchor="middle" font-size="12" fill="#1f2937">reasons (LLM)</text>
      <text x="505" y="220" text-anchor="middle" font-size="10" fill="#666">(Timing #1 priority)</text>
      
      <arrow x1="590" y1="195" x2="630" y2="195" stroke="#c026d3" stroke-width="2" marker-end="url(#arrowhead)" stroke-dasharray="5"/>
      <text x="615" y="185" font-size="10" fill="#c026d3">query KB</text>
      
      <!-- Phase 5b: Reason response -->
      <rect x="620" y="165" width="150" height="60" rx="8" fill="#fce7f3" stroke="#db2777" stroke-width="2"/>
      <text x="695" y="190" text-anchor="middle" font-size="12" fill="#1f2937">Suggest reasons</text>
      <text x="695" y="208" text-anchor="middle" font-size="12" fill="#1f2937">(injecting KB</text>
      <text x="695" y="220" text-anchor="middle" font-size="10" fill="#666">examples &amp; bans)</text>
      
      <arrow x1="770" y1="195" x2="810" y2="195" stroke="#c026d3" stroke-width="2" marker-end="url(#arrowhead)" stroke-dasharray="5"/>
      <text x="775" y="185" font-size="10" fill="#c026d3">return</text>
      
      <!-- Phase 6: Display results (y=270) -->
      <rect x="20" y="265" width="160" height="70" rx="8" fill="#dcfce7" stroke="#16a34a" stroke-width="2"/>
      <text x="100" y="290" text-anchor="middle" font-size="12" fill="#1f2937">6. Review tables:</text>
      <text x="100" y="308" text-anchor="middle" font-size="11" fill="#666">All / Matched /</text>
      <text x="100" y="325" text-anchor="middle" font-size="11" fill="#666">Unmatched</text>
      
      <arrow x1="180" y1="300" x2="220" y2="300" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- Phase 6b: Display with reasons -->
      <rect x="220" y="265" width="160" height="70" rx="8" fill="#f3f4f6" stroke="#6b7280" stroke-width="2"/>
      <text x="300" y="290" text-anchor="middle" font-size="12" fill="#1f2937">Show rows with</text>
      <text x="300" y="308" text-anchor="middle" font-size="11" fill="#666">sorted columns,</text>
      <text x="300" y="325" text-anchor="middle" font-size="11" fill="#666">frozen headers</text>
      
      <arrow x1="380" y1="300" x2="420" y2="300" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- Phase 7: Rate inline (y=270) -->
      <rect x="420" y="265" width="170" height="70" rx="8" fill="#e0e7ff" stroke="#6366f1" stroke-width="2"/>
      <text x="505" y="290" text-anchor="middle" font-size="12" fill="#1f2937">7. Rate inline:</text>
      <text x="505" y="308" text-anchor="middle" font-size="11" fill="#666">👍 = confirm</text>
      <text x="505" y="325" text-anchor="middle" font-size="11" fill="#666">👎 = flag wrong</text>
      
      <arrow x1="590" y1="300" x2="630" y2="300" stroke="#c026d3" stroke-width="2" marker-end="url(#arrowhead)" stroke-dasharray="5"/>
      <text x="600" y="290" font-size="10" fill="#c026d3">feedback</text>
      
      <!-- Phase 7b: Record feedback -->
      <rect x="620" y="265" width="150" height="70" rx="8" fill="#dbeafe" stroke="#0ea5e9" stroke-width="2"/>
      <text x="695" y="290" text-anchor="middle" font-size="12" fill="#1f2937">Record:</text>
      <text x="695" y="308" text-anchor="middle" font-size="11" fill="#666">👍 → user_reasons</text>
      <text x="695" y="325" text-anchor="middle" font-size="11" fill="#666">👎 → flagged_reasons</text>
      
      <!-- Phase 8: Update KB (y=380) -->
      <arrow x1="100" y1="340" x2="100" y2="365" stroke="#c026d3" stroke-width="2" marker-end="url(#arrowhead)" stroke-dasharray="5"/>
      <text x="150" y="355" font-size="10" fill="#c026d3">submit</text>
      
      <rect x="620" y="365" width="150" height="60" rx="8" fill="#fef08a" stroke="#eab308" stroke-width="2"/>
      <text x="695" y="390" text-anchor="middle" font-size="12" fill="#1f2937">8. Update KB:</text>
      <text x="695" y="408" text-anchor="middle" font-size="11" fill="#666">Recalc hash,</text>
      <text x="695" y="420" text-anchor="middle" font-size="10" fill="#666">invalidate cache</text>
      
      <!-- Phase 9: Admin review (y=480) -->
      <rect x="20" y="465" width="160" height="60" rx="8" fill="#e5e7eb" stroke="#6b7280" stroke-width="2"/>
      <text x="100" y="490" text-anchor="middle" font-size="12" fill="#1f2937">9. (Optional)</text>
      <text x="100" y="508" text-anchor="middle" font-size="12" fill="#1f2937">Admin review KB</text>
      
      <arrow x1="180" y1="495" x2="220" y2="495" stroke="#9ca3af" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- Phase 9b: Edit/manage -->
      <rect x="220" y="465" width="160" height="60" rx="8" fill="#f5f3ff" stroke="#a78bfa" stroke-width="2"/>
      <text x="300" y="490" text-anchor="middle" font-size="12" fill="#1f2937">Edit pairings,</text>
      <text x="300" y="508" text-anchor="middle" font-size="12" fill="#1f2937">examples, bans</text>
      
      <!-- Phase 10: Export (y=590) -->
      <rect x="20" y="575" width="160" height="60" rx="8" fill="#dcfce7" stroke="#16a34a" stroke-width="2"/>
      <text x="100" y="600" text-anchor="middle" font-size="12" fill="#1f2937">10. Export:</text>
      <text x="100" y="618" text-anchor="middle" font-size="12" fill="#1f2937">Excel / CSV</text>
      
      <arrow x1="180" y1="605" x2="220" y2="605" stroke="#4c78a8" stroke-width="2" marker-end="url(#arrowhead)"/>
      
      <!-- Phase 10b: Download -->
      <rect x="220" y="575" width="160" height="60" rx="8" fill="#f0fdfa" stroke="#14b8a6" stroke-width="2"/>
      <text x="300" y="600" text-anchor="middle" font-size="12" fill="#1f2937">Save report</text>
      <text x="300" y="618" text-anchor="middle" font-size="12" fill="#1f2937">(details + reasons)</text>
      
      <!-- Next run feedback loop -->
      <path d="M 420 605 Q 500 650 620 390" stroke="#c026d3" stroke-width="2" stroke-dasharray="5" fill="none" marker-end="url(#arrowhead-dashed)"/>
      <text x="480" y="640" font-size="10" fill="#c026d3" font-weight="bold">Next reconciliation</text>
      <text x="480" y="655" font-size="10" fill="#c026d3">uses learned KB</text>
      
      <!-- Arrow marker definition -->
      <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
          <polygon points="0 0, 10 3, 0 6" fill="#4c78a8"/>
        </marker>
        <marker id="arrowhead-dashed" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
          <polygon points="0 0, 10 3, 0 6" fill="#c026d3"/>
        </marker>
      </defs>
    </svg>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "**Swimlane flow**: Analyst (left) interacts with System (center) to review and rate reconciliation results. "
    "System queries AI/KB (right) for reason suggestions and learning. Feedback loop (dashed) ensures next reconciliation benefits from user corrections."
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



