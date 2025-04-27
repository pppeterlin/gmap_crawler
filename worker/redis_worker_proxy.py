import asyncio
import redis
import json
from crawler.browser_pool import BrowserPoolProxy
from crawler.html_parser import extract_info
from crawler.store import save_result
from crawler.config import MAX_CONTEXT, MAX_PAGES_PER_CONTEXT
from crawler.crawler import handle_task

async def worker_loop():
    r = redis.Redis(host="localhost", port=6379, db=0)
    async with BrowserPoolProxy(max_contexts=MAX_CONTEXT, max_pages_per_context=MAX_PAGES_PER_CONTEXT) as pool:
        # while True:
        #     tasks_batch = []
        #     for _ in range(100):
        #         data = r.blpop("gmap_tasks", timeout=1)  # 加timeout避免永卡
        #         if data:
        #             _, task_data = data
        #             task = json.loads(task_data)
        #             tasks_batch.append(task)

        #     if not tasks_batch:
        #         print("No more tasks in Redis. Exiting.")
        #         continue

        #     print(f"[TASK] Fetching batch of {len(tasks_batch)} URLs")
                    # await asyncio.gather(*(handle_task(task, pool, r) for task in tasks_batch))
        tasks_batch = []
        while True:
            data = r.blpop("gmap_tasks", timeout=1)
            if data:
                _, task_data = data
                task = json.loads(task_data)
                tasks_batch.append(task)

            if len(tasks_batch) >= 100 or not data:
                if tasks_batch:
                    print(f"[TASK] Fetching batch of {len(tasks_batch)} URLs")
                    await asyncio.gather(*(handle_task(task, pool, r) for task in tasks_batch))
                    tasks_batch = []
                else:
                    print("[INFO] No new tasks, waiting...")



if __name__ == "__main__":
    asyncio.run(worker_loop())




#TODO
# - 加入proxy pool之後
# - 啟動retry_manager, failed_task會被放回gmap_task
# - 但遇到的問題是: 
#     1. worker的retry速度沒有近似於“常駐” （只要gmap_task有東西就處理）
#     2. 重新檢查retry的設計，無效的proxy會造成多少task失敗，retry_count設定是否合理