import os
import ast
import tempfile
from database.db_manager import DBManager
from tools.static_analysis import _annotate_parents, _collect_call_edges

def test_db_manager_new_methods():
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)
    try:
        db = DBManager(db_path=temp_db_path)
        project_id = db.register_project("test_project", "/fake/path")
        
        # Test store_srs_version
        srs_id = db.store_srs_version(project_id, "# My Test SRS\n- Req 1", note="new")
        assert srs_id is not None
        
        # Test store_dependency_graph
        graph_id = db.store_dependency_graph(project_id, "static", '{"modules": {}}')
        assert graph_id is not None
        
        # Verify db persistence
        with db.get_connection() as conn:
            srs_rows = conn.execute("SELECT version, content FROM srs_versions").fetchall()
            assert len(srs_rows) == 1
            assert srs_rows[0][0] == 1
            assert "Req 1" in srs_rows[0][1]
            
            graph_rows = conn.execute("SELECT graph_type, graph_json FROM dependency_graphs").fetchall()
            assert len(graph_rows) == 1
            assert graph_rows[0][0] == "static"
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)

def test_collect_call_edges_nested():
    code = """
def test_function():
    x = 10
    if x > 5:
        nested_call()
    return another_call()
"""
    tree = ast.parse(code)
    _annotate_parents(tree)
    edges = _collect_call_edges(tree)
    
    # We expect caller for nested_call and another_call to be 'test_function' instead of '<unknown>'
    assert len(edges) == 2
    assert {"caller": "test_function", "callee": "nested_call"} in edges
    assert {"caller": "test_function", "callee": "another_call"} in edges

def test_db_c_cpp_functions_storage():
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)
    try:
        db = DBManager(db_path=temp_db_path)
        project_id = db.register_project("c_proj", "/fake/c_proj")
        
        sample_fns = [
            {"name": "enqueue", "return_type": "bool", "params": ["Queue *q", "int val"], "signature": "bool enqueue(Queue *q, int val)", "is_core": 1},
            {"name": "dequeue", "return_type": "bool", "params": ["Queue *q", "int *val"], "signature": "bool dequeue(Queue *q, int *val)", "is_core": 1}
        ]
        db.store_c_cpp_functions(project_id, "queue.c", sample_fns)
        
        retrieved = db.get_c_cpp_functions(project_id, core_only=True)
        assert len(retrieved) == 2
        names = [r["function_name"] for r in retrieved]
        assert "enqueue" in names
        assert "dequeue" in names
        assert retrieved[0]["file_path"] == "queue.c"
        
        db.clear_c_cpp_functions(project_id, "queue.c")
        empty = db.get_c_cpp_functions(project_id)
        assert len(empty) == 0
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)

def test_extract_and_store_c_cpp_functions():
    from tools.static_analysis import extract_and_store_c_cpp_functions
    import json
    
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)
    temp_dir = tempfile.mkdtemp()
    reports_dir = os.path.join(temp_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    try:
        db = DBManager(db_path=temp_db_path)
        project_id = db.register_project("calc_app", temp_dir)
        
        header_path = os.path.join(temp_dir, "calc.h")
        source_path = os.path.join(temp_dir, "calc.c")
        
        with open(header_path, "w", encoding="utf-8") as f:
            f.write("#ifndef CALC_H\n#define CALC_H\ndouble calc_add(double a, double b);\ndouble calc_sub(double a, double b);\n#endif\n")
            
        with open(source_path, "w", encoding="utf-8") as f:
            f.write('#include "calc.h"\ndouble calc_add(double a, double b) { return a + b; }\ndouble calc_sub(double a, double b) { return a - b; }\n')
            
        fns, formatted_ref = extract_and_store_c_cpp_functions(temp_dir, db_manager=db, project_id=project_id, reports_dir=reports_dir)
        
        assert len(fns) >= 2
        assert "calc_add" in formatted_ref
        assert "calc_sub" in formatted_ref
        
        json_report_path = os.path.join(reports_dir, "c_cpp_functions.json")
        assert os.path.exists(json_report_path)
        with open(json_report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert len(data) >= 2
            
        db_fns = db.get_c_cpp_functions(project_id)
        assert len(db_fns) >= 2
    finally:
        import shutil
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        shutil.rmtree(temp_dir)


def test_c_cpp_stdlib_table_and_reference():
    from tools.static_analysis import get_c_cpp_stdlib_reference
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)
    try:
        db = DBManager(db_path=temp_db_path)
        stdlib_entries = db.get_c_cpp_stdlib(language="cpp")
        assert len(stdlib_entries) >= 20
        
        symbols = [e["symbol_name"] for e in stdlib_entries]
        assert "std::max" in symbols
        assert "std::min" in symbols
        assert "std::sort" in symbols
        assert "std::vector" in symbols
        assert "malloc" in symbols
        
        ref_text = get_c_cpp_stdlib_reference(language="cpp", db_manager=db)
        assert "std::max" in ref_text
        assert "std::sort" in ref_text
        assert "ALGORITHM" in ref_text
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


