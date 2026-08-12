import os
import tempfile
import shutil
from tools.build_tools import (
    generate_makefile,
    compile_project,
    run_c_tests,
    parse_c_compiler_errors,
    analyze_c_bugs,
    debug_c_project
)
from agents.sdlc_crew import SDLCCrewManager
from tools.impact_tools import list_test_files, generate_test_impact_report


def test_parse_c_compiler_errors():
    sample_output = (
        "queue.c:15:5: error: expected ';' before 'return'\n"
        "queue.c:20:10: warning: unused variable 'x'\n"
    )
    errors = parse_c_compiler_errors(sample_output)
    assert len(errors) == 2
    assert errors[0]['file'] == 'queue.c'
    assert errors[0]['line'] == 15
    assert errors[0]['severity'] == 'error'
    assert "expected ';'" in errors[0]['message']


def test_analyze_c_bugs_and_debug():
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a header lacking header guards and missing stdlib.h for malloc
        header_path = os.path.join(temp_dir, "buffer.h")
        source_path = os.path.join(temp_dir, "buffer.c")
        main_path = os.path.join(temp_dir, "main.c")
        test_dir = os.path.join(temp_dir, "tests")
        os.makedirs(test_dir, exist_ok=True)
        test_runner_path = os.path.join(test_dir, "test_runner.c")

        with open(header_path, "w", encoding="utf-8") as f:
            f.write("typedef struct { int *data; } Buffer;\nvoid buffer_init(Buffer *b);\n")

        with open(source_path, "w", encoding="utf-8") as f:
            f.write('#include "buffer.h"\nvoid buffer_init(Buffer *b) { b->data = (int *)malloc(10 * sizeof(int)); }\n')

        with open(main_path, "w", encoding="utf-8") as f:
            f.write('#include "buffer.h"\nint main(void) { Buffer b; buffer_init(&b); return 0; }\n')

        with open(test_runner_path, "w", encoding="utf-8") as f:
            f.write('#include "buffer.h"\nint main(void) { Buffer b; buffer_init(&b); assert(b.data != 0); return 0; }\n')

        generate_makefile(temp_dir, "buffer_app", "c")

        issues = analyze_c_bugs(temp_dir)
        assert len(issues) >= 1
        assert any(i['type'] == 'missing_header_guard' for i in issues)
        assert any(i['type'] == 'missing_include' for i in issues)

        success, msg = debug_c_project(temp_dir)
        assert success is True
        assert "All C/C++ files compiled" in msg
    finally:
        shutil.rmtree(temp_dir)


def test_c_queue_generation_and_execution():
    temp_dir = tempfile.mkdtemp()
    project_name = "test_queue_c"
    try:
        manager = SDLCCrewManager(project_name=project_name)
        # Point project_dir to temp_dir for testing isolation
        manager.project_dir = temp_dir
        manager.project_language = "c"

        manager._generate_c_code("Create a queue data structure in C with enqueue and dequeue")
        manager._generate_c_tests(temp_dir)

        makefile_path = generate_makefile(temp_dir, project_name, "c")
        assert os.path.exists(makefile_path)

        comp_ok, comp_out = compile_project(temp_dir)
        assert comp_ok is True, f"Compilation failed: {comp_out}"

        test_ok, test_out = run_c_tests(temp_dir)
        assert test_ok is True, f"Tests failed: {test_out}"
        assert "tests passed" in test_out.lower()
    finally:
        shutil.rmtree(temp_dir)


def test_cpp_calculator_generation_and_execution():
    temp_dir = tempfile.mkdtemp()
    project_name = "test_calc_cpp"
    try:
        manager = SDLCCrewManager(project_name=project_name)
        manager.project_dir = temp_dir
        manager.project_language = "cpp"

        manager._generate_c_code("Create a calculator in C++ with add, subtract, multiply, divide")
        manager._generate_c_tests(temp_dir)

        makefile_path = generate_makefile(temp_dir, project_name, "cpp")
        assert os.path.exists(makefile_path)

        comp_ok, comp_out = compile_project(temp_dir)
        assert comp_ok is True, f"Compilation failed: {comp_out}"

        test_ok, test_out = run_c_tests(temp_dir)
        assert test_ok is True, f"Tests failed: {test_out}"
        assert "tests passed" in test_out.lower()
    finally:
        shutil.rmtree(temp_dir)


def test_c_impact_tools_mapping():
    temp_dir = tempfile.mkdtemp()
    try:
        test_dir = os.path.join(temp_dir, "tests")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "test_runner.c"), "w", encoding="utf-8") as f:
            f.write('#include "queue.h"\n')

        tests = list_test_files(temp_dir)
        assert "tests/test_runner.c" in tests

        report = generate_test_impact_report(["queue.c"], temp_dir)
        assert "queue.c -> tests/test_runner.c" in report
    finally:
        shutil.rmtree(temp_dir)


def test_c_function_reference_and_db_indexing():
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)
    temp_dir = tempfile.mkdtemp()
    project_name = "test_c_func_ref"
    try:
        from database.db_manager import DBManager
        db = DBManager(db_path=temp_db_path)
        manager = SDLCCrewManager(project_name=project_name)
        manager.project_dir = temp_dir
        manager.project_language = "c"
        manager.db = db
        manager.project_id = db.register_project(project_name, temp_dir)
        manager.reports_dir = os.path.join(temp_dir, "reports")
        os.makedirs(manager.reports_dir, exist_ok=True)

        manager._generate_c_code("Create a vector module in C")

        # Verify C/C++ functions were stored in SQLite DB
        db_fns = db.get_c_cpp_functions(manager.project_id)
        assert len(db_fns) >= 2

        # Verify c_cpp_functions.json was saved in reports directory
        json_report_path = os.path.join(manager.reports_dir, "c_cpp_functions.json")
        assert os.path.exists(json_report_path)

        # Test tool get_c_cpp_functions
        from tools.project_tools import get_c_cpp_functions
        ref_text = get_c_cpp_functions(temp_dir)
        assert "Core C/C++ Functions Reference" in ref_text
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        shutil.rmtree(temp_dir)

