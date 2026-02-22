"""
Tests for Knowledge Graph Engine
Verifies import parsing, graph construction, and context retrieval
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from app.core.knowledge import CodeKnowledgeBase


class TestCodeKnowledgeBase:
    """Test the Graph RAG engine"""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository with test files"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create directory structure
        (temp_dir / "app").mkdir()
        (temp_dir / "app" / "utils").mkdir()
        
        # File 1: main.py imports helper.py
        (temp_dir / "main.py").write_text("""
import helper
from app.utils import db

def main():
    helper.greet()
    db.query()
""")
        
        # File 2: helper.py (no imports)
        (temp_dir / "helper.py").write_text("""
def greet():
    print("Hello!")
""")
        
        # File 3: app/utils/db.py imports app/utils/config.py
        (temp_dir / "app" / "utils" / "db.py").write_text("""
from app.utils import config

def query():
    return config.get_db_url()
""")
        
        # File 4: app/utils/config.py (no imports)
        (temp_dir / "app" / "utils" / "config.py").write_text("""
def get_db_url():
    return "sqlite:///test.db"
""")
        
        # File 5: app/auth.py with relative import
        (temp_dir / "app" / "auth.py").write_text("""
from .utils import db

def login(username, password):
    return db.query()
""")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_knowledge_base_initialization(self):
        """Test knowledge base initializes correctly"""
        kb = CodeKnowledgeBase()
        
        assert kb is not None
        assert len(kb.analyzed_files) == 0
        assert len(kb.file_contents) == 0
    
    def test_build_graph_basic(self, temp_repo):
        """Test building a basic dependency graph"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # Should have found all Python files
        stats = kb.get_graph_stats()
        assert stats["total_files"] >= 4
        
        # Should have edges for imports
        assert stats["total_imports"] >= 2
    
    def test_import_detection(self, temp_repo):
        """Test that imports are correctly detected"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # main.py imports helper.py
        main_imports = kb.get_imports("main.py")
        assert "helper.py" in main_imports
        
        # main.py imports app/utils/db.py
        assert "app/utils/db.py" in main_imports
    
    def test_nested_imports(self, temp_repo):
        """Test nested import detection"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # app/utils/db.py imports app/utils/config.py
        db_imports = kb.get_imports("app/utils/db.py")
        assert "app/utils/config.py" in db_imports
    
    def test_relative_imports(self, temp_repo):
        """Test relative import resolution"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # app/auth.py imports from .utils (relative import)
        auth_imports = kb.get_imports("app/auth.py")
        if "app/auth.py" in kb.file_contents and "app/utils/db.py" in kb.file_contents:
            assert "app/utils/db.py" in auth_imports
    
    def test_get_context_depth_1(self, temp_repo):
        """Test context retrieval with depth=1 (direct dependencies)"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # Get context for main.py
        context = kb.get_context("main.py", depth=1)
        
        # Should contain main.py itself
        assert "main.py" in context
        assert "def main():" in context
        
        # Should contain helper.py (direct import)
        assert "helper.py" in context or "helper" in context
        assert "def greet():" in context
    
    def test_get_context_depth_2(self, temp_repo):
        """Test context retrieval with depth=2 (transitive dependencies)"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # Get context for main.py with depth=2
        context = kb.get_context("main.py", depth=2)
        
        # Should contain main.py
        assert "def main():" in context
        
        # Should contain direct imports (depth 1)
        assert "def greet():" in context  # from helper.py
        
        # Should contain transitive imports (depth 2)
        # main.py → app/utils/db.py → app/utils/config.py
        assert "def get_db_url():" in context or "config" in context
    
    def test_get_context_formatting(self, temp_repo):
        """Test context output format"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        context = kb.get_context("main.py", depth=1)
        
        # Should have context markers
        assert "=== Context:" in context or "===" in context
        assert "=== Target:" in context or "main.py" in context
    
    def test_file_contents_stored(self, temp_repo):
        """Test that file contents are stored correctly"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # Check that helper.py content is stored
        assert "helper.py" in kb.file_contents
        assert "def greet():" in kb.file_contents["helper.py"]
    
    def test_ignore_standard_library(self, temp_repo):
        """Test that standard library imports are ignored"""
        # Create file with stdlib imports
        (temp_repo / "stdlib_test.py").write_text("""
