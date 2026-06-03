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
- **Streamlit-AgGrid Integration** - Employs custom JavaScript cell renderers to enable direct **1-click clickable links** directly in the grid, bypassing default cell selection behaviors.
- **Area Comparison Mode** - Compare metrics, rental rates, and unit volumes between two locations side-by-side, complete with interactive AgGrid data tables and comparison bar charts.
- **Bar chart** - average monthly rent by room type
- **Interactive filters** - filter listings by Room Type, Furnishing, Rent Type
- **ROI Calculator** - estimate gross/net rental yield
- **Next.js data extraction** - tries Next.js SSR endpoints using the application's build ID (more reliable and structured)
- **Polite scraping** - 1.2s+ delay between pages, respects typical crawler conventions

## How It Works
1. User enters an area name (e.g. "Mont Kiara") or pastes a SPEEDHOME URL.
2. App resolves to a slug (e.g. `mont-kiara`) and fetches the relevant listing endpoint using the dynamically retrieved Next.js SSR build ID.
3. Listings are fetched page-by-page, cleaned, normalized, and cached.
4. Summary analytics are calculated.
5. If Comparison Mode is activated via the sidebar, the app fetches listings for a secondary target and presents their metrics side-by-side.
6. Datasets are parsed through `streamlit-aggrid` which binds standard sort/filter options to the spreadsheet columns while rendering native HTML link tags inside the cells.

## Deployment (Streamlit Cloud)
1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → connect your repo.
3. Set `app.py` as your entry point.
4. Streamlit Cloud will automatically install all libraries declared in `requirements.txt`.

## Tech Stack
- **Python 3.11**
- **Streamlit** - UI framework
- **Streamlit-AgGrid** - Advanced JavaScript grid wrapper for Streamlit
- **curl-cffi** - Advanced HTTP requests with browser impersonation features
- **Pandas** - Data manipulation
- **openpyxl** - Excel export engine

## Assumptions & Notes
- SPEEDHOME uses Next.js SSR; extracting data via the `_next/data/{build_id}` JSON structure is the most stable and performant method of listing retrieval.
- Max 5 pages are fetched by default (configurable in the sidebar).
- Fair Price = (Median × 0.6) + (Mean × 0.4) - weighted toward the median to reduce the statistical skew of outlier luxury listings.
- Standard Streamlit tables (`st.dataframe`) require a cell focus event (double-clicking) before rendering standard links. Using AgGrid's `JsCode` compiler lets us bypass this to achieve intuitive, single-click navigation.