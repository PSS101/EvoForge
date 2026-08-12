from typing import List, Dict
import json

class Task:
    def __init__(self, id: int, name: str, description: str, priority: int):
        self.id = id
        self.name = name
        self.description = description
        self.priority = priority
        self.status = "pending"

class TaskManager:
    def __init__(self):
        self.tasks: Dict[int, Task] = {}
        self.next_task_id = 1

    def add_task(self, task_name: str, description: str, priority: int) -> None:
        if not (1 <= priority <= 10):
            raise ValueError("Priority must be between 1 and 10")
        
        task = Task(id=self.next_task_id, name=task_name, description=description, priority=priority)
        self.tasks[self.next_task_id] = task
        self.next_task_id += 1

    def remove_task(self, task_id: int) -> None:
        if task_id not in self.tasks:
            raise ValueError("Task ID does not exist")
        
        del self.tasks[task_id]

    def update_task(self, task_id: int, new_description: str, new_priority: int) -> None:
        if task_id not in self.tasks:
            raise ValueError("Task ID does not exist")
        
        if not (1 <= new_priority <= 10):
            raise ValueError("Priority must be between 1 and 10")
        
        task = self.tasks[task_id]
        task.description = new_description
        task.priority = new_priority

    def get_tasks(self) -> List[Task]:
        return list(self.tasks.values())

    def persist_to_json(self, file_path: str) -> None:
        tasks_data = [
            {
                "id": task.id,
                "name": task.name,
                "description": task.description,
                "priority": task.priority,
                "status": task.status
            }
            for task in self.tasks.values()
        ]
        
        with open(file_path, 'w') as f:
            json.dump(tasks_data, f, indent=4)

    def load_from_json(self, file_path: str) -> None:
        with open(file_path, 'r') as f:
            tasks_data = json.load(f)
        
        self.tasks.clear()
        for task_data in tasks_data:
            task = Task(
                id=task_data["id"],
                name=task_data["name"],
                description=task_data["description"],
                priority=task_data["priority"]
            )
            task.status = task_data["status"]
            self.tasks[task.id] = task

        # Update next_task_id to ensure uniqueness
        if tasks_data:
            self.next_task_id = max(task.id for task in self.tasks.values()) + 1
