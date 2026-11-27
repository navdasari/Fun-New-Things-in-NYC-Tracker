"""Streamlit wrapper around nyc-openings-digest.html with a button to refresh it via Claude."""

import json
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from refresh import fetch_digest

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "nyc-openings-digest.html"
DATA = ROOT / "digest.json"

st.set_page_config(page_title="NYC: What's New", page_icon="🗽", layout="centered")


def api_key() -> str | None:
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # no secrets.toml
        key = None
    return key or os.environ.get("ANTHROPIC_API_KEY")


def load_digest() -> dict | None:
    if DATA.exists():
        return json.loads(DATA.read_text())
    return None


def build_html(digest: dict | None) -> str:
    """Return the page, with the saved digest swapped in through the page's own renderItems()."""
    html = TEMPLATE.read_text()
    if not digest:
        return html  # nothing refreshed yet: show the page as written
    payload = json.dumps(digest).replace("</", "<\\/")
    inject = (
        "<script>(function(){"
        f"const d = {payload};"
        "renderItems(d.items);"
        "dateLine.textContent = 'Last updated ' + d.updated;"
        "})();</script>"
    )
    return html.replace("</body>", inject + "\n</body>", 1)


digest = load_digest()

col_btn, col_dl = st.columns([1, 1])
with col_btn:
    refresh = st.button("🔄 Refresh with latest openings", type="primary", use_container_width=True)
with col_dl:
    st.download_button(
        "⬇️ Download as HTML",
        data=build_html(digest),
        file_name="nyc-openings-digest.html",
        mime="text/html",
        use_container_width=True,
    )

if refresh:
    key = api_key()
    if not key:
        st.error("Add ANTHROPIC_API_KEY to .streamlit/secrets.toml (or the environment) to refresh.")
    else:
        with st.spinner("Claude is searching for new openings. This takes a few minutes…"):
            try:
                digest = fetch_digest(key)
            except Exception as e:  # keep showing the previous list on any failure
                st.error(f"Refresh failed: {e}")
            else:
                DATA.write_text(json.dumps(digest, indent=2))
                st.rerun()  # redraw the page and the download with the new list

components.html(build_html(digest), height=3200, scrolling=True)
