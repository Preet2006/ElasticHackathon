"""
Knowledge Base Engine – Elasticsearch-backed persistent store for CodeJanitor 2.0

Indexes every function and its dependencies into Elasticsearch (Elastic Cloud)
so they are persistent and searchable across different scan sessions.

Uses Tree-sitter for parsing and stores code units in the ``code-knowledge`` index.
"""

import logging
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Optional

from elasticsearch import Elasticsearch
from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import ConnectionTimeout, ApiError
from elasticsearch.helpers import bulk
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from tree_sitter import Parser, Language, Node
import tree_sitter_python

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── index configuration ──────────────────────────────────────────────────────

INDEX_NAME = "code-knowledge"

_EXCLUDE_DIRS = {
    "venv", "__pycache__", "node_modules", "dist", "build",
    ".tox", ".eggs", ".mypy_cache", ".pytest_cache", "site-packages",
}

INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
    },
    "mappings": {
        "properties": {
            "file_path":    {"type": "keyword"},
            "content":      {"type": "text", "analyzer": "standard"},
            "functions":    {"type": "keyword"},
            "imports":      {"type": "keyword"},
            "project_name": {"type": "keyword"},
            "analyzed_at":  {"type": "date"},
        }
    },
}


# ── main class ───────────────────────────────────────────────────────────────

