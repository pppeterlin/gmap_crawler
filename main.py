import asyncio
import time

from crawler.browser_pool import BrowserPool
from crawler.crawler import handle_task
from crawler.config import MAX_CONTEXT, MAX_PAGES_PER_CONTEXT
from tasks.task_queue import load_tasks


async def main():
    start = time.time() 

    tasks = load_tasks()
    async with BrowserPool(max_contexts=MAX_CONTEXT, max_pages_per_context=MAX_PAGES_PER_CONTEXT) as pool:
        await asyncio.gather(*(handle_task(task, pool) for task in tasks))

    end = time.time()
    print(f"Total time: {end - start:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())