"""
Streamlit + Supabase demo — run from this folder:

    pip install -r requirements.txt
    streamlit run app.py

Secrets: `.streamlit/secrets.toml` (see `.streamlit/secrets.toml.example`).
Cloud: **[Streamlit Community Cloud](https://streamlit.io/cloud)** → same keys in **Secrets**.
"""

from __future__ import annotations

import importlib.util
import uuid

import streamlit as st


def _missing_runtime_packages() -> list[str]:
    out: list[str] = []
    for name in ("pandas", "supabase"):
        if importlib.util.find_spec(name) is None:
            out.append(name)
    return out


_missing = _missing_runtime_packages()


def _fatal_deps_page(msg: str) -> None:
    st.set_page_config(page_title="Fix dependencies", layout="wide")
    st.title("Deploy / environment issue")
    st.error(msg)
    st.markdown(
        "On **[Streamlit Community Cloud](https://streamlit.io/cloud)**, `requirements.txt` must sit **next to "
        "`app.py`** at the repo root and list `supabase` and `pandas`."
    )
    st.code("pip install -r requirements.txt\nstreamlit run app.py", language="bash")


if _missing:
    pkgs = ", ".join(sorted(_missing))
    _fatal_deps_page(f"Missing Python package(s): **{pkgs}**. Pull latest from GitHub and redeploy.")
    st.stop()


import pandas as pd

try:
    from postgrest.exceptions import APIError
except ImportError:  # pragma: no cover
    APIError = Exception

from supabase_helpers import get_supabase, normalize_project_url


def _try_title() -> str:
    try:
        return str(st.secrets["default"]["app_name"]).strip()
    except Exception:
        return "CareStream Tasks"


st.set_page_config(page_title=_try_title(), layout="wide", initial_sidebar_state="expanded")


def sidebar_status(sb) -> None:
    st.sidebar.header("Status")

    missing = []
    if "SUPABASE_URL" not in st.secrets:
        missing.append("SUPABASE_URL")
    if "SUPABASE_KEY" not in st.secrets:
        missing.append("SUPABASE_KEY")
    if missing:
        st.sidebar.error(
            f"Missing `{', '.join(missing)}` in Streamlit Secrets "
            "(local: `.streamlit/secrets.toml`, Cloud: app **Secrets**)."
        )
        return

    st.sidebar.caption("Project URL")
    st.sidebar.code(normalize_project_url(str(st.secrets["SUPABASE_URL"])), language="text")

    if sb is None:
        st.sidebar.error("Supabase client failed to initialize (invalid URL/key?).")
        return

    try:
        sb.table("todos").select("id").limit(1).execute()
        st.sidebar.success("Connected — `todos` table reachable.")
    except APIError as e:
        raw = getattr(e, "message", "") or str(e).lower()
        if "does not exist" in str(e).lower() or "could not find" in str(e).lower():
            st.sidebar.warning("Create the **`todos`** table (Database setup tab).")
        elif "jwt" in raw or "permission" in raw or "policy" in raw:
            st.sidebar.error("Blocked by RLS or key — adjust policies in Supabase.")
        else:
            st.sidebar.error(f"API error: `{e}`")
    except Exception as e:
        st.sidebar.error(str(e))


def tab_home(sb) -> None:
    st.title(_try_title())
    st.markdown(
        "**Tasks app** wired to Supabase: list, insert, delete rows on **`todos`**, "
        "plus SQL to create the table in one paste."
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        secrets_ok = "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets
        st.metric("Secrets configured", "Yes" if secrets_ok else "No")
    with col2:
        st.metric("Supabase client", "Ready" if sb else "Not ready")
    with col3:
        st.link_button("Deploy on Streamlit Cloud", "https://streamlit.io/cloud")


def tab_tasks(sb) -> None:
    st.header("Tasks (`todos` table)")

    if sb is None:
        st.warning("Fix Supabase secrets in the sidebar, then rerun.")
        return

    load = st.button("Reload from database")

    try:
        res = sb.table("todos").select("*").order("created_at", desc=True).execute()
        rows = list(res.data or [])
    except APIError as e:
        st.error(str(e))
        if "does not exist" in str(e).lower():
            st.info("Run the SQL in **Database setup** first.")
        return
    except Exception as e:
        st.exception(e)
        return

    if load:
        st.rerun()

    df = pd.DataFrame(rows)
    left, right = st.columns((2, 1))

    with left:
        st.subheader("Rows")
        if df.empty:
            st.info("No tasks yet — add one on the right.")
        else:
            cols = [c for c in ("id", "title", "done", "created_at") if c in df.columns]
            st.dataframe(
                df[cols] if cols else df,
                use_container_width=True,
                hide_index=True,
            )

    with right:
        st.subheader("Add task")
        with st.form("add", clear_on_submit=True):
            title = st.text_input("Title", placeholder="Morning vitals reminder")
            done = st.checkbox("Done?", value=False)
            go = st.form_submit_button("Save to Supabase")
        if go and title.strip():
            rid = str(uuid.uuid4())
            row = {"id": rid, "title": title.strip(), "done": done}
            try:
                sb.table("todos").insert(row).execute()
                st.success("Saved.")
                st.rerun()
            except APIError as e:
                st.error(str(e))

    ids = df["id"].tolist() if not df.empty and "id" in df.columns else []
    if ids:
        st.divider()
        st.subheader("Delete a task")
        pick = st.selectbox("Choose row id", options=ids, key="del_pick")
        if st.button("Delete this row"):
            try:
                sb.table("todos").delete().eq("id", pick).execute()
                st.success("Deleted.")
                st.rerun()
            except APIError as e:
                st.error(str(e))


def tab_setup(sb) -> None:
    st.header("Database setup")

    sql = """
create table if not exists public.todos (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  done boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.todos enable row level security;

-- Demo-only policy (anon/publishable can do everything).
-- Replace with real policies before production.

create policy "allow_anon_demo_all"
on public.todos
for all
to anon
using (true)
with check (true);
"""

    st.markdown(
        "**Run once** in Supabase → **SQL Editor** → *Run*. "
        "Then open the **Tasks** tab."
    )
    st.code(sql.strip(), language="sql")

    if sb is None:
        return

    try:
        r = sb.table("todos").select("id", count="exact").limit(1).execute()
        cnt = getattr(r, "count", len(r.data or []))
        st.success(f"Table reachable — `{cnt}` rows (count from REST).")
    except Exception as e:
        st.warning(f"`todos` not ready yet: {e}")


def main() -> None:
    sb = get_supabase()
    sidebar_status(sb)
    home, tasks, setup = st.tabs(["Home", "Tasks", "Database setup"])
    with home:
        tab_home(sb)
    with tasks:
        tab_tasks(sb)
    with setup:
        tab_setup(sb)


main()
