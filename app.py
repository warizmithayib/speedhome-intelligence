import streamlit as st
import pandas as pd
import re
import time
import io
import urllib.parse
from datetime import datetime
from statistics import median, mode, mean
import random
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# Fallback import for standard requests
import requests as standard_requests

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SPEEDHOME Price Intelligence",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #F2F4F8 !important;
}
h1 { font-size: 1.6rem !important; }

/* ── App header banner ── */
.app-header {
    background: #0F1923;
    margin: -1rem -1rem 1.5rem -1rem;
    padding: 22px 28px 18px;
    display: flex; align-items: center; gap: 14px;
    border-bottom: 2px solid #FF5A1F;
}
.app-header-icon { font-size: 2rem; line-height: 1; }
.app-header-title { color: #FFFFFF; font-size: 1.35rem; font-weight: 700; letter-spacing: -0.3px; margin: 0; }
.app-header-sub { color: #7A8FA6; font-size: 0.73rem; text-transform: uppercase; letter-spacing: 0.6px; margin-top: 3px; }

/* ── Metric cards ── */
.metric-card {
    background: #FFFFFF;
    border: 1px solid #DDE3EC;
    border-top: 3px solid #FF5A1F;
    border-radius: 10px;
    padding: 16px 18px;
    text-align: left;
}
.metric-label {
    font-size: .68rem; font-weight: 700;
    color: #7A8FA6; text-transform: uppercase;
    letter-spacing: .7px; margin-bottom: 8px;
}
.metric-value {
    font-size: 1.45rem; font-weight: 700;
    color: #0F1923; line-height: 1;
}
.metric-sub {
    font-size: .71rem; color: #9AAAB8; margin-top: 4px;
}

/* ── Badges ── */
.badge {
    display: inline-block; padding: 2px 9px;
    border-radius: 20px; font-size: .68rem; font-weight: 700;
}
.badge-monthly  { background: #EBF1FF; color: #2C55C5; }
.badge-daily    { background: #FFF0EB; color: #C44A10; }
.badge-yearly   { background: #EDFAF4; color: #1A7A47; }
.badge-ff       { background: #EBF1FF; color: #2C55C5; }
.badge-pf       { background: #FFF7EB; color: #A05C00; }
.badge-unf      { background: #F4EEFF; color: #6930C3; }

/* ── Section headers ── */
.section-header {
    font-size: .68rem; font-weight: 700;
    color: #7A8FA6; text-transform: uppercase;
    letter-spacing: 1px;
    margin: 24px 0 12px;
    display: flex; align-items: center; gap: 10px;
}
.section-header::after {
    content: ''; flex: 1; height: 1px; background: #DDE3EC;
}

/* ── Info note ── */
.info-note {
    background: #EBF1FF;
    border-left: 3px solid #3B6FE8;
    border-radius: 0 8px 8px 0;
    padding: 9px 14px;
    font-size: .78rem; color: #2C4FA8;
    margin-bottom: 14px;
}

/* ── Table tweaks ── */
.stDataFrame thead th { background: #0F1923 !important; color: #FFFFFF !important; font-size: .72rem !important; text-transform: uppercase; letter-spacing: .5px; }
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid #DDE3EC; }

/* ── Streamlit overrides ── */
[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #DDE3EC; border-top: 3px solid #FF5A1F; border-radius: 10px; padding: 14px 16px; }
.stButton > button[kind="primary"] { background: #FF5A1F !important; border: none !important; font-weight: 600; }
.stButton > button[kind="primary"]:hover { background: #E04A12 !important; }
.stExpander { border: 1px solid #DDE3EC !important; border-radius: 10px !important; background: #fff; }

/* ── Loading text ── */
.loading-text { font-size: 1rem; color: #7A8FA6; margin-top: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_URL = "https://speedhome.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://speedhome.com/",
}

HEADERS_HTML = {**HEADERS, "Accept": "text/html,application/xhtml+xml,*/*"}

POPULAR_AREAS = [
    "Mont Kiara", "Mont Kiara Aman", "Mont Kiara Bayu", "Mont Kiara Damai",
    "Petaling Jaya", "Subang Jaya", "Cheras", "Bangsar", "Bangsar South",
    "Damansara", "Damansara Perdana", "Damansara Damai", "Sri Damansara",
    "KLCC", "Bukit Bintang", "Ampang", "Ampang Hilir", "Wangsa Maju",
    "Setapak", "Kepong", "Sri Petaling", "Puchong", "Cyberjaya",
    "Shah Alam", "Klang", "Ara Damansara", "Sunway", "Sunway Geo",
    "Desa Parkcity", "KL City Centre", "Jalan Ipoh", "Sentul",
    "Titiwangsa", "Setiawangsa", "Taman Tun Dr Ismail", "TTDI",
    "Pavilion Residences", "The Troika", "Solaris Mont Kiara",
    "Penang", "Georgetown", "Bayan Lepas", "Jelutong", "Tanjung Tokong",
]

FURNISH_MAP = {
    "FULL": "Fully Furnished",
    "PARTIAL": "Partially Furnished",
    "UNFURNISHED": "Unfurnished",
    "NONE": "Unfurnished",
}

# Cached build ID so we only fetch it once per session
_BUILD_ID: str | None = None

# ── Sample data fallback (for Streamlit Cloud deployment) ──────────────────────

SAMPLE_DATA_DIR = "sample_data"

def load_sample_data(slug: str) -> tuple[list[dict], str | None]:
    """
    Load pre-scraped listings from sample_data/<slug>.json.
    Returns (listings, scraped_at) or ([], None) if not found.
    """
    import os, json
    path = os.path.join(SAMPLE_DATA_DIR, f"{slug}.json")
    if not os.path.exists(path):
        # Try fuzzy match: first slug token contained in filename
        prefix = slug.split("-")[0]
        candidates = [f for f in os.listdir(SAMPLE_DATA_DIR)
                      if f.endswith(".json") and not f.startswith("_") and prefix in f]
        if candidates:
            path = os.path.join(SAMPLE_DATA_DIR, candidates[0])
        else:
            return [], None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("listings", []), payload.get("scraped_at")
    except Exception:
        return [], None


def get_available_sample_areas() -> list[dict]:
    """Return list of areas available in sample_data/_index.json."""
    import os, json
    index_path = os.path.join(SAMPLE_DATA_DIR, "_index.json")
    if not os.path.exists(index_path):
        return []
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f).get("areas", [])
    except Exception:
        return []


def is_cloud_environment() -> bool:
    """Detect if running on Streamlit Cloud (or any non-local environment)."""
    import os
    # Streamlit Cloud sets this env variable
    return os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit" \
        or os.environ.get("IS_STREAMLIT_CLOUD", "").lower() == "true" \
        or "/mount/src/" in os.environ.get("HOME", "")

# ── Core helpers ───────────────────────────────────────────────────────────────

class MockResponse:
    """Mock standard Response object to format proxy-extracted payloads correctly."""
    def __init__(self, text: str, status_code: int):
        self.text = text
        self.status_code = status_code
        
    def json(self):
        import json
        return json.loads(self.text)

def safe_get(url: str, headers: dict, timeout: int = 15, use_proxy: bool = False):
    """
    Robust GET request wrapper.
    1. If use_proxy is True, route through a CORS proxy immediately.
    2. Try curl_cffi with Chrome impersonation directly.
    3. Fall back to standard requests directly.
    4. If direct requests return a 403 (Cloudflare block), automatically fall back to CORS proxies.
    """
    def route_through_proxy(target_url, proxy_index=0):
        encoded_url = urllib.parse.quote(target_url, safe="")
        proxies = [
            f"https://corsproxy.io/?{target_url}",
            f"https://api.allorigins.win/get?url={encoded_url}",
            f"https://api.codetabs.com/v1/proxy?quest={encoded_url}"
        ]
        return proxies[proxy_index]

    if use_proxy:
        for idx in range(3):
            try:
                proxy_url = route_through_proxy(url, idx)
                r = standard_requests.get(proxy_url, timeout=timeout)
                if r.status_code == 200:
                    if idx == 1:  # allorigins returns wrapped JSON
                        data = r.json()
                        contents = data.get("contents", "")
                        return MockResponse(contents, 200)
                    return r
            except Exception as e:
                st.session_state["last_fetch_error"] = f"Proxy fallback {idx} failed: {e}"
        raise Exception("All fallback proxies failed to retrieve the page data.")

    # 1. Direct attempt: curl_cffi
    try:
        from curl_cffi import requests as curl_requests
        
        # Ensure standard event loop is configured inside Streamlit worker threads
        try:
            import asyncio
            asyncio.get_event_loop()
        except RuntimeError:
            import asyncio
            asyncio.set_event_loop(asyncio.new_event_loop())

        r = curl_requests.get(url, headers=headers, timeout=timeout, impersonate="chrome")
        if r.status_code == 200:
            return r
        elif r.status_code == 403:
            st.session_state["last_fetch_error"] = "curl_cffi direct request blocked (403). Trying standard requests..."
    except Exception as e:
        st.session_state["last_fetch_error"] = f"curl_cffi direct request failed ({e}). Trying standard requests..."

    # 2. Direct attempt: standard requests
    try:
        r = standard_requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r
        elif r.status_code == 403:
            st.session_state["last_fetch_error"] = "Standard direct request was blocked with 403. Switching to proxy fallback..."
    except Exception as e:
        st.session_state["last_fetch_error"] = f"Standard direct request failed ({e}). Switching to proxy fallback..."

    # 3. Both direct attempts failed or got blocked -> Route through proxy
    st.info("🔄 Direct connection restricted by Cloudflare. Routing request through a secure web proxy...")
    return safe_get(url, headers, timeout=timeout, use_proxy=True)

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text

def extract_slug_from_url(url: str) -> str:
    url = url.strip()
    m = re.search(r"speedhome\.com/rent/([^/?#]+)", url)
    return m.group(1) if m else None

def detect_room_type(bedroom_count) -> str:
    try:
        n = int(bedroom_count)
        return "Studio" if n == 0 else f"{n}BR"
    except (TypeError, ValueError):
        return "Unknown"

def get_build_id() -> str | None:
    """Fetch the Next.js build ID from the SPEEDHOME homepage. Cached per session."""
    global _BUILD_ID
    if _BUILD_ID:
        return _BUILD_ID
    try:
        r = safe_get("https://speedhome.com/", headers=HEADERS_HTML, timeout=15)
        if r.status_code == 200:
            m = re.search(r'"buildId"\s*:\s*"([^"]+)"', r.text)
            if m:
                _BUILD_ID = m.group(1)
                return _BUILD_ID
            else:
                st.session_state["last_fetch_error"] = f"Failed to locate 'buildId' in page HTML. Status: {r.status_code}"
        else:
            st.session_state["last_fetch_error"] = f"Homepage request returned status code: {r.status_code}"
    except Exception as e:
        st.session_state["last_fetch_error"] = f"Failed to connect: {e}"
    return None

def fetch_next_data(slug: str, page: int = 1, build_id: str = None) -> dict | None:
    """
    Fetch listings via Next.js SSR data endpoint.
    Returns parsed pageProps dict or None on failure.
    """
    if not build_id:
        return None
    url = f"https://speedhome.com/_next/data/{build_id}/en/rent/{slug}.json"
    if page > 1:
        url += f"?page={page}"
    try:
        r = safe_get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json().get("pageProps", {})
        st.session_state["last_fetch_error"] = f"Listing API returned status code {r.status_code} on page {page}"
        return None
    except Exception as e:
        st.session_state["last_fetch_error"] = f"Listing request failed: {e}"
        return None

def normalize_listing(item: dict) -> dict:
    """Convert a raw API property object to our standard format."""
    ref  = item.get("ref", "")
    name = item.get("name", "")
    bedroom  = item.get("bedroom", 0)
    price    = item.get("price")
    sqft     = item.get("sqft")
    furnish_raw = item.get("furnishType", "")
    furnishing  = FURNISH_MAP.get(furnish_raw, furnish_raw.title() if furnish_raw else "Not Specified")

    addr_parts = [p.strip() for p in (item.get("address") or "").split(",") if p.strip() and not re.match(r"^\d", p.strip())]
    area = addr_parts[-2] if len(addr_parts) >= 2 else (addr_parts[-1] if addr_parts else name)

    # Correct URL format: https://speedhome.com/details/slugified-name-ref
    link = f"{BASE_URL}/details/{slugify(name)}-{ref}" if ref else ""

    return {
        "title": name,
        "area": area,
        "room_type": detect_room_type(bedroom),
        "furnishing": furnishing,
        "price_monthly": float(price) if price else None,
        "price_daily": None,
        "price_yearly": None,
        "sqft": float(sqft) if sqft else None,
        "rent_type": "Monthly",
        "link": link,
        "bedroom": bedroom,
        "bathroom": item.get("bathroom"),
        "carpark": item.get("carpark"),
        "no_deposit": item.get("noDeposit", False),
    }

def fetch_all_listings(slug: str, max_pages: int = 5, progress_cb=None) -> tuple[list[dict], list[str]]:
    """
    Fetch listings via _next/data SSR endpoint.
    On Streamlit Cloud (or when live fetch fails), automatically falls back
    to pre-scraped sample data from sample_data/<slug>.json.
    Returns (listings, errors).
    """
    all_listings = []
    errors = []

    # ── Try live fetch first ───────────────────────────────────────────────────
    if progress_cb:
        progress_cb("🔑 Getting site build ID...")

    build_id = get_build_id()

    if build_id:
        if progress_cb:
            progress_cb(f"✅ Build ID: {build_id}")

        page = 1
        while page <= max_pages:
            if progress_cb:
                progress_cb(f"📡 Fetching page {page}...")

            props = fetch_next_data(slug, page=page, build_id=build_id)

            if props is None:
                error_msg = f"❌ Page {page}: Failed to fetch — area slug may be incorrect or cloud IP is blocked."
                if "last_fetch_error" in st.session_state:
                    error_msg += f" (Detail: {st.session_state['last_fetch_error']})"
                errors.append(error_msg)
                break

            prop_list = props.get("propertyList", {})
            content   = prop_list.get("content", [])

            if not content:
                if page == 1:
                    errors.append(
                        f"⚠️ No listings found for **/{slug}/**. "
                        "Try a broader area name or paste the exact SPEEDHOME URL."
                    )
                break

            for item in content:
                all_listings.append(normalize_listing(item))

            total_pages    = prop_list.get("totalPages", 1)
            total_elements = prop_list.get("totalElements", len(all_listings))

            if progress_cb:
                progress_cb(f"✅ Got {len(all_listings)} of {total_elements} listings...")

            if page >= total_pages:
                break

            page += 1
            time.sleep(1.2 + random.uniform(0, 0.5))

        # Deduplicate
        seen, deduped = set(), []
        for item in all_listings:
            key = item.get("link") or item.get("title", "")
            if key not in seen:
                seen.add(key)
                deduped.append(item)

        if deduped:
            return deduped, errors

    else:
        error_msg = "❌ Could not fetch SPEEDHOME build ID."
        if "last_fetch_error" in st.session_state:
            error_msg += f" (Diagnostics: {st.session_state['last_fetch_error']})"
        errors.append(error_msg)

    # ── Fallback: load from sample_data/ ──────────────────────────────────────
    if progress_cb:
        progress_cb("📂 Loading cached sample data...")

    sample_listings, scraped_at = load_sample_data(slug)

    if sample_listings:
        scraped_date = scraped_at[:10] if scraped_at else "unknown date"
        errors.append(
            f"⚠️ **Live data unavailable** — showing cached sample data "
            f"({len(sample_listings)} listings, scraped {scraped_date}). "
            f"All analytics features are fully functional."
        )
        return sample_listings, errors

    # No live data AND no sample data
    errors.append(
        f"❌ No cached data available for **{slug}**. "
        f"Available areas: {', '.join(a['area_name'] for a in get_available_sample_areas()) or 'none'}."
    )
    return [], errors


def get_suggestions(query: str) -> list[str]:
    """Static suggestions from popular areas list."""
    q = query.lower()
    return [a for a in POPULAR_AREAS if q in a.lower()][:6]


# ── Analytics ──────────────────────────────────────────────────────────────────

def compute_price_summary(listings: list[dict]) -> pd.DataFrame:
    """Compute price summary grouped by room type."""
    rows = []
    for rent_type_label, price_key in [
        ("Monthly", "price_monthly"),
        ("Daily", "price_daily"),
        ("Yearly", "price_yearly"),
    ]:
        prices_by_room = {}
        sqft_by_room = {}
        for item in listings:
            price = item.get(price_key)
            if price is None or price <= 0:
                continue
            rt = item.get("room_type", "Unknown")
            prices_by_room.setdefault(rt, []).append(price)
            if item.get("sqft"):
                sqft_by_room.setdefault(rt, []).append(item["sqft"])

        for room, prices in prices_by_room.items():
            if not prices:
                continue
            try:
                mode_price = mode(prices)
            except Exception:
                mode_price = sorted(prices)[len(prices) // 2]
            sqfts = sqft_by_room.get(room, [])
            rows.append({
                "Rent Type": rent_type_label,
                "Room Type": room,
                "Count": len(prices),
                f"Avg Price (RM)": round(mean(prices), 0),
                f"Median (RM)": round(median(prices), 0),
                f"Mode (RM)": round(mode_price, 0),
                f"Fair Price (RM)": round((median(prices) * 0.6 + mean(prices) * 0.4), 0),
                f"Min (RM)": round(min(prices), 0),
                f"Max (RM)": round(max(prices), 0),
                "Avg Size (sqft)": round(mean(sqfts), 0) if sqfts else "N/A",
            })

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    order = ["Studio", "1BR", "2BR", "3BR", "4BR", "5BR", "Unknown"]
    df["_order"] = df["Room Type"].apply(lambda x: order.index(x) if x in order else 99)
    df = df.sort_values(["Rent Type", "_order"]).drop(columns=["_order"])
    return df.reset_index(drop=True)


def build_listings_df(listings: list[dict], area_name: str) -> pd.DataFrame:
    rows = []
    for item in listings:
        pm = item.get("price_monthly")
        pd_ = item.get("price_daily")
        py = item.get("price_yearly")
        rows.append({
            "Title": item.get("title", ""),
            "Area / Property": item.get("area", "") or area_name,
            "Room Type": item.get("room_type", ""),
            "Rent Type": item.get("rent_type", "Monthly"),
            "Price / Month (RM)": pm,
            "Price / Year (RM)": py if py else (round(pm * 12, 0) if pm else None),
            "Price / Day (RM)": pd_,
            "Size (sqft)": item.get("sqft"),
            "Furnishing": item.get("furnishing", ""),
            "Link": item.get("link", ""),
        })
    return pd.DataFrame(rows)


# ── Autocomplete suggestions ───────────────────────────────────────────────────

def get_suggestions(query: str) -> list[str]:
    q = query.lower()
    return [a for a in POPULAR_AREAS if q in a.lower()][:8]


# ── Download helpers ───────────────────────────────────────────────────────────

def to_excel(summary_df: pd.DataFrame, listings_df: pd.DataFrame, area: str) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Price Summary", index=False)
        listings_df.to_excel(writer, sheet_name="All Listings", index=False)
        # Metadata sheet
        meta = pd.DataFrame({
            "Field": ["Area", "Scraped At", "Total Listings", "Source"],
            "Value": [area, datetime.now().strftime("%Y-%m-%d %H:%M"), len(listings_df), "SPEEDHOME.com"],
        })
        meta.to_excel(writer, sheet_name="Metadata", index=False)
    return buf.getvalue()


def to_csv(listings_df: pd.DataFrame) -> bytes:
    return listings_df.to_csv(index=False).encode("utf-8")


# ── Auto Insights ──────────────────────────────────────────────────────────────

def generate_insights(listings, summary_df, area_name):
    insights = []
    if not listings or summary_df.empty:
        return insights
    monthly = summary_df[summary_df["Rent Type"] == "Monthly"]
    if monthly.empty:
        return insights
    total = len(listings)
    most_common = monthly.loc[monthly["Count"].idxmax()]
    insights.append(
        f"🏠 **{most_common['Room Type']}** is the most listed unit type "
        f"({int(most_common['Count'])} units, {int(most_common['Count']/total*100)}% of listings)."
    )
    cheapest = monthly.loc[monthly["Min (RM)"].idxmin()]
    insights.append(
        f"💰 **Cheapest entry point:** {cheapest['Room Type']} from RM {int(cheapest['Min (RM)']):,}/month."
    )
    monthly_sqft = monthly[monthly["Avg Size (sqft)"] != "N/A"].copy()
    if not monthly_sqft.empty:
        monthly_sqft = monthly_sqft.copy()
        monthly_sqft["ppsf"] = monthly_sqft["Avg Price (RM)"].astype(float) / monthly_sqft["Avg Size (sqft)"].astype(float)
        best = monthly_sqft.loc[monthly_sqft["ppsf"].idxmin()]
        insights.append(f"📐 **Best value per sqft:** {best['Room Type']} at RM {best['ppsf']:.2f}/sqft avg.")
    spread_pct = ((most_common["Max (RM)"] - most_common["Min (RM)"]) / most_common["Min (RM)"]) * 100
    insights.append(
        f"📈 **Price spread for {most_common['Room Type']}:** "
        f"RM {int(most_common['Min (RM)']):,} – RM {int(most_common['Max (RM)']):,} ({spread_pct:.0f}% range)."
    )
    furn_counts = {}
    for item in listings:
        f = item.get("furnishing", "Not Specified")
        furn_counts[f] = furn_counts.get(f, 0) + 1
    if furn_counts:
        top_furn = max(furn_counts, key=furn_counts.get)
        insights.append(
            f"🛋️ **{top_furn}** dominates ({furn_counts[top_furn]} of {total} units, {int(furn_counts[top_furn]/total*100)}%)."
        )
    avg_fair = monthly["Fair Price (RM)"].mean()
    avg_price = monthly["Avg Price (RM)"].mean()
    diff_pct = ((avg_price - avg_fair) / avg_fair) * 100
    if abs(diff_pct) > 5:
        direction = "above" if diff_pct > 0 else "below"
        insights.append(
            f"⚖️ **Market avg is {abs(diff_pct):.0f}% {direction} fair price** — room to negotiate below asking."
        )
    return insights


# ── Comparison Mode ────────────────────────────────────────────────────────────

def render_comparison(area_a, listings_a, area_b, listings_b):
    st.markdown('<div class="section-header">📊 Area Comparison</div>', unsafe_allow_html=True)
    summary_a = compute_price_summary(listings_a)
    summary_b = compute_price_summary(listings_b)
    monthly_a = summary_a[summary_a["Rent Type"] == "Monthly"] if not summary_a.empty else pd.DataFrame()
    monthly_b = summary_b[summary_b["Rent Type"] == "Monthly"] if not summary_b.empty else pd.DataFrame()

    col_a, col_b = st.columns(2)
    def _metrics(col, name, listings, mdf):
        with col:
            st.markdown(f"**{name}** — {len(listings)} listings")
            if mdf.empty:
                st.info("No data")
                return
            m1, m2 = st.columns(2)
            m1.metric("Avg Price", f"RM {int(mdf['Avg Price (RM)'].mean()):,}")
            m2.metric("Median", f"RM {int(mdf['Median (RM)'].mean()):,}")
            m3, m4 = st.columns(2)
            m3.metric("Most Listed", mdf.loc[mdf["Count"].idxmax(), "Room Type"])
            m4.metric("Starts From", f"RM {int(mdf['Min (RM)'].min()):,}/mo")
    _metrics(col_a, area_a, listings_a, monthly_a)
    _metrics(col_b, area_b, listings_b, monthly_b)

    room_order = ["Studio", "1BR", "2BR", "3BR", "4BR", "5BR"]
    all_rooms = sorted(
        set(monthly_a["Room Type"].tolist() + monthly_b["Room Type"].tolist()),
        key=lambda x: room_order.index(x) if x in room_order else 99,
    )
    comp_rows = []
    for room in all_rooms:
        ra = monthly_a[monthly_a["Room Type"] == room]
        rb = monthly_b[monthly_b["Room Type"] == room]
        avg_a = int(ra["Avg Price (RM)"].values[0]) if not ra.empty else None
        avg_b = int(rb["Avg Price (RM)"].values[0]) if not rb.empty else None
        cnt_a = int(ra["Count"].values[0]) if not ra.empty else 0
        cnt_b = int(rb["Count"].values[0]) if not rb.empty else 0
        if avg_a and avg_b:
            diff = avg_b - avg_a
            diff_str = f"+RM {diff:,}" if diff > 0 else f"-RM {abs(diff):,}"
            cheaper = area_a if avg_a < avg_b else area_b
        else:
            diff_str, cheaper = "N/A", "N/A"
        comp_rows.append({
            "Room Type": room,
            f"{area_a} Avg": f"RM {avg_a:,}" if avg_a else "-",
            f"{area_a} Units": cnt_a,
            f"{area_b} Avg": f"RM {avg_b:,}" if avg_b else "-",
            f"{area_b} Units": cnt_b,
            "Difference": diff_str,
            "Cheaper": cheaper,
        })
    if comp_rows:
        st.markdown("**Price by Room Type**")
        comp_df = pd.DataFrame(comp_rows)
        # Using AgGrid for visual uniformity in comparison view
        gb_comp = GridOptionsBuilder.from_dataframe(comp_df)
        gb_comp.configure_default_column(sortable=True, filter=True, resizable=True)
        grid_options_comp = gb_comp.build()
        AgGrid(
            comp_df,
            gridOptions=grid_options_comp,
            use_container_width=True,
            theme="alpine",
            height=250
        )

    chart_data = {}
    for room in all_rooms:
        ra = monthly_a[monthly_a["Room Type"] == room]
        rb = monthly_b[monthly_b["Room Type"] == room]
        if not ra.empty:
            chart_data.setdefault(area_a, {})[room] = ra["Avg Price (RM)"].values[0]
        if not rb.empty:
            chart_data.setdefault(area_b, {})[room] = rb["Avg Price (RM)"].values[0]
    if chart_data:
        st.markdown("**Avg Monthly Rent — Side by Side**")
        st.bar_chart(pd.DataFrame(chart_data, index=all_rooms).fillna(0))


# ── UI helpers ─────────────────────────────────────────────────────────────────

def badge(label: str, category: str) -> str:
    cls_map = {
        "Monthly": "badge-monthly", "Daily": "badge-daily", "Yearly": "badge-yearly",
        "Fully Furnished": "badge-ff", "Partially Furnished": "badge-pf",
        "Unfurnished": "badge-unf",
    }
    cls = cls_map.get(label, "badge-monthly")
    return f'<span class="badge {cls}">{label}</span>'


def fmt_rm(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    return f"RM {int(val):,}"


def render_summary_table(df: pd.DataFrame):
    """Render price summary as styled HTML table."""
    if df.empty:
        st.warning("No price data available to summarize.")
        return

    for rent_type in ["Monthly", "Daily", "Yearly"]:
        sub = df[df["Rent Type"] == rent_type]
        if sub.empty:
            st.info(f"No **{rent_type}** rental listings found for this area.")
            continue

        st.markdown(f'<div class="section-header">{rent_type} Rentals — Price Summary</div>', unsafe_allow_html=True)

        cols = st.columns(len(sub))
        for col, (_, row) in zip(cols, sub.iterrows()):
            with col:
                st.markdown(f"""
<div class="metric-card">
  <div class="metric-label">{row['Room Type']}</div>
  <div class="metric-value">{fmt_rm(row.get('Avg Price (RM)'))}</div>
  <div class="metric-sub">avg/month · {int(row['Count'])} units</div>
  <hr style="margin:8px 0;border:none;border-top:1px solid #eee">
  <div style="display:flex;justify-content:space-between;font-size:.78rem;color:#555;">
    <span>Median</span><b>{fmt_rm(row.get('Median (RM)'))}</b>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:.78rem;color:#555;">
    <span>Mode</span><b>{fmt_rm(row.get('Mode (RM)'))}</b>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:.78rem;color:#555;">
    <span>Fair Price</span><b>{fmt_rm(row.get('Fair Price (RM)'))}</b>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:.78rem;color:#555;">
    <span>Range</span><b>{fmt_rm(row.get('Min (RM)'))} – {fmt_rm(row.get('Max (RM)'))}</b>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:.78rem;color:#aaa;margin-top:4px;">
    <span>Avg Size</span><b>{row.get('Avg Size (sqft)', 'N/A')} sqft</b>
  </div>
</div>
""", unsafe_allow_html=True)


def render_chart(df: pd.DataFrame):
    """Bar chart of average prices by room type, ordered Studio → 1BR → 2BR → 3BR → 4BR."""
    sub = df[df["Rent Type"] == "Monthly"].copy()
    if sub.empty or "Avg Price (RM)" not in sub.columns:
        return
    order = ["Studio", "1BR", "2BR", "3BR", "4BR", "5BR", "Unknown"]
    sub["_order"] = sub["Room Type"].apply(lambda x: order.index(x) if x in order else 99)
    sub = sub.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)
    # Use a list-indexed DataFrame to force st.bar_chart to respect insertion order
    chart_data = pd.DataFrame(
        {"Avg Price (RM)": sub["Avg Price (RM)"].values},
        index=pd.CategoricalIndex(sub["Room Type"].values, categories=sub["Room Type"].values, ordered=True)
    )
    st.markdown('<div class="section-header">Average Monthly Rent by Room Type</div>', unsafe_allow_html=True)
    st.bar_chart(chart_data, color="#FF5A1F")


# ── Main UI ────────────────────────────────────────────────────────────────────

def main():
    st.markdown(
        """
        <div class="app-header">
          <div class="app-header-icon">🏠</div>
          <div>
            <div class="app-header-title">SPEEDHOME Price Intelligence</div>
            <div class="app-header-sub">Rental market analytics · Malaysia</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Input Section ──────────────────────────────────────────────────────────
    # State init
    if "typed_query" not in st.session_state:
        st.session_state["typed_query"] = ""
    if "do_search" not in st.session_state:
        st.session_state["do_search"] = False

    def _on_type():
        st.session_state["typed_query"] = st.session_state.get("_type_shadow", "")

    def _on_enter():
        st.session_state["typed_query"] = st.session_state.get("_type_shadow", "")
        st.session_state["do_search"] = True

    typed = st.session_state["typed_query"]

    # Build dropdown options from what user has typed
    if typed and not typed.startswith("http") and len(typed) >= 1:
        suggestions = get_suggestions(typed)
        options = [typed] + [s for s in suggestions if s.lower() != typed.lower()]
    elif typed.startswith("http"):
        options = [typed]
    else:
        options = [""]

    col_inp, col_btn = st.columns([4, 1])

    with col_inp:
        st.text_input(
            "Search",
            value=typed,
            placeholder="Type area name or paste SPEEDHOME URL and press Enter...",
            label_visibility="collapsed",
            key="_type_shadow",
            on_change=_on_enter,
        )

        if len(options) > 1:
            st.markdown("<small style='color:#888'>Suggestions — click to search instantly:</small>", unsafe_allow_html=True)
            sug_cols = st.columns(min(len(options) - 1, 4))
            for i, sug in enumerate(options[1:5]):
                if sug_cols[i % 4].button(sug, key=f"sug_{i}"):
                    st.session_state["typed_query"] = sug
                    st.session_state["_type_shadow"] = sug
                    st.session_state["do_search"] = True
                    st.rerun()

    with col_btn:
        search_clicked = st.button("🔍 Search", use_container_width=True, type="primary")

    query = st.session_state["typed_query"]

    # Show different info note depending on environment
    available_areas = get_available_sample_areas()
    if available_areas:
        area_names = ", ".join(a["area_name"] for a in available_areas[:5])
        if len(available_areas) > 5:
            area_names += f" +{len(available_areas) - 5} more"
        st.markdown(
            f'<div class="info-note">ℹ️ Live data is fetched directly from SPEEDHOME.com when available. '
            f'On cloud deployment, cached sample data is used as fallback. '
            f'Pre-loaded areas: <b>{area_names}</b>. Requests are rate-limited and robots.txt is respected.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="info-note">ℹ️ Data is scraped directly from public SPEEDHOME.com listings in real-time. '
            'Requests are rate-limited and robots.txt is respected.</div>',
            unsafe_allow_html=True,
        )

    should_search = (search_clicked or st.session_state.pop("do_search", False)) and query

    with st.sidebar:
        st.header("⚙️ Settings")
        max_pages = st.slider("Max pages to fetch", 1, 10, 3)
        st.caption("More pages = more data but slower.")
        st.markdown("---")
        st.subheader("🔀 Compare Areas")
        compare_area = st.text_input(
            "Compare with another area",
            placeholder="e.g. Bangsar",
            key="compare_input",
            help="First search an area above, then enter a second area here to compare.",
            on_change=lambda: st.session_state.update({"do_compare": True}),
        )
        compare_clicked = st.button("Compare", use_container_width=True, key="compare_btn")

    if should_search:
        if query.startswith("http"):
            slug = extract_slug_from_url(query)
            area_name = slug.replace("-", " ").title() if slug else query
        else:
            slug = slugify(query)
            area_name = query.strip().title()

        if not slug:
            st.error("Could not parse URL. Please enter a valid SPEEDHOME URL or area name.")
        else:
            status_ph = st.empty()
            prog = st.progress(0)
            with st.spinner(f"Fetching listings for **{area_name}**..."):
                listings, fetch_errors = fetch_all_listings(slug, max_pages=max_pages, progress_cb=lambda m: status_ph.info(m))
            prog.empty()
            status_ph.empty()

            st.session_state["results"] = {
                "listings": listings,
                "area_name": area_name,
                "fetch_errors": fetch_errors,
            }
            st.session_state.pop("compare_results", None)

    results = st.session_state.get("results")
    if not results:
        return

    listings    = results["listings"]
    area_name   = results["area_name"]
    fetch_errors = results["fetch_errors"]

    if fetch_errors:
        with st.expander("🔍 Fetch Diagnostics", expanded=not listings):
            for err in fetch_errors:
                st.markdown(err)

    if not listings:
        st.error(f"**No listings retrieved for '{area_name}'.**")
        st.info("💡 Try pasting the exact SPEEDHOME URL, e.g. https://speedhome.com/rent/mont-kiara")
        return

    st.success(f"Found **{len(listings)}** listings for **{area_name}**")

    summary_df  = compute_price_summary(listings)
    listings_df = build_listings_df(listings, area_name)

    is_comparing = "compare_results" in st.session_state or (compare_clicked and compare_area.strip()) or (st.session_state.get("do_compare") and compare_area.strip())
    if not is_comparing:
        insights = generate_insights(listings, summary_df, area_name)
        if insights:
            with st.expander("💡 Auto Insights", expanded=True):
                for insight in insights:
                    st.markdown(f"- {insight}")

    if (compare_clicked or st.session_state.pop("do_compare", False)) and compare_area.strip():
        compare_slug = slugify(compare_area.strip())
        compare_name = compare_area.strip().title()
        with st.spinner(f"Fetching listings for **{compare_name}**..."):
            compare_listings, _ = fetch_all_listings(compare_slug, max_pages=max_pages)
        if compare_listings:
            st.session_state["compare_results"] = {"listings": compare_listings, "name": compare_name}
        else:
            st.warning(f"No listings found for **{compare_name}**.")
            st.session_state.pop("compare_results", None)

    if "compare_results" in st.session_state:
        cr = st.session_state["compare_results"]
        render_comparison(area_name, listings, cr["name"], cr["listings"])
        return

    if not summary_df.empty:
        render_chart(summary_df)

    render_summary_table(summary_df)

    # ── Full Listings Table with Direct Links ─────────────────────────────────
    st.markdown('<div class="section-header">All Listings</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    with f1:
        sel_room = st.selectbox("Filter by Room Type", ["All"] + sorted(listings_df["Room Type"].dropna().unique().tolist()))
    with f2:
        sel_furn = st.selectbox("Filter by Furnishing", ["All"] + sorted(listings_df["Furnishing"].dropna().unique().tolist()))
    with f3:
        sel_rent = st.selectbox("Filter by Rent Type", ["All"] + sorted(listings_df["Rent Type"].dropna().unique().tolist()))

    filtered = listings_df.copy()
    if sel_room != "All": filtered = filtered[filtered["Room Type"] == sel_room]
    if sel_furn != "All": filtered = filtered[filtered["Furnishing"] == sel_furn]
    if sel_rent != "All": filtered = filtered[filtered["Rent Type"] == sel_rent]

    # Convert Link values to strings to prevent formatting errors
    filtered["Link"] = filtered["Link"].fillna("").astype(str)

    st.caption("💡 *Click directly on **Open Listing ↗** in the View Link column below to open it instantly. You can still sort, filter, and resize columns!*")

    # Build GridOptions for AgGrid
    gb = GridOptionsBuilder.from_dataframe(filtered)

    # Define custom JavaScript to render the URL column as a true 1-click clickable anchor tag
    link_renderer = JsCode("""
    class UrlCellRenderer {
        init(params) {
            this.eGui = document.createElement('a');
            if (params.value && params.value !== "") {
                this.eGui.innerText = 'Open Listing ↗';
                this.eGui.setAttribute('href', params.value);
                this.eGui.setAttribute('style', "color: #FF5A1F; font-weight: 600; text-decoration: none; cursor: pointer;");
                this.eGui.setAttribute('target', "_blank");
            } else {
                this.eGui.innerText = '-';
            }
        }
        getGui() {
            return this.eGui;
        }
    }
    """)

    # Explicit column widths so nothing truncates on mobile
    gb.configure_column("Title",              minWidth=160, width=180)
    gb.configure_column("Area / Property",    minWidth=140, width=160)
    gb.configure_column("Room Type",          minWidth=90,  width=100)
    gb.configure_column("Rent Type",          minWidth=90,  width=100)
    gb.configure_column("Price / Month (RM)", minWidth=120, width=130)
    gb.configure_column("Price / Year (RM)",  minWidth=120, width=130)
    gb.configure_column("Price / Day (RM)",   minWidth=110, width=120)
    gb.configure_column("Size (sqft)",        minWidth=100, width=110)
    gb.configure_column("Furnishing",         minWidth=150, width=170)
    gb.configure_column("Link",               minWidth=130, width=140,
                        headerName="View Link", cellRenderer=link_renderer, pinned="right")

    gb.configure_default_column(sortable=True, filter=True, resizable=True, suppressSizeToFit=True)

    # Enable horizontal scroll and suppress auto column fit to viewport width
    gb.configure_grid_options(
        suppressHorizontalScroll=False,
        alwaysShowHorizontalScroll=True,
        suppressColumnVirtualisation=False,
    )

    grid_options = gb.build()

    # Render interactive table with streamlit-aggrid
    AgGrid(
        filtered,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        theme="alpine",
        height=420,
        fit_columns_on_grid_load=False,   # Critical: prevents columns squishing to fit viewport
    )

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Download Data</div>', unsafe_allow_html=True)
    date_str  = datetime.now().strftime("%Y%m%d")
    file_slug = area_name.replace(" ", "_")
    d1, d2 = st.columns(2)
    with d1:
        st.download_button("📥 Download Excel (.xlsx)", data=to_excel(summary_df, listings_df, area_name),
            file_name=f"SPEEDHOME_{file_slug}_{date_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with d2:
        st.download_button("📥 Download CSV", data=to_csv(listings_df),
            file_name=f"SPEEDHOME_{file_slug}_{date_str}.csv", mime="text/csv", use_container_width=True)

    # ── ROI Calculator ────────────────────────────────────────────────────────
    with st.expander("💡 Quick ROI Calculator", expanded=False):
        rc1, rc2, rc3 = st.columns(3)
        with rc1: purchase_price = st.number_input("Purchase Price (RM)", value=600000, step=10000)
        with rc2: monthly_rent   = st.number_input("Monthly Rent (RM)", value=2500, step=100)
        with rc3: expenses_pct   = st.slider("Annual Expenses (% of price)", 0.0, 5.0, 1.5, 0.1)
        annual_rent = monthly_rent * 12
        net_income  = annual_rent - purchase_price * (expenses_pct / 100)
        r1, r2, r3 = st.columns(3)
        r1.metric("Gross Yield", f"{(annual_rent/purchase_price*100):.2f}%")
        r2.metric("Net Yield",   f"{(net_income/purchase_price*100):.2f}%")
        r3.metric("Annual Net Income", f"RM {net_income:,.0f}")


if __name__ == "__main__":
    main()