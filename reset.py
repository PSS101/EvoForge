#!/usr/bin/env python3
"""
reset.py - EvoForge Workspace Reset Utility

Resets the EvoForge workspace by clearing all generated project directories,
removing reports, and resetting the SQLite database to a clean state.
"""

import os
import shutil
from database.db_manager import DBManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DB_PATH = os.path.join(BASE_DIR, "database", "project_state.db")


def reset_workspace():
    print("=" * 50)
    print("      EvoForge Workspace Reset Utility")
    print("=" * 50)

    # 1. Clean projects directory
    cleaned_projects = 0
    if os.path.exists(PROJECTS_DIR):
        for item in os.listdir(PROJECTS_DIR):
            item_path = os.path.join(PROJECTS_DIR, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                cleaned_projects += 1
            except Exception as e:
                print(f"Error removing {item_path}: {e}")
        print(f"[+] Cleared {cleaned_projects} project directory items from '{PROJECTS_DIR}'.")
    else:
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        print(f"[+] Created clean '{PROJECTS_DIR}' directory.")

    # 2. Clean reports directory
    cleaned_reports = 0
    if os.path.exists(REPORTS_DIR):
        for item in os.listdir(REPORTS_DIR):
            item_path = os.path.join(REPORTS_DIR, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                cleaned_reports += 1
            except Exception as e:
                print(f"Error removing {item_path}: {e}")
        print(f"[+] Cleared {cleaned_reports} report directory items from '{REPORTS_DIR}'.")
    else:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        print(f"[+] Created clean '{REPORTS_DIR}' directory.")

    # 3. Reset database
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"[+] Deleted existing database at '{DB_PATH}'.")
        except Exception as e:
            print(f"Error removing database file {DB_PATH}: {e}")

    # Re-initialize DB tables
    db_mgr = DBManager(db_path=DB_PATH)
    print(f"[+] Re-initialized clean database schema at '{DB_PATH}'.")

    print("=" * 50)
    print("  Workspace successfully reset to clean state!")
    print("=" * 50)


if __name__ == "__main__":
    reset_workspace()
