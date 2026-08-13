import streamlit as st
from helper_functions.utility import check_password

st.set_page_config(
    layout="wide",
    page_title="About ReconBuddy",
    page_icon="📘",
)

if not check_password():
    st.stop()

st.markdown(
    """
    <style>
        .rb-hero {
            background: linear-gradient(135deg, #e8f4ff 0%, #f7fbff 45%, #eef9f1 100%);
            border: 1px solid #d4e7fb;
            border-radius: 16px;
            padding: 1.3rem 1.5rem;
            margin-bottom: 1rem;
        }
        .rb-hero h1 {
            margin: 0 0 0.5rem 0;
            color: #0f3557;
        }
        .rb-hero p {
            margin: 0;
            color: #23384d;
            line-height: 1.5;
        }
        .rb-note {
            border-left: 4px solid #0f6ab4;
            background: #f3f9ff;
            padding: 0.8rem 1rem;
            border-radius: 8px;
            margin: 0.8rem 0 1rem 0;
            color: #19344d;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1rem;
            line-height: 1.2;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="rb-hero">
        <h1>📘 About ReconBuddy</h1>
        <p>
            ReconBuddy is an AI-assisted reconciliation platform that automates matching, investigation,
            and explanation of financial transactions across disparate systems.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="rb-note">
        By combining deterministic reconciliation controls with adaptive AI learning,
        ReconBuddy helps finance teams reconcile data more efficiently, investigate exceptions faster,
        and continuously improve reconciliation outcomes.
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Key AI Capabilities")
cap_col1, cap_col2 = st.columns(2)
with cap_col1:
    st.write("- AI-assisted identifier discovery across heterogeneous datasets")
    st.write("- LLM-powered reconciliation reasoning for unmatched transactions")
with cap_col2:
    st.write("- Conversational AI assistance for natural language investigation")
    st.write("- Continuous learning through analyst feedback with governance")

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Problem Statement",
        "Proposed Solution",
        "PoC and Evolution",
        "Impact",
        "Core AI Features",
        "Technology and Team",
    ]
)

with tab1:
    st.markdown("### CPSA+ Reconciliation Challenge")
    st.write(
        "The Consumer Product Safety and Accuracy+ (CPSA+) system serves consumers, businesses, "
        "conformity assessment bodies, and regulators for Singapore's consumer product safety and "
        "weights and measures regimes."
    )

    st.markdown("#### Payment Flow")
    st.markdown(
        "1. Users make payments via Stripe.\n"
        "2. Payment details are transmitted to CPSA+.\n"
        "3. CPSA+ interfaces payment journals to NFS@GOV.\n"
        "4. Stripe consolidates payments and disburses payouts to CCS bank account."
    )

    st.markdown("#### Current Manual Reconciliation Inputs")
    cols = st.columns(4)
    cols[0].metric("Report 1", "Stripe Payout")
    cols[1].metric("Report 2", "Bank Statement")
    cols[2].metric("Report 3", "NFS Report")
    cols[3].metric("Report 4", "CPSA+ Report")

    st.markdown("#### Why Reconciliation Is Complex")
    st.write("- Reports use different formats, structures, and field names")
    st.write("- Some transactions are consolidated, while others are split")
    st.write("- Some reports show gross amounts, others show net amounts after Stripe fees")
    st.write("- Timing differences across systems create apparent mismatches")
    st.write("- NFS lacks common identifiers, requiring manual date and amount matching")

    st.warning(
        "Result: Finance officers spend significant effort on manual reconciliation and investigation, "
        "increasing error risk and reducing operational efficiency."
    )

with tab2:
    st.markdown("### What ReconBuddy Delivers")
    st.write(
        "ReconBuddy automates ingestion, interpretation, matching, and investigation of reconciliation "
        "data across multiple sources. Unlike traditional rule-heavy approaches, ReconBuddy leverages "
        "semantic AI to identify relationships across heterogeneous datasets, explain discrepancies, and "
        "improve recommendation quality through analyst feedback."
    )

    st.markdown("#### Platform Building Blocks")
    st.write("- AI-assisted identifier discovery")
    st.write("- Automated reconciliation and timing-difference detection")
    st.write("- AI-powered mismatch reason inference")
    st.write("- Human-in-the-loop validation and learning")
    st.write("- Conversational investigation through natural language queries")

    st.success(
        "Results are presented through a dashboard that enables users to review matched and "
        "unmatched transactions, validate AI-generated recommendations, investigate discrepancies, and "
        "export reconciliation results."
    )

with tab3:
    st.markdown("### Proof-of-Concept Scope")
    st.write("The original Proof-of-Concept validated core reconciliation capability by:")
    st.markdown(
        "- Accepting two reports in common formats\n"
        "- Identifying matching fields and records\n"
        "- Producing structured outputs for matched transactions, valid differences, and discrepancies"
    )

    st.info(
        "The PoC demonstrated the feasibility of AI-assisted matching and reconciliation across "
        "heterogeneous financial reports."
    )
    st.write(
           "To address the first two objectives, development began with a Shared Identifier Finder capability. "
           "This component enables users to upload two documents and identify likely shared identifiers"
           "before reconciliation is performed."
    )
    st.write(
           "Rather than relying on hard-coded field-name matching, the solution uses semantic analysis and "
           "LLM reasoning to identify likely matching identifiers across heterogeneous datasets. "
           "It can interpret the meaning of fields, recognise relationships between differently named columns, "
           "and identify identifiers embedded within descriptions or other free-text fields. "
           "The system then proposes recommended identifier mappings and allows analysts to confirm "
           "the preferred matching keys before reconciliation begins."
       )
    st.info(
        "This capability forms the foundation for subsequent reconciliation processes and can also be used independently "
        "to discover shared identifiers across disparate documents, even where reconciliation is not required."
    )

    st.markdown("### Enhanced the Proof-of-Concept - ⚖️ 2-way Match")
    st.write("The original Proof-of-Concept focused on validating the core reconciliation capability by accepting "
             "two reports, identifying matching fields and records, and producing a structured output showing "
             "matched transactions, valid differences, and discrepancies.")
    st.write("ReconBuddy has since evolved into a comprehensive AI-assisted 2-way reconciliation platform with "
             "capabilities beyond basic transaction matching, including:")
    st.markdown(
        "- AI-assisted identifier discovery across heterogeneous and free-text fields\n"
        "- Automated timing-difference detection for valid variances vs genuine exceptions\n"
        "- LLM-powered mismatch reason inference for unmatched transactions\n"
        "- Human-in-the-loop validation with inline feedback and approval workflows\n"
        "- Continuous learning knowledge base from analyst feedback\n"
        "- Conversational AI for natural language queries on source documents and results\n"
        "- Knowledge base administration, review tools, and exportable reports"
    )
    st.info(
        "As a result, ReconBuddy not only automates transaction matching but also assists users in investigating, "
        "explaining, and continuously improving reconciliation outcomes through AI-driven insights and learning. "
    )

    st.markdown("### Beyond the Proof-of-Concept - 🔄 4-way Match")
    st.write("The ultimate target is to implement 4-way reconciliation across the Stripe Payout Report, "
             "Bank Statement, NFS Report, and CPSA+ Report within a single reconciliation workflow. ")
    st.write("While the current 2-way matching capability can reconcile reports pairwise (e.g. Stripe vs Bank, "
             "CPSA+ vs NFS), it requires multiple reconciliation runs and does not provide a consolidated "
             "end-to-end view across all four data sources.")
    st.write("Implementing a 4-way reconciliation presents several challenges, including: ")
    st.markdown(
        "- Different data structures, field names and levels of aggregation across systems\n"
        "- Transactions that are consolidated in one report but split across multiple records in another\n"
        "- Gross and net amount differences arising from payment gateway fees\n"
        "- Timing differences across multiple systems and reporting periods\n"
        "- Absence of common identifiers in some systems\n"
        "- Discrepancies that span multiple reports rather than a single source pair"
    )
    st.info(
        "Addressing these challenges requires more advanced matching logic, multi-source relationship analysis "
        "and AI-assisted reasoning. The planned 4-way reconciliation capability will provide a more holistic and"
        "automated reconciliation process, enabling Finance officers to trace transactions across the entire "
        "payment lifecycle and identify exceptions more efficiently."
    )
with tab4:
    st.markdown("### Short-Term Benefits")
    short_col1, short_col2 = st.columns(2)
    with short_col1:
        st.write("- Reduce manual reconciliation effort for CCS Finance")
        st.write("- Accelerate reconciliation and investigation cycles")
    with short_col2:
        st.write("- Improve consistency and accuracy")
        st.write("- Reduce risk of human error in discrepancy analysis")

    st.markdown("### Long-Term Benefits")
    st.write(
        "ReconBuddy is designed as a scalable, reusable AI-assisted reconciliation capability. "
        "By understanding relationships between fields, identifiers, and transactions using semantic AI, "
        "the platform can extend beyond hard-coded rules and adapt across many reconciliation scenarios."
    )

    st.markdown("#### Potential Reuse Scenarios")
    st.write("- Cross-system financial reconciliations")
    st.write("- Inter-agency reconciliations")
    st.write("- Payment and collection reconciliations")
    st.write("- Grant and subsidy reconciliations")
    st.write("- Other multi-source matching and exception-management processes")

    st.caption(
        "This positions ReconBuddy not only as a CPSA+ solution, but as a reusable AI-assisted "
        "reconciliation capability across Singapore Government contexts."
    )

with tab5:
    st.markdown("### Core Capabilities")
    st.markdown(
        "| Capability | Description |\n"
        "|---|---|\n"
        "| 📄 Upload and Parse Multiple Source Files | Ingest PDF, Excel, and CSV files for reconciliation |\n"
        "| 🔍 AI-Assisted Identifier Discovery | Identify likely shared identifiers across heterogeneous datasets, including free text |\n"
        "| 🧾 Amount Reconciliation Using Selected Identifier Pairs | Reconcile transactions across multiple sources using analyst-approved keys |\n"
        "| ⏰ Automatic Timing Difference Detection | Detect timing differences by comparing transaction dates against matched periods |\n"
        "| 🤖 LLM-Powered Mismatch Reason Inference | Generate likely explanations for unmatched transactions using context and feedback |\n"
        "| 📊 Interactive Reconciliation Review | Review matched, unmatched, and all transactions through sortable tables with frozen headers |\n"
        "| 👍👎 Inline Analyst Feedback and Validation | Edit, confirm, or reject AI-generated mismatch reasons directly in results |\n"
        "| 📚 Continuous Learning Knowledge Base | Confirmed reasons become positive examples; flagged reasons are excluded later |\n"
        "| ✓ Knowledge Base Administration | Manage approved field pairings, user examples, and flagged reasons |\n"
        "| 💬 Conversational Reconciliation Assistant | Ask natural-language questions about files, transactions, and results |\n"
        "| 📤 Export Reconciliation Reports | Download outcomes and explanations in Excel or CSV |\n"
        "| 🔒 Privacy-Preserving Local Learning | Store learning locally without retaining transaction-level data in the knowledge base |"
    )

with tab6:
    st.markdown("### Technology Stack")
    st.markdown(
        "| Component | Tool |\n"
        "|---|---|\n"
        "| UI Framework | Streamlit |\n"
        "| Language Model | OpenAI GPT-4o-mini |\n"
        "| Backend | Python 3.10+ |\n"
        "| Data Processing | pandas |\n"
        "| Document Parsing | PyPDF2 |\n"
        "| Spreadsheet Support | openpyxl |\n"
        "| Visualisation | Altair |"
    )

    st.markdown("### Team")
    st.markdown(
        "| Name | Role |\n"
        "|---|---|\n"
        "| Jencus Lin | ReconBuddy Developer |"
    )

st.divider()
st.caption("ReconBuddy: AI-assisted reconciliation with explainability, governance, and continuous learning.")
