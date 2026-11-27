"""Free refresh: pull recent posts from NYC food and culture RSS feeds and sort them into the digest's categories.

No API key or AI involved. Items are matched with simple keyword rules, so expect rougher results than a
curated refresh: headlines as names, article snippets as blurbs, and the occasional misfiled post.
"""

from __future__ import annotations

import datetime as dt
import html
import re
import time

import feedparser

# Feeds that fail or return nothing are skipped; the app shows which ones worked.
FEEDS = {
    "Eater NY": "https://ny.eater.com/rss/index.xml",
    "Grub Street": "https://www.grubstreet.com/feed/rss",
    "Secret NYC": "https://secretnyc.co/feed/",
    "Untapped New York": "https://untappedcities.com/feed/",
    "Time Out New York": "https://www.timeout.com/newyork/rss",
}

MAX_AGE_DAYS = 35
PER_CATEGORY = 8

# A post counts only if it sounds like something new or happening now.
NEW_SIGNALS = [
    "open", "opening", "opens", "debut", "new ", "now serving", "pop-up", "popup", "arrives", "launch",
    "festival", "fest ", "market", "exhibit", "exhibition", "museum", "show", "immersive", "returns",
]

# Category -> keyword -> type label shown on the card.
CATEGORY_RULES = {
    "Indian & Asian Restaurants": {
        "indian": "Indian", "south indian": "South Indian", "dosa": "South Indian", "biryani": "Indian",
        "nepalese": "Nepalese", "pakistani": "Pakistani", "bangladeshi": "Bangladeshi", "sri lankan": "Sri Lankan",
        "chinese": "Chinese", "cantonese": "Cantonese", "sichuan": "Sichuan", "dim sum": "Dim Sum",
        "dumpling": "Chinese", "japanese": "Japanese", "sushi": "Japanese", "ramen": "Japanese",
        "omakase": "Japanese", "yakitori": "Japanese", "izakaya": "Japanese", "korean": "Korean",
        "kimbap": "Korean", "thai": "Thai", "vietnamese": "Vietnamese", "pho": "Vietnamese",
        "filipino": "Filipino", "malaysian": "Malaysian", "singaporean": "Singaporean",
        "indonesian": "Indonesian", "taiwanese": "Taiwanese", "hot pot": "Hot Pot",
    },
    "Cocktail & Wine Bars": {
        "cocktail": "Cocktail Bar", "wine bar": "Wine Bar", "natural wine": "Wine Bar", "speakeasy": "Speakeasy",
        "martini": "Cocktail Bar", "rooftop bar": "Rooftop Bar", "lounge": "Lounge", "brewery": "Brewery",
        "taproom": "Beer Bar", "bar ": "Bar",
    },
    "Coffee & Dessert": {
        "coffee": "Coffee", "cafe": "Café", "café": "Café", "espresso": "Coffee", "bakery": "Bakery",
        "pastry": "Bakery", "croissant": "Bakery", "dessert": "Dessert", "ice cream": "Ice Cream",
        "gelato": "Gelato", "donut": "Doughnuts", "doughnut": "Doughnuts", "cake": "Dessert",
        "cookie": "Dessert", "matcha": "Tea", "tea house": "Tea", "chocolate": "Dessert",
    },
    "Experiences": {
        "exhibit": "Exhibition", "exhibition": "Exhibition", "museum": "Museum", "gallery": "Gallery",
        "festival": "Festival", "market": "Market", "pop-up": "Pop-Up", "popup": "Pop-Up",
        "immersive": "Experience", "concert": "Music", "show": "Show", "fair": "Fair", "tour": "Tour",
        "holiday": "Seasonal", "skating": "Outdoors", "park": "Outdoors",
    },
}

# Extra words for the page's vibe search.
VIBE_TAGS = {
    "date night": ["date night", "romantic", "intimate", "candlelit"],
    "cheap eats": ["cheap", "affordable", "under $", "budget", "$10", "$15"],
    "late night": ["late night", "late-night", "until 2", "until 4", "2am", "4am", "midnight"],
    "group friendly": ["group", "family-style", "share", "large party"],
    "outdoor": ["outdoor", "rooftop", "patio", "garden", "ice rink", "skating"],
    "upscale": ["tasting menu", "omakase", "fine dining", "michelin"],
    "free": ["free admission", "free entry", "free event", "is free"],
    "sweet tooth": ["dessert", "ice cream", "gelato", "cake", "pastry", "chocolate", "donut", "doughnut"],
    "weekend": ["weekend", "saturday", "sunday", "brunch"],
}

