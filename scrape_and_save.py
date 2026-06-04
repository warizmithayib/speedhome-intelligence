"""
scrape_and_save.py
──────────────────
Run this locally (NOT on Streamlit Cloud) to pre-fetch listings from SPEEDHOME
and save them as JSON files inside the `sample_data/` folder.

Those JSON files are then committed to your Git repo and used as a fallback
when the app is deployed to Streamlit Cloud (where live scraping is blocked).

Usage:
    pip install curl_cffi   # if not already installed
    python scrape_and_save.py

Outputs:
    sample_data/<slug>.json   for each area in AREAS_TO_SCRAPE
    sample_data/_index.json   index of all available cached areas + metadata
"""

import json
import re
import time
import random
import os
from datetime import datetime
from statistics import mean

# Use curl_cffi for Chrome impersonation to bypass Cloudflare
try:
    from curl_cffi import requests
    print("✓ Using curl_cffi with Chrome impersonation")
except ImportError:
    import requests
    print("⚠️  curl_cffi not found, using standard requests (may get 403)")
    print("   Install with: pip install curl_cffi\n")

# ── Config ─────────────────────────────────────────────────────────────────────

BASE_URL    = "https://speedhome.com"
OUTPUT_DIR  = "sample_data"
MAX_PAGES   = 5  # pages per area — increase for more data

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://speedhome.com/",
}

HEADERS_HTML = {**HEADERS, "Accept": "text/html,application/xhtml+xml,*/*"}

FURNISH_MAP = {
    "FULL":        "Fully Furnished",
    "PARTIAL":     "Partially Furnished",
    "UNFURNISHED": "Unfurnished",
    "NONE":        "Unfurnished",
}

# ── Areas to scrape ─────────────────────────────────────────────────────────────
# Add or remove areas as needed.

AREAS_TO_SCRAPE = [
    ("Mont Kiara",    "mont-kiara"),
    ("Bangsar",       "bangsar"),
    ("KLCC",          "klcc"),
    ("Petaling Jaya", "petaling-jaya"),
    ("Subang Jaya",   "subang-jaya"),
    ("Cheras",        "cheras"),
    ("Damansara",     "damansara"),
    ("Cyberjaya",     "cyberjaya"),
    ("Shah Alam",     "shah-alam"),
    ("Bukit Bintang", "bukit-bintang"),
]

# ── Helpers ─────────────────────────────────────────────────────────────────────

def safe_get(url: str, hdrs: dict, timeout: int = 15):
    """GET with Chrome impersonation via curl_cffi if available."""
    try:
        from curl_cffi import requests as curl_req
        return curl_req.get(url, headers=hdrs, timeout=timeout, impersonate="chrome")
    except ImportError:
        return requests.get(url, headers=hdrs, timeout=timeout)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def get_build_id() -> str | None:
    try:
        r = safe_get(BASE_URL + "/", HEADERS_HTML, timeout=15)
        if r.status_code == 200:
            m = re.search(r'"buildId"\s*:\s*"([^"]+)"', r.text)
            if m:
                return m.group(1)
            print("  ✗ Build ID not found in page HTML")
        else:
            print(f"  ✗ Homepage returned {r.status_code}")
    except Exception as e:
        print(f"  ✗ Could not fetch build ID: {e}")
    return None


def detect_room_type(bedroom_count) -> str:
    try:
        n = int(bedroom_count)
        return "Studio" if n == 0 else f"{n}BR"
    except (TypeError, ValueError):
        return "Unknown"


