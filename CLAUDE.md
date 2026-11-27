# NYC tracker: curated refresh

When asked to "refresh the NYC tracker" (or similar), rebuild `digest.json`, which the Streamlit app shows as the curated list.

1. Search the web for what's opened or started in NYC in about the last 5 weeks. Good sources: The Infatuation and
   Eater NY new-openings guides, Time Out New York, Grub Street, museum and gallery listings, food festival calendars.
2. Pick 5-8 items for each category, using these names exactly:
   `Indian & Asian Restaurants`, `Cocktail & Wine Bars`, `Coffee & Dessert`, `Experiences`
   (Experiences = exhibitions, festivals, markets, pop-ups happening now or in the next few weeks).
   Skip anything closed or ended. Don't invent details; every fact should come from a source you read.
3. Write `digest.json` in this shape:

   ```json
   {
     "updated": "November 27, 2026",
     "source": "curated",
     "items": [
       {
         "category": "Cocktail & Wine Bars",
         "name": "Place name",
         "neighborhood": "West Village",
         "type": "Wine Bar",
         "blurb": "One or two sentences with concrete details: dishes, prices, hours, who's behind it.",
         "tags": "wine date night intimate late night",
         "link": "https://source-article-url"
       }
     ]
   }
   ```

   `tags` is one lowercase, space-separated string of words people might search for (cuisine, "date night",
   "cheap eats", "late night", "group friendly", "outdoor", "sweet tooth"…). `link` is optional.
4. Check it loads: `python -c "import json; d=json.load(open('digest.json')); print(len(d['items']))"`.
5. Commit `digest.json` on its own and push it to `main`, which the Streamlit app deploys from.

Don't edit `nyc-openings-digest.html` for a refresh; the app injects `digest.json` into it.
