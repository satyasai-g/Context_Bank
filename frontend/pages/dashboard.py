import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from frontend.components.api_client import ContextBankAPI
from frontend.components.trigger_lookup import render_quick_trigger_lookup


def render_dashboard(api: ContextBankAPI):
    st.markdown("## 📊 Dashboard")
    st.caption("Central trigger-based context repository for humans and autonomous AI agents.")

    try:
        stats = api.get_dashboard_stats()
    except Exception as e:
        st.error(f"Unable to connect to backend service: {str(e)}")
        st.info("Ensure the FastAPI backend is running on `http://127.0.0.1:8000`.")
        return

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Contexts", stats["total_contexts"])
    with col2:
        st.metric("Registered Triggers", stats["total_triggers"])
    with col3:
        accessed_cnt = len(stats["recently_accessed"])
        st.metric("Recently Active", accessed_cnt)
    with col4:
        freq_cnt = len(stats["frequently_used_triggers"])
        st.metric("Tracked Lookups", freq_cnt)

    st.markdown("---")

    # Quick trigger lookup
    render_quick_trigger_lookup(api)

    st.markdown("---")

    # Check for empty state
    if not stats["has_data"]:
        with st.container(border=True):
            st.markdown("### 👋 Welcome to Context Bank")
            st.write(
                "You haven't saved any contexts yet! Context Bank allows you to store architecture, "
                "decisions, and state under custom trigger words (like `VOXCENT` or `SQLPATH`). "
                "Whenever you or an external AI need it, just use the trigger word."
            )
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("➕ Create Your First Context", type="primary", use_container_width=True):
                    try:
                        st.switch_page("pages/create_context.py")
                    except Exception:
                        st.session_state["current_page"] = "Create Context"
                        st.rerun()
            with col_b:
                if st.button("🌱 Load Demo Contexts (VOXCENT, SQLPATH, RESUME)", use_container_width=True):
                    _seed_demo_contexts(api)
                    st.success("Demo contexts created! Refreshing...")
                    st.rerun()
        return

    # Two columns: Recently Updated vs Frequently Used Triggers
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### 🕒 Recently Updated Contexts")
        recent = stats.get("recently_updated", [])
        if recent:
            for c in recent:
                with st.container(border=True):
                    cols = st.columns([3, 1])
                    with cols[0]:
                        st.markdown(f"**`{c['primary_trigger']}`** — {c['title']}")
                        st.caption(f"{c['summary'][:100]}...")
                    with cols[1]:
                        if st.button("Open", key=f"dash_open_{c['id']}"):
                            st.session_state["selected_context_id"] = c["id"]
                            try:
                                st.switch_page("pages/context_detail.py")
                            except Exception:
                                st.session_state["current_page"] = "Context Detail"
                                st.rerun()
        else:
            st.info("No contexts updated recently.")

    with col_right:
        st.markdown("#### 🔥 Frequently Used Triggers")
        freq = stats.get("frequently_used_triggers", [])
        if freq:
            for t in freq:
                with st.container(border=True):
                    col_t1, col_t2 = st.columns([3, 1])
                    with col_t1:
                        st.markdown(f"**`{t['trigger_word']}`**")
                        st.caption(f"Used {t['access_count']} times")
                    with col_t2:
                        if st.button("Retrieve", key=f"freq_btn_{t['trigger_word']}"):
                            st.session_state["quick_trigger_input"] = t["trigger_word"]
                            st.rerun()
        else:
            st.caption("Trigger lookups will appear here as they are retrieved by users and AI applications.")

    # Recent Activity Audit
    st.markdown("---")
    st.markdown("#### 📜 Recent Retrieval Activity")
    activity = stats.get("recent_activity", [])
    if activity:
        st.dataframe(
            [
                {
                    "Timestamp": a["timestamp"][:19].replace("T", " "),
                    "Trigger": a["trigger_used"] or "Direct",
                    "Context": a["context_title"],
                    "Client / Method": a["accessed_via"],
                }
                for a in activity
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No recent retrievals logged.")


def _seed_demo_contexts(api: ContextBankAPI):
    """Seed initial realistic demo contexts including VOXCENT."""
    demo1 = {
        "trigger_word": "VOXCENT",
        "title": "Voxcent AI Learning and Career Assistant",
        "summary": "A voice-first AI application with five specialized roles and an independent Context Bank.",
        "detailed_content": "Voxcent is designed to assist learners and job seekers with speech and conversation interfaces.",
        "status": "In Progress",
        "category": "Projects",
        "tags": ["voice", "assistant", "career", "fastapi", "streamlit"],
        "important_decisions": [
            {"text": "Context Bank is an independent portable subsystem.", "status": "confirmed"},
            {"text": "Python is the primary programming language.", "status": "confirmed"},
            {"text": "PostgreSQL is the persistent database with pgvector for semantic retrieval.", "status": "confirmed"},
            {"text": "FastAPI is the REST backend and Streamlit is the frontend.", "status": "confirmed"}
        ],
        "completed_work": [
            "Initial project specification defined.",
            "Database models and trigger registry architecture established.",
            "Independent retrieval engine implemented."
        ],
        "open_questions": [
            "External integration strategy and authentication details."
        ],
        "next_steps": [
            "Implement the core trigger registry.",
            "Build context CRUD operations.",
            "Integrate retrieval with a compatible AI client."
        ],
        "privacy": "private"
    }

    demo2 = {
        "trigger_word": "SQLPATH",
        "title": "SQL Mastery Learning Roadmap",
        "summary": "Tracks progress through advanced PostgreSQL, indexing strategies, and query optimization exercises.",
        "status": "Active",
        "category": "Learning",
        "tags": ["sql", "postgresql", "database", "indexing"],
        "important_decisions": [
            {"text": "Focus on window functions and CTEs before query plan analysis.", "status": "confirmed"},
            {"text": "Practice with LeetCode SQL 50 and custom datasets.", "status": "confirmed"}
        ],
        "completed_work": ["Basic JOINs, subqueries, and aggregation exercises completed."],
        "open_questions": ["Best practice for indexing JSONB columns with gin."],
        "next_steps": ["Complete EXPLAIN ANALYZE deep dive on large datasets."],
        "privacy": "private"
    }

    demo3 = {
        "trigger_word": "RESUME",
        "title": "Full-Stack AI Software Engineer Profile",
        "summary": "Curated experience, project achievements, and target roles for senior engineer positions.",
        "status": "Active",
        "category": "Career",
        "tags": ["career", "resume", "portfolio", "python"],
        "important_decisions": [
            {"text": "Highlight Python backend and generative AI integration experience.", "status": "confirmed"}
        ],
        "completed_work": ["Updated GitHub portfolio with Context Bank project."],
        "open_questions": ["Add Docker Compose deployment section to portfolio."],
        "next_steps": ["Apply to target AI developer roles with tailored cover letter."],
        "privacy": "private"
    }

    for d in [demo1, demo2, demo3]:
        try:
            api.create_context(d)
        except Exception:
            pass


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
    render_dashboard(_api)
