"""Free headline check: pull recent posts from NYC food and culture RSS feeds and keep the ones that
announce an opening or event.

No API key or AI involved. Results are shown as headlines with links, never as cards: a headline isn't a
place name, and keyword rules can't reliably pull the real name out of an article.
"""

from __future__ import annotations

import datetime as dt
import html
import re
import time

import feedparser

FEEDS = {
    "Eater NY": "https://ny.eater.com/rss/index.xml",
    "Grub Street": "https://www.grubstreet.com/feed/rss",
    "Secret NYC": "https://secretnyc.co/feed/",
    "Untapped New York": "https://untappedcities.com/feed/",
    "Time Out New York": "https://www.timeout.com/newyork/rss",
}

MAX_AGE_DAYS = 21
PER_GROUP = 6

# The headline must say something opened, is opening, or is on now.
HEADLINE_SIGNALS = [
    "opens", "opened", "opening", "now open", "debuts", "debut", "coming to", "arrives", "lands",
    "pop-up", "popup", "festival", "exhibit", "exhibition", "retrospective", "holiday market",
    "night market", "winter market", "food market", "flea", "returns", "launches", "expands",
]

# Headlines that are never about one new place or event in the city.
SKIP_PATTERNS = [
    "where to", "best ", "guide", "all the new", "to know", "everything you need", "how to", "ways to",
    "things to do", "breaking", "postponed", "canceled", "cancelled", "closing", "closes", "closed",
    "shutter", "listed for", "penthouse", "apartment", "townhouse", "for sale", "million", "rent",
    "trip from", "road trip", "getaway", "upstate", "new jersey", "whole foods", "trader joe", "target",
    "costco", "starbucks", "mcdonald", "chipotle", "sweetgreen", "recipe",
]

# Group -> words that put a headline in it (whole words, checked in the headline first).
GROUPS = {
    "Indian & Asian Restaurants": [
        "indian", "south indian", "dosa", "biryani", "nepalese", "pakistani", "bangladeshi", "sri lankan",
        "chinese", "cantonese", "sichuan", "dim sum", "dumpling", "dumplings", "japanese", "sushi", "ramen",
        "udon", "soba", "tempura", "omakase", "yakitori", "izakaya", "tokyo", "korean", "kimbap", "thai",
        "vietnamese", "pho", "filipino", "malaysian", "singaporean", "indonesian", "taiwanese", "hot pot",
        "hotpot",
    ],
    "Cocktail & Wine Bars": [
        "cocktail bar", "cocktails", "wine bar", "natural wine", "speakeasy", "martini", "rooftop bar",
        "lounge", "brewery", "taproom", "bar", "pub",
    ],
    "Coffee & Dessert": [
        "coffee", "cafe", "café", "espresso", "bakery", "pastry", "croissant", "croissants", "dessert",
        "ice cream", "gelato", "donut", "donuts", "doughnut", "doughnuts", "cake", "cookie", "cookies",
        "matcha", "chocolate", "bagel", "bagels",
    ],
    "Experiences": [
        "exhibit", "exhibition", "retrospective", "museum", "gallery", "festival", "holiday market",
        "night market", "winter market", "food market", "flea", "pop-up", "popup", "immersive", "ice rink",
        "skating",
    ],
}

TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", text or ""))).strip()


def _first_hit(text: str) -> str | None:
    """Group whose keyword appears earliest in the text."""
    best = None
    for group, words in GROUPS.items():
        for w in words:
            m = re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", text)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), group)
    return best[1] if best else None


def _headline(entry, source: str) -> dict | None:
    title = _clean(entry.get("title", ""))
    t = title.lower()
    if not title or any(p in t for p in SKIP_PATTERNS):
        return None
    if not any(re.search(r"(?<![\w-])" + re.escape(s) + r"(?![\w-])", t) for s in HEADLINE_SIGNALS):
        return None
    group = _first_hit(t) or _first_hit(_clean(entry.get("summary", "")).lower()[:300])
    if not group:
        return None
    return {"group": group, "title": title, "source": source, "link": entry.get("link", "")}


def fetch_headlines(feeds: dict[str, str] = FEEDS, today: dt.date | None = None) -> dict:
    """Return {"checked", "feeds_ok", "feeds_failed", "groups": {group: [headline, ...]}}."""
    today = today or dt.date.today()
    cutoff = dt.datetime.combine(today, dt.time()) - dt.timedelta(days=MAX_AGE_DAYS)
    ok, failed, found, seen = [], [], [], set()

    for source, url in feeds.items():
        parsed = feedparser.parse(url, agent="Mozilla/5.0 (compatible; nyc-tracker feed reader)")
        if not parsed.entries:
            failed.append(source)
            continue
        ok.append(source)
        for entry in parsed.entries:
            stamp = entry.get("published_parsed") or entry.get("updated_parsed")
            when = dt.datetime.fromtimestamp(time.mktime(stamp)) if stamp else None
            if when and when < cutoff:
                continue
            h = _headline(entry, source)
            if h and h["title"].lower() not in seen:
                seen.add(h["title"].lower())
                found.append((when or dt.datetime.min, h))

    found.sort(key=lambda pair: pair[0], reverse=True)  # newest first
    groups: dict[str, list] = {g: [] for g in GROUPS}
    for _, h in found:
        if len(groups[h["group"]]) < PER_GROUP:
            groups[h["group"]].append(h)

    return {
        "checked": f"{today:%B} {today.day}, {today.year}",
        "feeds_ok": ok,
        "feeds_failed": failed,
        "groups": {g: hs for g, hs in groups.items() if hs},
    }
