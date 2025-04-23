import redis
from crawler.config import REDIS_TASK_QUEUE
import json

r = redis.Redis()

task = {
    "url": "https://www.google.com/maps/search/7-11/@25.03,121.56,17z"
}

r.rpush(REDIS_TASK_QUEUE, json.dumps(task))