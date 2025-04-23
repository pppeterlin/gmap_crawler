import redis
import json
import asyncio
from crawler.browser_pool import BrowserPool  # 你的現成 pool
from crawler.html_parser import extract_info
from crawler.store import save_result

async def worker_loop():
    r = redis.Redis()
    async with BrowserPool() as pool:
        while True:
            _, task_data = r.blpop("gmap_tasks")  # 阻塞等待任務
            if not task_data:
                print("No more tasks in Redis. Exiting.")
                break

            task = json.loads(task_data)
            print(f"[TASK] Fetching: {task['url']}")

            async def run(page):
                await page.goto(task["url"])
                await page.wait_for_selector(".Nv2PK", timeout=10000)
                html = await page.content()
                print(f"HTML length: {len(html)}")

                items = extract_info(html)
                print(f"Parsed {len(items)} items")

                for item in items:
                    print(f"Saving item: {item.get('title', str(item))}")
                    await save_result(item)

            await pool.use_context(run)

asyncio.run(worker_loop())
