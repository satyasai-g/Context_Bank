import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from frontend.components.api_client import ContextBankAPI
from frontend.components.context_card import render_context_card


def render_context_bank(api: ContextBankAPI):
    st.markdown("## 🗂️ Context Bank")
    st.caption("Browse, filter, and search all contexts stored under your registered triggers.")

    # Search and Filter Bar
    with st.container(border=True):
        col_s1, col_s2, col_s3, col_s4 = st.columns([3, 2, 2, 2])
        with col_s1:
            search_query = st.text_input("🔍 Search keyword or concept", placeholder="e.g. voice assistant, postgresql...")
        with col_s2:
            category_filter = st.selectbox("Category", ["All", "Projects", "Learning", "Career", "Specs", "General"])
        with col_s3:
            status_filter = st.selectbox("Status", ["All", "Active", "In Progress", "Completed", "Paused", "Archived"])
        with col_s4:
            sort_by = st.selectbox("Sort By", ["updated_desc", "created_desc", "accessed_desc", "title_asc"],
                                   format_func=lambda x: {
                                       "updated_desc": "Recently Updated",
                                       "created_desc": "Recently Created",
                                       "accessed_desc": "Recently Accessed",
                                       "title_asc": "Title A-Z"
                                   }.get(x, x))

    # If search query is provided, invoke search service
    if search_query and search_query.strip():
        st.markdown(f"#### 🔎 Search Results for: *'{search_query}'*")
        try:
            search_res = api.search_contexts(search_query.strip(), limit=15)
            results = search_res.get("results", [])

            if not results:
                st.warning(f"No contexts found matching query '{search_query}'.")
                st.caption("Tip: Try searching broader terms or use exact trigger lookup on the Dashboard.")
            else:
                st.caption(f"Found {len(results)} relevant contexts via {search_res.get('search_provider_used')}:")
                for r in results:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"**`{r['primary_trigger']}`** — {r['title']}")
                            st.write(r["summary"])
                            st.caption(f"💡 Match reason: {r['match_reason']} | Relevance: {r['relevance_score']}")
                        with c2:
                            if st.button("Open Context →", key=f"srch_open_{r['context_id']}"):
                                st.session_state["selected_context_id"] = r["context_id"]
                                try:
                                    st.switch_page("pages/context_detail.py")
                                except Exception:
                                    st.session_state["current_page"] = "Context Detail"
                                    st.rerun()
        except Exception as e:
            st.error(f"Search failed: {str(e)}")
        return

    # Normal list view
    cat_param = None if category_filter == "All" else category_filter
    stat_param = None if status_filter == "All" else status_filter

    try:
        data = api.list_contexts(
            category=cat_param,
            status=stat_param,
            sort_by=sort_by,
            page=1,
            page_size=50,
        )
        contexts = data.get("contexts", [])
        total = data.get("total", 0)

        st.caption(f"Showing {len(contexts)} of {total} contexts")

        if not contexts:
            st.info("No contexts match the current filters.")
            if st.button("➕ Create Context Now"):
                try:
                    st.switch_page("pages/create_context.py")
                except Exception:
                    st.session_state["current_page"] = "Create Context"
                    st.rerun()
            return

        def on_select(ctx_id: str):
            st.session_state["selected_context_id"] = ctx_id
            try:
                st.switch_page("pages/context_detail.py")
            except Exception:
                st.session_state["current_page"] = "Context Detail"
                st.rerun()

        # Display cards
        for ctx in contexts:
            render_context_card(ctx, on_select_cb=on_select)

    except Exception as e:
        st.error(f"Error loading contexts: {str(e)}")


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
    render_context_bank(_api)
