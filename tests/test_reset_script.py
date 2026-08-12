import os
import shutil
import reset
from reset import reset_workspace
from database.db_manager import DBManager

def test_reset_workspace_clears_directories_and_db(tmp_path, monkeypatch):
    tmp_projects = tmp_path / "projects"
    tmp_reports = tmp_path / "reports"
    tmp_db = tmp_path / "database" / "project_state.db"
    
    monkeypatch.setattr(reset, "PROJECTS_DIR", str(tmp_projects))
    monkeypatch.setattr(reset, "REPORTS_DIR", str(tmp_reports))
    monkeypatch.setattr(reset, "DB_PATH", str(tmp_db))
    
    # Create dummy items
    dummy_proj = tmp_projects / "dummy_project"
    dummy_rep = tmp_reports / "dummy_project"
    dummy_proj.mkdir(parents=True, exist_ok=True)
    dummy_rep.mkdir(parents=True, exist_ok=True)
    
    with open(dummy_proj / "test.txt", "w") as f:
        f.write("test")
    with open(dummy_rep / "SRS.md", "w") as f:
        f.write("# SRS")

    # Run reset
    reset_workspace()

    assert not dummy_proj.exists()
    assert not dummy_rep.exists()
    
    # Verify DB connection works after reset
    db = DBManager(db_path=str(tmp_db))
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        assert "projects" in tables
        assert "file_registry" in tables

