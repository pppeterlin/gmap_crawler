from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re

REQUIRED_SELECTORS = [
    ".hfpxzc[aria-label]",
    ".ZkP5Je[aria-label]",
    ".hfpxzc[href]"
]

# BLOCK_ALWAYS = ["image", "media", "font", "stylesheet"]
BLOCK_ALWAYS = []
REQUEST_LOG_PATH = "observed_requests.jsonl"
SAFE_RULES_PATH = "smart_safe_block_rules.json"


def check_required_elements(html):
    soup = BeautifulSoup(html, "html.parser")
    return all(soup.select_one(selector) for selector in REQUIRED_SELECTORS)


def collect_requests_with_block(url):
    all_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        def log_request(request):
            all_requests.append({
                "resource_type": request.resource_type,
                "method": request.method,
                "url": request.url
            })

        def static_blocker(route, request):
            if request.resource_type in BLOCK_ALWAYS:
                return route.abort()
            return route.continue_()

        page.route("**/*", static_blocker)
        page.on("request", log_request)
        page.goto(url)
        page.wait_for_timeout(10000)
        browser.close()

    with open(REQUEST_LOG_PATH, "w", encoding="utf-8") as f:
        for item in all_requests:
            f.write(json.dumps(item) + "\n")


def extract_per_url_blocks():
    tested = set()
    url_blocks = []
    with open(REQUEST_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            req = json.loads(line)
            if req["resource_type"] in BLOCK_ALWAYS:
                continue
            url = req["url"]
            if url not in tested:
                tested.add(url)
                url_blocks.append(url)
    return url_blocks


from itertools import islice

def batch(iterable, size=5):
    """將迭代器切片為每 batch size 一批"""
    iterator = iter(iterable)
    while True:
        chunk = list(islice(iterator, size))
        if not chunk:
            break
        yield chunk

def test_each_blocked_url(url, block_list):
    passed = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 預先驗證 baseline 頁面能成功
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)
        page.wait_for_selector(REQUIRED_SELECTORS[0])
        assert check_required_elements(page.content())
        context.close()

        # 每批測試 5 個 blocked_url
        for url_batch in batch(block_list, size=5):
            contexts = []
            results = []

            for blocked_url in url_batch:
                context = browser.new_context()
                page = context.new_page()

                def make_handler(burl):
                    def route_handler(route, request):
                        if request.resource_type in BLOCK_ALWAYS:
                            return route.abort()
                        if request.url == burl:
                            return route.abort()
                        return route.continue_()
                    return route_handler

                page.route("**/*", make_handler(blocked_url))
                contexts.append((context, page, blocked_url))

            for context, page, blocked_url in contexts:
                try:
                    page.goto(url)
                    page.wait_for_selector(REQUIRED_SELECTORS[0], timeout=5000)
                    if check_required_elements(page.content()):
                        passed.append(blocked_url)
                except Exception as e:
                    print(f"[FAILED] {blocked_url} → {str(e)}")
                finally:
                    context.close()

        browser.close()

    with open(SAFE_RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(passed, f, indent=2)


if __name__ == "__main__":
    test_url = "https://www.google.com/maps/search/coffee/@25.008968,121.249627,18z"
    collect_requests_with_block(test_url)
    url_rules = extract_per_url_blocks()
    test_each_blocked_url(test_url, url_rules)
