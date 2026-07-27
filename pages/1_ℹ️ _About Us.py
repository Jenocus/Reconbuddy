import streamlit as st
from helper_functions.utility import check_password

st.set_page_config(
    layout="centered",
    page_title="About Us",
    page_icon="ℹ️",
)

if not check_password():
    st.stop()

st.title("ℹ️ About Us")
st.write(
    "Reconbuddy is an AI-assisted reconciliation workspace designed to help teams compare financial and operational records with less manual effort and more transparency."
)

st.subheader("Project scope")
st.write(
    "Reconbuddy combines document ingestion, shared-identifier discovery, and reconciliation in a single workflow for comparing reports from different systems."
)

st.subheader("Objectives")
col1, col2 = st.columns(2)
with col1:
    st.write("- Speed up reconciliation between mismatched reports")
    st.write("- Identify likely shared identifiers across different formats")
    st.write("- Highlight unmatched records and likely causes")
with col2:
    st.write("- Use AI to interpret meaning rather than rely on exact field names")
    st.write("- Provide transparent reasoning behind matches and recommendations")
    st.write("- Export results for review and audit workflows")

st.subheader("Data sources")
st.write(
    "Reconbuddy can work with a variety of business documents, including PDF statements, Excel workbooks, and CSV exports. The app extracts tables or text from those files, normalizes headers where possible, and then applies AI-assisted reasoning to identify likely matching fields and reconciliation keys."
)

st.subheader("Intelligence approach")
st.write(
    "Reconbuddy uses semantic analysis and an LLM to highlight the most likely shared identifiers across heterogeneous documents. Instead of relying on hard-coded field-name matching, the model can interpret meaning, connect related fields, and detect identifiers that appear inside descriptions or other free-text fields."
)

st.subheader("Core features")
st.write("- 📄 Upload and parse multiple source files")
st.write("- 🔍 Discover candidate shared identifiers across heterogeneous data")
st.write("- 🧾 Reconcile amounts using a selected identifier pair")
st.write("- 📊 Review matched and unmatched rows with reason summaries")
st.write("- ⬇️ Download reconciliation results as Excel or CSV")
st.write("- 🤖 Use LLM-based reasoning to interpret field meaning and support matches")

st.subheader("Tech Stack")
st.write("""
| Component | Tool |
|---|---|
| UI Framework | [Streamlit](https://streamlit.io/) |
| Language Model | [OpenAI GPT-4o-mini](https://openai.com/) |
| Backend | Python 3.10+ |
| Data Processing | [pandas](https://pandas.pydata.org/) |
| Document Parsing | [PyPDF2](https://pypdf.readthedocs.io/) |
| Spreadsheet Support | [openpyxl](https://openpyxl.readthedocs.io/) |
| Visualization | [Altair](https://altair-viz.github.io/) |
""")

st.subheader("Who this is for")
st.write(
    "This workflow is especially useful for finance operations, controls teams, audit support, and data analysts who need a faster way to validate records that come from different formats or systems."
)
