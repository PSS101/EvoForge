import re
import os

# --- Pattern sets ---
_CPP_PATTERNS = [
    r'\bc\+\+', r'\bcpp\b', r'using\s+c\+\+', r'c\+\+\s+language',
    r'c\+\+\s+code', r'write\s+in\s+c\+\+', r'\bg\+\+', r'\.cpp\b', r'c/c\+\+'
]

_C_PATTERNS = [
    r'\bin\s+c(?!\+)\b', r'\bc\s+program\b', r'\bc\s+language\b', r'\bc\s+code\b',
    r'using\s+c(?!\+)\b', r'\.c\s+file\b', r'\bgcc\b', r'write\s+in\s+c(?!\+)\b'
]

_PYTHON_PATTERNS = [
    r'\bpython\b', r'\bpy\b', r'\bpytest\b', r'in\s+python', r'python\s+code', r'\.py\b'
]

def detect_language(prompt: str) -> str:
    """Detect programming language from a user prompt.

    Returns:
        'cpp'    – C++ project
        'c'      – C project
        'python' – Python project (default if language is not explicitly mentioned)
    """
    if not prompt:
        return 'python'

    text = prompt.lower()

    cpp_score = sum(1 for p in _CPP_PATTERNS if re.search(p, text))
    c_score   = sum(1 for p in _C_PATTERNS   if re.search(p, text))
    py_score  = sum(1 for p in _PYTHON_PATTERNS if re.search(p, text))

    if cpp_score > 0 and cpp_score >= c_score:
        return 'cpp'
    if c_score > 0:
        return 'c'
    if py_score > 0:
        return 'python'

    # Default to Python when language is not explicitly specified
    return 'python'


def get_language_label(language: str) -> str:
    """Return a human-readable label for the language code."""
    return {'python': 'Python', 'c': 'C', 'cpp': 'C++'}.get(language, 'Python')


def get_language_emoji(language: str) -> str:
    """Return the emoji icon for the language code."""
    return {'python': '🐍 Python', 'c': '⚙️ C', 'cpp': '⚡ C++'}.get(language, '🐍 Python')


def get_source_extensions(language: str):
    """Return the set of source/header file extensions for the language."""
    if language == 'cpp':
        return {'.cpp', '.cxx', '.cc', '.c', '.h', '.hpp', '.hxx'}
    if language == 'c':
        return {'.c', '.h'}
    return {'.py'}


def save_project_language(project_dir: str, language: str) -> None:
    """Persist the language tag inside the project directory."""
    lang_file = os.path.join(project_dir, '.evoforge_lang')
    with open(lang_file, 'w', encoding='utf-8') as f:
        f.write(language)


def load_project_language(project_dir: str) -> str:
    """Load the persisted language tag, falling back to file-extension detection."""
    lang_file = os.path.join(project_dir, '.evoforge_lang')
    if os.path.exists(lang_file):
        with open(lang_file, 'r', encoding='utf-8') as f:
            return f.read().strip()

    # Fallback: sniff from file extensions
    for root, _, files in os.walk(project_dir):
        for fname in files:
            if fname.endswith(('.cpp', '.cxx', '.cc')):
                return 'cpp'
            if fname.endswith('.c'):
                return 'c'
    return 'python'


def has_explicit_language(prompt: str) -> bool:
    """Return True if user prompt explicitly mentions C, C++, or Python."""
    if not prompt:
        return False
    text = prompt.lower()
    return any(re.search(p, text) for p in _CPP_PATTERNS + _C_PATTERNS + _PYTHON_PATTERNS)

