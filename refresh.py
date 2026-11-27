"""Ask Claude (with web search) for the newest NYC openings and return them as card data."""

from __future__ import annotations

import datetime as dt
from typing import List, Literal

import anthropic
from pydantic import BaseModel

MODEL = "claude-opus-5-5"
BETAS = ["server-side-fallback-2026-07-01"]

# Must match the data-category values in nyc-openings-digest.html.
Category = Literal[
    "Indian & Asian Restaurants",
    "Cocktail & Wine Bars",
    "Coffee & Dessert",
    "Experiences",
]


class Item(BaseModel):
    category: Category
    name: str
    neighborhood: str
    type: str  # e.g. "Korean", "Wine Bar", "Festival"
    blurb: str
    tags: str  # space-separated, lowercase: words people might search for


class Digest(BaseModel):
    items: List[Item]


RESEARCH_PROMPT = """Today is {today}. Find what's new and fun in New York City from roughly the last month \
(openings since about {since}), for a digest with exactly these four categories:

1. Indian & Asian Restaurants
2. Cocktail & Wine Bars
3. Coffee & Dessert
4. Experiences (exhibitions, festivals, food markets, pop-ups, events happening now or in the next few weeks)

Search sources like The Infatuation's and Eater NY's new-openings guides, Time Out New York, museum and gallery \
listings, and NYC food festival calendars. Aim for 5-8 items per category, all genuinely new or current. Skip \
anything that has closed or ended.

For each item give: its name, neighborhood (and venue if it's an event), a short type label (cuisine or kind of \
place), a one- or two-sentence blurb with specific concrete details (signature dishes, prices, hours, who's behind \
it), and a list of lowercase vibe tags someone might search for (e.g. "date night", "cheap eats", "late night", \
"group friendly", "outdoor", "quiet", "sweet tooth", plus cuisine words like "indian", "korean")."""

FORMAT_PROMPT = """Convert these research notes into the structured digest. Keep every item that clearly fits one \
of the four categories; drop anything that doesn't. Tags must be a single space-separated lowercase string. \
Keep blurbs to one or two sentences and don't invent details that aren't in the notes.

<notes>
{notes}
</notes>"""


def _research(client: anthropic.Anthropic, today: dt.date) -> str:
    since = today - dt.timedelta(days=35)
    messages = [{
        "role": "user",
        "content": RESEARCH_PROMPT.format(
            today=today.strftime("%B %d, %Y"), since=since.strftime("%B %d, %Y")
        ),
    }]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 15}]

    response = None
    for _ in range(5):  # resume up to 5 times if the server-side search loop pauses
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=64000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            betas=BETAS,
            fallbacks="default",
            tools=tools,
            messages=messages,
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": response.content}]

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined the research request.")
    notes = "\n".join(b.text for b in response.content if b.type == "text").strip()
    if not notes:
        raise RuntimeError(f"Research returned no text (stop reason: {response.stop_reason}).")
    return notes


def _structure(client: anthropic.Anthropic, notes: str) -> List[dict]:
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "low"},
        betas=BETAS,
        fallbacks="default",
        output_format=Digest,
        messages=[{"role": "user", "content": FORMAT_PROMPT.format(notes=notes)}],
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"Couldn't structure the results (stop reason: {response.stop_reason}).")
    return [item.model_dump() for item in response.parsed_output.items]


def fetch_digest(api_key: str | None = None) -> dict:
    """Run a full refresh. Returns {"updated": "Month D, YYYY", "items": [...]}."""
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    today = dt.date.today()
    items = _structure(client, _research(client, today))
    if not items:
        raise RuntimeError("Refresh found no items; keeping the previous list.")
    return {"updated": f"{today:%B} {today.day}, {today.year}", "items": items}
