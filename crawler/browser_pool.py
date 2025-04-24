from playwright.async_api import async_playwright, Browser
import asyncio
from crawler.config import MAX_CONTEXT, MAX_PAGES_PER_CONTEXT

class BrowserPool:
    def __init__(self, max_contexts=MAX_CONTEXT, max_pages_per_context=MAX_PAGES_PER_CONTEXT):
        self.max_contexts = max_contexts
        self.max_pages = max_pages_per_context
        self.semaphore = asyncio.Semaphore(max_contexts * max_pages_per_context)
        self.contexts = []
        self.browser: Browser = None
        self.lock = asyncio.Lock()
        self.proxy_pool = []
        self.ua_pool = []
        self.proxy_index = 0
        self.ua_index = 0

    async def load_proxies(self):
        # TODO: Load proxies from Redis or other source
        self.proxy_pool = [
            {"server": "http://proxy1.example.com:8080"},
            {"server": "http://proxy2.example.com:8080"},
        ]

    async def load_user_agents(self):
        # TODO: Load user agents from Redis or other source
        self.ua_pool = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        ]

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, *args):
        for ctx in self.contexts:
            await ctx["context"].close()
        await self.browser.close()
        await self.playwright.stop()

    async def _get_available_context(self):
        async with self.lock:
            for ctx in self.contexts:
                if ctx["active"] < self.max_pages:
                    ctx["active"] += 1
                    return ctx

            if len(self.contexts) < self.max_contexts:
                # proxy = self.proxy_pool[self.proxy_index % len(self.proxy_pool)] if self.proxy_pool else None
                proxy=None
                ua = self.ua_pool[self.ua_index % len(self.ua_pool)] if self.ua_pool else None
                self.proxy_index += 1
                self.ua_index += 1

                context = await self.browser.new_context(proxy=proxy, user_agent=ua)
                ctx_entry = {"context": context, "active": 1}
                self.contexts.append(ctx_entry)
                return ctx_entry

            # 如果都滿了，就等待有 context 釋放
            await asyncio.sleep(0.1)
            return await self._get_available_context()

    async def use_context(self, fn):
        async with self.semaphore:
            ctx_entry = await self._get_available_context()
            context = ctx_entry["context"]
            try:
                page = await context.new_page()
                return await fn(page)
            finally:
                await page.close()  # 每個 page 用完即關，不需等 context 所有 page 結束
                async with self.lock:
                    ctx_entry["active"] -= 1