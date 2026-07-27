import streamlit as st
from helper_functions.utility import check_password

st.set_page_config(
    layout="centered",
    page_title="About Us",
    page_icon="📘",
)

if not check_password():
    st.stop()

st.title("📘 About Us")
st.write(
    "Reconbuddy is an AI-assisted reconciliation workspace designed to help teams compare financial and operational records with less manual effort and more transparency."
)

st.subheader("Project scope")
st.write(
    "The application brings together document ingestion, field discovery, shared-identifier analysis, and reconciliation workflows in a single Streamlit experience. It is intended for analysts who need to compare reports from different systems without manually building every mapping by hand."
)

st.subheader("Objectives")
col1, col2 = st.columns(2)
with col1:
    st.write("- Reduce time spent on manual reconciliation")
    st.write("- Surface likely shared identifiers across inconsistent files")
    st.write("- Provide explainable reconciliation results instead of opaque outputs")
with col2:
    st.write("- Support both conversational exploration and structured analysis")
    st.write("- Help users inspect unmatched records and their likely causes")
    st.write("- Deliver downloadable evidence for audit and review workflows")

st.subheader("Data sources")
st.write(
    "Reconbuddy can work with a variety of business documents, including PDF statements, Excel workbooks, and CSV exports. The app extracts tables or text from those files, normalizes headers where possible, and then applies AI-assisted reasoning to identify likely matching fields and reconciliation keys."
)

st.subheader("Intelligence approach")
st.write(
    "Reconbuddy uses semantic analysis and an LLM to map fields across heterogeneous documents. Instead of relying on hard-coded field-name matching, it can identify shared identifiers even when they appear inside descriptions or other free-text fields."
)

st.subheader("Core features")
st.write("- 📄 Upload and parse multiple source files")
st.write("- 🔍 Discover candidate shared identifiers across heterogeneous data")
st.write("- 🧾 Reconcile amounts using a selected identifier pair")
st.write("- 📊 Review matched and unmatched rows with reason summaries")
st.write("- ⬇️ Download reconciliation results as Excel or CSV")
st.write("- 💬 Ask questions and explore the application through the conversational interface")

st.subheader("Who this is for")
st.write(
    "This workflow is especially useful for finance operations, controls teams, audit support, and data analysts who need a faster way to validate records that come from different formats or systems."
)