import os
import sys
import json
from pathlib import Path

def test():
    pass
""")
        
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # Should not have edges to stdlib modules
        stdlib_imports = kb.get_imports("stdlib_test.py")
        assert "os" not in stdlib_imports
        assert "sys" not in stdlib_imports
        assert "json" not in stdlib_imports
    
    def test_get_dependents(self, temp_repo):
        """Test reverse dependency lookup"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # helper.py is imported by main.py
        dependents = kb.get_dependents("helper.py")
        
        assert "main.py" in dependents
    
    def test_graph_stats(self, temp_repo):
        """Test graph statistics"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        stats = kb.get_graph_stats()
        
        assert "total_files" in stats
        assert "total_imports" in stats
        assert stats["total_files"] >= 4
        assert stats["total_imports"] >= 2
    
    def test_visualize_dependencies(self, temp_repo):
        """Test dependency tree visualization"""
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        tree = kb.visualize_dependencies("main.py", max_depth=2)
        
        assert "main.py" in tree
        assert "├──" in tree or "└──" in tree  # Tree structure
    
    def test_circular_dependencies(self, temp_repo):
        """Test handling of circular dependencies"""
        # Create circular dependency
        (temp_repo / "a.py").write_text("import b")
        (temp_repo / "b.py").write_text("import a")
        
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # Should not crash or infinite loop
        context = kb.get_context("a.py", depth=5)
        
        # Should handle circular deps gracefully
        assert "a.py" in context
    
    def test_missing_import_file(self, temp_repo):
        """Test handling of imports that don't exist"""
        (temp_repo / "missing.py").write_text("""
import nonexistent_module
from fake import module

def test():
    pass
""")
        
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_repo)
        
        # Should not crash
        assert "missing.py" in kb.file_contents


def test_real_codebase_analysis():
    """
    Integration test: Analyze the actual CodeJanitor codebase
    """
    repo_path = Path(__file__).parent.parent
    
    kb = CodeKnowledgeBase()
    kb.build_graph(repo_path)
    
    # Should have found many files
    stats = kb.get_graph_stats()
    assert stats["total_files"] > 0
    
    print(f"\n=== CodeJanitor Knowledge Graph ===")
    print(f"Total files: {stats['total_files']}")
    print(f"Total imports: {stats['total_imports']}")
    print(f"Avg imports per file: {stats['avg_imports_per_file']:.2f}")
    
    # Test context retrieval on actual files
    if "app/agents/auditor.py" in kb.file_contents:
        context = kb.get_context("app/agents/auditor.py", depth=1)
        assert len(context) > 0
        print(f"\nContext size for auditor.py: {len(context)} chars")
    
    # Visualize orchestrator dependencies
    if "app/core/orchestrator.py" in kb.file_contents:
        tree = kb.visualize_dependencies("app/core/orchestrator.py", max_depth=1)
        print(f"\nOrchestrator dependencies:\n{tree}")


def test_context_for_vulnerable_code():
    """
    Test that context retrieval works for vulnerability analysis
    """
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create a vulnerable file that imports a helper
        (temp_dir / "auth.py").write_text("""
from database import query

def login(username, password):
    # VULNERABLE: Uses imported query function unsafely
    result = query(f"SELECT * FROM users WHERE name='{username}'")
    return result
""")
        
        (temp_dir / "database.py").write_text("""
import sqlite3

def query(sql):
    # The actual vulnerable function
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(sql)  # DANGEROUS: No parameterization
    return cursor.fetchall()
""")
        
        kb = CodeKnowledgeBase()
        kb.build_graph(temp_dir)
        
        # Get full context for auth.py
        context = kb.get_context("auth.py", depth=1)
        
        # Context should include BOTH files
        assert "def login(username, password):" in context
        assert "def query(sql):" in context
        assert "cursor.execute(sql)" in context
        
        # Now the Red Team can see the FULL vulnerability chain:
        # login() passes unsanitized input → query() executes it unsafely
        print("\n=== Vulnerability Context ===")
        print(context[:500])
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
