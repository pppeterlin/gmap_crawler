import redis
import json
import asyncio
from crawler.browser_pool import BrowserPool  # 你的現成 pool
from crawler.html_parser import extract_info
from crawler.store import save_result
from crawler.crawler import handle_task  # 加入這行在 import 區塊

async def worker_loop():
    r = redis.Redis(host="localhost", port=6379, db=0)
    async with BrowserPool() as pool:
        while True:
            # 批次撈取 100 筆任務
            tasks_batch = []
            for _ in range(50):
                data = r.blpop("gmap_tasks")
                if data:
                    _, task_data = data
                    task = json.loads(task_data)
                    tasks_batch.append(task)

            if not tasks_batch:
                print("No more tasks in Redis. Exiting.")
                break

            print(f"[TASK] Fetching batch of {len(tasks_batch)} URLs")

            async def run(task):
                await handle_task(task, pool, r)
                r.incr("gmap_tasks_done")

            await asyncio.gather(*(run(task) for task in tasks_batch))

asyncio.run(worker_loop())