def normalize_listing(item: dict) -> dict:
    ref         = item.get("ref", "")
    name        = item.get("name", "")
    bedroom     = item.get("bedroom", 0)
    price       = item.get("price")
    sqft        = item.get("sqft")
    furnish_raw = item.get("furnishType", "")
    furnishing  = FURNISH_MAP.get(furnish_raw, furnish_raw.title() if furnish_raw else "Not Specified")

    addr_parts = [p.strip() for p in (item.get("address") or "").split(",")
                  if p.strip() and not re.match(r"^\d", p.strip())]
    area = addr_parts[-2] if len(addr_parts) >= 2 else (addr_parts[-1] if addr_parts else name)

    link = f"{BASE_URL}/details/{slugify(name)}-{ref}" if ref else ""

    return {
        "title":         name,
        "area":          area,
        "room_type":     detect_room_type(bedroom),
        "furnishing":    furnishing,
        "price_monthly": float(price) if price else None,
        "price_daily":   None,
        "price_yearly":  None,
        "sqft":          float(sqft) if sqft else None,
        "rent_type":     "Monthly",
        "link":          link,
        "bedroom":       bedroom,
        "bathroom":      item.get("bathroom"),
        "carpark":       item.get("carpark"),
        "no_deposit":    item.get("noDeposit", False),
    }


def fetch_area(slug: str, build_id: str, max_pages: int = MAX_PAGES) -> list[dict]:
    all_listings = []
    page = 1

    while page <= max_pages:
        url = f"{BASE_URL}/_next/data/{build_id}/en/rent/{slug}.json"
        if page > 1:
            url += f"?page={page}"

        try:
            r = safe_get(url, HEADERS, timeout=20)
            if r.status_code != 200:
                print(f"    Page {page}: HTTP {r.status_code} — stopping.")
                break

            props     = r.json().get("pageProps", {})
            prop_list = props.get("propertyList", {})
            content   = prop_list.get("content", [])

            if not content:
                print(f"    Page {page}: no content — done.")
                break

            for item in content:
                all_listings.append(normalize_listing(item))

            total_pages    = prop_list.get("totalPages", 1)
            total_elements = prop_list.get("totalElements", len(all_listings))
            print(f"    Page {page}/{total_pages}: {len(all_listings)}/{total_elements} listings so far")

            if page >= total_pages:
                break

            page += 1
            time.sleep(1.5 + random.uniform(0, 0.8))

        except Exception as e:
            print(f"    Page {page}: Error — {e}")
            break

    # Deduplicate
    seen, deduped = set(), []
    for item in all_listings:
        key = item.get("link") or item.get("title", "")
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("🔑 Fetching SPEEDHOME build ID...")
    build_id = get_build_id()
    if not build_id:
        print("✗ Could not get build ID. Make sure curl_cffi is installed:")
        print("  pip install curl_cffi")
        return
    print(f"  ✓ Build ID: {build_id}\n")

    index = []

    for area_name, slug in AREAS_TO_SCRAPE:
        print(f"📡 Scraping: {area_name} ({slug})")
        listings = fetch_area(slug, build_id)

        if not listings:
            print(f"  ✗ No listings found for {area_name}, skipping.\n")
            continue

        prices    = [l["price_monthly"] for l in listings if l.get("price_monthly")]
        avg_price = round(mean(prices), 0) if prices else None

        out_path = os.path.join(OUTPUT_DIR, f"{slug}.json")
        payload  = {
            "area_name":      area_name,
            "slug":           slug,
            "scraped_at":     datetime.now().isoformat(),
            "total_listings": len(listings),
            "listings":       listings,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        index.append({
            "area_name":          area_name,
            "slug":               slug,
            "scraped_at":         payload["scraped_at"],
            "total_listings":     len(listings),
            "avg_price_monthly":  avg_price,
        })

        print(f"  ✓ Saved {len(listings)} listings → {out_path}\n")
        time.sleep(2)

    index_path = os.path.join(OUTPUT_DIR, "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"generated_at": datetime.now().isoformat(), "areas": index}, f, indent=2)

    print(f"✅ Done! {len(index)} areas saved.")
    print(f"📁 Files are in ./{OUTPUT_DIR}/")
    print(f"📋 Index: ./{OUTPUT_DIR}/_index.json")
    print("\n👉 Next steps:")
    print("   1. git add sample_data/")
    print("   2. git commit -m 'Add sample data for cloud fallback'")
    print("   3. git push → redeploy on Streamlit Cloud")


if __name__ == "__main__":
    main()
