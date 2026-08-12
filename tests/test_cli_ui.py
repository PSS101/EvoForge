import os
import pytest
from tools.cli_ui import (
    is_rich_available,
    fetch_project_portfolio,
    get_project_inspect_info,
    print_banner,
    print_triage_result,
    print_verification_summary,
    print_projects_portfolio,
    print_system_diagnostics,
    resolve_model_choice,
    get_active_model_info,
    prompt_model_selection
)

def test_is_rich_available():
    assert is_rich_available() is True

def test_fetch_project_portfolio():
    portfolio = fetch_project_portfolio()
    assert isinstance(portfolio, list)
    if portfolio:
        item = portfolio[0]
        assert "name" in item
        assert "path" in item
        assert "language" in item
        assert "file_count" in item
        assert "has_srs" in item

def test_get_project_inspect_info():
    project_dir, reports_dir, files_list, srs_content = get_project_inspect_info("calculator")
    assert "calculator" in project_dir
    assert isinstance(files_list, list)

def test_resolve_model_choice():
    # Option 1: Qwen 2.5 Coder 14B
    name1, tag1 = resolve_model_choice("1")
    assert name1 == "qwen 2.5 coder 14B"
    assert tag1 == "qwen2.5-coder:14b"

    name_qwen, tag_qwen = resolve_model_choice("qwen 2.5 coder 14B")
    assert name_qwen == "qwen 2.5 coder 14B"
    assert tag_qwen == "qwen2.5-coder:14b"

    # Option 2: GPT OSS 20B
    name2, tag2 = resolve_model_choice("2")
    assert name2 == "gpt OSS 20B"
    assert tag2 == "gpt-oss:20b"

    name_gpt, tag_gpt = resolve_model_choice("gpt OSS 20B")
    assert name_gpt == "gpt OSS 20B"
    assert tag_gpt == "gpt-oss:20b"

    # Default / Empty
    name_def, tag_def = resolve_model_choice("")
    assert name_def == "qwen 2.5 coder 14B"
    assert tag_def == "qwen2.5-coder:14b"

def test_prompt_model_selection(monkeypatch):
    # Simulate user choosing option 2 (gpt OSS 20B) via prompt
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda prompt_msg, default="1": "2")
    display_name, tag = prompt_model_selection()
    assert display_name == "gpt OSS 20B"
    assert tag == "gpt-oss:20b"
    assert os.getenv("OLLAMA_MODEL") == "gpt-oss:20b"

    # Simulate user choosing option 1 (qwen 2.5 coder 14B)
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda prompt_msg, default="1": "1")
    display_name, tag = prompt_model_selection()
    assert display_name == "qwen 2.5 coder 14B"
    assert tag == "qwen2.5-coder:14b"
    assert os.getenv("OLLAMA_MODEL") == "qwen2.5-coder:14b"

def test_print_functions_do_not_crash(capsys):
    print_banner()
    print_triage_result("test_proj", "new", "python")
    print_verification_summary(
        project_name="test_proj",
        language="python",
        compile_success=True,
        compile_output="",
        test_success=True,
        test_output="1 passed in 0.01s"
    )
    print_projects_portfolio([
        {"name": "demo", "language": "python", "file_count": 2, "has_srs": True, "path": "/tmp/demo"}
    ])
    print_system_diagnostics({"LLM_PROVIDER": "ollama"}, "Connected", True)
    captured = capsys.readouterr()
    assert len(captured.out) > 0

