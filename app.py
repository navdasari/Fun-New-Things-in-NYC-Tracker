"""Streamlit wrapper around nyc-openings-digest.html. No API costs.

- The cards always show the curated list in digest.json, refreshed by asking Claude in a Claude Code
  session (see CLAUDE.md).
- "Check the news" pulls fresh headlines from free RSS feeds into a separate list with links. Headlines
  never go into the cards, because a headline isn't a place name.
"""

import json
import re
from pathlib import Path

import streamlit as st

from feeds import fetch_headlines

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "nyc-openings-digest.html"
CURATED = ROOT / "digest.json"
HEADLINES = ROOT / "headlines.json"  # not committed; lasts until the app restarts

st.set_page_config(page_title="NYC: What's New", page_icon="🗽", layout="centered")


def load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def build_html(digest: dict | None) -> str:
    """Return the page, with the curated list swapped in through the page's own renderItems()."""
    page = TEMPLATE.read_text()
    if not digest:
        return page
    payload = json.dumps(digest).replace("</", "<\\/")
    inject = (
        "<script>(function(){"
        f"const d = {payload};"
        "renderItems(d.items);"
        "dateLine.textContent = 'Last updated ' + d.updated;"
        "})();</script>"
    )
    return page.replace("</body>", inject + "\n</body>", 1)


def md_link(text: str, url: str) -> str:
    safe = re.sub(r"([\[\]\\*_`])", r"\\\1", text)
    return f"[{safe}]({url})" if url.startswith(("http://", "https://")) else safe


digest = load(CURATED)
headlines = load(HEADLINES)

col_news, col_dl = st.columns(2)
with col_news:
    check = st.button("📰 Check the news (free)", type="primary", width="stretch",
                      help="Pull this week's opening and event headlines from NYC news feeds.")
with col_dl:
    st.download_button("⬇️ Download HTML", data=build_html(digest), file_name="nyc-openings-digest.html",
                       mime="text/html", width="stretch")

if check:
    with st.spinner("Reading news feeds…"):
        headlines = fetch_headlines()
    HEADLINES.write_text(json.dumps(headlines, indent=2))

if headlines:
    total = sum(len(hs) for hs in headlines["groups"].values())
    with st.expander(f"In the news this week: {total} headlines (checked {headlines['checked']})",
                     expanded=bool(check)):
        if not total:
            st.write("No opening or event headlines in the feeds right now.")
        for group, hs in headlines["groups"].items():
            st.markdown(f"**{group}**")
            st.markdown("\n".join(f"- {md_link(h['title'], h['link'])} · *{h['source']}*" for h in hs))
        if headlines["feeds_failed"]:
            st.caption("Couldn't reach: " + ", ".join(headlines["feeds_failed"]))
        st.caption("Headlines are picked by keyword and may include the odd miss. "
                   "The cards below are the curated list.")

st.iframe(build_html(digest), height=3200)
