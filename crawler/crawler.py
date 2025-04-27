from crawler.store import save_result
from crawler.html_parser import extract_info
import json
import redis
import random
import asyncio

r = redis.Redis()

async def block_resource_types(page):
    BLOCKED_URL_PREFIXES = [
        "https://fonts.googleapis.com/css",
        "https://maps.gstatic.com/",
        "https://www.google.com/maps/vt/icon/"
        # "https://www.gstatic.com/feedback/",
        # "https://www.google.com/maps/vt/",
        # "https://maps.gstatic.com/consumer/",
        # "https://maps.gstatic.com/tactile",
        # "https://fonts.gstatic.com/s/notosanstc/"
    ]

    async def intercept_route(route, request):
        url = request.url
        if request.resource_type in ["image", "media", "font", "stylesheet"]:
            await route.abort()
        elif any(url.startswith(prefix) for prefix in BLOCKED_URL_PREFIXES):
            await route.abort()
        elif request.resource_type == "xhr" and any(ext in url for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", "photo", "thumbnail"]):
            await route.abort()
        else:
            await route.continue_()

    await page.route("**/*", intercept_route)

async def handle_task(task, pool, r):
    url = task.get('url', 'unknown')

    try:
        async def process(page):
            await block_resource_types(page)
            # await asyncio.sleep(random.uniform(0.05, 0.3))
            await page.goto(task["url"], timeout=60000)
            await page.wait_for_selector(".Nv2PK", timeout=30000)
            html = await page.content()
            print(f"[{url}] HTML length: {len(html)}")
            stores = extract_info(html)
            print(f"[{url}] Parsed {len(stores)} items")
            for store in stores:
                await save_result({**task, **store})

        success, error = await pool.use_context(process)

        if success:
            r.incr("gmap_tasks_done")
            print(f"[Success] {url}")
        else:
            print(f"[Failed] {url} | use_context error: {type(error).__name__} - {error}")
            r.rpush("gmap_failed_tasks", json.dumps(task))

    except Exception as e:
        print(f"[Failed] {url} | Error: {type(e).__name__} - {e}")
        r.rpush("gmap_failed_tasks", json.dumps(task))