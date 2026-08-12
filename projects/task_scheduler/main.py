from task_manager import TaskManager, Task
from utils import input_int, input_str

def display_menu():
    print("\nTask Scheduler Menu")
    print("1. Add Task")
    print("2. Remove Task")
    print("3. Update Task")
    print("4. List Tasks")
    print("5. Persist to JSON")
    print("6. Load from JSON")
    print("7. Exit")

def handle_add_task(task_manager: TaskManager):
    task_name = input_str("Enter task name: ")
    description = input_str("Enter task description: ")
    priority = input_int("Enter task priority (1-10): ")
    try:
        task_manager.add_task(task_name, description, priority)
        print("Task added successfully.")
    except ValueError as e:
        print(f"Error: {e}")

def handle_remove_task(task_manager: TaskManager):
    task_id = input_int("Enter task ID to remove: ")
    try:
        task_manager.remove_task(task_id)
        print("Task removed successfully.")
    except ValueError as e:
        print(f"Error: {e}")

def handle_update_task(task_manager: TaskManager):
    task_id = input_int("Enter task ID to update: ")
    new_description = input_str("Enter new description: ")
    new_priority = input_int("Enter new priority (1-10): ")
    try:
        task_manager.update_task(task_id, new_description, new_priority)
        print("Task updated successfully.")
    except ValueError as e:
        print(f"Error: {e}")

def handle_list_tasks(task_manager: TaskManager):
    tasks = task_manager.get_tasks()
    if not tasks:
        print("No tasks available.")
    else:
        for task in tasks:
            print(f"ID: {task.id}, Name: {task.name}, Description: {task.description}, Priority: {task.priority}, Status: {task.status}")

def handle_persist_to_json(task_manager: TaskManager):
    file_path = input_str("Enter JSON file path to persist tasks: ")
    task_manager.persist_to_json(file_path)
    print(f"Tasks persisted to {file_path}.")

def handle_load_from_json(task_manager: TaskManager):
    file_path = input_str("Enter JSON file path to load tasks from: ")
    task_manager.load_from_json(file_path)
    print(f"Tasks loaded from {file_path}.")

def main():
    task_manager = TaskManager()
    while True:
        display_menu()
        choice = input_int("Choose an option: ")
        
        if choice == 1:
            handle_add_task(task_manager)
        elif choice == 2:
            handle_remove_task(task_manager)
        elif choice == 3:
            handle_update_task(task_manager)
        elif choice == 4:
            handle_list_tasks(task_manager)
        elif choice == 5:
            handle_persist_to_json(task_manager)
        elif choice == 6:
            handle_load_from_json(task_manager)
        elif choice == 7:
            print("Exiting...")
            break
        else:
            print("Invalid option. Please choose a valid option.")

if __name__ == "__main__":
    main()
