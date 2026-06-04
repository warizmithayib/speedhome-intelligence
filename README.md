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

## Cloud Deployment & Data Availability

### ⚠️ Important: Live Scraping Limitation on Cloud

SPEEDHOME.com employs Cloudflare bot protection that **blocks requests originating from cloud datacenter IPs** (AWS, GCP, Azure) with a `403 Forbidden` response. This affects all cloud platforms including Streamlit Cloud, Railway, Render, Heroku, and Vercel — it is an infrastructure-level IP block, not a code issue.

**This app handles this gracefully with a two-tier data strategy:**

| Environment | Data Source |
|---|---|
| Local (`localhost`) | ✅ Live scraping from SPEEDHOME.com in real-time |
| Cloud (Streamlit Cloud) | ✅ Pre-scraped sample data bundled in `sample_data/` |

On cloud deployment, the app automatically detects the live fetch failure and falls back to the cached dataset, displaying a notice to the user. All analytics features (summary table, charts, filters, comparison, ROI calculator, downloads) remain **fully functional** using the cached data.

### Pre-loaded Areas (Cloud)

The following areas are available when using the cloud-deployed version:

| Area | Slug |
|---|---|
| Mont Kiara | `mont-kiara` |
| Bangsar | `bangsar` |
| KLCC | `klcc` |
| Petaling Jaya | `petaling-jaya` |
| Subang Jaya | `subang-jaya` |
| Cheras | `cheras` |
| Damansara | `damansara` |
| Cyberjaya | `cyberjaya` |
| Shah Alam | `shah-alam` |
| Bukit Bintang | `bukit-bintang` |
| Penang | `penang` |

> Searching for areas outside this list on the cloud deployment will return no results. To access any area in real-time, run the app locally.

### Refreshing the Sample Data

To update or expand the cached dataset, run `scrape_and_save.py` locally and commit the output:

```bash
pip install curl_cffi   # required for Chrome impersonation
python scrape_and_save.py

git add sample_data/
git commit -m "Refresh sample data"
git push
```

## Local Setup

```bash
git clone <your-repo-url>
cd speedhome-app
pip install -r requirements.txt
streamlit run app.py
```

When running locally, live scraping is fully active — any area on SPEEDHOME.com can be searched without restriction.

## Deployment (Streamlit Cloud)
1. Push this repo to GitHub (include the `sample_data/` folder).
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → connect your repo.
3. Set `app.py` as your entry point.
4. Streamlit Cloud will automatically install all libraries declared in `requirements.txt`.

## Repository Structure

```
├── app.py                  # Main Streamlit application
├── scrape_and_save.py      # Local scraper to refresh sample data
├── requirements.txt        # Python dependencies
├── sample_data/            # Pre-scraped listings for cloud fallback
│   ├── _index.json         # Index of available areas + metadata
│   ├── mont-kiara.json
│   ├── bangsar.json
│   └── ...
└── README.md
```

## Tech Stack
- **Python 3.11**
- **Streamlit** - UI framework
- **Streamlit-AgGrid** - Advanced JavaScript grid wrapper for Streamlit
- **curl-cffi** - Advanced HTTP requests with browser impersonation (bypasses Cloudflare fingerprinting locally)
- **Pandas** - Data manipulation
- **openpyxl** - Excel export engine

## Assumptions & Notes
- SPEEDHOME uses Next.js SSR; extracting data via the `_next/data/{build_id}` JSON structure is the most stable and performant method of listing retrieval.
- Max 5 pages are fetched by default (configurable in the sidebar).
- Fair Price = (Median × 0.6) + (Mean × 0.4) — weighted toward the median to reduce the statistical skew of outlier luxury listings.
- Standard Streamlit tables (`st.dataframe`) require a cell focus event (double-clicking) before rendering standard links. Using AgGrid's `JsCode` compiler lets us bypass this to achieve intuitive, single-click navigation.
- The cloud data limitation is a known infrastructure constraint, not a deficiency in the scraping logic. The same code fetches live data successfully in a local environment.
