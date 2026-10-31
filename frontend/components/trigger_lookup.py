import streamlit as st
from frontend.components.api_client import ContextBankAPI


def render_quick_trigger_lookup(api: ContextBankAPI):
    st.markdown("#### ⚡ Quick Trigger Lookup")
    st.caption("Enter an exact trigger word (e.g. `VOXCENT`, `SQLPATH`) or a prompt to retrieve its stored context.")

    col1, col2 = st.columns([3, 1])
    with col1:
        trigger_input = st.text_input(
            "Trigger word or prompt",
            placeholder="e.g. VOXCENT or 'Continue VOXCENT from where I stopped'",
            label_visibility="collapsed",
            key="quick_trigger_input"
        )
    with col2:
        lookup_btn = st.button("🔍 Lookup Context", use_container_width=True, type="primary")

    if lookup_btn and trigger_input:
        trig_clean = trigger_input.strip()

        # Check if natural language prompt or single trigger word
        is_prompt = len(trig_clean.split()) > 1

        with st.spinner("Resolving trigger..."):
            try:
                if is_prompt:
                    pkg = api.retrieve_prompt(trig_clean, detail_level="summary_and_state", output_format="markdown")
                    st.success(f"Matched prompt to trigger: `{pkg['primary_trigger']}`")
                    with st.expander("📄 Retrieved Context Package", expanded=True):
                        st.markdown(pkg["package_content"])
                        st.code(pkg["package_content"], language="markdown")
                else:
                    res = api.quick_lookup(trig_clean)
                    if res["found"]:
                        st.success(f"Exact Trigger Match: `{res['trigger_searched']}`")
                        ctx = res["context"]
                        st.markdown(f"**Title:** {ctx['title']}")
                        st.markdown(f"**Summary:** {ctx['summary']}")
                        st.markdown(f"**Status:** `{ctx['status']}` | **Category:** `{ctx['category']}`")

                        with st.expander("📦 Structured AI Package (Ready to copy)", expanded=False):
                            st.code(res["package"], language="markdown")

                        if st.button("👉 View Full Context Details", key="view_detail_from_lookup"):
                            st.session_state["selected_context_id"] = ctx["id"]
                            try:
                                st.switch_page("pages/context_detail.py")
                            except Exception:
                                st.session_state["current_page"] = "Context Detail"
                                st.rerun()
                    else:
                        st.warning(f"⚠️ {res['message']}")
                        st.caption("Exact trigger matches are strict. Check spelling or use Semantic Search.")
            except Exception as e:
                st.error(f"Lookup error: {str(e)}")
