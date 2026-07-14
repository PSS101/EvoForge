import textwrap
from tools.requirement_tools import parse_markdown_sections, classify_requirements


def test_parse_markdown_sections_extracts_list_items():
    markdown = textwrap.dedent(
        """
        # Software Requirements Specification (SRS)
        ## Functional Requirements
        - The system shall add numbers.
        - The system shall subtract numbers.

        ## Non-Functional Requirements
        - The system shall respond within 200ms.
        """
    )
    sections = parse_markdown_sections(markdown)
    assert sections["Functional Requirements"] == [
        "The system shall add numbers.",
        "The system shall subtract numbers."
    ]
    assert sections["Non-Functional Requirements"] == [
        "The system shall respond within 200ms."
    ]


def test_classify_requirements_detects_new_modified_removed():
    old_srs = textwrap.dedent(
        """
        # Software Requirements Specification (SRS)
        ## Functional Requirements
        - The system shall add numbers.
        - The system shall subtract numbers.
        """
    )
    new_srs = textwrap.dedent(
        """
        # Software Requirements Specification (SRS)
        ## Functional Requirements
        - The system shall add numbers.
        - The system shall multiply numbers.
        """
    )
    merged, delta_report, classified = classify_requirements(old_srs, new_srs)
    assert "- [UNCHANGED] The system shall add numbers." in merged
    assert any(item["tag"] == "NEW" and "multiply" in item["text"] for item in classified)
    assert any(item["tag"] == "REMOVED" and "subtract" in item["text"] for item in classified)
    assert "New requirements: 1" in delta_report
    assert "Removed requirements: 1" in delta_report
