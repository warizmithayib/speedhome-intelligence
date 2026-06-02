# SPEEDHOME Price Intelligence App

A web application that scrapes real-time rental listing data from SPEEDHOME.com and presents it in a clean, analytical dashboard.

## Live App
> Deploy to Streamlit Cloud and paste the link here.

## Features

### Minimum Requirements (All Met)
| Feature | Status |
|---|---|
| URL or area name input | ✅ |
| Autocomplete suggestions | ✅ |
| Price Summary table (per room type) | ✅ |
| Average, Median, Mode, Fair Price, Avg sqft | ✅ |
| Unit Listings table with all columns | ✅ |
| Daily / Monthly / Yearly rent types | ✅ |
| Download Excel (.xlsx) with filename | ✅ |
| Download CSV with filename | ✅ |
| Responsive / mobile-friendly layout | ✅ |

### Bonus Features
- **Bar chart** — average monthly rent by room type
- **Interactive filters** — filter listings by Room Type, Furnishing, Rent Type
- **ROI Calculator** — estimate gross/net rental yield
- **Next.js data extraction** — tries `__NEXT_DATA__` JSON before HTML parsing (more reliable)
- **Polite scraping** — 1.5s+ delay between pages, robots.txt paths respected

## How It Works
1. User enters an area name (e.g. "Mont Kiara") or pastes a SPEEDHOME URL
2. App resolves to a slug (e.g. `mont-kiara`) and fetches `speedhome.com/rent/{slug}`
3. Scraper tries two strategies:
   - Parse `__NEXT_DATA__` JSON embedded in the page (fastest, most structured)
   - Fall back to CSS selector-based card parsing
4. Data is cleaned, normalized, and presented in summary + detail tables
5. User can filter, chart, and download

## Deployment (Streamlit Cloud)
1. Push this repo to GitHub
2. Go to share.streamlit.io → New app → connect repo → set `app.py` as entry
3. No secrets needed — runs publicly

## Tech Stack
- **Python 3.11**
- **Streamlit** — UI framework
- **Requests + BeautifulSoup4** — HTTP fetching and HTML parsing
- **Pandas** — data manipulation
- **openpyxl** — Excel export

## Assumptions & Notes
- SPEEDHOME uses Next.js SSR; the `__NEXT_DATA__` approach is the most reliable method
- If a page is fully client-rendered (no SSR data), HTML card parsing is used as fallback
- Max 5 pages fetched by default (configurable in sidebar)
- Daily rental type is shown as "Not Available" if no listings exist for that type
- Fair Price = (Median × 0.6) + (Mean × 0.4) — weighted toward median to reduce outlier impact
