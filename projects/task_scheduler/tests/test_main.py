import pytest
from main import TaskManager, input_int, input_str

def test_display_menu(capsys):
    display_menu()
    captured = capsys.readouterr()
    assert "Task Scheduler Menu" in captured.out

def test_handle_add_task(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: "42")
    tm = TaskManager()
    handle_add_task(tm)
    assert len(tm.tasks) == 1
    assert tm.tasks[1].name == "Task 1"
    assert tm.tasks[1].description == "Description 1"
    assert tm.tasks[1].priority == 5

def test_handle_remove_task(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: "42")
    tm = TaskManager()
    tm.add_task("Task 1", "Description 1", 5)
    handle_remove_task(tm)
    assert len(tm.tasks) == 0

def test_handle_update_task(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: "42")
    tm = TaskManager()
    tm.add_task("Task 1", "Description 1", 5)
    handle_update_task(tm)
    assert tm.tasks[1].description == "New Description"
    assert tm.tasks[1].priority == 7

def test_handle_list_tasks(monkeypatch, capsys):
    monkeypatch.setattr('builtins.input', lambda _: "42")
    tm = TaskManager()
    tm.add_task("Task 1", "Description 1", 5)
    handle_list_tasks(tm)
    captured = capsys.readouterr()
    assert "ID: 1, Name: Task 1" in captured.out

def test_handle_persist_to_json(monkeypatch, tmp_path):
    monkeypatch.setattr('builtins.input', lambda _: str(tmp_path / "tasks.json"))
    tm = TaskManager()
    tm.add_task("Task 1", "Description 1", 5)
    handle_persist_to_json(tm)
    assert (tmp_path / "tasks.json").exists()

def test_handle_load_from_json(monkeypatch, tmp_path):
    monkeypatch.setattr('builtins.input', lambda _: str(tmp_path / "tasks.json"))
    tm = TaskManager()
    with open(tmp_path / "tasks.json", 'w') as f:
        json.dump([{"id": 1, "name": "Task 1", "description": "Description 1", "priority": 5, "status": "pending"}], f)
    handle_load_from_json(tm)
    assert len(tm.tasks) == 1
    assert tm.tasks[1].name == "Task 1"
    assert tm.tasks[1].description == "Description 1"
    assert tm.tasks[1].priority == 5
