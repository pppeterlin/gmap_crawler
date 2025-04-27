import redis

def main():
    # 連接 Redis
    r = redis.Redis(host="localhost", port=6379, db=0)

    # 10 個確定無法使用的 proxy
    broken_proxies = [
        "http://0.0.0.0:8080",
        "http://127.0.0.2:8888",
        "http://192.168.300.1:9999",
        "http://example.invalid:8000",
        "http://bad.proxy.test:1234",
        "http://1.2.3.4:5678",
        "http://255.255.255.255:8888",
        "http://10.255.255.1:8080",
        # "http://unreachable.proxy:9000",
        # "http://proxy.doesnotexist.com:8080"
    ]

    # 6 個空的 proxy（代表直接不使用代理）
    empty_proxies = [""] * 3

    # 合併所有 proxy
    all_proxies = broken_proxies + empty_proxies

    # 清除舊的 gmap_proxies list
    r.delete("gmap_proxies")

    # 將 proxy 全部寫入 Redis
    for proxy in all_proxies:
        r.rpush("gmap_proxies", proxy)

    print(f"[INFO] Inserted {len(all_proxies)} proxies into Redis ({len(broken_proxies)} broken + {len(empty_proxies)} empty).")

if __name__ == "__main__":
    main()