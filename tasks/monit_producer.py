import time
from datetime import datetime
import redis
import json
from tasks.task_queue import load_tasks

r = redis.Redis(host="localhost", port=6379, db=0)
# file_path="./tasks/sample/tasks_10000_tw_4cities.json"
file_path="./tasks/sample/tasks_taipei_100.json"
tasks = load_tasks(file_path)

# 清空 Redis 中的狀態（視情況使用）
r.flushdb()

# 記錄任務總數與起始時間
r.set("gmap_total_tasks", len(tasks))
r.set("gmap_tasks_done", 0)
r.set("gmap_task_start", time.time())

# 發送任務
for task in tasks:
    r.rpush("gmap_tasks", json.dumps(task))

print(f"Pushed {len(tasks)} tasks to Redis. Waiting for completion...")

# 監控進度
while True:
    done = int(r.get("gmap_tasks_done") or 0)
    print(f"[DEBUG] Redis gmap_tasks_done = {done}")
    if done >= len(tasks):
        end = time.time()
        duration = end - float(r.get("gmap_task_start"))
        print(f"\n✅ All {done} tasks finished in {duration:.2f} seconds.")
        break
    else:
        print(f"Progress: {done}/{len(tasks)}", end="\r")
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open("./tasks/sample/progress.log", "a", encoding="utf-8") as log_file:
            log_file.write(f"[{now}] Progress: {done}/{len(tasks)}\n")
        time.sleep(1)