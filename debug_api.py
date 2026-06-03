"""
Run this: python debug_api.py
It will show exactly what's happening with the API calls.
"""
from curl_cffi import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://speedhome.com/",
    "Origin": "https://speedhome.com",
}

tests = [
    ("Search API", "https://speedhome.com/api/properties/search", {"area": "Mont Kiara", "page": 0, "size": 20, "lang": "en"}),
    ("Autocomplete", "https://api.speedrent.com/v2/properties/search/name/autocomplete", {"name": "Mont Kiara", "lang": "en"}),
    ("Search with slug", "https://speedhome.com/api/properties/search", {"area": "mont-kiara", "page": 0, "size": 20}),
    ("Search no params", "https://speedhome.com/api/properties/search", {"page": 0, "size": 5}),
]

for label, url, params in tests:
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"URL:  {url}")
    print(f"PARAMS: {params}")
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=20, impersonate="chrome")
        print(f"STATUS: {r.status_code}")
        print(f"RESPONSE LENGTH: {len(r.text)}")
        try:
            data = r.json()
            print(f"JSON KEYS: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            print(f"PREVIEW: {json.dumps(data)[:500]}")
        except Exception as e:
            print(f"NOT JSON: {e}")
            print(f"RAW: {r.text[:300]}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
