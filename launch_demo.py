# launch_producer_and_workers.py

import time
import json
import redis
import multiprocessing
import subprocess
import os
from datetime import datetime
from tasks.task_queue import load_tasks
import sys
import glob

# ====== 設定區 ======
FILE_PATH = "./tasks/sample/tasks_taipei_100.json"
NUM_WORKERS = 3
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
# ====================

def produce_tasks():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

    # 清空 Redis 的任務相關資料（不清空 proxy pool）
    for key in ["gmap_tasks", "gmap_failed_tasks", "gmap_tasks_done", "gmap_total_tasks", "gmap_task_start"]:
        r.delete(key)

    tasks = load_tasks(FILE_PATH)

    r.set("gmap_total_tasks", len(tasks))
    r.set("gmap_tasks_done", 0)
    r.set("gmap_task_start", time.time())

    for task in tasks:
        task["retry_count"] = task.get("retry_count", 0)
        r.rpush("gmap_tasks", json.dumps(task))

    print(f"[Producer] Pushed {len(tasks)} tasks to Redis.")

def start_worker(worker_id):
    print(f"[Worker {worker_id}] Starting...")
    env = os.environ.copy()
    env["WORKER_ID"] = str(worker_id)
    subprocess.run(["python3", "-m", "worker.redis_worker"], env=env, check=True)

def main():
    # Step 1: 先推送任務
    produce_tasks()

    # Step 2: 啟動多個 worker
    processes = []

    for i in range(NUM_WORKERS):
        p = multiprocessing.Process(target=start_worker, args=(i,))
        p.start()
        processes.append(p)
        time.sleep(0.5)

    # Step 3: 監控任務完成狀況
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    start_time = time.time()

    while True:
        done = int(r.get("gmap_tasks_done") or 0)
        total = int(r.get("gmap_total_tasks") or 0)

        print(f"[Monitor] Progress: {done}/{total}", end="\r")

        if done >= total and total > 0:
            end_time = time.time()
            duration = end_time - start_time

            # 合併所有 worker 的結果
            combined_path = "./results/result_combined.jsonl"
            with open(combined_path, "w", encoding="utf-8") as outfile:
                for filepath in sorted(glob.glob("./results/result_worker_*.jsonl")):
                    with open(filepath, "r", encoding="utf-8") as infile:
                        for line in infile:
                            outfile.write(line)
            print(f"\n✅ All worker results combined into {combined_path}.")
            print(f"\n✅ All {done} tasks completed in {duration:.2f} seconds.")

            # 正常結束所有 workers
            for p in processes:
                p.terminate()
                p.join()

            break  # 正常結束 while loop

        time.sleep(1)

        
if __name__ == "__main__":
    main()