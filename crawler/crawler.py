from crawler.store import save_result
from crawler.html_parser import extract_info
import json
import redis

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

# async def handle_task(task, pool, r):
#     url = task.get('url', 'unknown')

#     try:
#         async def process(page):
#             await block_resource_types(page)
#             await page.goto(task["url"], timeout=30000)
#             await page.wait_for_selector(".Nv2PK", timeout=10000)
#             html = await page.content()
#             print(f"[{url}] HTML length: {len(html)}")
#             stores = extract_info(html)
#             print(f"[{url}] Parsed {len(stores)} items")
#             for store in stores:
#                 await save_result({**task, **store})

#         success = await pool.use_context(process)
#         if success is False:
#             raise Exception("Proxy Error")

#         r.incr("gmap_tasks_done")
#         print(f"[Success] {url}")

#     except Exception as e:
#         print(f"[Failed] {url} | {e}")
#         r.rpush("gmap_failed_tasks", json.dumps(task))
async def handle_task(task, pool, r):
    url = task.get('url', 'unknown')

    try:
        async def process(page):
            await block_resource_types(page)
            await page.goto(task["url"], timeout=30000)
            await page.wait_for_selector(".Nv2PK", timeout=10000)
            html = await page.content()
            print(f"[{url}] HTML length: {len(html)}")
            stores = extract_info(html)
            print(f"[{url}] Parsed {len(stores)} items")
            for store in stores:
                await save_result({**task, **store})

        success, proxy_used, ctx_entry = await pool.use_context(process)

        if success:
            r.incr("gmap_tasks_done")
            print(f"[Success] {url}")
        else:
            raise Exception("Proxy Error")

    except Exception as e:
        print(f"[Failed] {url} | {e}")
        # 標記 proxy 失敗
        if proxy_used:
            print(f"[Proxy Error] Mark proxy failed: {proxy_used}")
            r.sadd("gmap_failed_proxies", proxy_used)
            if proxy_used in pool.proxy_pool:
                pool.proxy_pool.remove(proxy_used)

        # 把 context 強制關閉
        if ctx_entry:
            try:
                await ctx_entry["context"].close()
                async with pool.lock:
                    if ctx_entry in pool.contexts:
                        pool.contexts.remove(ctx_entry)
                print(f"[Context Closed] due to proxy failure")
            except Exception as close_e:
                print(f"[Context Close Error] {close_e}")

        # 丟回 failed task
        r.rpush("gmap_failed_tasks", json.dumps(task))