import redis
from crawler.config import REDIS_TASK_QUEUE
import json

r = redis.Redis()

task = {
    "url": "https://www.google.com/maps/search/coffee/@25.055356,121.4805,18z"
}

r.rpush(REDIS_TASK_QUEUE, json.dumps(task))
print(f"Pushed task to Redis: {task['url']}")