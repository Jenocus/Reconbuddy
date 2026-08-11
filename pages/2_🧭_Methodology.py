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
    "The reconciliation workflow is a multi-phase process involving deterministic matching, LLM-assisted reason inference, user feedback loops, and knowledge base updates."
)

st.mermaid("""
graph TD
    A["📊 ANALYST: Select Identifier Pair<br/>(e.g., invoice_id)"]
    B["🔧 SYSTEM: Aggregate & Reconcile<br/>(Group by ID, sum amounts)"]
    C["⏰ SYSTEM: Pre-detect Timing Diffs<br/>(Code: check date ranges)"]
    D["📚 AI/KB: Load Context<br/>(user reasons, flagged bans)"]
    E["🔀 SYSTEM: Classify Rows<br/>(Matched / Unmatched)"]
    F["🧠 SYSTEM: Infer Unmatched Reasons<br/>(LLM: timing priority #1)"]
    G["🤖 AI/KB: Suggest Reasons<br/>(inject KB examples/bans)"]
    H["📋 ANALYST: Review Tables<br/>(All / Matched / Unmatched tabs)"]
    I["⭐ SYSTEM: Display with Reasons<br/>(frozen headers, sortable)"]
    J["👍👎 ANALYST: Rate Inline<br/>(confirm or flag wrong)"]
    K["💾 SYSTEM: Record Feedback<br/>(user_reasons / flagged_reasons)"]
    L["🔄 AI/KB: Update KB<br/>(recalc hash, invalidate cache)"]
    M["✅ ANALYST: Export Report<br/>(Excel / CSV)"]
    N["📥 SYSTEM: Save & Download<br/>(details + reasons)"]
    O["🔁 NEXT RECONCILIATION<br/>Uses Learned KB Patterns"]
    
    A --> B
    B --> C
    C --> D
    C --> E
    E --> F
    F --> G
    G --> F
    E --> H
    B --> I
    H --> J
    I --> J
    J --> K
    K --> L
    L --> O
    M --> N
    N --> O
    
    style A fill:#dbeafe,stroke:#0ea5e9,stroke-width:2px
    style B fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style C fill:#fce7f3,stroke:#db2777,stroke-width:2px
    style D fill:#fef08a,stroke:#ca8a04,stroke-width:2px
    style E fill:#e0e7ff,stroke:#6366f1,stroke-width:2px
    style F fill:#fbf8f3,stroke:#f97316,stroke-width:2px
    style G fill:#f5f3ff,stroke:#a78bfa,stroke-width:2px
    style H fill:#dcfce7,stroke:#16a34a,stroke-width:2px
    style I fill:#f0fdfa,stroke:#14b8a6,stroke-width:2px
    style J fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style K fill:#dbeafe,stroke:#0ea5e9,stroke-width:2px
    style L fill:#fef08a,stroke:#ca8a04,stroke-width:2px
    style M fill:#dcfce7,stroke:#16a34a,stroke-width:2px
    style N fill:#f0fdfa,stroke:#14b8a6,stroke-width:2px
    style O fill:#f3e8ff,stroke:#c084fc,stroke-width:3px
""")

st.caption(
    "**Workflow**: Analyst selects an identifier, System aggregates and classifies rows, AI/KB loads context and suggests reasons (with timing priority). "
    "Analyst rates each reason inline. Feedback updates KB for next reconciliation. Results exported and downloaded."
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



