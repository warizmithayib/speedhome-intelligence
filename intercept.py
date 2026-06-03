from playwright.sync_api import sync_playwright
import json, re

url = "https://speedhome.com/rent/mont-kiara"
api_calls = []

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
    )
    page = ctx.new_page()

    def on_request(request):
        u = request.url
        if any(k in u for k in ["api", "listing", "property", "search", "rent", "graphql", "_next/data"]):
            api_calls.append({"method": request.method, "url": u})

    def on_response(response):
        u = response.url
        if any(k in u for k in ["api", "listing", "property", "search", "_next/data", "graphql"]):
            try:
                body = response.body()
                if len(body) > 100:
                    print(f"\n=== RESPONSE {response.status} {u[:120]} ===")
                    try:
                        data = json.loads(body)
                        print(json.dumps(data)[:1000])
                    except:
                        print(body[:400].decode("utf-8", errors="replace"))
            except:
                pass

    page.on("request", on_request)
    page.on("response", on_response)
    page.goto(url, wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(5000)

    print("\n\n=== ALL API CALLS ===")
    for c in api_calls:
        print(f"  {c['method']} {c['url']}")

    html = page.content()
    print(f"\nHTML length: {len(html)}")
    classes = re.findall(r'class="([^"]*(?:listing|property|card|unit)[^"]*)"', html, re.I)
    print("Relevant classes:", list(set(classes))[:20])
    
    with open("speedhome_debug.html", "w") as f:
        f.write(html)
    print("Full HTML saved to speedhome_debug.html")
    browser.close()