import streamlit as st
from helper_functions.utility import check_password

# region <--------- Streamlit Page Configuration --------->

st.set_page_config(
    layout="centered",
    page_title="ReconBuddy",
    page_icon="🧾",
)

# Do not continue if check_password is not True.
if not check_password():
    st.stop()

# endregion <--------- Streamlit Page Configuration --------->

st.title("🧾 ReconBuddy")
st.write("""
Welcome to ReconBuddy! Navigate using the **sidebar** to explore:

- ℹ️ **About Us** — Learn about the project scope, objectives, and tech stack
- 🧭 **Methodology** — Understand the workflow behind shared-identifier discovery and reconciliation
- 🔍 **Shared Identifier Finder** — Discover likely shared identifiers across two reports
- 🧾 **ReconBuddy** — Reconcile amounts using a selected identifier pair and review unmatched rows
""")
