import pytest
from task_manager import TaskManager, Task

def test_add_task_valid():
    tm = TaskManager()
    tm.add_task("Task 1", "Description 1", 5)
    assert len(tm.tasks) == 1
    assert tm.tasks[1].name == "Task 1"
    assert tm.tasks[1].description == "Description 1"
    assert tm.tasks[1].priority == 5

def test_add_task_invalid_priority():
    tm = TaskManager()
    with pytest.raises(ValueError):
        tm.add_task("Task 1", "Description 1", 0)

def test_remove_task_valid():
    tm = TaskManager()
    tm.add_task("Task 1", "Description 1", 5)
    tm.remove_task(1)
    assert len(tm.tasks) == 0

def test_remove_task_invalid_id():
    tm = TaskManager()
    with pytest.raises(ValueError):
        tm.remove_task(1)

def test_update_task_valid():
    tm = TaskManager()
    tm.add_task("Task 1", "Description 1", 5)
    tm.update_task(1, "New Description", 7)
    assert tm.tasks[1].description == "New Description"
    assert tm.tasks[1].priority == 7

def test_update_task_invalid_id():
    tm = TaskManager()
    with pytest.raises(ValueError):
        tm.update_task(1, "New Description", 7)

def test_update_task_invalid_priority():
    tm = TaskManager()
    tm.add_task("Task 1", "Description 1", 5)
    with pytest.raises(ValueError):
        tm.update_task(1, "New Description", 0)

def test_get_tasks():
    tm = TaskManager()
    tm.add_task("Task 1", "Description 1", 5)
    tasks = tm.get_tasks()
    assert len(tasks) == 1
    assert tasks[0].name == "Task 1"
    assert tasks[0].description == "Description 1"
    assert tasks[0].priority == 5

def test_persist_to_json(tmp_path):
    tm = TaskManager()
    tm.add_task("Task 1", "Description 1", 5)
    json_file = tmp_path / "tasks.json"
    tm.persist_to_json(str(json_file))
    with open(json_file, 'r') as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["name"] == "Task 1"
    assert data[0]["description"] == "Description 1"
    assert data[0]["priority"] == 5

def test_load_from_json(tmp_path):
    tm = TaskManager()
    json_file = tmp_path / "tasks.json"
    with open(json_file, 'w') as f:
        json.dump([{"id": 1, "name": "Task 1", "description": "Description 1", "priority": 5, "status": "pending"}], f)
    tm.load_from_json(str(json_file))
    assert len(tm.tasks) == 1
    assert tm.tasks[1].name == "Task 1"
    assert tm.tasks[1].description == "Description 1"
    assert tm.tasks[1].priority == 5
