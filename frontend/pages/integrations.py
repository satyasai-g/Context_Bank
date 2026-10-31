import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from frontend.components.api_client import ContextBankAPI


def render_integrations(api: ContextBankAPI):
    st.markdown("## 🔌 External AI Integrations")
    st.caption("Connect Voxcent, Cursor, Claude Desktop, and custom LLM agents to your Context Bank.")

    # Status Cards
    status = api.get_system_status()
    st.markdown("#### 📡 System Status")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.success(f"**REST API:** {status.get('status', 'online').upper()}")
    with c2:
        st.info(f"**Database:** {status.get('database_type', 'PostgreSQL')}")
    with c3:
        if status.get("gemini_configured"):
            st.success("**Gemini AI:** CONNECTED")
        else:
            st.warning("**Gemini AI:** OFFLINE (Optional)")
    with c4:
        st.success("**MCP Server:** AVAILABLE")

    st.markdown("---")

    # API Authentication & Key Management
    st.markdown("#### 🔑 Authentication & API Tokens")
    st.write(
        "External AI applications authenticate using a secure Bearer token or the `X-API-Key` header. "
        "Stored keys are hashed via SHA-256; raw keys are never stored or displayed again after generation."
    )

    col_k1, col_k2 = st.columns([2, 1])
    with col_k1:
        if st.button("Generate New Integration API Key", type="primary"):
            try:
                res = api.create_api_key()
                st.session_state["newly_generated_key"] = res["api_key"]
                st.rerun()
            except Exception as e:
                st.error(f"Error generating key: {str(e)}")

    with col_k2:
        if st.button("Revoke Active API Key"):
            try:
                api.revoke_api_key()
                st.success("API key revoked.")
                if "newly_generated_key" in st.session_state:
                    del st.session_state["newly_generated_key"]
                st.rerun()
            except Exception as e:
                st.error(f"Error revoking key: {str(e)}")

    if "newly_generated_key" in st.session_state:
        st.warning(
            "⚠️ **Copy your API key now. It will not be shown again!**"
        )
        st.code(st.session_state["newly_generated_key"], language="text")

    st.markdown("---")

    # Integration Methods
    st.markdown("#### 🛠️ Available Integration Methods")

    tab_rest, tab_mcp, tab_python = st.tabs(["🌐 REST API", "⚡ Model Context Protocol (MCP)", "🐍 Python Client"])

    with tab_rest:
        st.markdown("##### 1. Retrieve Context Package by Exact Trigger")
        st.caption("Endpoint: `POST /api/v1/contexts/retrieve`")
        curl_retrieve = """curl -X POST "http://127.0.0.1:8000/api/v1/contexts/retrieve" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -d '{
    "trigger": "VOXCENT",
    "detail_level": "summary_and_state",
    "output_format": "markdown"
  }'"""
        st.code(curl_retrieve, language="bash")

        st.markdown("##### 2. Natural Language Prompt Retrieval")
        st.caption("Endpoint: `POST /api/v1/contexts/retrieve-prompt`")
        curl_prompt = """curl -X POST "http://127.0.0.1:8000/api/v1/contexts/retrieve-prompt" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -d '{
    "prompt": "Continue VOXCENT from where I stopped.",
    "detail_level": "summary_and_state",
    "output_format": "prompt"
  }'"""
        st.code(curl_prompt, language="bash")

        st.markdown("##### 3. Interactive OpenAPI Documentation")
        st.write("Browse and execute all REST endpoints live in the Swagger UI:")
        st.markdown("[Open Swagger Docs → http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)")

    with tab_mcp:
        st.markdown("##### Model Context Protocol (MCP) Setup")
        st.write(
            "Context Bank provides a compliant MCP server (`backend.integrations.mcp_server`) "
            "exposing tools to Claude Desktop, Cursor, or compatible MCP orchestrators."
        )

        st.markdown("###### Claude Desktop Configuration (`claude_desktop_config.json`)")
        mcp_config = """{
  "mcpServers": {
    "context-bank": {
      "command": "python",
      "args": [
        "-m",
        "backend.integrations.mcp_server"
      ],
      "cwd": "C:/Users/Gowtham/.gemini/antigravity/scratch/context_bank",
      "env": {
        "DATABASE_URL": "postgresql+psycopg2://postgres:postgres@localhost:5432/context_bank"
      }
    }
  }
}"""
        st.code(mcp_config, language="json")

        st.markdown("###### Available MCP Tools:")
        st.dataframe([
            {"Tool": "resolve_trigger", "Description": "Resolve trigger word to context ID & summary", "Permission": "Read"},
            {"Tool": "retrieve_context", "Description": "Retrieve compact AI-ready package for prompt continuation", "Permission": "Read"},
            {"Tool": "search_contexts", "Description": "Semantic & keyword search across saved contexts", "Permission": "Read"},
            {"Tool": "list_contexts", "Description": "List all contexts saved in user namespace", "Permission": "Read"},
            {"Tool": "create_context", "Description": "Create a new context with primary trigger and decisions", "Permission": "Write"},
            {"Tool": "update_context", "Description": "Update an existing context and record version snapshot", "Permission": "Write"},
        ], use_container_width=True, hide_index=True)

    with tab_python:
        st.markdown("##### Python External AI Client Example")
        st.write("How external applications (like Voxcent) call Context Bank using `httpx`:")

        py_example = """import httpx

API_BASE = "http://127.0.0.1:8000"
API_KEY = "cbk_live_your_api_key_here"

def get_context_for_prompt(prompt: str) -> str:
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    
    # 1. Ask Context Bank to resolve any trigger mentioned in the user prompt
    resp = httpx.post(
        f"{API_BASE}/api/v1/contexts/retrieve-prompt",
        headers=headers,
        json={"prompt": prompt, "detail_level": "summary_and_state", "output_format": "prompt"},
        timeout=10.0
    )
    
    if resp.status_code == 200:
        package = resp.json()
        return package["package_content"]
    elif resp.status_code == 404:
        return "No context trigger found in prompt."
    else:
        resp.raise_for_status()

# Example usage:
context_block = get_context_for_prompt("Continue VOXCENT from where I stopped.")
print(context_block)
"""
        st.code(py_example, language="python")


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
    render_integrations(_api)
