"""Shared Supabase bootstrap for Streamlit (cached across reruns)."""

from __future__ import annotations

import streamlit as st
from supabase import Client, create_client


def normalize_project_url(url: str) -> str:
    """supabase-py expects https://PROJECT_REF.supabase.co (no /rest/v1/)."""
    u = url.strip().rstrip("/")
    sep = "/rest/v1"
    if sep in u:
        u = u.split(sep, 1)[0].rstrip("/")
    return u


@st.cache_resource(show_spinner="Connecting to Supabase…")
def connect_supabase(url: str, key: str) -> Client:
    return create_client(normalize_project_url(url), key.strip())


def get_supabase() -> Client | None:
    """Returns None if secrets are missing or the client fails to initialize."""
    try:
        url_raw = str(st.secrets["SUPABASE_URL"]).strip()
        key = str(st.secrets["SUPABASE_KEY"]).strip()
    except KeyError:
        return None

    if not url_raw or not key:
        return None

    try:
        return connect_supabase(url_raw, key)
    except Exception:
        return None
