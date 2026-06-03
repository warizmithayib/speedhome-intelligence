"""
Run: python debug_api2.py
Tests POST for search, and finds the auth token for autocomplete.
"""
from curl_cffi import requests as cffi_requests
import json, re

HEADERS_HTML = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}
HEADERS_JSON = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Referer": "https://speedhome.com/",
    "Origin": "https://speedhome.com",
}

# ── Step 1: GET homepage to grab cookies + any tokens ─────────────────────────
print("="*60)
print("STEP 1: Fetching homepage for cookies/tokens")
home = cffi_requests.get("https://speedhome.com/rent/mont-kiara", headers=HEADERS_HTML, timeout=20, impersonate="chrome")
print(f"  Status: {home.status_code}, Length: {len(home.text)}")
cookies = dict(home.cookies)
print(f"  Cookies: {list(cookies.keys())}")

# Look for bearer token / API key in page source
token_match = re.search(r'"token"\s*:\s*"([^"]{20,})"', home.text)
bearer_match = re.search(r'Bearer\s+([A-Za-z0-9\-_\.]+)', home.text)
api_key_match = re.search(r'"apiKey"\s*:\s*"([^"]+)"', home.text)
print(f"  Token in page: {token_match.group(1)[:40] if token_match else 'NOT FOUND'}")
print(f"  Bearer in page: {bearer_match.group(1)[:40] if bearer_match else 'NOT FOUND'}")
print(f"  ApiKey in page: {api_key_match.group(1)[:40] if api_key_match else 'NOT FOUND'}")

# ── Step 2: Try POST to search API ────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 2: POST to search API")

post_bodies = [
    {"area": "Mont Kiara", "page": 0, "size": 20, "lang": "en"},
    {"location": "Mont Kiara", "page": 0, "size": 20},
    {"keyword": "Mont Kiara", "pageNumber": 0, "pageSize": 20},
    {"search": "Mont Kiara", "page": 0, "size": 20, "rentalType": "MONTHLY"},
    {"areaName": "Mont Kiara", "page": 0, "size": 20},
]

for body in post_bodies:
    r = cffi_requests.post(
        "https://speedhome.com/api/properties/search",
        headers=HEADERS_JSON,
        cookies=cookies,
        json=body,
        timeout=15,
        impersonate="chrome",
    )
    print(f"  POST {json.dumps(body)[:60]} → {r.status_code} | {r.text[:150]}")

# ── Step 3: Try the internal Next.js data endpoint ────────────────────────────
print("\n" + "="*60)
print("STEP 3: Try _next/data endpoint")
# Extract build ID from page
build_id = re.search(r'"buildId"\s*:\s*"([^"]+)"', home.text)
if build_id:
    bid = build_id.group(1)
    print(f"  Build ID: {bid}")
    next_url = f"https://speedhome.com/_next/data/{bid}/en/rent/mont-kiara.json"
    r = cffi_requests.get(next_url, headers=HEADERS_JSON, cookies=cookies, timeout=15, impersonate="chrome")
    print(f"  Status: {r.status_code}, Length: {len(r.text)}")
    try:
        d = r.json()
        print(f"  Keys: {list(d.keys())}")
        print(f"  Preview: {json.dumps(d)[:500]}")
    except:
        print(f"  Raw: {r.text[:300]}")
else:
    print("  No build ID found in page")

# ── Step 4: Try autocomplete with various auth approaches ─────────────────────
print("\n" + "="*60)
print("STEP 4: Autocomplete with cookies from homepage")
r = cffi_requests.get(
    "https://api.speedrent.com/v2/properties/search/name/autocomplete",
    headers=HEADERS_JSON,
    cookies=cookies,
    params={"name": "Mont Kiara", "lang": "en"},
    timeout=15,
    impersonate="chrome",
)
print(f"  Status: {r.status_code}, Length: {len(r.text)}, Preview: {r.text[:300]}")

