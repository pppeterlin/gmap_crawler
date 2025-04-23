from crawler.store import save_result
from crawler.html_parser import extract_info

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

async def handle_task(task, pool):
    async def process(page):
        await block_resource_types(page)
        await page.goto(task["url"])
        await page.wait_for_selector(".Nv2PK", timeout=10000)

        html = await page.content()
        stores = extract_info(html)

        for store in stores:
            await save_result({**task, **store})  # 即時儲存

    await pool.use_context(process)