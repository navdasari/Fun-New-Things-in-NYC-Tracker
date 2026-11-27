# Fun New Things in NYC Tracker

A digest of new NYC restaurants, bars, coffee and dessert spots, and experiences, as a Streamlit app.
Press **Refresh** and Claude searches the web for what opened in the past month, then redraws the page.

## Run locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then paste your Anthropic API key
streamlit run app.py
```

## How it works

- `nyc-openings-digest.html`: the page design, search and "Surprise me", unchanged. It works on its own too.
- `refresh.py`: one Claude call with web search to research openings, then a second call that turns the notes into structured items.
- `app.py`: shows the page, saves each refresh to `digest.json`, and feeds it to the page's `renderItems()`.
  **Download as HTML** saves a standalone copy of the current list.

A refresh takes a few minutes and costs roughly a dollar or less in API usage.

On Streamlit Community Cloud, add `ANTHROPIC_API_KEY` under App settings → Secrets. The Cloud
filesystem is temporary, so a refreshed list lasts until the app restarts; then it falls back to the list in the HTML.
