# file: tasks/retry_manager.py

import time
import json
import redis

# Redis 設定
r = redis.Redis(host="localhost", port=6379, db=0)

# Redis 的 key 名稱
FAILED_TASK_QUEUE = "gmap_failed_tasks"
TASK_QUEUE = "gmap_tasks"

# Retry 設定
MAX_RETRY = 10
SLEEP_INTERVAL = 1  # 每次等待幾秒再掃描一次

# def move_failed_tasks():
#     while True:
#         # 一次全部取出來（你可以改成批次看情況）
#         failed_tasks = r.lrange(FAILED_TASK_QUEUE, 0, -1)

#         if not failed_tasks:
#             print("[Retry Manager] No failed tasks to retry.")
#             time.sleep(SLEEP_INTERVAL)
#             continue

#         print(f"[Retry Manager] Found {len(failed_tasks)} failed tasks.")

#         for raw_task in failed_tasks:
#             try:
#                 task = json.loads(raw_task)
#             except json.JSONDecodeError:
#                 print("[Retry Manager] Invalid task format, skipping.")
#                 continue

#             # 確保 task 有 retry_count 欄位
#             retry_count = task.get("retry_count", 0)

#             if retry_count < MAX_RETRY:
#                 task["retry_count"] = retry_count + 1
#                 # 推回主任務 queue
#                 r.rpush(TASK_QUEUE, json.dumps(task))
#                 print(f"[Retry Manager] Retried task (retry_count={task['retry_count']}): {task.get('url', '')}")
#             else:
#                 print(f"[Retry Manager] Discarded task after {MAX_RETRY} retries: {task.get('url', '')}")

#             # 無論 retry 或 discard，都要從 failed_task 裡刪掉
#             r.lrem(FAILED_TASK_QUEUE, 1, raw_task)

#         time.sleep(SLEEP_INTERVAL)

def move_failed_tasks():
    while True:
        raw_task = r.lpop(FAILED_TASK_QUEUE)

        if not raw_task:
            print("[Retry Manager] No failed tasks to retry.")
            time.sleep(SLEEP_INTERVAL)
            continue

        try:
            task = json.loads(raw_task)
        except json.JSONDecodeError:
            print("[Retry Manager] Invalid task format, skipping.")
            continue

        retry_count = task.get("retry_count", 0)

        if retry_count < MAX_RETRY:
            task["retry_count"] = retry_count + 1
            r.rpush(TASK_QUEUE, json.dumps(task))
            print(f"[Retry Manager] Retried task (retry_count={task['retry_count']}): {task.get('url', '')}")
        else:
            print(f"[Retry Manager] Discarded task after {MAX_RETRY} retries: {task.get('url', '')}")
        
        # ✅ 因為是 lpop 出來的，不用再 lrem 了

if __name__ == "__main__":
    move_failed_tasks()