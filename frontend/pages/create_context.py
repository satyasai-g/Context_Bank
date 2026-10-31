import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from frontend.components.api_client import ContextBankAPI


def render_create_context(api: ContextBankAPI):
    st.markdown("## ➕ Create Context")
    st.caption("Save project state manually or let Context Bank automatically determine the trigger word from chat.")

    tab_auto, tab_manual = st.tabs(["⚡ Auto-Create from Chat", "✍️ Manual Form"])

    # TAB 1: AUTO-CREATE FROM CHAT
    with tab_auto:
        st.markdown("#### 💬 Auto-Generate Trigger Word & Context from Chat")
        st.write(
            "Paste any conversation or meeting transcript (e.g. from ChatGPT, Claude, Cursor, team notes). "
            "Context Bank's Trigger Engine will **automatically analyze the discussion, identify the core subject, "
            "and generate a memorable, unique trigger word** with decisions and next steps."
        )

        chat_input = st.text_area(
            "Paste chat conversation or notes",
            height=180,
            placeholder="Paste your chat here...\n\nExample:\nUser: Let's design a voice-first career coach called Voxcent.\nAssistant: Great, Voxcent will have 5 roles. Let's decide on Python for backend and PostgreSQL for vector database.\nUser: Agreed, next step is building the trigger registry.",
            key="auto_chat_input"
        )

        col_act1, col_act2 = st.columns([2, 1])
        with col_act1:
            analyze_btn = st.button("🔍 Analyze Chat & Generate Trigger", type="primary", use_container_width=True)

        if analyze_btn:
            if not chat_input.strip():
                st.warning("Please paste a conversation first.")
            else:
                with st.spinner("Analyzing conversation and generating optimal trigger word..."):
                    try:
                        extracted = api.extract_from_text(chat_input)
                        st.session_state["auto_extracted_data"] = extracted
                        st.session_state["auto_selected_trigger"] = extracted.get("suggested_trigger", "CONTEXT")
                    except Exception as e:
                        st.error(f"Analysis error: {str(e)}")

        # If analysis results exist in session state, display interactive auto-card
        if "auto_extracted_data" in st.session_state:
            data = st.session_state["auto_extracted_data"]
            current_trigger = st.session_state.get("auto_selected_trigger", data.get("suggested_trigger", "CONTEXT"))

            st.markdown("---")
            st.markdown("### 🎯 Generated Trigger & Extracted Context")

            with st.container(border=True):
                # Trigger display & alternative candidates
                t_col1, t_col2 = st.columns([1, 2])
                with t_col1:
                    st.markdown(f"#### 🏷️ Trigger: `{current_trigger}`")
                    st.caption(f"💡 **Reason:** {data.get('trigger_reasoning', 'Extracted from conversation subject.')}")

                with t_col2:
                    candidates = data.get("trigger_candidates", [])
                    if len(candidates) > 1:
                        st.write("**Alternative Trigger Options:**")
                        cand_cols = st.columns(min(len(candidates), 4))
                        for idx, cand in enumerate(candidates[:4]):
                            if cand_cols[idx].button(f"`{cand}`", key=f"cand_btn_{cand}"):
                                st.session_state["auto_selected_trigger"] = cand
                                st.rerun()

                st.markdown("---")

                # Context summary preview
                st.markdown(f"**Title:** {data.get('title', 'Untitled')}")
                st.markdown(f"**Summary:** {data.get('summary', '')}")
                st.markdown(f"**Status:** `{data.get('status', 'Active')}` | **Category:** `{data.get('category', 'Projects')}`")

                c_dec, c_steps = st.columns(2)
                with c_dec:
                    st.markdown("**Confirmed Decisions:**")
                    for d in data.get("confirmed_decisions", []):
                        st.markdown(f"- 🟢 {d}")
                with c_steps:
                    st.markdown("**Next Steps:**")
                    for s in data.get("next_steps", []):
                        st.markdown(f"- [ ] {s}")

                st.markdown("---")

                col_save1, col_save2 = st.columns(2)
                with col_save1:
                    if st.button("⚡ 1-Click Save to Context Bank", type="primary", use_container_width=True):
                        with st.spinner("Saving context and indexing..."):
                            try:
                                saved = api.auto_create_from_chat(
                                    chat_text=chat_input,
                                    custom_trigger=current_trigger,
                                )
                                st.success(f"Context saved under trigger `{saved['primary_trigger']}`!")
                                del st.session_state["auto_extracted_data"]
                                st.session_state["selected_context_id"] = saved["id"]
                                try:
                                    st.switch_page("pages/context_detail.py")
                                except Exception:
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error saving context: {str(e)}")

                with col_save2:
                    if st.button("✏️ Load into Manual Form to Edit", use_container_width=True):
                        st.session_state["form_trigger"] = current_trigger
                        st.session_state["form_title"] = data.get("title", "")
                        st.session_state["form_summary"] = data.get("summary", "")
                        st.session_state["form_category"] = data.get("category", "Projects")
                        st.session_state["form_status"] = data.get("status", "Active")
                        st.session_state["form_decisions"] = "\n".join(data.get("confirmed_decisions", []))
                        st.session_state["form_next_steps"] = "\n".join(data.get("next_steps", []))
                        st.info("Loaded into Manual Form. Switch to 'Manual Form' tab to edit.")

    # TAB 2: MANUAL FORM
    with tab_manual:
        st.markdown("#### ✍️ Manual Context Registration")
        with st.form("manual_context_form", clear_on_submit=False):
            col1, col2 = st.columns([1, 1])
            with col1:
                trigger_word = st.text_input(
                    "Primary Trigger Word *",
                    value=st.session_state.get("form_trigger", ""),
                    help="Uppercase unique keyword (e.g. VOXCENT, SQLPATH, RESUME)",
                    placeholder="e.g. VOXCENT"
                )
            with col2:
                alt_triggers = st.text_input(
                    "Alternative Trigger Aliases (Optional)",
                    help="Comma-separated secondary triggers (e.g. VOX, VC_ASSISTANT)",
                    placeholder="e.g. VOX, VOXCENT_BOT"
                )

            title = st.text_input(
                "Context Title *",
                value=st.session_state.get("form_title", ""),
                placeholder="e.g. Voxcent AI Learning and Career Assistant"
            )

            summary = st.text_area(
                "Current Summary *",
                value=st.session_state.get("form_summary", ""),
                height=90,
                placeholder="Concise summary of project, core architecture, and current state."
            )

            detailed_content = st.text_area(
                "Detailed Context Content (Optional)",
                value=st.session_state.get("form_detailed", ""),
                height=100,
                placeholder="In-depth specifications, architectural details, or notes."
            )

            col_c, col_s, col_p = st.columns(3)
            with col_c:
                cat_list = ["Projects", "Learning", "Career", "Specs", "General"]
                default_cat = st.session_state.get("form_category", "Projects")
                cat_idx = cat_list.index(default_cat) if default_cat in cat_list else 0
                category = st.selectbox("Category", cat_list, index=cat_idx)
            with col_s:
                stat_list = ["Active", "In Progress", "Completed", "Paused"]
                default_stat = st.session_state.get("form_status", "Active")
                stat_idx = stat_list.index(default_stat) if default_stat in stat_list else 0
                status_val = st.selectbox("Current Status", stat_list, index=stat_idx)
            with col_p:
                privacy = st.selectbox("Privacy", ["private", "shared"])

            tags_str = st.text_input("Tags (comma-separated)", value=st.session_state.get("form_tags", ""), placeholder="e.g. voice, fastapi, postgresql")

            st.markdown("##### 📌 Structured State Tracking")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                decisions_input = st.text_area("Confirmed Decisions (one per line)", value=st.session_state.get("form_decisions", ""), height=80)
                completed_input = st.text_area("Completed Work (one per line)", value=st.session_state.get("form_completed", ""), height=80)
            with col_d2:
                questions_input = st.text_area("Open Questions (one per line)", value=st.session_state.get("form_questions", ""), height=80)
                next_steps_input = st.text_area("Next Steps (one per line)", value=st.session_state.get("form_next_steps", ""), height=80)

            submitted = st.form_submit_button("💾 Save Context to Bank", type="primary", use_container_width=True)

        if submitted:
            if not trigger_word.strip() or not title.strip() or not summary.strip():
                st.error("Trigger Word, Title, and Summary are required fields.")
                return

            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            alts = [a.strip().upper() for a in alt_triggers.split(",") if a.strip()]
            dec_lines = [d.lstrip("-* ").strip() for d in decisions_input.splitlines() if d.strip()]
            decisions_list = [{"text": d, "status": "confirmed"} for d in dec_lines]

            comp_lines = [c.lstrip("-* ").strip() for c in completed_input.splitlines() if c.strip()]
            quest_lines = [q.lstrip("-*? ").strip() for q in questions_input.splitlines() if q.strip()]
            step_lines = [s.lstrip("-* ").strip() for s in next_steps_input.splitlines() if s.strip()]

            payload = {
                "trigger_word": trigger_word.strip().upper(),
                "alternative_triggers": alts,
                "title": title.strip(),
                "summary": summary.strip(),
                "detailed_content": detailed_content.strip(),
                "category": category,
                "status": status_val,
                "privacy": privacy,
                "tags": tags,
                "important_decisions": decisions_list,
                "completed_work": comp_lines,
                "open_questions": quest_lines,
                "next_steps": step_lines,
            }

            with st.spinner("Saving context..."):
                try:
                    new_ctx = api.create_context(payload)
                    st.success(f"Context `{new_ctx['primary_trigger']}` created successfully!")
                    for k in list(st.session_state.keys()):
                        if k.startswith("form_"):
                            del st.session_state[k]
                    st.session_state["selected_context_id"] = new_ctx["id"]
                    try:
                        st.switch_page("pages/context_detail.py")
                    except Exception:
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to create context: {str(e)}")


# Standalone runner if executed directly by Streamlit
if __name__ == "__main__" or not __name__.startswith("frontend.pages"):
    from frontend.components.api_client import ContextBankAPI
    _api = ContextBankAPI()
    render_create_context(_api)
