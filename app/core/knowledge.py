"""
Knowledge Graph Engine - The Brain of CodeJanitor 2.0

Builds a dependency graph of the codebase and provides context-aware code retrieval.
When analyzing a file, automatically includes its dependencies for complete understanding.
"""

import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
import networkx as nx
from tree_sitter import Parser, Language, Node
import tree_sitter_python

logger = logging.getLogger(__name__)


class CodeKnowledgeBase:
    """
    Graph RAG Engine for CodeJanitor
    
    Builds and maintains a knowledge graph of code dependencies.
    Provides context-aware retrieval: when analyzing a file, automatically
    includes the content of imported modules.
    
    Example:
        kb = CodeKnowledgeBase()
        kb.build_graph(Path("./src"))
        
        # Get file + all its dependencies
        context = kb.get_context("src/auth.py", depth=1)
        # Returns: content of auth.py + content of all files it imports
    """
    
    def __init__(self):
        """Initialize the knowledge graph"""
        self.graph = nx.DiGraph()
        self.file_contents: Dict[str, str] = {}
        self.parser = self._init_parser()
        
        # Track which files have been analyzed
        self.analyzed_files: Set[str] = set()
    
    def _init_parser(self) -> Parser:
        """Initialize Tree-sitter parser for Python"""
        python_language = Language(tree_sitter_python.language())
        parser = Parser(python_language)
        return parser
    
    def build_graph(self, repo_path: Path) -> None:
        """
        Build dependency graph for entire repository
        
        Args:
            repo_path: Root directory of the repository
        
        The graph will contain:
        - Nodes: File paths (relative to repo_path)
        - Edges: Import relationships (A imports B → edge A->B)
        """
        logger.info(f"Building knowledge graph for: {repo_path}")
        
        if not repo_path.exists():
            logger.error(f"Repository path does not exist: {repo_path}")
            return
        
        # Find all Python files
        python_files = list(repo_path.rglob("*.py"))
        logger.info(f"Found {len(python_files)} Python files")
        
        # Process each file
        for file_path in python_files:
            self._process_file(file_path, repo_path)
        
        logger.info(f"Graph built: {self.graph.number_of_nodes()} nodes, "
                   f"{self.graph.number_of_edges()} edges")
    
    def _process_file(self, file_path: Path, repo_root: Path) -> None:
        """
        Process a single file: extract imports and add to graph
        
        Args:
            file_path: Absolute path to the file
            repo_root: Repository root (for relative path calculation)
        """
        try:
            # Get relative path for graph node (normalize to forward slashes)
            rel_path = str(file_path.relative_to(repo_root)).replace('\\', '/')
            
            # Read file content
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            self.file_contents[rel_path] = content
            
            # Add node to graph
            self.graph.add_node(rel_path, path=str(file_path))
            
            # Parse imports
            imports = self._extract_imports(content, file_path, repo_root)
            
            # Add edges for each import
            for imported_file in imports:
                self.graph.add_edge(rel_path, imported_file)
                logger.debug(f"Edge: {rel_path} -> {imported_file}")
            
            self.analyzed_files.add(rel_path)
            
        except Exception as e:
            logger.warning(f"Error processing {file_path}: {e}")
    
    def _extract_imports(self, content: str, file_path: Path, repo_root: Path) -> List[str]:
        """
        Extract all import statements and resolve them to file paths
        
        Args:
            content: File content
            file_path: Current file path
            repo_root: Repository root
        
        Returns:
            List of relative file paths that this file imports
        """
        imports = []
        
        try:
            tree = self.parser.parse(bytes(content, 'utf8'))
            root_node = tree.root_node
            
            # Find all import statements
            import_nodes = self._find_import_nodes(root_node)
            
            for node in import_nodes:
                resolved = self._resolve_import(node, file_path, repo_root)
                if resolved:
                    imports.extend(resolved)
        
        except Exception as e:
            logger.debug(f"Error extracting imports from {file_path}: {e}")
        
        return imports
    
    def _find_import_nodes(self, node: Node) -> List[Node]:
        """Find all import_statement and import_from_statement nodes"""
        import_nodes = []
        
        if node.type in ['import_statement', 'import_from_statement']:
            import_nodes.append(node)
        
        for child in node.children:
            import_nodes.extend(self._find_import_nodes(child))
        
        return import_nodes
    
    def _resolve_import(self, node: Node, current_file: Path, repo_root: Path) -> List[str]:
        """
        Resolve an import statement to actual file path(s)
        
        Handles:
        - import module
        - from module import function
        - from .relative import function
        
        Args:
            node: Tree-sitter import node
            current_file: Path of the file containing the import
            repo_root: Repository root
        
        Returns:
            List of relative file paths (empty if not resolvable)
        """
        resolved = []
        
        try:
            # Get import text
            import_text = node.text.decode('utf-8')
            
            # Parse import statement
            if node.type == 'import_statement':
                # import module or import module as alias
                module_name = self._extract_module_name(node)
                if module_name:
                    resolved_path = self._find_module_file(module_name, current_file, repo_root)
                    if resolved_path:
                        resolved.append(resolved_path)
            
            elif node.type == 'import_from_statement':
                # from module import x, y, z
                module_name = self._extract_from_module_name(node)
                if module_name:
                    # First try to resolve the module itself
                    resolved_path = self._find_module_file(module_name, current_file, repo_root)
                    if resolved_path:
                        resolved.append(resolved_path)
                    
                    # Also try to resolve "from module import submodule"
                    # Example: "from app.utils import db" → try app/utils/db.py
                    imported_names = self._extract_imported_names(node)
                    for name in imported_names:
                        full_module = f"{module_name}.{name}" if module_name else name
                        sub_resolved = self._find_module_file(full_module, current_file, repo_root)
                        if sub_resolved and sub_resolved not in resolved:
                            resolved.append(sub_resolved)
        
        except Exception as e:
            logger.debug(f"Error resolving import {node.text}: {e}")
        
        return resolved
    
    def _extract_imported_names(self, node: Node) -> List[str]:
        """
        Extract the names being imported from 'from module import x, y, z'
        
        Returns list like ['x', 'y', 'z']
        """
        names = []
        found_import_keyword = False
        
        for child in node.children:
            # Look for dotted_name nodes that come AFTER the 'import' keyword
            if child.type == 'import':
                found_import_keyword = True
                continue
            
            if found_import_keyword and child.type == 'dotted_name':
                names.append(child.text.decode('utf-8'))
            elif found_import_keyword and child.type == 'aliased_import':
                # from module import x as y
                for subchild in child.children:
                    if subchild.type == 'dotted_name':
                        names.append(subchild.text.decode('utf-8'))
                        break
        
        return names
    
    def _extract_module_name(self, node: Node) -> Optional[str]:
        """Extract module name from 'import module' statement"""
        for child in node.children:
            if child.type == 'dotted_name':
                return child.text.decode('utf-8')
        return None
    
    def _extract_from_module_name(self, node: Node) -> Optional[str]:
        """Extract module name from 'from module import x' statement"""
        # First child should be 'from' keyword
        # Next should be the module name (dotted_name or relative_import)
        for i, child in enumerate(node.children):
            if child.type in ['dotted_name', 'relative_import']:
                module_text = child.text.decode('utf-8')
                # Handle 'from' with relative imports like "from .utils import x"
                return module_text
            # Also check for aliased_import which contains the dotted_name
            if child.type == 'aliased_import':
                for subchild in child.children:
                    if subchild.type == 'dotted_name':
                        return subchild.text.decode('utf-8')
        return None
    
    def _find_module_file(self, module_name: str, current_file: Path, repo_root: Path) -> Optional[str]:
        """
        Find the actual file path for a module name
        
        Args:
            module_name: e.g., "utils.db" or ".helpers"
            current_file: File that contains the import
            repo_root: Repository root
        
        Returns:
            Relative path to the module file, or None if not found
        """
        # Ignore standard library imports
        stdlib_modules = {
            'os', 'sys', 'json', 'time', 'datetime', 're', 'math', 'random',
            'collections', 'itertools', 'functools', 'typing', 'pathlib',
            'logging', 'unittest', 'pytest', 'sqlite3', 'requests', 'flask',
            'django', 'numpy', 'pandas', 'docker', 'networkx'
        }
        
        base_module = module_name.split('.')[0].lstrip('.')
        if base_module in stdlib_modules:
            return None
        
        # Handle relative imports (.module or ..module)
        if module_name.startswith('.'):
            return self._resolve_relative_import(module_name, current_file, repo_root)
        
        # Handle absolute imports (module.submodule)
        return self._resolve_absolute_import(module_name, repo_root)
    
    def _resolve_relative_import(self, module_name: str, current_file: Path, repo_root: Path) -> Optional[str]:
        """
        Resolve relative import (.module or ..module)
        
        Example:
            In file: src/auth/login.py
            Import: from .database import query
            Resolves to: src/auth/database.py
        """
        # Count leading dots
        level = 0
        for char in module_name:
            if char == '.':
                level += 1
            else:
                break
        
        # Get the actual module name after dots
        actual_module = module_name[level:]
        
        # Start from current file's directory
        current_dir = current_file.parent
        
        # Go up 'level-1' directories (one dot = same dir, two dots = parent, etc.)
        for _ in range(level - 1):
            current_dir = current_dir.parent
        
        # Try different file patterns
        if actual_module:
            # from .module import x
            patterns = [
                current_dir / f"{actual_module}.py",
                current_dir / actual_module / "__init__.py",
                current_dir / actual_module.replace('.', '/') / "__init__.py",
                current_dir / f"{actual_module.replace('.', '/')}.py"
            ]
        else:
            # from . import x (imports from __init__.py)
            patterns = [current_dir / "__init__.py"]
        
        for pattern in patterns:
            if pattern.exists() and pattern.is_file():
                try:
                    rel_path = str(pattern.relative_to(repo_root)).replace('\\', '/')
                    return rel_path
                except ValueError:
                    continue
        
        return None
    
    def _resolve_absolute_import(self, module_name: str, repo_root: Path) -> Optional[str]:
        """
        Resolve absolute import (module.submodule)
        
        Example:
            Import: from app.utils.db import query
            Resolves to: app/utils/db.py or app/utils/db/__init__.py
            
            Import: from app.utils import db
            Resolves to: app/utils/db.py (db is a module in utils package)
        """
        module_path = module_name.replace('.', '/')
        
        # Try different patterns
        patterns = [
            repo_root / f"{module_path}.py",
            repo_root / module_path / "__init__.py"
        ]
        
        for pattern in patterns:
            if pattern.exists() and pattern.is_file():
                try:
                    rel_path = str(pattern.relative_to(repo_root))
                    # Normalize path separators to forward slashes for consistency
                    rel_path = rel_path.replace('\\', '/')
                    return rel_path
                except ValueError:
                    continue
        
        return None
    
    def get_context(self, file_path: str, depth: int = 1) -> str:
        """
        Get full context for a file: its content + all dependencies
        
        Args:
            file_path: Relative path to the target file
            depth: How many levels of dependencies to include
                   1 = direct imports only
                   2 = imports + imports of imports, etc.
        
        Returns:
            Formatted string with all relevant code:
            === Context: utils/db.py ===
            [content]
            
            === Target: auth.py ===
            [content]
        
        Example:
            kb.get_context("src/auth.py", depth=1)
            # Returns auth.py + all files it directly imports
        """
        if file_path not in self.graph:
            logger.warning(f"File not in graph: {file_path}")
            return self.file_contents.get(file_path, "")
        
        # Get all dependencies up to specified depth
        dependencies = self._get_dependencies(file_path, depth)
        
        # Build context string
        context_parts = []
        
        # Add dependencies first (so target file sees imported code)
        for dep in dependencies:
            if dep in self.file_contents:
                context_parts.append(f"=== Context: {dep} ===\n")
                context_parts.append(self.file_contents[dep])
                context_parts.append("\n\n")
        
        # Add target file last
        if file_path in self.file_contents:
            context_parts.append(f"=== Target: {file_path} ===\n")
            context_parts.append(self.file_contents[file_path])
        
        return "".join(context_parts)
    
    def _get_dependencies(self, file_path: str, depth: int) -> List[str]:
        """
        Get all dependencies of a file up to specified depth
        
        Uses BFS to explore the dependency graph
        """
        if file_path not in self.graph:
            return []
        
        dependencies = []
        visited = {file_path}  # Don't include the target file itself
        queue = [(file_path, 0)]  # (node, current_depth)
        
        while queue:
            current, current_depth = queue.pop(0)
            
            if current_depth >= depth:
                continue
            
            # Get all files that current file imports
            for neighbor in self.graph.neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    dependencies.append(neighbor)
                    queue.append((neighbor, current_depth + 1))
        
        return dependencies
    
    def get_dependents(self, file_path: str) -> List[str]:
        """
        Get all files that depend on this file (reverse lookup)
        
        Args:
            file_path: Relative path to the file
        
        Returns:
            List of files that import this file
        
        Example:
            If auth.py imports db.py, then:
            get_dependents("db.py") -> ["auth.py"]
        """
        if file_path not in self.graph:
            return []
        
        # Use reverse graph (predecessors = files that import this one)
        return list(self.graph.predecessors(file_path))
    
    def get_graph_stats(self) -> Dict:
        """Get statistics about the knowledge graph"""
        return {
            "total_files": self.graph.number_of_nodes(),
            "total_imports": self.graph.number_of_edges(),
            "analyzed_files": len(self.analyzed_files),
            "isolated_files": len([n for n in self.graph.nodes() 
                                  if self.graph.degree(n) == 0]),
            "avg_imports_per_file": (self.graph.number_of_edges() / 
                                    self.graph.number_of_nodes() 
                                    if self.graph.number_of_nodes() > 0 else 0)
        }
    
    def visualize_dependencies(self, file_path: str, max_depth: int = 2) -> str:
        """
        Create a text visualization of a file's dependencies
        
        Args:
            file_path: Target file
            max_depth: Maximum depth to show
        
        Returns:
            ASCII tree showing dependencies
        """
        if file_path not in self.graph:
            return f"File not found: {file_path}"
        
        lines = [file_path]
        self._build_tree(file_path, lines, depth=0, max_depth=max_depth, visited=set())
        return "\n".join(lines)
    
    def _build_tree(self, node: str, lines: List[str], depth: int, max_depth: int, 
                   visited: Set[str], prefix: str = "") -> None:
        """Recursively build dependency tree visualization"""
        if depth >= max_depth or node in visited:
            return
        
        visited.add(node)
        neighbors = list(self.graph.neighbors(node))
        
        for i, neighbor in enumerate(neighbors):
            is_last = i == len(neighbors) - 1
            current_prefix = "└── " if is_last else "├── "
            lines.append(f"{prefix}{current_prefix}{neighbor}")
            
            next_prefix = prefix + ("    " if is_last else "│   ")
            self._build_tree(neighbor, lines, depth + 1, max_depth, visited, next_prefix)


def get_knowledge_base() -> CodeKnowledgeBase:
    """Factory function to create a knowledge base"""
    return CodeKnowledgeBase()
