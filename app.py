"""Streamlit wrapper around nyc-openings-digest.html.

Two sources for the list, no API costs:
- digest.json: the curated list, refreshed by asking Claude in a Claude Code session (see CLAUDE.md).
- feed_digest.json: a quick refresh from free RSS feeds, made by the button below (not committed).
"""

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from feeds import fetch_digest

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "nyc-openings-digest.html"
CURATED = ROOT / "digest.json"
FEED = ROOT / "feed_digest.json"

st.set_page_config(page_title="NYC: What's New", page_icon="🗽", layout="centered")


def load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def build_html(digest: dict | None) -> str:
    """Return the page, with the digest swapped in through the page's own renderItems()."""
    page = TEMPLATE.read_text()
    if not digest:
        return page  # no saved list: show the page as written
    payload = json.dumps(digest).replace("</", "<\\/")
    inject = (
        "<script>(function(){"
        f"const d = {payload};"
        "renderItems(d.items);"
        "dateLine.textContent = 'Last updated ' + d.updated;"
        "})();</script>"
    )
    return page.replace("</body>", inject + "\n</body>", 1)


feed = load(FEED)
digest = feed or load(CURATED)

col_refresh, col_reset, col_dl = st.columns(3)
with col_refresh:
    refresh = st.button("🔄 Quick refresh (free)", type="primary", use_container_width=True,
                        help="Pull the latest posts from NYC food and culture news feeds.")
with col_reset:
    reset = st.button("✨ Curated list", use_container_width=True, disabled=feed is None,
                      help="Go back to the list Claude curated.")
with col_dl:
    st.download_button("⬇️ Download HTML", data=build_html(digest), file_name="nyc-openings-digest.html",
                       mime="text/html", use_container_width=True)

if refresh:
    with st.spinner("Reading news feeds…"):
        result = fetch_digest()
    if result["items"]:
        FEED.write_text(json.dumps(result, indent=2))
        st.session_state["flash"] = (
            f"Found {len(result['items'])} items from {', '.join(result['feeds_ok'])}."
            + (f" Couldn't reach: {', '.join(result['feeds_failed'])}." if result["feeds_failed"] else "")
        )
        st.rerun()
    else:
        st.warning("No new items found in the feeds, so the current list is unchanged."
                   + (f" Couldn't reach: {', '.join(result['feeds_failed'])}." if result["feeds_failed"] else ""))

if reset:
    FEED.unlink(missing_ok=True)
    st.rerun()

if msg := st.session_state.pop("flash", None):
    st.success(msg)

if feed:
    st.caption("Showing a quick refresh from news feeds: headlines and snippets, sorted by keyword, "
               "so some items may be off. **Curated list** switches back.")
elif digest:
    st.caption(f"Showing the curated list from {digest['updated']}.")

components.html(build_html(digest), height=3200, scrolling=True)
