import os
import sys
from pathlib import Path

# Add project root to sys.path so 'frontend' and 'backend' packages are always discoverable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from frontend.components.api_client import ContextBankAPI

st.set_page_config(
    page_title="Context Bank",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize API client
backend_url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
api = ContextBankAPI(base_url=backend_url)

# Multi-Page Navigation using Streamlit modern navigation API
p_dash = st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=True)
p_contexts = st.Page("pages/contexts.py", title="Context Bank", icon="🗂️")
p_create = st.Page("pages/create_context.py", title="Create Context", icon="➕")
p_detail = st.Page("pages/context_detail.py", title="Context Detail", icon="📋")
p_integrations = st.Page("pages/integrations.py", title="Integrations", icon="🔌")
p_settings = st.Page("pages/settings.py", title="Settings", icon="⚙️")

pg = st.navigation(
    {
        "Context Bank": [p_dash, p_contexts, p_create, p_integrations, p_settings],
        "Details": [p_detail],
    }
)

with st.sidebar:
    st.markdown("### 🏦 **Context Bank**")
    st.caption("Portable Trigger-Based Context Management")

    health = api.get_health()
    if health.get("status") == "healthy":
        st.markdown("🟢 **Backend Connected**")
    else:
        st.markdown("🔴 **Backend Unreachable**")
        st.caption("Run: `uvicorn backend.main:app --reload`")

    st.markdown("---")
    st.caption("💡 **Tip:** Use triggers like `VOXCENT` in prompts to retrieve context instantly.")
    st.caption("v1.0.0 • Python + FastAPI + PostgreSQL")

pg.run()
