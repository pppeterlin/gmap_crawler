# launch_demo.py

import time
import subprocess
import redis
import os
import signal

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

def start_proxy_initializer():
    print("[Proxy Initializer] Running...")
    subprocess.run(["python3", "tasks/proxy_initializer.py"], check=True)

def start_worker_proxy():
    print("[Worker] Starting...")
    return subprocess.Popen(["python3", "-m", "worker.redis_worker_proxy"])

def start_retry_manager():
    print("[Retry Manager] Starting...")
    return subprocess.Popen(["python3", "-m", "worker.retry_manager"])

def start_monit_producer(worker, retry_manager):
    print("[Monit Producer] Pushing tasks...")
    try:
        subprocess.run(["python3", "-m", "tasks.monit_producer"], check=True)
    except subprocess.CalledProcessError as e:
        print("[Error] Monit Producer failed to start.")
        print("\n[Cleanup] Terminating worker and retry manager due to producer failure...")
        worker.send_signal(signal.SIGTERM)
        retry_manager.send_signal(signal.SIGTERM)
        exit(1)

def main():
    start_time = time.time()

    start_proxy_initializer()
    time.sleep(1)

    worker = start_worker_proxy()
    time.sleep(1)

    retry_manager = start_retry_manager()
    time.sleep(2)

    start_monit_producer(worker, retry_manager)

    # 監控進度
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

    while True:
        done = int(r.get("gmap_tasks_done") or 0)
        total = int(r.get("gmap_total_tasks") or 0)

        print(f"[Monitor] Progress: {done}/{total}", end="\r")

        if done >= total and total > 0:
            duration = time.time() - start_time
            print(f"\n✅ All {done} tasks completed in {duration:.2f} seconds.")
            break

        time.sleep(1)

    # 全部完成，關掉子程序
    print("\n[Cleanup] Terminating worker and retry manager...")
    worker.send_signal(signal.SIGTERM)
    retry_manager.send_signal(signal.SIGTERM)

if __name__ == "__main__":
    main()