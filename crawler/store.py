import os
import json
from pathlib import Path
from asyncio import Lock

RESULT_FILE = f"./results/result_worker_{os.getenv('WORKER_ID', '0')}.jsonl"
result_file = Path(RESULT_FILE)
result_file.parent.mkdir(exist_ok=True, parents=True)

lock = Lock()  # async-safe write

async def save_result(data):
    async with lock:
        with result_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")