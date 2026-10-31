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


def render_context_detail(api: ContextBankAPI):
    context_id = st.session_state.get("selected_context_id")
    if not context_id:
        st.warning("No context selected. Return to the Context Bank to select a context.")
        if st.button("← Back to Context Bank"):
            try:
                st.switch_page("pages/contexts.py")
            except Exception:
                st.session_state["current_page"] = "Context Bank"
                st.rerun()
        return

    try:
        ctx = api.get_context(context_id)
    except Exception as e:
        st.error(f"Error loading context: {str(e)}")
        if st.button("← Back to Context Bank"):
            try:
                st.switch_page("pages/contexts.py")
            except Exception:
                st.session_state["current_page"] = "Context Bank"
                st.rerun()
        return

    # Header section
    col_back, col_actions = st.columns([1, 4])
    with col_back:
        if st.button("← Back"):
            try:
                st.switch_page("pages/contexts.py")
            except Exception:
                st.session_state["current_page"] = "Context Bank"
                st.rerun()

    # Title & Trigger Header
    primary_trigger = ctx.get("primary_trigger", "UNKNOWN")
    alts = ctx.get("alternative_triggers", [])
    title = ctx.get("title", "Untitled")

    st.markdown(f"# `{primary_trigger}`")
    st.markdown(f"### {title}")

    # Aliases and Metadata badges
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown(f"**Category:** `{ctx['category']}`")
    with col_m2:
        st.markdown(f"**Status:** `{ctx['status']}`")
    with col_m3:
        st.markdown(f"**Privacy:** `{ctx['privacy']}`")
    with col_m4:
        st.markdown(f"**Versions:** `{ctx.get('version_count', 1)}`")

    if alts:
        st.caption(f"Alternative Triggers (Aliases): {', '.join([f'`{a}`' for a in alts])}")

    # Trigger Registry Management Popover / Expander
    with st.expander("⚙️ Manage Triggers & Aliases", expanded=False):
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("##### Add Alias Trigger")
            new_alias = st.text_input("New alias name", key="new_alias_input", placeholder="e.g. VOX_DEV")
            if st.button("Add Alias", key="btn_add_alias"):
                if new_alias:
                    try:
                        api.register_trigger(new_alias.strip().upper(), ctx["id"], is_primary=False)
                        st.success(f"Alias `{new_alias.strip().upper()}` added!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Error adding alias: {err}")

        with col_t2:
            st.markdown("##### Rename Primary Trigger")
            new_primary = st.text_input("New trigger name", key="new_primary_input", placeholder=primary_trigger)
            if st.button("Rename Trigger", key="btn_rename_primary"):
                if new_primary and new_primary.strip().upper() != primary_trigger:
                    try:
                        api.rename_trigger(primary_trigger, new_primary.strip().upper())
                        st.success(f"Renamed trigger to `{new_primary.strip().upper()}`!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Error renaming: {err}")

    st.markdown("---")

    # Tabs for organization
    tab_overview, tab_package, tab_versions, tab_edit, tab_export = st.tabs([
        "📋 Overview & State",
        "🤖 AI Context Package",
        "🕒 Version History",
        "✏️ Edit Context",
        "📤 Export / Import",
    ])

    # TAB 1: Overview & State
    with tab_overview:
        st.markdown("#### 📝 Current Summary")
        st.info(ctx.get("summary", ""))

        if ctx.get("detailed_content"):
            st.markdown("#### 📖 Detailed Content")
            st.markdown(ctx["detailed_content"])

        st.markdown("---")

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("#### 🎯 Confirmed Decisions")
            decisions = ctx.get("important_decisions", [])
            confirmed = [
                d["text"] if isinstance(d, dict) else str(d)
                for d in decisions
                if (isinstance(d, dict) and d.get("status") == "confirmed") or isinstance(d, str)
            ]
            if confirmed:
                for c in confirmed:
                    st.markdown(f"- 🟢 **{c}**")
            else:
                st.caption("No confirmed decisions recorded yet.")

            st.markdown("#### 💡 Proposed Changes")
            proposed = [
                d["text"] for d in decisions
                if isinstance(d, dict) and d.get("status") == "proposed"
            ]
            if proposed:
                for p in proposed:
                    st.markdown(f"- 🟡 *{p}*")
            else:
                st.caption("No proposed changes pending.")

            st.markdown("#### ✅ Completed Work")
            completed = ctx.get("completed_work", [])
            if completed:
                for w in completed:
                    st.markdown(f"- [x] {w}")
            else:
                st.caption("No completed work items listed.")

        with col_right:
            st.markdown("#### ❓ Open / Unresolved Questions")
            questions = ctx.get("open_questions", [])
            if questions:
                for q in questions:
                    st.markdown(f"- ❓ {q}")
            else:
                st.caption("No open questions.")

            st.markdown("#### 🚀 Next Steps")
            next_steps = ctx.get("next_steps", [])
            if next_steps:
                for s in next_steps:
                    st.markdown(f"- [ ] **{s}**")
            else:
                st.caption("No immediate next steps listed.")

        # Tags
        tags = ctx.get("tags", [])
        if tags:
            st.markdown("#### 🏷️ Tags")
            st.markdown(" ".join([f"`#{t}`" for t in tags]))

    # TAB 2: AI Context Package
    with tab_package:
        st.markdown("#### 🤖 Compact Package for External AI Applications")
        st.caption("This structured package is what Context Bank sends when an AI model requests this context.")

        col_p1, col_p2 = st.columns([1, 1])
        with col_p1:
            pkg_detail = st.selectbox(
                "Detail Level",
                ["summary_and_state", "summary_only", "detailed", "full_archive"],
                format_func=lambda x: {
                    "summary_and_state": "Summary & State (Recommended)",
                    "summary_only": "Summary Only (Ultra Compact)",
                    "detailed": "Detailed Content",
                    "full_archive": "Full Archive",
                }.get(x, x),
                key="pkg_detail_sel"
            )
        with col_p2:
            pkg_fmt = st.selectbox("Output Format", ["markdown", "prompt", "json"], key="pkg_fmt_sel")

        try:
            pkg = api.retrieve_package(primary_trigger, detail_level=pkg_detail, output_format=pkg_fmt)
            st.markdown("##### Package Preview:")
            st.code(pkg["package_content"], language=pkg_fmt if pkg_fmt != "prompt" else "markdown")

            st.markdown("##### 💬 Continuation Prompt:")
            st.write("You or an AI agent can continue working by feeding this prompt to an LLM:")
            cont_prompt = f"Continue {primary_trigger} from where I stopped."
            st.code(cont_prompt, language="text")
        except Exception as e:
            st.error(f"Error packaging context: {str(e)}")

    # TAB 3: Version History
    with tab_versions:
        st.markdown("#### 🕒 Version Snapshots & Restoration")
        st.caption("Context Bank creates an immutable snapshot every time a context is updated or restored.")

        try:
            versions = api.list_versions(ctx["id"])

            if not versions:
                st.info("No previous versions recorded.")
            else:
                for v in versions:
                    with st.container(border=True):
                        v_col1, v_col2 = st.columns([3, 1])
                        with v_col1:
                            st.markdown(f"**Version {v['version_number']}** — *{v['change_summary']}*")
                            st.caption(f"Created: {v['created_at'][:19].replace('T', ' ')}")
                        with v_col2:
                            if st.button("Restore this version", key=f"restore_{v['id']}"):
                                with st.spinner("Restoring..."):
                                    api.restore_version(ctx["id"], v["id"], reason="User initiated restore")
                                    st.success(f"Restored Version {v['version_number']}!")
                                    st.rerun()

                        with st.expander(f"View Snapshot Data (v{v['version_number']})"):
                            st.json(v["snapshot_data"])

                # Version Comparison Tool
                if len(versions) >= 2:
                    st.markdown("---")
                    st.markdown("##### 🔍 Compare Two Versions")
                    c1, c2, c3 = st.columns([2, 2, 1])
                    v_nums = [v["version_number"] for v in versions]
                    with c1:
                        cmp_v1 = st.selectbox("Base Version", v_nums, index=1, key="cmp_v1")
                    with c2:
                        cmp_v2 = st.selectbox("Compare With", v_nums, index=0, key="cmp_v2")
                    with c3:
                        cmp_btn = st.button("Diff", key="btn_diff")

                    if cmp_btn:
                        diff_res = api.compare_versions(ctx["id"], cmp_v1, cmp_v2)
                        diffs = diff_res.get("diff_fields", {})
                        if not diffs:
                            st.info("No field differences found between these versions.")
                        else:
                            st.markdown(f"**Changes from Version {cmp_v1} to Version {cmp_v2}:**")
                            for field, vals in diffs.items():
                                with st.container(border=True):
                                    st.markdown(f"**Field:** `{field}`")
                                    d_col1, d_col2 = st.columns(2)
                                    with d_col1:
                                        st.caption(f"v{cmp_v1}:")
                                        st.write(vals.get("v1"))
                                    with d_col2:
                                        st.caption(f"v{cmp_v2}:")
                                        st.write(vals.get("v2"))
        except Exception as e:
            st.error(f"Error loading versions: {str(e)}")

    # TAB 4: Edit Context
    with tab_edit:
        st.markdown("#### ✏️ Update Context")
        with st.form("edit_context_form"):
            new_title = st.text_input("Title", value=ctx["title"])
            new_summary = st.text_area("Summary", value=ctx["summary"], height=90)
            new_detailed = st.text_area("Detailed Content", value=ctx.get("detailed_content", ""), height=100)

            c_c, c_s, c_p = st.columns(3)
            with c_c:
                new_cat = st.selectbox("Category", ["Projects", "Learning", "Career", "Specs", "General"],
                                       index=["Projects", "Learning", "Career", "Specs", "General"].index(ctx["category"]))
            with c_s:
                new_status = st.selectbox("Status", ["Active", "In Progress", "Completed", "Paused"],
                                          index=["Active", "In Progress", "Completed", "Paused"].index(ctx["status"]))
            with c_p:
                new_privacy = st.selectbox("Privacy", ["private", "shared"],
                                           index=["private", "shared"].index(ctx["privacy"]))

            new_tags_str = st.text_input("Tags (comma-separated)", value=", ".join(ctx.get("tags", [])))

            # Format existing decisions/next steps
            dec_texts = "\n".join([d["text"] if isinstance(d, dict) else str(d) for d in ctx.get("important_decisions", [])])
            comp_texts = "\n".join(ctx.get("completed_work", []))
            quest_texts = "\n".join(ctx.get("open_questions", []))
            step_texts = "\n".join(ctx.get("next_steps", []))

            e_col1, e_col2 = st.columns(2)
            with e_col1:
                new_decisions = st.text_area("Confirmed Decisions (one per line)", value=dec_texts, height=80)
                new_completed = st.text_area("Completed Work (one per line)", value=comp_texts, height=80)
            with e_col2:
                new_questions = st.text_area("Open Questions (one per line)", value=quest_texts, height=80)
                new_steps = st.text_area("Next Steps (one per line)", value=step_texts, height=80)

            change_desc = st.text_input("Summary of Changes for Version Snapshot", value="Updated context fields")

            save_btn = st.form_submit_button("💾 Save Changes & Create Snapshot", type="primary", use_container_width=True)

        if save_btn:
            tags = [t.strip() for t in new_tags_str.split(",") if t.strip()]
            dec_lines = [d.lstrip("-* ").strip() for d in new_decisions.splitlines() if d.strip()]
            comp_lines = [c.lstrip("-* ").strip() for c in new_completed.splitlines() if c.strip()]
            quest_lines = [q.lstrip("-*? ").strip() for q in new_questions.splitlines() if q.strip()]
            step_lines = [s.lstrip("-* ").strip() for s in new_steps.splitlines() if s.strip()]

            update_payload = {
                "title": new_title.strip(),
                "summary": new_summary.strip(),
                "detailed_content": new_detailed.strip(),
                "category": new_cat,
                "status": new_status,
                "privacy": new_privacy,
                "tags": tags,
                "important_decisions": [{"text": d, "status": "confirmed"} for d in dec_lines],
                "completed_work": comp_lines,
                "open_questions": quest_lines,
                "next_steps": step_lines,
                "change_summary": change_desc.strip() or "Updated context fields",
            }

            try:
                api.update_context(ctx["id"], update_payload)
                st.success("Context updated and new version snapshot captured!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating context: {str(e)}")

    # TAB 5: Export / Import
    with tab_export:
        st.markdown("#### 📤 Export Context")
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            if st.button("Export as Markdown", use_container_width=True):
                res = api.export_context(ctx["id"], format="markdown")
                st.download_button(
                    label="⬇️ Download Markdown (.md)",
                    data=res["content"],
                    file_name=f"{primary_trigger}_context.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
        with e_col2:
            if st.button("Export as JSON", use_container_width=True):
                res = api.export_context(ctx["id"], format="json")
                st.download_button(
                    label="⬇️ Download JSON (.json)",
                    data=res["content"],
                    file_name=f"{primary_trigger}_context.json",
                    mime="application/json",
                    use_container_width=True,
                )

    # Danger Zone: Delete
    st.markdown("---")
    with st.expander("⚠️ Danger Zone: Delete Context"):
        st.write(
            f"Deleting this context will permanently remove **`{primary_trigger}`** and all its aliases, "
            "version history, access logs, and relationships. Active triggers for this context will be deactivated."
        )
        confirm_del = st.checkbox(f"I understand and want to permanently delete `{primary_trigger}`", key="del_confirm_chk")
        if st.button("🗑️ Permanently Delete Context", type="primary", disabled=not confirm_del):
            try:
                api.delete_context(ctx["id"])
                st.success(f"Context `{primary_trigger}` deleted successfully.")
                st.session_state["selected_context_id"] = None
                try:
                    st.switch_page("pages/contexts.py")
                except Exception:
                    st.session_state["current_page"] = "Context Bank"
                    st.rerun()
            except Exception as e:
                st.error(f"Deletion failed: {str(e)}")


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
    render_context_detail(_api)
