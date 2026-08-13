import streamlit as st
from helper_functions.utility import check_password

st.set_page_config(
    layout="wide",
    page_title="Methodology",
    page_icon="🧭",
)

if not check_password():
    st.stop()

st.markdown(
    """
    <style>
        .m2-hero {
            background: linear-gradient(135deg, #e9f6ff 0%, #f8fcff 42%, #eef8ef 100%);
            border: 1px solid #d2e8fb;
            border-radius: 16px;
            padding: 1.2rem 1.4rem;
            margin-bottom: 1rem;
        }
        .m2-hero h1 {
            margin: 0 0 0.4rem 0;
            color: #163d61;
        }
        .m2-hero p {
            margin: 0;
            color: #234158;
            line-height: 1.45;
        }
        .m2-note {
            border-left: 4px solid #0d7a5f;
            background: #effcf8;
            color: #1c4135;
            border-radius: 8px;
            padding: 0.8rem 1rem;
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="m2-hero">
        <h1>🧭 Methodology</h1>
        <p>
            A complete end-to-end AI-assisted reconciliation workflow that combines deterministic checks,
            LLM reasoning, analyst governance, and continuous learning.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="m2-note">
        This page documents the operational flow, core AI design choices, and business value proposition
        of ReconBuddy for finance reconciliation use cases.
    </div>
    """,
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(
    [
        "End-to-End Workflow",
        "Key AI and Design Decisions",
        "AI Value Proposition",
    ]
)

with tab1:
    st.subheader("End-to-End Reconciliation Workflow")
    st.markdown(
        "| Phase | Performed By | Step | Details |\n"
        "|---:|---|---|---|\n"
        "| 1 | 📊 Analyst | Upload Source Files | Upload one or more source files in PDF, Excel, or CSV format. |\n"
        "| 2 | 🔧 System | Parse and Extract Data | Extract tables and text from uploaded documents, including structured and semi-structured content. |\n"
        "| 3 | 🔧 System | Normalise Data | Standardise column headers, identify likely amount fields, and prepare data for reconciliation. |\n"
        "| 4 | 🧠 AI/LLM | Analyse Data Structure | Review field names, descriptions, and extracted text to understand the business context of each dataset. |\n"
        "| 5 | 🧠 AI/LLM + 📊 Analyst | AI-Assisted Identifier Selection | Use semantic analysis to identify likely matching identifiers across datasets, including differently named fields and identifiers embedded in free text. Present recommended matches for analyst review and confirmation. |\n"
        "| 6 | 🔧 System | Aggregate and Reconcile | Group transactions by the selected identifier and aggregate amounts from each source for comparison. |\n"
        "| 7 | 🔧 System | Pre-detect Timing Differences | Analyse matched transaction date ranges and automatically flag potential timing differences before AI analysis. |\n"
        "| 8 | 📚 AI/KB | Load Knowledge Base Context | Retrieve relevant field mappings, confirmed examples, and flagged reasons from prior reconciliations. |\n"
        "| 9 | 🔧 System | Classify Records | Categorise transactions as Matched (within tolerance) or Unmatched (difference exceeds tolerance). |\n"
        "| 10 | 🧠 AI/LLM| Infer Reconciliation Reasons | Analyse unmatched transactions using transaction details, timing indicators, and knowledge base context. |\n"
        "| 11 | 🧠 AI/KB | Generate Suggested Reasons | Suggest explanations using approved examples while excluding previously flagged reasons. |\n"
        "| 12 | 📊 Analyst | Review Results | Review All, Matched, and Unmatched transactions through sortable tables with frozen headers. |\n"
        "| 13 | 🔧 System | Display Suggested Reasons | Present AI-generated explanations alongside each unmatched transaction. |\n"
        "| 14 | 📊 Analyst | Rate Suggestions | Confirm accurate explanations (👍) or flag incorrect explanations (👎). |\n"
        "| 15 | 🔧 System | Record Feedback | Save confirmed explanations as positive examples and flagged explanations as prohibited reasons in the knowledge base. |\n"
        "| 16 | 🧠 AI/KB | Update Knowledge Base | Recalculate the KB hash and invalidate cached AI responses whenever feedback changes. |\n"
        "| 17 | 📊 Analyst + 🧠 AI/LLM | Conversational Reconciliation Assistant | Ask natural-language questions about uploaded documents, transactions, mismatches, reconciliation results, and identified patterns. The assistant provides contextual insights, summaries, and investigation support without manual filtering. |\n"
        "| 18 | 📊 Analyst | Export Reconciliation Report | Download reconciliation results, status, differences, and explanations in Excel or CSV format. |\n"
        "| 19 | 🔁 Continuous Learning | Next Reconciliation | Future reconciliations automatically leverage approved examples, banned reasons, and learnt field mappings to improve suggestion quality and consistency. |"
    )

with tab2:
    st.subheader("Key AI and Design Decisions")
    st.markdown(
        "| Design Decision | Rationale |\n"
        "|---|---|\n"
        "| AI-Assisted Identifier Discovery | Uses semantic analysis and LLM reasoning to identify likely matching identifiers across heterogeneous datasets, including differently named fields and identifiers embedded in free-text descriptions. Reduces manual mapping effort and improves matching accuracy. |\n"
        "| Direct Prompt Engineering over RAG | Reconciliation datasets are typically small, structured, and fit within a single prompt context. Direct prompting enables the LLM to reason across field mappings, mismatch patterns, timing indicators, and knowledge base context in a single pass without retrieval overhead. |\n"
        "| Dual-Layer Timing Difference Detection | Combines deterministic date-range analysis with AI reasoning. The system first identifies timing differences using rule-based logic before invoking AI, ensuring reliable detection and minimising hallucination risk. |\n"
        "| Knowledge Base-Guided Reasoning | AI recommendations are enhanced using previously confirmed examples and prohibited explanations stored in the knowledge base. This improves consistency, relevance, and organisational alignment over time. |\n"
        "| Human-in-the-Loop Validation | Analysts retain control over reconciliation outcomes by reviewing and validating AI-generated recommendations. This ensures governance, accountability, and auditability in financial processes. |\n"
        "| Continuous Learning Through Feedback | Confirmed reasons (👍) are stored as positive examples, while rejected reasons (👎) become prohibited explanations. Future reconciliations automatically benefit from prior analyst decisions. |\n"
        "| Conversational Reconciliation Assistant | Enables users to interact with uploaded documents and reconciliation results using natural language. Users can investigate discrepancies, query transaction details, identify patterns, and generate summaries without manual dataset analysis. |\n"
        "| Session-State Caching with KB Invalidation | Reduces duplicate LLM calls while ensuring newly approved examples and flagged reasons are reflected immediately. Cached results are refreshed when the knowledge base changes. |\n"
        "| Privacy-Preserving AI Architecture | Learning is retained locally through a JSON-based knowledge base. No transaction-level data is stored in the knowledge base, reducing privacy, security, and compliance risks. |\n"
        "| GPT-4o-mini LLM Strategy | Selected to balance reasoning quality, response time, and operational cost. Provides strong performance for identifier discovery, reconciliation reasoning, and conversational assistance. |\n"
        "| Interactive Analyst Experience | Sortable tables, frozen headers, and synchronised views support efficient review of large reconciliation datasets while maintaining visibility of AI-generated recommendations. |\n"
        "| Comprehensive Automated Testing Framework | Validates reconciliation logic, knowledge base learning, timing-difference detection, prompt generation, and end-to-end workflows to ensure reliability and learning integrity. |"
    )

with tab3:
    st.subheader("AI Value Proposition")
    st.markdown(
        "| AI Capability | Business Value |\n"
        "|---|---|\n"
        "| Semantic matching | Identifies shared identifiers based on meaning, not only exact field names. |\n"
        "| Adaptive recommendations | Uses confirmed and flagged reasons to improve future suggestions. |\n"
        "| Conversational investigation | Lets analysts query uploaded documents and reconciliation results using natural language. |\n"
        "| Governed AI use | Keeps the analyst in control through confirmation, rejection, and exportable audit outputs. |"
    )

st.divider()
st.caption("Methodology2: structured workflow, explainable AI reasoning, and analyst-governed continuous learning.")
