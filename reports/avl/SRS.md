# Software Requirements Specification (SRS)
## SRS.md
## 1. Introduction & Project Scope
## 1.1 Purpose
- [NEW] The purpose of this Software Requirements Specification (SRS) is to define the functional and non‑functional requirements for a Python implementation of an AVL (Adelson‑Velsky and Landis) self‑balancing binary search tree. The system shall provide efficient, reliable, and maintainable operations for insertion, deletion, searching, and traversal while maintaining strict balance properties.
## 1.2 System Vision
- [NEW] The envisioned product is a reusable Python library that can be integrated into larger applications requiring ordered data structures with guaranteed logarithmic time complexity for core operations. It should expose a clean API, support serialization/deserialization, and provide diagnostic information for debugging and monitoring.
## 1.3 Product Perspective
- [NEW] This product is an independent module that will be packaged as a pip‑installable library (`avl_tree`). It will depend only on the Python Standard Library (Python ≥ 3.8). The library will not interact with external services or databases; persistence, if required, will be handled by client code through serialization.
## 1.4 User Characteristics
- [NEW] **Software Engineers**: Developers who need a balanced binary search tree for in‑memory data structures.
- [NEW] **Data Scientists**: Users requiring efficient sorted collections for algorithmic tasks.
- [NEW] **Educators/Students**: Individuals learning about self‑balancing trees and their properties.
## 1.5 Definitions & Acronyms
- [NEW] | Term | Definition |
- [NEW] |------|------------|
- [NEW] | AVL Tree | A binary search tree that maintains a balance factor of −1, 0, or +1 for every node. |
- [NEW] | Node | An element in the tree containing a key, optional value, left and right child references, height, and balance factor. |
- [NEW] | Balance Factor | The difference between the heights of the left and right subtrees of a node. |
- [NEW] | Rotation | A local restructuring operation (left or right) that restores balance after insertions or deletions. |
- [NEW] | API | Application Programming Interface – the set of functions exposed to client code. |
- [NEW] | CLI | Command Line Interface – optional interactive shell for testing. |
## 2. References & Applicable Standards
- [NEW] ISO/IEC/IEEE 29148:2018 – Software Requirements Specification.
- [NEW] Python 3.8+ Documentation – https://docs.python.org/3/
- [NEW] PEP 8 – Style Guide for Python Code (for maintainability considerations).
- [NEW] JSON 1.0 Specification – https://www.json.org/json-en.html (serialization format).
## 3. Specific Requirements
## 3.1 External Interface Requirements
## 3.1.1 User Interfaces
- [NEW] **[NEW]** The system shall provide a command‑line interface (`avl_cli.py`) that allows users to perform insert, delete, search, and traversal operations interactively.
- [NEW] **[NEW]** The CLI shall display clear prompts, accept user input, and present results in a human‑readable format.
## 3.1.2 API/CLI Interfaces
- [NEW] **[NEW]** The library shall expose the following public functions:
- [NEW] `insert(key: Any) -> None`
- [NEW] `delete(key: Any) -> None`
- [NEW] `search(key: Any) -> Optional[Any]`
- [NEW] `inorder_traversal() -> List[Any]`
- [NEW] `preorder_traversal() -> List[Any]`
- [NEW] `postorder_traversal() -> List[Any]`
- [NEW] `serialize() -> str` (JSON string)
- [NEW] `deserialize(json_str: str) -> None`
- [NEW] **[NEW]** All API functions shall raise a `ValueError` if the input key is not comparable to existing keys.
- [NEW] **[NEW]** The CLI shall map user commands (`insert`, `delete`, `search`, `inorder`, `preorder`, `postorder`, `serialize`, `deserialize`) to the corresponding API calls.
## 3.1.3 Data Exchange Formats
- [NEW] **[NEW]** Serialization output shall be a JSON array of objects, each representing a node with fields: `key`, `value` (optional), `left`, `right`. The structure must preserve tree topology.
- [NEW] **[NEW]** Deserialization shall accept the same JSON format and reconstruct an AVL tree with identical structure and balance properties.
## 3.2 System Capabilities & Functional Requirements
## 3.2.1 Core Operations
- [NEW] **[NEW]** The system shall allow insertion of a key (and optional value) into the AVL tree while maintaining balance.
- [NEW] **[NEW]** The system shall allow deletion of a key from the AVL tree while maintaining balance.
- [NEW] **[NEW]** The system shall support searching for a key and return its associated value if present, or indicate absence.
- [NEW] **[NEW]** The system shall provide inorder, preorder, and postorder traversal methods returning lists of keys in the respective order.
## 3.2.2 Input Validation & Error Handling
- [NEW] **[NEW]** For `insert`, if the key already exists, the system shall update its value without altering tree structure.
- [NEW] **[NEW]** For `delete`, if the key does not exist, the system shall raise a `KeyError` with an informative message.
- [NEW] **[NEW]** All public functions shall validate that input keys are of comparable types; otherwise, they shall raise a `TypeError`.
- [NEW] **[NEW]** The CLI shall handle invalid commands gracefully by displaying usage information.
## 3.2.3 Data Processing
- [NEW] **[NEW]** After each insertion or deletion, the system shall recompute node heights and balance factors up to the root.
- [NEW] **[NEW]** Rotations (single left/right, double left‑right, double right‑left) shall be performed as needed to restore AVL balance.
## 3.2.4 Status Monitoring
- [NEW] **[NEW]** The library shall expose a `get_height()` method returning the height of the tree.
- [NEW] **[NEW]** The library shall expose a `is_balanced()` method that verifies all nodes satisfy the AVL balance factor constraint.
## 3.3 System Quality Attributes & Non‑Functional Requirements
## 3.3.1 Performance & Latency
- [NEW] **[NEW]** Insertion, deletion, and search operations shall have worst‑case time complexity O(log n), where n is the number of nodes.
- [NEW] **[NEW]** Traversal methods shall operate in O(n) time.
## 3.3.2 Reliability & Safety
- [NEW] **[NEW]** The system shall not lose data during normal operation; all modifications must be immediately reflected in subsequent operations.
- [NEW] **[NEW]** In the event of an exception, the tree shall remain in a consistent state (no partial updates).
## 3.3.3 Maintainability
- [NEW] **[NEW]** Code documentation shall follow PEP 257 docstring conventions for all public functions and classes.
- [NEW] **[NEW]** The library shall be structured into modules: `node.py`, `avl_tree.py`, `cli.py`.
## 3.3.4 Security & Verification
- [NEW] **[NEW]** Input validation shall prevent injection of malicious data that could corrupt the tree structure.
- [NEW] **[NEW]** Unit tests shall cover at least 90 % code coverage for core functionality.
## 3.4 Operational & Design Constraints
- [NEW] **[NEW]** The library shall be compatible with Python ≥ 3.8 and must not use external dependencies beyond the Standard Library.
- [NEW] **[NEW]** Memory usage shall be O(n) for storing n nodes; no additional large data structures are permitted during operations.
- [NEW] **[NEW]** All public methods shall return promptly, ensuring that no single operation exceeds 100 ms on typical hardware for trees up to 10⁶ nodes.
## 4. Verification Criteria & Acceptance Tests
- [NEW] | Requirement | Verification Method | Acceptance Criterion |
- [NEW] |-------------|----------------------|----------------------|
- [NEW] | Insertion maintains AVL balance | Unit test: insert sequence of random keys, then call `is_balanced()` | Returns True |
- [NEW] | Deletion maintains AVL balance | Unit test: delete random keys, then call `is_balanced()` | Returns True |
- [NEW] | Search returns correct value | Unit test: search for inserted keys and verify returned values | Matches expected |
- [NEW] | Duplicate key updates value | Unit test: insert key twice with different values, then search | Value equals last inserted |
- [NEW] | Delete non‑existent key raises KeyError | Unit test: delete absent key | Raises KeyError |
- [NEW] | Serialization/Deserialization preserves structure | Unit test: serialize tree, deserialize into new instance, compare traversals | Traversal lists identical |
- [NEW] | Performance O(log n) for operations | Benchmark test: insert 10⁶ keys, measure average operation time | < 100 ms per operation |
- [NEW] | Memory usage O(n) | Profiling test: monitor memory after inserting n nodes | Memory ≈ constant × n |
- [NEW] | CLI handles invalid commands | Integration test: feed invalid command to CLI, capture output | Displays help message |
## 5. Appendices & Supporting Information
## 5.1 Glossary
- [NEW] **AVL Tree** – Self‑balancing binary search tree.
- [NEW] **Node Height** – Length of the longest path from a node to a leaf.
- [NEW] **Balance Factor** – Difference between left and right subtree heights.
## 5.2 Assumption Log
- [NEW] | Assumption | Rationale |
- [NEW] |------------|-----------|
- [NEW] | Keys are comparable using `<` and `==`. | Required for binary search tree ordering. |
- [NEW] | Duplicate keys are allowed only as updates, not as separate nodes. | Simplifies balancing logic. |
- [NEW] | Serialization format is JSON; clients will handle persistence if needed. | Keeps library lightweight. |
- [NEW] ---
