import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
import time
import io
from datetime import datetime
from statistics import median, mode, mean
from urllib.parse import quote, urljoin
import random

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
/* Global */
html, body, [data-testid="stAppViewContainer"] { background: #f7f9fc; }
h1 { font-size: 1.8rem !important; }

/* Cards */
.metric-card {
    background: white;
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    text-align: center;
}
.metric-label { font-size: .75rem; color: #888; text-transform: uppercase; letter-spacing:.5px; margin-bottom:4px; }
.metric-value { font-size: 1.5rem; font-weight: 700; color: #1a1a2e; }
.metric-sub   { font-size: .78rem; color: #555; margin-top:2px; }

/* Badge */
.badge {
    display:inline-block; padding:2px 9px; border-radius:20px;
    font-size:.72rem; font-weight:600;
}
.badge-monthly  { background:#e8f4fd; color:#1565c0; }
.badge-daily    { background:#fce8e8; color:#c62828; }
.badge-yearly   { background:#e8f5e9; color:#2e7d32; }
.badge-ff       { background:#e8f4fd; color:#1565c0; }
.badge-pf       { background:#fff3e0; color:#e65100; }
.badge-unf      { background:#f3e5f5; color:#6a1b9a; }

/* Table tweaks */
.stDataFrame thead th { background:#1a1a2e !important; color:white !important; }
div[data-testid="stDataFrame"] { border-radius:10px; overflow:hidden; }

/* Search box */
.search-container input { border-radius: 8px !important; }

/* Section header */
.section-header {
    font-size:1.1rem; font-weight:700; color:#1a1a2e;
    border-left: 4px solid #e63946; padding-left:10px;
    margin: 22px 0 12px;
}

/* Alert */
.info-note {
    background:#fff8e1; border-left:4px solid #ffc107;
    padding: 10px 14px; border-radius:6px; font-size:.85rem; color:#555;
    margin-bottom:12px;
}

/* Spinner overlay */
.loading-text { font-size: 1rem; color: #555; margin-top: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
BASE_URL = "https://speedhome.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://speedhome.com/",
}

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
]

AREA_TO_SLUG = {
    name: name.lower().replace(" ", "-") for name in POPULAR_AREAS
}

# ── Scraping helpers ───────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text

def extract_slug_from_url(url: str) -> str:
    url = url.strip()
    m = re.search(r"speedhome\.com/rent/([^/?#]+)", url)
    if m:
        return m.group(1)
    return None

def build_rent_url(slug: str, page: int = 1) -> str:
    if page == 1:
        return f"{BASE_URL}/rent/{slug}"
    return f"{BASE_URL}/rent/{slug}?page={page}"

def safe_get(url: str, retries: int = 3) -> requests.Response | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                time.sleep(5 + attempt * 3)
        except requests.RequestException:
            time.sleep(2)
        time.sleep(1.2 + random.random())
    return None

def parse_price(text: str) -> float | None:
    if not text:
        return None
    text = text.replace(",", "").replace("RM", "").strip()
    m = re.search(r"[\d.]+", text)
    if m:
        try:
            return float(m.group())
        except ValueError:
            pass
    return None

def parse_sqft(text: str) -> float | None:
    if not text:
        return None
    m = re.search(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft)", text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return None

def detect_room_type(title: str, beds: str) -> str:
    t = (title + " " + (beds or "")).lower()
    if "studio" in t:
        return "Studio"
    for n in ["1", "2", "3", "4", "5"]:
        if (
            f"{n} bed" in t
            or f"{n}br" in t
            or f"{n} br" in t
            or f"{n} room" in t
            or f"{n}+1" in t
        ):
            return f"{n}BR"
    return "Unknown"

def detect_furnishing(title: str, desc: str = "") -> str:
    t = (title + " " + (desc or "")).lower()
    if "fully furnished" in t or "full furnished" in t:
        return "Fully Furnished"
    if "partially furnished" in t or "partial furnished" in t or "semi furnished" in t:
        return "Partially Furnished"
    if "unfurnished" in t or "bare" in t:
        return "Unfurnished"
    return "Not Specified"

def parse_listing_card(card, base_url=BASE_URL) -> dict | None:
    """Extract data from a single listing card element."""
    try:
        # Title
        title_el = (
            card.select_one("h2")
            or card.select_one("h3")
            or card.select_one(".listing-title")
            or card.select_one("[class*='title']")
            or card.select_one("a[href*='/rent/']")
        )
        title = title_el.get_text(strip=True) if title_el else ""

        # Link
        link_el = card.select_one("a[href*='/rent/']") or card.select_one("a")
        href = link_el["href"] if link_el and link_el.get("href") else ""
        if href and not href.startswith("http"):
            href = urljoin(base_url, href)

        # Price — look for RM pattern anywhere in card text
        card_text = card.get_text(" ", strip=True)
        price = None
        price_text = ""
        price_m = re.search(
            r"RM\s*([\d,]+(?:\.\d+)?)\s*(?:/\s*(?:month|mo|mth|year|yr|day|night))?",
            card_text, re.IGNORECASE
        )
        if price_m:
            price = float(price_m.group(1).replace(",", ""))
            price_text = price_m.group(0)

        # Detect rent type from surrounding text
        rent_type = "Monthly"
        lower_text = card_text.lower()
        if any(k in lower_text for k in ["per day", "/day", "nightly", "daily"]):
            rent_type = "Daily"
        elif any(k in lower_text for k in ["per year", "/year", "annually", "yearly"]):
            rent_type = "Yearly"

        # Beds / sqft
        beds_m = re.search(r"(\d+)\s*(?:bed|br|room)", card_text, re.IGNORECASE)
        beds = beds_m.group(0) if beds_m else ""

        sqft_m = re.search(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft)", card_text, re.IGNORECASE)
        sqft = float(sqft_m.group(1).replace(",", "")) if sqft_m else None

        # Room type & furnishing
        room_type = detect_room_type(title, beds)
        furnishing = detect_furnishing(title, card_text)

        # Area
        area_el = card.select_one("[class*='location']") or card.select_one("[class*='area']")
        area = area_el.get_text(strip=True) if area_el else ""

        if not title and not price:
            return None

        return {
            "title": title,
            "area": area,
            "room_type": room_type,
            "furnishing": furnishing,
            "price_monthly": price if rent_type == "Monthly" else None,
            "price_daily": price if rent_type == "Daily" else None,
            "price_yearly": price if rent_type == "Yearly" else None,
            "sqft": sqft,
            "rent_type": rent_type,
            "link": href,
            "_raw_price_text": price_text,
        }
    except Exception:
        return None


def extract_from_next_data(soup) -> list[dict]:
    """Try to pull listings from Next.js __NEXT_DATA__ JSON blob."""
    listings = []
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script:
        return listings
    try:
        data = json.loads(script.string)
        # Walk the JSON tree looking for arrays that look like listings
        raw_str = json.dumps(data)
        # Look for objects with price/rent fields
        # Common SPEEDHOME keys
        for key in ["listings", "properties", "units", "items", "data", "results"]:
            found = _find_key(data, key)
            if found and isinstance(found, list) and len(found) > 0:
                for item in found:
                    if isinstance(item, dict):
                        listing = _normalize_json_listing(item)
                        if listing:
                            listings.append(listing)
                if listings:
                    break
    except Exception:
        pass
    return listings


def _find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            result = _find_key(v, key)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _find_key(item, key)
            if result is not None:
                return result
    return None


def _normalize_json_listing(item: dict) -> dict | None:
    """Try common field names to normalize a JSON listing object."""
    title = (
        item.get("title") or item.get("name") or item.get("propertyName")
        or item.get("listing_title") or ""
    )
    price_raw = (
        item.get("price") or item.get("rental_price") or item.get("asking_price")
        or item.get("monthly_price") or item.get("rent") or 0
    )
    try:
        price = float(str(price_raw).replace(",", "").replace("RM", "").strip())
    except Exception:
        price = None

    sqft_raw = (
        item.get("size") or item.get("sqft") or item.get("floor_area")
        or item.get("built_up") or None
    )
    try:
        sqft = float(str(sqft_raw).replace(",", "").strip()) if sqft_raw else None
    except Exception:
        sqft = None

    beds_raw = str(
        item.get("bedrooms") or item.get("bedroom") or item.get("beds")
        or item.get("room") or ""
    )
    furnishing = item.get("furnished") or item.get("furnishing") or ""
    area = (
        item.get("area") or item.get("location") or item.get("district")
        or item.get("neighborhood") or ""
    )
    slug = item.get("slug") or item.get("url") or item.get("path") or ""
    link = f"{BASE_URL}/rent/{slug}" if slug and not slug.startswith("http") else slug

    if not title and not price:
        return None

    room_type = detect_room_type(title, beds_raw)
    furn_label = detect_furnishing(title, furnishing)

    return {
        "title": str(title),
        "area": str(area),
        "room_type": room_type,
        "furnishing": furn_label,
        "price_monthly": price,
        "price_daily": None,
        "price_yearly": None,
        "sqft": sqft,
        "rent_type": "Monthly",
        "link": link,
        "_raw_price_text": f"RM {price}",
    }


def scrape_page(url: str) -> tuple[list[dict], str | None]:
    """Scrape one page, return (listings, next_page_url)."""
    resp = safe_get(url)
    if not resp:
        return [], None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 1) Try Next.js data first
    listings = extract_from_next_data(soup)

    # 2) Fall back to HTML card parsing
    if not listings:
        selectors = [
            "[class*='listing-card']",
            "[class*='property-card']",
            "[class*='PropertyCard']",
            "[class*='ListingCard']",
            "[class*='listing-item']",
            "[class*='property-item']",
            "article",
        ]
        cards = []
        for sel in selectors:
            cards = soup.select(sel)
            if cards:
                break

        for card in cards:
            item = parse_listing_card(card)
            if item:
                listings.append(item)

    # 3) Find next page link
    next_url = None
    next_el = (
        soup.select_one("a[rel='next']")
        or soup.select_one("[class*='next'] a")
        or soup.select_one("[aria-label='Next page']")
        or soup.select_one("[aria-label='next']")
    )
    if next_el and next_el.get("href"):
        href = next_el["href"]
        next_url = href if href.startswith("http") else urljoin(BASE_URL, href)

    # Also check for numbered pagination
    if not next_url:
        page_m = re.search(r"[?&]page=(\d+)", url)
        current_page = int(page_m.group(1)) if page_m else 1
        # Check if there are more pages via meta or script hints
        total_hint = re.search(r'"totalPage[s]?":\s*(\d+)', resp.text)
        if total_hint and current_page < int(total_hint.group(1)):
            sep = "&" if "?" in url else "?"
            next_url = f"{url.split('?')[0]}?page={current_page + 1}"

    return listings, next_url


def fetch_all_listings(slug: str, max_pages: int = 5, progress_cb=None) -> list[dict]:
    """Fetch up to max_pages pages of listings for a slug."""
    all_listings = []
    url = build_rent_url(slug, 1)
    seen_urls = set()

    for page_num in range(1, max_pages + 1):
        if url in seen_urls:
            break
        seen_urls.add(url)

        if progress_cb:
            progress_cb(f"Fetching page {page_num}...")

        listings, next_url = scrape_page(url)
        all_listings.extend(listings)

        if not next_url or not listings:
            break

        url = next_url
        time.sleep(1.5 + random.uniform(0, 0.8))  # polite delay

    # Deduplicate by link
    seen_links = set()
    deduped = []
    for item in all_listings:
        key = item.get("link") or item.get("title", "")
        if key not in seen_links:
            seen_links.add(key)
            deduped.append(item)

    return deduped


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
    """Bar chart of average prices by room type."""
    sub = df[df["Rent Type"] == "Monthly"].copy()
    if sub.empty or "Avg Price (RM)" not in sub.columns:
        return
    st.markdown('<div class="section-header">Average Monthly Rent by Room Type</div>', unsafe_allow_html=True)
    chart_data = sub.set_index("Room Type")["Avg Price (RM)"]
    st.bar_chart(chart_data, color="#e63946")


# ── Main UI ────────────────────────────────────────────────────────────────────

def main():
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">
          <span style="font-size:2.2rem">🏠</span>
          <div>
            <h1 style="margin:0;color:#1a1a2e;">SPEEDHOME Price Intelligence</h1>
            <p style="margin:0;color:#777;font-size:.9rem;">Real-time rental market data from SPEEDHOME.com · Malaysia</p>
          </div>
        </div>
        <hr style="margin:12px 0 20px;border:none;border-top:2px solid #e63946;opacity:.4">
        """,
        unsafe_allow_html=True,
    )

    # ── Input Section ──────────────────────────────────────────────────────────
    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        query = st.text_input(
            "Search area / apartment name or paste SPEEDHOME URL",
            placeholder="e.g. Mont Kiara  or  https://speedhome.com/rent/mont-kiara",
            label_visibility="collapsed",
            key="main_query",
        )

    with col_btn:
        search_clicked = st.button("🔍 Search", use_container_width=True, type="primary")

    # Autocomplete suggestions
    if query and not query.startswith("http") and len(query) >= 2:
        suggestions = get_suggestions(query)
        if suggestions:
            st.markdown(
                "<small style='color:#888'>Suggestions (click to copy):</small>",
                unsafe_allow_html=True,
            )
            sug_cols = st.columns(min(len(suggestions), 4))
            for i, sug in enumerate(suggestions[:4]):
                if sug_cols[i % 4].button(sug, key=f"sug_{i}"):
                    st.session_state["main_query"] = sug
                    st.rerun()

    st.markdown(
        '<div class="info-note">ℹ️ Data is scraped directly from public SPEEDHOME.com listings in real-time. '
        'Requests are rate-limited and robots.txt is respected.</div>',
        unsafe_allow_html=True,
    )

    # ── Trigger search ─────────────────────────────────────────────────────────
    if search_clicked and query:
        # Determine slug
        if query.startswith("http"):
            slug = extract_slug_from_url(query)
            area_name = slug.replace("-", " ").title() if slug else query
        else:
            slug = slugify(query)
            area_name = query.strip().title()

        if not slug:
            st.error("Could not parse URL. Please enter a valid SPEEDHOME URL or area name.")
            return

        # Max pages control in sidebar
        with st.sidebar:
            st.header("Settings")
            max_pages = st.slider("Max pages to fetch", 1, 10, 3)
            st.caption("More pages = more data but slower. Start with 3.")

        status_placeholder = st.empty()
        progress_bar = st.progress(0)

        def update_progress(msg):
            status_placeholder.info(msg)

        with st.spinner(f"Fetching listings for **{area_name}**..."):
            listings = fetch_all_listings(
                slug,
                max_pages=max_pages,
                progress_cb=update_progress,
            )

        progress_bar.empty()
        status_placeholder.empty()

        if not listings:
            st.error(
                f"No listings found for **{area_name}**. "
                "This could mean the area has no active listings, "
                "the page uses heavy JavaScript rendering, or the slug is incorrect.\n\n"
                "Try pasting the exact SPEEDHOME URL instead."
            )
            return

        # ── Results Header ─────────────────────────────────────────────────────
        st.success(f"Found **{len(listings)}** listings for **{area_name}**")

        summary_df = compute_price_summary(listings)
        listings_df = build_listings_df(listings, area_name)

        # ── Price Summary Cards ────────────────────────────────────────────────
        render_summary_table(summary_df)

        # ── Chart ─────────────────────────────────────────────────────────────
        if not summary_df.empty:
            render_chart(summary_df)

        # ── Full Listings Table ────────────────────────────────────────────────
        st.markdown('<div class="section-header">All Listings</div>', unsafe_allow_html=True)

        # Filters
        f1, f2, f3 = st.columns(3)
        with f1:
            room_opts = ["All"] + sorted(listings_df["Room Type"].dropna().unique().tolist())
            sel_room = st.selectbox("Filter by Room Type", room_opts)
        with f2:
            furn_opts = ["All"] + sorted(listings_df["Furnishing"].dropna().unique().tolist())
            sel_furn = st.selectbox("Filter by Furnishing", furn_opts)
        with f3:
            rent_opts = ["All"] + sorted(listings_df["Rent Type"].dropna().unique().tolist())
            sel_rent = st.selectbox("Filter by Rent Type", rent_opts)

        filtered = listings_df.copy()
        if sel_room != "All":
            filtered = filtered[filtered["Room Type"] == sel_room]
        if sel_furn != "All":
            filtered = filtered[filtered["Furnishing"] == sel_furn]
        if sel_rent != "All":
            filtered = filtered[filtered["Rent Type"] == sel_rent]

        # Render table with clickable links
        display_df = filtered.copy()
        if "Link" in display_df.columns:
            display_df["Link"] = display_df["Link"].apply(
                lambda x: f'<a href="{x}" target="_blank">View ↗</a>' if x else ""
            )

        st.dataframe(
            filtered.drop(columns=["Link"] if "Link" in filtered.columns else []),
            use_container_width=True,
            height=420,
        )

        # Show link column separately as clickable
        if "Link" in filtered.columns and filtered["Link"].notna().any():
            st.markdown(
                "<small style='color:#888'>Listing links (click to verify on SPEEDHOME):</small>",
                unsafe_allow_html=True
            )
            for _, row in filtered[["Title", "Link"]].head(20).iterrows():
                if row["Link"]:
                    st.markdown(f"- [{row['Title'][:60]}...]({row['Link']})")

        # ── Downloads ─────────────────────────────────────────────────────────
        st.markdown('<div class="section-header">Download Data</div>', unsafe_allow_html=True)
        date_str = datetime.now().strftime("%Y%m%d")
        file_slug = area_name.replace(" ", "_")
        d1, d2 = st.columns(2)

        with d1:
            xlsx_bytes = to_excel(summary_df, listings_df, area_name)
            st.download_button(
                "📥 Download Excel (.xlsx)",
                data=xlsx_bytes,
                file_name=f"SPEEDHOME_{file_slug}_{date_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with d2:
            csv_bytes = to_csv(listings_df)
            st.download_button(
                "📥 Download CSV",
                data=csv_bytes,
                file_name=f"SPEEDHOME_{file_slug}_{date_str}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # ── ROI Calculator (bonus feature) ────────────────────────────────────
        with st.expander("💡 Quick ROI Calculator", expanded=False):
            st.markdown("Estimate rental yield based on scraped data.")
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                purchase_price = st.number_input("Purchase Price (RM)", value=600000, step=10000)
            with rc2:
                monthly_rent = st.number_input("Monthly Rent (RM)", value=2500, step=100)
            with rc3:
                expenses_pct = st.slider("Annual Expenses (% of price)", 0.0, 5.0, 1.5, 0.1)
            annual_rent = monthly_rent * 12
            annual_expenses = purchase_price * (expenses_pct / 100)
            net_income = annual_rent - annual_expenses
            gross_yield = (annual_rent / purchase_price) * 100
            net_yield = (net_income / purchase_price) * 100
            r1, r2, r3 = st.columns(3)
            r1.metric("Gross Yield", f"{gross_yield:.2f}%")
            r2.metric("Net Yield", f"{net_yield:.2f}%")
            r3.metric("Annual Net Income", f"RM {net_income:,.0f}")


if __name__ == "__main__":
    main()
