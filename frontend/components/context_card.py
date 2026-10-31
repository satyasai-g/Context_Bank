import streamlit as st
from typing import Dict, Any


def render_context_card(ctx: Dict[str, Any], on_select_cb=None):
    """Render a card representing a context item."""
    trigger = ctx.get("primary_trigger", "UNKNOWN")
    alts = ctx.get("alternative_triggers", [])
    title = ctx.get("title", "Untitled")
    summary = ctx.get("summary", "")
    category = ctx.get("category", "General")
    status = ctx.get("status", "Active")
    tags = ctx.get("tags", [])
    updated = ctx.get("updated_at", "")[:10] if ctx.get("updated_at") else ""

    status_color = {
        "Active": "🟢",
        "In Progress": "🟡",
        "Completed": "🔵",
        "Paused": "⚪",
        "Archived": "⚫",
    }.get(status, "⚪")

    with st.container(border=True):
        col_t, col_s = st.columns([3, 1])
        with col_t:
            st.markdown(f"### `{trigger}` — {title}")
            if alts:
                st.caption(f"Aliases: {', '.join([f'`{a}`' for a in alts])}")
        with col_s:
            st.markdown(f"<div style='text-align: right;'>{status_color} <b>{status}</b></div>", unsafe_allow_html=True)
            st.caption(f"<div style='text-align: right;'>{category}</div>", unsafe_allow_html=True)

        st.write(summary[:220] + ("..." if len(summary) > 220 else ""))

        col_b1, col_b2 = st.columns([3, 1])
        with col_b1:
            if tags:
                tag_badges = " ".join([f"`#{t}`" for t in tags[:4]])
                st.markdown(tag_badges)
            if updated:
                st.caption(f"Updated: {updated}")
        with col_b2:
            if st.button("Open Details →", key=f"btn_open_{ctx['id']}", use_container_width=True):
                if on_select_cb:
                    on_select_cb(ctx["id"])
