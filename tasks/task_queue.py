import json

def load_tasks(file_path="./tasks/sample/tasks_taoyuan_100.json"):
    # file_path = "task/tasks_taipei_100.json"
    with open(file_path) as f:
        return json.load(f)