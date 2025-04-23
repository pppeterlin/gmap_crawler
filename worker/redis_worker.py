import redis
import json
import asyncio
from crawler.browser_pool import BrowserPool  # 你的現成 pool

async def worker_loop():
    r = redis.Redis()
    async with BrowserPool() as pool:
        while True:
            _, task_data = r.blpop("gmap_tasks")  # 阻塞等待任務
            task = json.loads(task_data)

            async def run(page):
                await page.goto(task["url"])
                await page.wait_for_selector(".Nv2PK", timeout=10000)
                html = await page.content()
                print(f"Fetched {task['url']}, length: {len(html)}")

            await pool.use_context(run)

asyncio.run(worker_loop())