import os
import shutil
import tempfile
import pytest
from agents.sdlc_crew import SDLCCrewManager
from tools.build_tools import generate_makefile

def test_mixed_pattern_file_extraction():
    manager = SDLCCrewManager("temp_mixed_proj")
    
    mixed_llm_output = """
Here are the files for your application:

--- FILE: src/main.cpp ---
```cpp
#include <iostream>
int main() { return 0; }
```

```cpp filename="include/app.hpp"
#ifndef APP_HPP
#define APP_HPP
void run();
#endif
```

### `src/app.cpp`
```cpp
#include "app.hpp"
void run() {}
```
"""
    file_map = manager._extract_file_map(mixed_llm_output)
    assert "src/main.cpp" in file_map
    assert "include/app.hpp" in file_map
    assert "src/app.cpp" in file_map
    assert len(file_map) == 3

def test_nested_directory_makefile_generation():
    temp_dir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(temp_dir, "include", "deep"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "src", "core"), exist_ok=True)
        
        with open(os.path.join(temp_dir, "include", "deep", "util.h"), "w") as f:
            f.write("#ifndef UTIL_H\n#define UTIL_H\nvoid util();\n#endif\n")
        with open(os.path.join(temp_dir, "src", "core", "util.c"), "w") as f:
            f.write("#include \"util.h\"\nvoid util() {}\n")
            
        makefile_path = generate_makefile(temp_dir, "nested_proj", "c")
        assert os.path.exists(makefile_path)
        with open(makefile_path) as f:
            content = f.read()
            assert "-Iinclude/deep" in content
            assert "-Isrc/core" in content
            assert "SRC_SRC_CORE" in content
    finally:
        shutil.rmtree(temp_dir)
