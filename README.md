# Fun New Things in NYC Tracker

A digest of new NYC restaurants, bars, coffee and dessert spots, and experiences, as a free Streamlit app available [here](https://fun-new-things-in-nyc-tracker.streamlit.app/).

## Two ways to refresh (no API costs)

- **Quick refresh (free)**, the button in the app: pulls the latest posts from NYC food and culture RSS feeds
  (Eater NY, Grub Street, Secret NYC, Untapped New York, Time Out New York) and sorts them into the four
  categories with keyword rules. It's instant but rough: headlines as names, article snippets as blurbs, and
  some misfiled posts. Each card links to the original article. **Curated list** switches back.
- **Curated refresh**: in a Claude Code session on this repo, say "refresh the NYC tracker." Claude researches
  new openings, writes `digest.json` (steps in `CLAUDE.md`) and pushes it. This is covered by a Claude
  subscription, with no API key needed.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files

- `nyc-openings-digest.html`: the page design, search and "Surprise me". It also works on its own.
- `digest.json`: the curated list. Until the first curated refresh, the app shows the list built into the HTML.
- `feeds.py`: the free feed reader and keyword rules. Edit `FEEDS` to add or remove sources.
- `app.py`: shows the page and swaps in whichever list is current. **Download HTML** saves a standalone copy.

On Streamlit Community Cloud, a quick refresh lasts until the app restarts; then the app shows the curated list again.
