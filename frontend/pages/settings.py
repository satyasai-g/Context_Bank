import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import json
from frontend.components.api_client import ContextBankAPI


def render_settings(api: ContextBankAPI):
    st.markdown("## ⚙️ Settings")
    st.caption("Manage user preferences, data backup, AI providers, and security.")

    try:
        user = api.get_me()
        system_status = api.get_system_status()
    except Exception as e:
        st.error(f"Error loading settings: {str(e)}")
        return

    tab_profile, tab_providers, tab_backup = st.tabs(["👤 Profile & Security", "🧠 AI & Providers", "💾 Data & Export"])

    with tab_profile:
        st.markdown("#### User Information")
        st.write(f"**Email:** `{user['email']}`")
        st.write(f"**Account ID:** `{user['id']}`")
        st.write(f"**Account Status:** `{'Active' if user['is_active'] else 'Inactive'}`")
        st.write(f"**Active Integration Key:** `{'Configured' if user['has_api_key'] else 'None'}`")

        st.markdown("---")
        st.markdown("#### Security Settings")
        st.write("Context Bank enforces namespace isolation: your contexts and triggers are accessible only to your account.")

    with tab_providers:
        st.markdown("#### AI & Retrieval Configuration")
        st.write(f"**Database Engine:** `{system_status.get('database_type', 'PostgreSQL')}`")
        st.write(f"**Semantic Embedding Provider:** `{system_status.get('embedding_provider', 'tfidf')}`")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Google Gemini API")
            if system_status.get("gemini_configured"):
                st.success("Configured & Ready")
                st.caption(f"Model: `{system_status.get('gemini_model')}`")
            else:
                st.warning("Not configured")
                st.caption("To enable Gemini AI extraction, add `GEMINI_API_KEY=your_key` to `.env`.")

        with col2:
            st.markdown("##### Semantic pgvector Engine")
            st.info("Adaptive Vector Engine Active")
            st.caption("Supports pgvector on PostgreSQL with cosine similarity fallback on SQLite.")

    with tab_backup:
        st.markdown("#### Account Data Export")
        st.write("Download an archival copy of all your saved contexts, decisions, next steps, and version history in JSON format.")

        if st.button("📦 Prepare Full Data Export", type="primary"):
            try:
                data = api.list_contexts(page_size=1000)
                contexts = data.get("contexts", [])
                full_export = []
                for c in contexts:
                    full_ctx = api.get_context(c["id"])
                    full_export.append(full_ctx)

                json_str = json.dumps(full_export, indent=2, default=str)
                st.download_button(
                    label="⬇️ Download All Contexts (.json)",
                    data=json_str,
                    file_name="context_bank_export.json",
                    mime="application/json",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Export error: {str(e)}")


# Standalone runner if executed directly by Streamlit
if __name__ == "__main__" or not __name__.startswith("frontend.pages"):
    import os
    import sys
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from frontend.components.api_client import ContextBankAPI
    _api = ContextBankAPI()
    render_settings(_api)
