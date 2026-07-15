import importlib

def test_import_project_modules():
    modules = [
        "generated_code_1",
    ]
    for module in modules:
        importlib.import_module(module)
