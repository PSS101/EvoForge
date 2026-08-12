import sqlite3
import os
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "project_state.db")

class DBManager:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # File Registry
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL, -- 'source', 'test', 'doc', 'spec'
                    content_hash TEXT NOT NULL,
                    last_modified TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    UNIQUE(project_id, file_path)
                );
            """)
            # SDLC Runs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sdlc_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    srs_hash TEXT,
                    design_hash TEXT,
                    status TEXT, -- 'success', 'failed'
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
            """)
            # SRS version history for incremental comparison
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS srs_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    version INTEGER,
                    content_hash TEXT,
                    content TEXT,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
            """)
            # Dependency graph storage and extracted metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dependency_graphs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    graph_type TEXT,
                    file_path TEXT,
                    graph_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
            """)
            # C/C++ Functions table for code generation reference
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS c_cpp_functions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    file_path TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    return_type TEXT,
                    parameters TEXT,
                    signature TEXT,
                    is_core INTEGER DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    UNIQUE(project_id, file_path, function_name)
                );
            """)
            # Standard Library & Built-in C/C++ Functions and Data Types table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS c_cpp_stdlib (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    header TEXT NOT NULL,
                    symbol_type TEXT NOT NULL,
                    symbol_name TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    description TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'both',
                    UNIQUE(symbol_name, header)
                );
            """)
            conn.commit()
            self.seed_c_cpp_stdlib()

    def seed_c_cpp_stdlib(self):
        entries = [
            ("algorithm", "<algorithm>", "function", "std::max", "template<class T> const T& max(const T& a, const T& b)", "Returns the larger of a and b.", "cpp"),
            ("algorithm", "<algorithm>", "function", "std::min", "template<class T> const T& min(const T& a, const T& b)", "Returns the smaller of a and b.", "cpp"),
            ("algorithm", "<algorithm>", "function", "std::sort", "template<class RandomIt> void sort(RandomIt first, RandomIt last)", "Sorts elements in range [first, last) in ascending order.", "cpp"),
            ("algorithm", "<algorithm>", "function", "std::find", "template<class InputIt, class T> InputIt find(InputIt first, InputIt last, const T& value)", "Finds first element matching value in range [first, last).", "cpp"),
            ("algorithm", "<algorithm>", "function", "std::reverse", "template<class BidirIt> void reverse(BidirIt first, BidirIt last)", "Reverses the order of elements in range [first, last).", "cpp"),
            ("algorithm", "<algorithm>", "function", "std::clamp", "template<class T> const T& clamp(const T& v, const T& lo, const T& hi)", "Clamps v between lo and hi bounds.", "cpp"),
            ("numeric", "<numeric>", "function", "std::accumulate", "template<class InputIt, class T> T accumulate(InputIt first, InputIt last, T init)", "Computes the sum of elements in range [first, last).", "cpp"),
            ("algorithm", "<algorithm>", "function", "std::lower_bound", "template<class ForwardIt, class T> ForwardIt lower_bound(ForwardIt first, ForwardIt last, const T& value)", "Returns iterator to first element not less than value.", "cpp"),
            ("algorithm", "<algorithm>", "function", "std::upper_bound", "template<class ForwardIt, class T> ForwardIt upper_bound(ForwardIt first, ForwardIt last, const T& value)", "Returns iterator to first element greater than value.", "cpp"),
            ("algorithm", "<algorithm>", "function", "std::swap", "template<class T> void swap(T& a, T& b)", "Swaps values of two objects.", "cpp"),
            ("utility", "<utility>", "type", "std::pair", "template<class T1, class T2> struct pair { T1 first; T2 second; }", "Holds two heterogeneous objects.", "cpp"),
            ("container", "<vector>", "type", "std::vector", "template<class T> class vector", "Dynamic contiguous array container (push_back, pop_back, size, clear, at).", "cpp"),
            ("container", "<string>", "type", "std::string", "using string = std::basic_string<char>", "String container class (length, substr, find, c_str, append).", "cpp"),
            ("container", "<map>", "type", "std::map", "template<class Key, class T> class map", "Sorted associative container mapping unique keys to values.", "cpp"),
            ("container", "<unordered_map>", "type", "std::unordered_map", "template<class Key, class T> class unordered_map", "Unordered hash table mapping unique keys to values.", "cpp"),
            ("container", "<set>", "type", "std::set", "template<class Key> class set", "Sorted set of unique keys.", "cpp"),
            ("memory", "<memory>", "type", "std::unique_ptr", "template<class T> class unique_ptr", "Smart pointer with sole ownership management (std::make_unique).", "cpp"),
            ("memory", "<memory>", "type", "std::shared_ptr", "template<class T> class shared_ptr", "Smart pointer with shared reference-counted ownership (std::make_shared).", "cpp"),
            ("utility", "<optional>", "type", "std::optional", "template<class T> class optional", "Manages an optional contained value (has_value, value).", "cpp"),
            ("math", "<cmath>", "function", "std::pow", "double pow(double base, double exp)", "Computes base raised to power exp.", "both"),
            ("math", "<cmath>", "function", "std::sqrt", "double sqrt(double arg)", "Computes square root of arg.", "both"),
            ("math", "<cmath>", "function", "std::abs", "int abs(int n) / double abs(double n)", "Computes absolute value.", "both"),
            ("math", "<cmath>", "function", "std::floor", "double floor(double arg)", "Computes largest integer not greater than arg.", "both"),
            ("math", "<cmath>", "function", "std::ceil", "double ceil(double arg)", "Computes smallest integer not less than arg.", "both"),
            ("math", "<cmath>", "function", "std::log", "double log(double arg)", "Computes natural logarithm of arg.", "both"),
            ("math", "<cmath>", "function", "std::sin", "double sin(double arg)", "Computes sine of arg in radians.", "both"),
            ("math", "<cmath>", "function", "std::cos", "double cos(double arg)", "Computes cosine of arg in radians.", "both"),
            ("memory", "<stdlib.h>", "function", "malloc", "void* malloc(size_t size)", "Allocates uninitialized memory block of size bytes.", "both"),
            ("memory", "<stdlib.h>", "function", "free", "void free(void* ptr)", "Deallocates memory space previously allocated by malloc/calloc.", "both"),
            ("memory", "<stdlib.h>", "function", "realloc", "void* realloc(void* ptr, size_t new_size)", "Reallocates memory block to new size.", "both"),
            ("memory", "<stdlib.h>", "function", "calloc", "void* calloc(size_t num, size_t size)", "Allocates memory for array of num elements zero-initialized.", "both"),
            ("io", "<iostream>", "type", "std::cout", "extern std::ostream cout", "Standard output stream object.", "cpp"),
            ("io", "<iostream>", "type", "std::cin", "extern std::istream cin", "Standard input stream object.", "cpp"),
            ("io", "<stdio.h>", "function", "printf", "int printf(const char* format, ...)", "Prints formatted output to stdout.", "both"),
            ("io", "<stdio.h>", "function", "scanf", "int scanf(const char* format, ...)", "Reads formatted data from stdin.", "both"),
            ("io", "<stdio.h>", "function", "snprintf", "int snprintf(char* buf, size_t buf_size, const char* format, ...)", "Safe formatted string output into buffer.", "both"),
            ("io", "<string.h>", "function", "memcpy", "void* memcpy(void* dest, const void* src, size_t count)", "Copies count bytes from src to dest.", "both"),
            ("io", "<string.h>", "function", "memset", "void* memset(void* dest, int ch, size_t count)", "Fills buffer with ch character value.", "both"),
            ("io", "<string.h>", "function", "strncpy", "char* strncpy(char* dest, const char* src, size_t count)", "Copies up to count characters from src to dest.", "both"),
        ]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM c_cpp_stdlib")
            if cursor.fetchone()[0] == 0:
                cursor.executemany("""
                    INSERT OR IGNORE INTO c_cpp_stdlib (category, header, symbol_type, symbol_name, signature, description, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, entries)
                conn.commit()

    def get_c_cpp_stdlib(self, category=None, language=None):
        self.seed_c_cpp_stdlib()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT category, header, symbol_type, symbol_name, signature, description, language FROM c_cpp_stdlib WHERE 1=1"
            params = []
            if category:
                query += " AND category = ?"
                params.append(category)
            if language and language != "both":
                query += " AND (language = ? OR language = 'both')"
                params.append(language)
            query += " ORDER BY category, symbol_name"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    "category": r[0],
                    "header": r[1],
                    "symbol_type": r[2],
                    "symbol_name": r[3],
                    "signature": r[4],
                    "description": r[5],
                    "language": r[6]
                }
                for r in rows
            ]


    def register_project(self, name, path):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO projects (name, path) VALUES (?, ?)", (name, path)
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                cursor.execute("SELECT id FROM projects WHERE name = ?", (name,))
                return cursor.fetchone()[0]

    def get_project(self, name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, path FROM projects WHERE name = ?", (name,))
            return cursor.fetchone()

    def register_file(self, project_id, file_path, file_type, content_hash):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO file_registry (project_id, file_path, file_type, content_hash, last_modified)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id, file_path) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    last_modified = excluded.last_modified
            """, (project_id, file_path, file_type, content_hash, now))
            conn.commit()

    def get_file_registry(self, project_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT file_path, file_type, content_hash, last_modified FROM file_registry WHERE project_id = ?",
                (project_id,)
            )
            return cursor.fetchall()

    def get_registered_file(self, project_id, file_path):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT file_path, file_type, content_hash, last_modified FROM file_registry WHERE project_id = ? AND file_path = ?",
                (project_id, file_path)
            )
            return cursor.fetchone()

    def log_run(self, project_id, srs_hash, design_hash, status):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sdlc_runs (project_id, srs_hash, design_hash, status)
                VALUES (?, ?, ?, ?)
            """, (project_id, srs_hash, design_hash, status))
            conn.commit()
            return cursor.lastrowid

    def get_last_run(self, project_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT srs_hash, design_hash, status FROM sdlc_runs
                WHERE project_id = ? ORDER BY run_date DESC LIMIT 1
            """, (project_id,))
            return cursor.fetchone()

    def store_srs_version(self, project_id, content, note=None):
        from tools.file_tools import calculate_content_hash
        content_hash = calculate_content_hash(content)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(version) FROM srs_versions WHERE project_id = ?",
                (project_id,)
            )
            val = cursor.fetchone()[0]
            next_version = (val or 0) + 1
            cursor.execute("""
                INSERT INTO srs_versions (project_id, version, content_hash, content, note)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, next_version, content_hash, content, note))
            conn.commit()
            return cursor.lastrowid

    def store_dependency_graph(self, project_id, graph_type, graph_json, file_path=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO dependency_graphs (project_id, graph_type, file_path, graph_json)
                VALUES (?, ?, ?, ?)
            """, (project_id, graph_type, file_path, graph_json))
            conn.commit()
            return cursor.lastrowid

    def store_c_cpp_functions(self, project_id, file_path, functions_list):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            for fn in functions_list:
                name = fn.get("name", "")
                if not name:
                    continue
                return_type = fn.get("return_type", "void")
                params = fn.get("params", [])
                params_str = ", ".join(params) if isinstance(params, list) else str(params)
                signature = fn.get("signature", f"{return_type} {name}({params_str})")
                is_core = fn.get("is_core", 1)

                cursor.execute("""
                    INSERT INTO c_cpp_functions (project_id, file_path, function_name, return_type, parameters, signature, is_core, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id, file_path, function_name) DO UPDATE SET
                        return_type = excluded.return_type,
                        parameters = excluded.parameters,
                        signature = excluded.signature,
                        is_core = excluded.is_core,
                        last_updated = excluded.last_updated
                """, (project_id, file_path, name, return_type, params_str, signature, is_core, now))
            conn.commit()

    def get_c_cpp_functions(self, project_id, core_only=False):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if core_only:
                cursor.execute("""
                    SELECT file_path, function_name, return_type, parameters, signature, is_core
                    FROM c_cpp_functions WHERE project_id = ? AND is_core = 1
                    ORDER BY file_path, function_name
                """, (project_id,))
            else:
                cursor.execute("""
                    SELECT file_path, function_name, return_type, parameters, signature, is_core
                    FROM c_cpp_functions WHERE project_id = ?
                    ORDER BY file_path, function_name
                """, (project_id,))
            rows = cursor.fetchall()
            return [
                {
                    "file_path": r[0],
                    "function_name": r[1],
                    "return_type": r[2],
                    "parameters": r[3],
                    "signature": r[4],
                    "is_core": r[5]
                }
                for r in rows
            ]

    def clear_c_cpp_functions(self, project_id, file_path=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if file_path:
                cursor.execute("DELETE FROM c_cpp_functions WHERE project_id = ? AND file_path = ?", (project_id, file_path))
            else:
                cursor.execute("DELETE FROM c_cpp_functions WHERE project_id = ?", (project_id,))
            conn.commit()

