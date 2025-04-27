from playwright.async_api import async_playwright, Browser
import asyncio
import redis, random
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


class BrowserPoolProxy:
    def __init__(self, max_contexts=MAX_CONTEXT, max_pages_per_context=MAX_PAGES_PER_CONTEXT):
        self.max_contexts = max_contexts
        self.max_pages = max_pages_per_context
        self.semaphore = asyncio.Semaphore(max_contexts * max_pages_per_context)
        self.contexts = []
        self.browser: Browser = None
        self.lock = asyncio.Lock()
        self.redis = redis.Redis(host="localhost", port=6379, db=0)
        self.proxy_pool = []
        self.proxy_index = 0

    async def load_proxies(self):
        proxies = self.redis.lrange("gmap_proxies", 0, -1)
        self.proxy_pool = [p.decode("utf-8") for p in proxies]
        if not self.proxy_pool:
            print("[WARNING] Proxy pool is empty!")

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        await self.load_proxies()
        return self

    async def __aexit__(self, *args):
        for ctx in self.contexts:
            await ctx["context"].close()
        await self.browser.close()
        await self.playwright.stop()

    async def _get_available_context(self):
        async with self.lock:
            # 先找現有 context
            for ctx in self.contexts:
                if ctx["active"] < self.max_pages:
                    ctx["active"] += 1
                    return ctx

            # 沒有空位，就建新的context
            if len(self.contexts) < self.max_contexts:
                proxy_server = None
                if self.proxy_pool:
                    candidate = random.choice(self.proxy_pool)
                    proxy_server = candidate if candidate.strip() else None
                # proxy = self.redis.lindex("gmap_proxies", 0)
                # if proxy:
                #     proxy_server = proxy.decode("utf-8")
                #     if not proxy_server or proxy_server.lower() == "localhost":
                #         proxy_server = None
                # else:
                #     proxy_server = None

                if proxy_server:
                    context = await self.browser.new_context(proxy={"server": proxy_server})
                else:
                    context = await self.browser.new_context()

                ctx_entry = {"context": context, "active": 1, "proxy": proxy_server}
                self.contexts.append(ctx_entry)
                print(f"[Context] Created with proxy: {proxy_server}")
                return ctx_entry

            # 都滿了，等一下再重試
            await asyncio.sleep(0.1)
            return await self._get_available_context()

    async def use_context(self, fn):
        async with self.semaphore:
            ctx_entry = await self._get_available_context()
            context = ctx_entry["context"]
            proxy_used = ctx_entry.get("proxy")
            page = None
            try:
                page = await context.new_page()
                await fn(page)
                return True, proxy_used, ctx_entry
            except Exception as e:
                print(f"[Page Error] {e}")
                try:
                    await ctx_entry["context"].close()
                    async with self.lock:
                        if ctx_entry in self.contexts:
                            self.contexts.remove(ctx_entry)
                    print(f"[Context Closed] due to error (proxy={proxy_used})")
                except Exception as close_err:
                    print(f"[Context Close Error] {close_err}")
                return False, proxy_used, ctx_entry
            finally:
                try:
                    if page:
                        await page.close()
                except Exception:
                    pass
                async with self.lock:
                    ctx_entry["active"] -= 1

############