class ElasticKnowledgeBase:
    """
    Elasticsearch-backed Knowledge Base for CodeJanitor.

    Replaces the old in-memory NetworkX graph with a persistent Elasticsearch
    index.  Each file is stored as a document with parsed functions, resolved
    imports, and full content.  Dependency resolution uses Elasticsearch
    queries instead of graph traversal.

    When ``ES_CLOUD_ID`` / ``ES_API_KEY`` are **not** configured the class
    transparently falls back to an in-memory dict so that unit tests and
    local development continue to work without a running cluster.

    Example::

        kb = ElasticKnowledgeBase()
        kb.build_graph(Path("./src"))

        # file + all direct dependencies
        context = kb.get_context("src/auth.py", depth=1)
    """

    # ── construction ─────────────────────────────────────────────────

    def __init__(self, project_name: Optional[str] = None):
        """
        Initialise the knowledge base.

        Args:
            project_name: Logical project / repo name used to partition the
                          index.  Falls back to ``Settings.project_name``.
        """
        settings = get_settings()
        self.project_name: str = project_name or settings.project_name
        self.parser: Parser = self._init_parser()

        # Local content cache – also serves backward-compat for code that
        # reads ``knowledge_base.file_contents`` directly (e.g. api.py).
        self.file_contents: Dict[str, str] = {}
        self.analyzed_files: Set[str] = set()

        # Session-local stats (populated by build_graph)
        self._total_import_edges: int = 0
        self._isolated_count: int = 0

        # ── Elasticsearch or in-memory fallback ──
        self._use_es = bool(settings.es_cloud_id and settings.es_api_key)
        if self._use_es:
            self.es: Optional[Elasticsearch] = self._init_client(settings)
            self._ensure_index()
            logger.info("Using Elasticsearch backend (index: %s)", INDEX_NAME)
        else:
            self.es = None
            self._memory_store: Dict[str, Dict] = {}
            logger.info(
                "ES credentials not configured – using in-memory fallback"
            )

    # ── client / parser init ─────────────────────────────────────────

    @staticmethod
    def _init_client(settings) -> Elasticsearch:
        """Create an Elasticsearch client using Cloud ID + API Key."""
        return Elasticsearch(
            cloud_id=settings.es_cloud_id,
            api_key=settings.es_api_key,
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )

    @staticmethod
    def _init_parser() -> Parser:
        """Initialise Tree-sitter Python parser."""
        lang = Language(tree_sitter_python.language())
        parser = Parser(lang)
        return parser

    def _ensure_index(self) -> None:
        """Create the ``code-knowledge`` index if it does not already exist."""
        try:
            if not self.es.indices.exists(index=INDEX_NAME):
                self.es.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
                logger.info("Created Elasticsearch index '%s'", INDEX_NAME)
            else:
                logger.debug("Index '%s' already exists", INDEX_NAME)
        except ApiError as exc:
            logger.error("Failed to create/check index: %s", exc)
            raise

    # ── indexing ──────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ESConnectionError, ConnectionTimeout)),
        reraise=True,
    )
    def index_code_unit(self, file_data: Dict) -> None:
        """
        Index a single code unit (file) into the ``code-knowledge`` index.

        Args:
            file_data: dict with keys ``file_path``, ``content``,
                       ``functions``, ``imports``, ``project_name``.
        """
        doc_id = self._make_doc_id(
            file_data["project_name"], file_data["file_path"]
        )
        doc = {
            "file_path":    file_data["file_path"],
            "content":      file_data["content"],
            "functions":    file_data["functions"],
            "imports":      file_data["imports"],
            "project_name": file_data["project_name"],
            "analyzed_at":  datetime.now(timezone.utc).isoformat(),
        }

        if self._use_es:
            self.es.index(index=INDEX_NAME, id=doc_id, document=doc)
        else:
            self._memory_store[doc_id] = doc

        logger.debug("Indexed %s", file_data["file_path"])

    @staticmethod
    def _make_doc_id(project_name: str, file_path: str) -> str:
        """Deterministic document ID from project + path."""
        return hashlib.sha256(
            f"{project_name}:{file_path}".encode()
        ).hexdigest()

    # ── build_graph ──────────────────────────────────────────────────

    def build_graph(
        self, repo_path: Path, project_name: Optional[str] = None
    ) -> None:
        """
        Walk a repository, parse every Python file with Tree-sitter,
        and bulk-index the results into Elasticsearch.

        Args:
            repo_path:     Root directory of the repository.
            project_name:  Override the project_name for this build.
        """
        if project_name:
            self.project_name = project_name

        logger.info("Building knowledge base for: %s", repo_path)

        if not repo_path.exists():
            logger.error("Repository path does not exist: %s", repo_path)
            return

        python_files = [
            f
            for f in repo_path.rglob("*.py")
            if not any(
                part.startswith(".") or part in _EXCLUDE_DIRS
                for part in f.relative_to(repo_path).parts
            )
        ]
        logger.info("Found %d Python files", len(python_files))

        actions: List[Dict] = []
        for file_path in python_files:
            action = self._process_file(file_path, repo_path)
            if action:
                actions.append(action)

        # ── persist ──
        if self._use_es and actions:
            success, errors = bulk(self.es, actions, raise_on_error=False)
            logger.info("Bulk indexed %d documents (%d errors)", success, len(errors))
            if errors:
                for err in errors[:5]:
                    logger.warning("Index error: %s", err)
            self.es.indices.refresh(index=INDEX_NAME)
        elif not self._use_es:
            for action in actions:
                self._memory_store[action["_id"]] = action["_source"]

        # ── compute session stats ──
        all_imported: Set[str] = set()
        file_imports: Dict[str, List[str]] = {}
        for action in actions:
            src = action["_source"]
            file_imports[src["file_path"]] = src["imports"]
            all_imported.update(src["imports"])

        self._total_import_edges = sum(len(v) for v in file_imports.values())
        self._isolated_count = sum(
            1
            for fp, imps in file_imports.items()
            if not imps and fp not in all_imported
        )

        logger.info(
            "Knowledge base built: %d files, %d import edges",
            len(self.analyzed_files),
            self._total_import_edges,
        )

    def _process_file(
        self, file_path: Path, repo_root: Path
    ) -> Optional[Dict]:
        """Parse a single Python file and return a bulk-index action dict."""
        try:
            rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            # local cache
            self.file_contents[rel_path] = content

            # Tree-sitter extraction
            imports = self._extract_imports(content, file_path, repo_root)
            functions = self._extract_functions(content)

            self.analyzed_files.add(rel_path)

            doc = {
                "file_path":    rel_path,
                "content":      content,
                "functions":    functions,
                "imports":      imports,
                "project_name": self.project_name,
                "analyzed_at":  datetime.now(timezone.utc).isoformat(),
            }

            return {
                "_index":  INDEX_NAME,
                "_id":     self._make_doc_id(self.project_name, rel_path),
                "_source": doc,
            }
        except Exception as exc:
            logger.warning("Error processing %s: %s", file_path, exc)
            return None

    # ── tree-sitter parsing ──────────────────────────────────────────

    def _extract_functions(self, content: str) -> List[str]:
        """Extract function and class names using Tree-sitter."""
        names: List[str] = []
        try:
            tree = self.parser.parse(bytes(content, "utf-8"))
            self._walk_for_functions(tree.root_node, names)
        except Exception as exc:
            logger.debug("Error extracting functions: %s", exc)
        return names

    def _walk_for_functions(self, node: Node, names: List[str]) -> None:
        """Recursively collect function_definition and class_definition names."""
        if node.type in ("function_definition", "class_definition"):
            for child in node.children:
                if child.type == "identifier":
                    names.append(child.text.decode("utf-8"))
                    break
        for child in node.children:
            self._walk_for_functions(child, names)

    def _extract_imports(
        self, content: str, file_path: Path, repo_root: Path
    ) -> List[str]:
        """Extract and resolve Python imports to repository-relative paths."""
        imports: List[str] = []
        try:
            tree = self.parser.parse(bytes(content, "utf-8"))
            for node in self._find_import_nodes(tree.root_node):
                resolved = self._resolve_import(node, file_path, repo_root)
                if resolved:
                    imports.extend(resolved)
        except Exception as exc:
            logger.debug("Error extracting imports from %s: %s", file_path, exc)
        return imports

    # -- AST helpers (ported from the original implementation) ----------

    def _find_import_nodes(self, node: Node) -> List[Node]:
        """Find all import_statement and import_from_statement nodes."""
        nodes: List[Node] = []
        if node.type in ("import_statement", "import_from_statement"):
            nodes.append(node)
        for child in node.children:
            nodes.extend(self._find_import_nodes(child))
        return nodes

    def _resolve_import(
        self, node: Node, current_file: Path, repo_root: Path
    ) -> List[str]:
        """Resolve an import AST node to repository-relative file paths."""
        resolved: List[str] = []
        try:
            if node.type == "import_statement":
                module_name = self._extract_module_name(node)
                if module_name:
                    path = self._find_module_file(
                        module_name, current_file, repo_root
                    )
                    if path:
                        resolved.append(path)

            elif node.type == "import_from_statement":
                module_name = self._extract_from_module_name(node)
                if module_name:
                    path = self._find_module_file(
                        module_name, current_file, repo_root
                    )
                    if path:
                        resolved.append(path)
                    for name in self._extract_imported_names(node):
                        full = f"{module_name}.{name}" if module_name else name
                        sub = self._find_module_file(
                            full, current_file, repo_root
                        )
                        if sub and sub not in resolved:
                            resolved.append(sub)

        except Exception as exc:
            logger.debug("Error resolving import %s: %s", node.text, exc)
        return resolved

    def _extract_imported_names(self, node: Node) -> List[str]:
        """Extract names from ``from module import x, y, z``."""
        names: List[str] = []
        found_import = False
        for child in node.children:
            if child.type == "import":
                found_import = True
                continue
            if found_import and child.type == "dotted_name":
                names.append(child.text.decode("utf-8"))
            elif found_import and child.type == "aliased_import":
                for sub in child.children:
                    if sub.type == "dotted_name":
                        names.append(sub.text.decode("utf-8"))
                        break
        return names

    def _extract_module_name(self, node: Node) -> Optional[str]:
        """Extract module name from ``import module`` statement."""
        for child in node.children:
            if child.type == "dotted_name":
                return child.text.decode("utf-8")
        return None

    def _extract_from_module_name(self, node: Node) -> Optional[str]:
        """Extract module name from ``from module import x`` statement."""
        for child in node.children:
            if child.type in ("dotted_name", "relative_import"):
                return child.text.decode("utf-8")
            if child.type == "aliased_import":
                for sub in child.children:
                    if sub.type == "dotted_name":
                        return sub.text.decode("utf-8")
        return None

    def _find_module_file(
        self, module_name: str, current_file: Path, repo_root: Path
    ) -> Optional[str]:
        """Map a Python module name to its relative file path in the repo."""
        stdlib_modules = {
            "os", "sys", "json", "time", "datetime", "re", "math", "random",
            "collections", "itertools", "functools", "typing", "pathlib",
            "logging", "unittest", "pytest", "sqlite3", "requests", "flask",
            "django", "numpy", "pandas", "docker", "networkx", "elasticsearch",
        }
        base = module_name.split(".")[0].lstrip(".")
        if base in stdlib_modules:
            return None
        if module_name.startswith("."):
            return self._resolve_relative_import(
                module_name, current_file, repo_root
            )
        return self._resolve_absolute_import(module_name, repo_root)

    def _resolve_relative_import(
        self, module_name: str, current_file: Path, repo_root: Path
    ) -> Optional[str]:
        """Resolve a relative import (e.g. ``.module`` or ``..module``)."""
        level = 0
        for ch in module_name:
            if ch == ".":
                level += 1
            else:
                break
        actual = module_name[level:]
        current_dir = current_file.parent
        for _ in range(level - 1):
            current_dir = current_dir.parent

        if actual:
            patterns = [
                current_dir / f"{actual}.py",
                current_dir / actual / "__init__.py",
                current_dir / actual.replace(".", "/") / "__init__.py",
                current_dir / f"{actual.replace('.', '/')}.py",
            ]
        else:
            patterns = [current_dir / "__init__.py"]

        for p in patterns:
            if p.exists() and p.is_file():
                try:
                    return str(p.relative_to(repo_root)).replace("\\", "/")
                except ValueError:
                    continue
        return None

    def _resolve_absolute_import(
        self, module_name: str, repo_root: Path
    ) -> Optional[str]:
        """Resolve an absolute import (``module.submodule`` → file path)."""
        module_path = module_name.replace(".", "/")
        for p in [
            repo_root / f"{module_path}.py",
            repo_root / module_path / "__init__.py",
        ]:
            if p.exists() and p.is_file():
                try:
                    return str(p.relative_to(repo_root)).replace("\\", "/")
                except ValueError:
                    continue
        return None

    # ── queries ──────────────────────────────────────────────────────

    def _get_document(self, file_path: str) -> Optional[Dict]:
        """Fetch a document by *file_path* for the current project."""
        if self._use_es:
            return self._es_get_document(file_path)
        return self._mem_get_document(file_path)

    # -- Elasticsearch query helpers ---

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ESConnectionError, ConnectionTimeout)),
        reraise=True,
    )
    def _es_get_document(self, file_path: str) -> Optional[Dict]:
        resp = self.es.search(
            index=INDEX_NAME,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"file_path": file_path}},
                            {"term": {"project_name": self.project_name}},
                        ]
                    }
                },
                "size": 1,
            },
        )
        hits = resp["hits"]["hits"]
        return hits[0]["_source"] if hits else None

    # -- In-memory query helpers ---

    def _mem_get_document(self, file_path: str) -> Optional[Dict]:
        for doc in self._memory_store.values():
            if (
                doc["file_path"] == file_path
                and doc["project_name"] == self.project_name
            ):
                return doc
        return None

    # ── dependency resolution ────────────────────────────────────────

    def _get_dependencies(self, file_path: str, depth: int) -> List[str]:
        """
        BFS to collect all transitive dependencies up to *depth* levels.
        """
        if self._use_es:
            return self._es_get_dependencies(file_path, depth)
        return self._mem_get_dependencies(file_path, depth)

    def _es_get_dependencies(self, file_path: str, depth: int) -> List[str]:
        """BFS via Elasticsearch – one query per depth level."""
        dependencies: List[str] = []
        visited: Set[str] = {file_path}
        current_level = [file_path]

        for _ in range(depth):
            if not current_level:
                break
            resp = self.es.search(
                index=INDEX_NAME,
                body={
                    "query": {
                        "bool": {
                            "must": [
                                {"terms": {"file_path": current_level}},
                                {"term": {"project_name": self.project_name}},
                            ]
                        }
                    },
                    "_source": ["file_path", "imports"],
                    "size": 1000,
                },
            )
            next_level: List[str] = []
            for hit in resp["hits"]["hits"]:
                for imp in hit["_source"].get("imports", []):
                    if imp not in visited:
                        visited.add(imp)
                        dependencies.append(imp)
                        next_level.append(imp)
            current_level = next_level

        return dependencies

    def _mem_get_dependencies(self, file_path: str, depth: int) -> List[str]:
        """BFS via the in-memory store."""
        dependencies: List[str] = []
        visited: Set[str] = {file_path}
        current_level = [file_path]

        for _ in range(depth):
            if not current_level:
                break
            next_level: List[str] = []
            for fp in current_level:
                doc = self._mem_get_document(fp)
                if doc:
                    for imp in doc.get("imports", []):
                        if imp not in visited:
                            visited.add(imp)
                            dependencies.append(imp)
                            next_level.append(imp)
            current_level = next_level

        return dependencies

    # ── public API ───────────────────────────────────────────────────

    def get_context(self, file_path: str, depth: int = 1) -> str:
        """
        Retrieve the full context for *file_path*: its own content plus
        the content of all dependencies up to *depth* levels.

        Returns a formatted string suitable for LLM prompts::

            === Context: utils/db.py ===
            [content]

            === Target: auth.py ===
            [content]
        """
        dependencies = self._get_dependencies(file_path, depth)

        parts: List[str] = []
        for dep in dependencies:
            content = self._get_content(dep)
            if content:
                parts.append(f"=== Context: {dep} ===\n")
                parts.append(content)
                parts.append("\n\n")

        target_content = self._get_content(file_path)
        if target_content:
            parts.append(f"=== Target: {file_path} ===\n")
            parts.append(target_content)

        return "".join(parts)

    def _get_content(self, file_path: str) -> Optional[str]:
        """Return file content from local cache or Elasticsearch."""
        if file_path in self.file_contents:
            return self.file_contents[file_path]
        doc = self._get_document(file_path)
        if doc:
            content = doc.get("content", "")
            self.file_contents[file_path] = content  # cache
            return content
        return None

    def get_imports(self, file_path: str) -> List[str]:
        """
        Return the resolved import list for *file_path*.

        Useful for verifying dependency edges (replaces
        ``graph.has_edge(A, B)`` – now: ``B in kb.get_imports(A)``).
        """
        doc = self._get_document(file_path)
        return doc.get("imports", []) if doc else []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ESConnectionError, ConnectionTimeout)),
        reraise=True,
    )
    def get_dependents(self, file_path: str) -> List[str]:
        """
        Find all files that **import** the given *file_path*.

        This is the Elasticsearch replacement for
        ``graph.predecessors(file_path)`` – a search query that finds every
        document where *file_path* appears in the ``imports`` list.
        """
        if self._use_es:
            return self._es_get_dependents(file_path)
        return self._mem_get_dependents(file_path)

    def _es_get_dependents(self, file_path: str) -> List[str]:
        resp = self.es.search(
            index=INDEX_NAME,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"imports": file_path}},
                            {"term": {"project_name": self.project_name}},
                        ]
                    }
                },
                "_source": ["file_path"],
                "size": 1000,
            },
        )
        return [hit["_source"]["file_path"] for hit in resp["hits"]["hits"]]

    def _mem_get_dependents(self, file_path: str) -> List[str]:
        return [
            doc["file_path"]
            for doc in self._memory_store.values()
            if doc["project_name"] == self.project_name
            and file_path in doc.get("imports", [])
        ]

    def get_graph_stats(self) -> Dict:
        """Return statistics about the knowledge base for this project."""
        total_files = len(self.analyzed_files)
        total_imports = self._total_import_edges

        if not total_files and self._use_es:
            # Fallback: query ES if build_graph was not called this session
            try:
                count_resp = self.es.count(
                    index=INDEX_NAME,
                    body={
                        "query": {
                            "term": {"project_name": self.project_name}
                        }
                    },
                )
                total_files = count_resp["count"]
            except Exception as exc:
                logger.warning("Stats count query failed: %s", exc)

        avg = total_imports / total_files if total_files else 0

        return {
            "total_files":         total_files,
            "total_imports":       total_imports,
            "analyzed_files":      len(self.analyzed_files),
            "isolated_files":      self._isolated_count,
            "avg_imports_per_file": round(avg, 2),
        }

    # ── visualisation ────────────────────────────────────────────────

    def visualize_dependencies(
        self, file_path: str, max_depth: int = 2
    ) -> str:
        """ASCII-tree visualisation of a file's dependency chain."""
        doc = self._get_document(file_path)
        if not doc:
            return f"File not found: {file_path}"

        lines = [file_path]
        self._build_tree(file_path, lines, 0, max_depth, set())
        return "\n".join(lines)

    def _build_tree(
        self,
        node: str,
        lines: List[str],
        depth: int,
        max_depth: int,
        visited: Set[str],
        prefix: str = "",
    ) -> None:
        """Recursively build dependency tree visualisation."""
        if depth >= max_depth or node in visited:
            return
        visited.add(node)

        doc = self._get_document(node)
        neighbors = doc.get("imports", []) if doc else []

        for i, neighbor in enumerate(neighbors):
            is_last = i == len(neighbors) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{neighbor}")
            next_prefix = prefix + ("    " if is_last else "│   ")
            self._build_tree(
                neighbor, lines, depth + 1, max_depth, visited, next_prefix
            )

    # ── utility ──────────────────────────────────────────────────────

    def clear_project(self, project_name: Optional[str] = None) -> int:
        """Delete all documents for a project.  Returns count deleted."""
        target = project_name or self.project_name

        if self._use_es:
            resp = self.es.delete_by_query(
                index=INDEX_NAME,
                body={"query": {"term": {"project_name": target}}},
                refresh=True,
            )
            deleted = resp.get("deleted", 0)
        else:
            to_remove = [
                k for k, v in self._memory_store.items()
                if v["project_name"] == target
            ]
            for k in to_remove:
                del self._memory_store[k]
            deleted = len(to_remove)

        logger.info("Deleted %d documents for project '%s'", deleted, target)
        return deleted


# ── backward compatibility ───────────────────────────────────────────────────

CodeKnowledgeBase = ElasticKnowledgeBase


def get_knowledge_base() -> ElasticKnowledgeBase:
    """Factory function to create a knowledge base."""
    return ElasticKnowledgeBase()
