# Fun New Things in NYC Tracker

A digest of new NYC restaurants, bars, coffee and dessert spots, and experiences, as a free Streamlit app.

## Keeping it fresh (no API costs)

- **Curated list (the cards)**: in a Claude Code session on this repo, say "refresh the NYC tracker." Claude
  researches new openings, writes `digest.json` (steps in `CLAUDE.md`) and pushes it. This is covered by a
  Claude subscription, with no API key needed.
- **Check the news (free)**, the button in the app: pulls this week's opening and event headlines from NYC
  news feeds (Eater NY, Grub Street, Secret NYC, Untapped New York, Time Out New York) into a separate,
  linked list above the cards. Headlines never go into the cards, because a headline isn't a place name.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files

- `nyc-openings-digest.html`: the page design, search and "Surprise me". It also works on its own.
- `digest.json`: the curated list shown on the cards.
- `feeds.py`: the free headline check and its keyword rules. Edit `FEEDS` to add or remove sources.
- `app.py`: shows the page with the curated list and the headlines. **Download HTML** saves a standalone copy.

On Streamlit Community Cloud, checked headlines last until the app restarts.
