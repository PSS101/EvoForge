import re
import difflib
from collections import OrderedDict
from typing import Dict, List, Tuple

LIST_ITEM_PATTERN = re.compile(r"^\s*[-*+]\s+(.*)$")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s*(.+)$")


def normalize_text(text: str) -> str:
    """Normalize requirement text for similarity comparison."""
    text = text or ""
    normalized = re.sub(r"[^a-z0-9 ]+", "", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def parse_markdown_sections(markdown_text: str) -> OrderedDict:
    """Parse a Markdown document into sections and list-item requirements."""
    sections: OrderedDict[str, List[str]] = OrderedDict()
    current_section = "Preamble"
    current_lines: List[str] = []

    for line in markdown_text.splitlines():
        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            if current_section in sections:
                sections[current_section].extend(current_lines)
            else:
                sections[current_section] = list(current_lines)
            heading_level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            # Treat the first H1 title as document metadata rather than a section name.
            if heading_level == 1 and heading_text.lower().startswith("software requirements specification"):
                current_section = "Preamble"
            else:
                current_section = heading_text
            current_lines = []
        else:
            current_lines.append(line)

    if current_section in sections:
        sections[current_section].extend(current_lines)
    else:
        sections[current_section] = list(current_lines)

    parsed_sections: OrderedDict[str, List[str]] = OrderedDict()
    for section_name, lines in sections.items():
        items: List[str] = []
        for line in lines:
            item_match = LIST_ITEM_PATTERN.match(line)
            if item_match:
                items.append(item_match.group(1).strip())
            elif line.strip() and not section_name == "Preamble":
                items.append(line.strip())
        parsed_sections[section_name] = items
    return parsed_sections


def strip_tag_prefix(text: str) -> str:
    """Strip any pre-existing requirement classification tag from text."""
    if not text:
        return ""
    return re.sub(r"^\s*(?:[-*+]\s*)?\[(NEW|MODIFIED|REMOVED|UNCHANGED)\]\s*", "", text, flags=re.IGNORECASE).strip()


def _match_best_pair(source_items: List[str], target_items: List[str], threshold: float = 0.85) -> Dict[int, Tuple[int, float]]:
    matches: Dict[int, Tuple[int, float]] = {}
    used_target_indices = set()

    for i, source in enumerate(source_items):
        best_ratio = 0.0
        best_j = -1
        for j, target in enumerate(target_items):
            if j in used_target_indices:
                continue
            ratio = difflib.SequenceMatcher(
                None,
                normalize_text(strip_tag_prefix(source)),
                normalize_text(strip_tag_prefix(target))
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_j = j
        if best_j >= 0 and best_ratio >= threshold:
            matches[i] = (best_j, best_ratio)
            used_target_indices.add(best_j)
    return matches


def classify_requirements(old_srs: str, new_srs: str) -> Tuple[str, str, List[Dict[str, str]]]:
    """Classify requirements between an old SRS and a new SRS, and generate tagged markdown."""
    old_sections = parse_markdown_sections(old_srs or "")
    new_sections = parse_markdown_sections(new_srs or "")

    old_items = []
    for section, items in old_sections.items():
        for item in items:
            clean_txt = strip_tag_prefix(item)
            if clean_txt:
                old_items.append({"section": section, "text": clean_txt})

    new_items = []
    for section, items in new_sections.items():
        for item in items:
            clean_txt = strip_tag_prefix(item)
            if clean_txt:
                new_items.append({"section": section, "text": clean_txt})

    old_texts = [item["text"] for item in old_items]
    new_texts = [item["text"] for item in new_items]

    matches = _match_best_pair(old_texts, new_texts, threshold=0.85)
    classified = []
    matched_old_indices = set()
    matched_new_indices = set()

    for old_index, (new_index, ratio) in matches.items():
        old_item = old_items[old_index]
        new_item = new_items[new_index]
        matched_old_indices.add(old_index)
        matched_new_indices.add(new_index)

        if normalize_text(old_item["text"]) == normalize_text(new_item["text"]):
            tag = "UNCHANGED"
        elif ratio >= 0.85:
            tag = "MODIFIED"
        else:
            tag = "NEW"

        classified.append({
            "tag": tag,
            "section": new_item["section"],
            "text": new_item["text"],
            "old_text": old_item["text"],
            "similarity": f"{ratio:.2f}"
        })

    for idx, new_item in enumerate(new_items):
        if idx in matched_new_indices:
            continue
        classified.append({
            "tag": "NEW",
            "section": new_item["section"],
            "text": new_item["text"],
            "old_text": "",
            "similarity": "0.00"
        })

    for idx, old_item in enumerate(old_items):
        if idx in matched_old_indices:
            continue
        classified.append({
            "tag": "REMOVED",
            "section": old_item["section"],
            "text": old_item["text"],
            "old_text": old_item["text"],
            "similarity": "0.00"
        })

    section_order = list(new_sections.keys())
    for section in old_sections.keys():
        if section not in section_order:
            section_order.append(section)

    section_items: Dict[str, List[Dict[str, str]]] = {section: [] for section in section_order}
    for item in classified:
        section_items.setdefault(item["section"], []).append(item)

    merged_sections: List[str] = ["# Software Requirements Specification (SRS)"]
    for section in section_order:
        if not section or section == "Preamble":
            continue
        merged_sections.append(f"## {section}")
        for item in section_items.get(section, []):
            clean_txt = strip_tag_prefix(item['text'])
            merged_sections.append(f"- [{item['tag']}] {clean_txt}")

    merged_markdown = "\n".join(merged_sections).strip() + "\n"
    delta_report = build_requirement_delta_report(classified, section_order)
    return merged_markdown, delta_report, classified


def build_requirement_delta_report(classified_items: List[Dict[str, str]], section_order: List[str]) -> str:
    """Build a structured delta report from classified requirement items."""
    counts = {"NEW": 0, "MODIFIED": 0, "REMOVED": 0, "UNCHANGED": 0}
    for item in classified_items:
        counts[item["tag"]] = counts.get(item["tag"], 0) + 1

    lines = [
        "# Requirement Delta Report",
        "",
        "## Summary",
        f"- New requirements: {counts['NEW']}",
        f"- Modified requirements: {counts['MODIFIED']}",
        f"- Removed requirements: {counts['REMOVED']}",
        f"- Unchanged requirements: {counts['UNCHANGED']}",
        "",
        "## Detailed Requirement Delta",
    ]

    section_items: Dict[str, List[Dict[str, str]]] = {section: [] for section in section_order}
    for item in classified_items:
        section_items.setdefault(item["section"], []).append(item)

    for section in section_order:
        if section == "Preamble" or not section:
            continue
        items = section_items.get(section, [])
        if not items:
            continue
        lines.extend([f"", f"### {section}", ""])
        for item in items:
            note = f" (matched old requirement: {item['old_text']})" if item["tag"] in ["MODIFIED", "REMOVED"] and item["old_text"] else ""
            lines.append(f"- [{item['tag']}] {item['text']}{note}")

    lines.append("")
    return "\n".join(lines)
