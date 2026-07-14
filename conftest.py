import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(ROOT_DIR, "projects")

if os.path.isdir(PROJECTS_DIR):
    sys.path.insert(0, PROJECTS_DIR)
    for entry in os.listdir(PROJECTS_DIR):
        full_path = os.path.join(PROJECTS_DIR, entry)
        if os.path.isdir(full_path):
            sys.path.insert(0, full_path)
