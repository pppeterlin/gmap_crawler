import json
from pathlib import Path
from asyncio import Lock

# result_file = Path("./results/output_touyuan.jsonl")
result_file = Path("./results/output_test.jsonl")
result_file.parent.mkdir(exist_ok=True, parents=True)

lock = Lock()  # async-safe write

async def save_result(data):
    async with lock:
        with result_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")