NEIGHBORHOODS = [
    "Upper East Side", "Upper West Side", "Lower East Side", "East Village", "West Village", "Greenwich Village",
    "Hell's Kitchen", "Midtown", "Chelsea", "Flatiron", "NoMad", "Gramercy", "Murray Hill", "Kips Bay",
    "SoHo", "NoHo", "Nolita", "Tribeca", "Chinatown", "Little Italy", "Financial District", "FiDi",
    "Harlem", "East Harlem", "Washington Heights", "Inwood", "Union Square", "Koreatown", "Hudson Yards",
    "Williamsburg", "Greenpoint", "Bushwick", "Park Slope", "Prospect Heights", "Crown Heights",
    "Fort Greene", "Clinton Hill", "Bed-Stuy", "Bedford-Stuyvesant", "Cobble Hill", "Carroll Gardens",
    "Boerum Hill", "Red Hook", "Gowanus", "DUMBO", "Brooklyn Heights", "Sunset Park", "Bay Ridge",
    "Borough Park", "Flatbush", "Ditmas Park", "Astoria", "Long Island City", "Jackson Heights",
    "Flushing", "Elmhurst", "Sunnyside", "Ridgewood", "Woodside", "Forest Hills", "Jamaica",
    "Mott Haven", "Arthur Avenue", "Bryant Park", "Central Park", "Brooklyn Bridge Park", "Coney Island",
    "Rockefeller Center", "Times Square", "Lincoln Center", "Governors Island", "Staten Island", "Bronx", "Brooklyn", "Queens", "Manhattan",
]

# Broad words added to every item in a category, so searches like "drinks" or "restaurant" work.
CATEGORY_TAGS = {
    "Indian & Asian Restaurants": "restaurant dinner food",
    "Cocktail & Wine Bars": "bar drinks nightlife",
    "Coffee & Dessert": "cafe treat",
    "Experiences": "things to do event",
}

TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", text or ""))).strip()


def _short(text: str, limit: int = 220) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:—-")
    return cut + "…"


def _published(entry) -> dt.datetime | None:
    stamp = entry.get("published_parsed") or entry.get("updated_parsed")
    return dt.datetime.fromtimestamp(time.mktime(stamp)) if stamp else None


def _first_match(text: str, words) -> str | None:
    for w in words:
        if w in text:
            return w
    return None


def _classify(text: str) -> tuple[str, str] | None:
    """Return (category, type label) for the category whose keyword appears earliest in the text."""
    best = None
    for category, rules in CATEGORY_RULES.items():
        for word, label in rules.items():
            pos = text.find(word)
            if pos != -1 and (best is None or pos < best[0]):
                best = (pos, category, label)
    return (best[1], best[2]) if best else None


def _item(entry, source: str) -> dict | None:
    title = _clean(entry.get("title", ""))
    summary = _clean(entry.get("summary", ""))
    if not title:
        return None
    text = f" {title} {summary} ".lower()
    if not _first_match(text, NEW_SIGNALS):
        return None
    found = _classify(f" {title.lower()} ") or _classify(text)
    if not found:
        return None
    category, label = found
    hood = next((n for n in NEIGHBORHOODS if n.lower() in text), "NYC")
    tags = {label.lower(), *CATEGORY_TAGS[category].split()}
    tags.update(word for word in CATEGORY_RULES[category] if word in text)
    tags.update(tag for tag, words in VIBE_TAGS.items() if _first_match(text, words))
    return {
        "category": category,
        "name": title,
        "neighborhood": hood,
        "type": label,
        "blurb": _short(summary) or f"From {source}.",
        "tags": " ".join(sorted(t.strip() for t in tags if t.strip())),
        "link": entry.get("link", ""),
        "source": source,
    }


def fetch_digest(feeds: dict[str, str] = FEEDS, today: dt.date | None = None) -> dict:
    """Return {"updated", "source", "feeds_ok", "feeds_failed", "items"} built from the RSS feeds."""
    today = today or dt.date.today()
    cutoff = dt.datetime.combine(today, dt.time()) - dt.timedelta(days=MAX_AGE_DAYS)
    ok, failed, candidates, seen = [], [], [], set()

    for source, url in feeds.items():
        parsed = feedparser.parse(url, agent="Mozilla/5.0 (compatible; nyc-tracker feed reader)")
        if not parsed.entries:
            failed.append(source)
            continue
        ok.append(source)
        for entry in parsed.entries:
            when = _published(entry)
            if when and when < cutoff:
                continue
            item = _item(entry, source)
            key = item and item["name"].lower()
            if item and key not in seen:
                seen.add(key)
                candidates.append((when or dt.datetime.min, item))

    candidates.sort(key=lambda pair: pair[0], reverse=True)  # newest first
    counts: dict[str, int] = {}
    items = []
    for _, item in candidates:
        if counts.get(item["category"], 0) < PER_CATEGORY:
            counts[item["category"]] = counts.get(item["category"], 0) + 1
            items.append(item)

    return {
        "updated": f"{today:%B} {today.day}, {today.year}",
        "source": "feeds",
        "feeds_ok": ok,
        "feeds_failed": failed,
        "items": items,
    }
