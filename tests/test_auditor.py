"""
Tests for the Repository Auditor
Verifies vulnerability detection and reporting
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agents.auditor import RepositoryAuditor, AuditorError
from app.tools.parsing import CodeParser
from app.core.llm import LLMClient


class TestCodeParser:
    """Test Tree-sitter code parser"""
    
    def test_parse_simple_function(self):
        """Test parsing a simple function"""
        parser = CodeParser()
        
        code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        
        functions = parser.parse_functions(code)
        
        assert len(functions) == 1
        assert functions[0]["name"] == "hello_world"
        assert "print" in functions[0]["code"]
        assert functions[0]["start_line"] == 2
    
    def test_parse_multiple_functions(self):
        """Test parsing multiple functions"""
        parser = CodeParser()
        
        code = """
def function_one():
    return 1

def function_two(x, y):
    return x + y

def function_three():
    pass
"""
        
        functions = parser.parse_functions(code)
        
        assert len(functions) == 3
        assert functions[0]["name"] == "function_one"
        assert functions[1]["name"] == "function_two"
        assert functions[2]["name"] == "function_three"
    
    def test_parse_function_with_docstring(self):
        """Test extracting docstring from function"""
        parser = CodeParser()
        
        code = '''
def documented_function():
    """This is a docstring"""
    return True
'''
        
        functions = parser.parse_functions(code)
        
        assert len(functions) == 1
        assert "This is a docstring" in functions[0]["docstring"]


class TestRepositoryAuditor:
    """Test vulnerability auditor"""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client"""
        llm = Mock(spec=LLMClient)
        return llm
    
    @pytest.fixture
    def mock_github(self):
        """Create a mock GitHub manager"""
        github = Mock()
        github.get_existing_issues.return_value = []
        github.create_issue.return_value = {
            "number": 1,
            "url": "https://github.com/test/repo/issues/1",
            "title": "Test Issue"
        }
        return github
    
    def test_auditor_initialization(self, mock_llm):
        """Test auditor initializes correctly"""
        auditor = RepositoryAuditor(llm=mock_llm, create_issues=False)
        
        assert auditor is not None
        assert auditor.llm == mock_llm
        assert auditor.parser is not None
    
    def test_auditor_requires_github_for_issues(self):
        """Test that create_issues=True requires GitHubManager"""
        with pytest.raises(AuditorError):
            RepositoryAuditor(create_issues=True)
    
    def test_scan_vulnerable_function(self, mock_llm):
        """Test detection of vulnerable SQL injection function"""
        # Mock LLM to return vulnerability
        mock_llm.analyze_vulnerability.return_value = {
            "vulnerable": True,
            "risk_score": 9,
            "type": "SQL Injection",
            "description": "User input directly interpolated into SQL query without sanitization"
        }
        
        auditor = RepositoryAuditor(llm=mock_llm, create_issues=False)
        
        # Vulnerable code with SQL injection
        vulnerable_code = """
def get_user(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return execute_query(query)
"""
        
        findings = auditor.scan_file("test.py", vulnerable_code)
        
        # Verify findings
        assert len(findings) == 1
        assert findings[0]["vulnerable"] is True
        assert findings[0]["risk_score"] >= 7
        assert findings[0]["type"] == "SQL Injection"
        assert findings[0]["function"] == "get_user"
        
        # Verify LLM was called
        mock_llm.analyze_vulnerability.assert_called_once()
    
    def test_scan_safe_function(self, mock_llm):
        """Test that safe code is marked as not vulnerable"""
        # Mock LLM to return no vulnerability
        mock_llm.analyze_vulnerability.return_value = {
            "vulnerable": False,
            "risk_score": 0,
            "type": "none",
            "description": "No significant security vulnerabilities detected."
        }
        
        auditor = RepositoryAuditor(llm=mock_llm, create_issues=False)
        
        # Safe code
        safe_code = """
def add_numbers(a, b):
    return a + b
"""
        
        findings = auditor.scan_file("test.py", safe_code)
        
        assert len(findings) == 1
        assert findings[0]["vulnerable"] is False
        assert findings[0]["risk_score"] == 0
    
    def test_scan_multiple_functions(self, mock_llm):
        """Test scanning file with multiple functions"""
        # Mock LLM to alternate between vulnerable and safe
        mock_llm.analyze_vulnerability.side_effect = [
            {
                "vulnerable": True,
                "risk_score": 8,
                "type": "Command Injection",
                "description": "Shell command with user input"
            },
            {
                "vulnerable": False,
                "risk_score": 0,
                "type": "none",
                "description": "Safe function"
            },
            {
                "vulnerable": True,
                "risk_score": 7,
                "type": "Path Traversal",
                "description": "Unsanitized file path"
            }
        ]
        
        auditor = RepositoryAuditor(llm=mock_llm, create_issues=False)
        
        code = """
def execute_command(cmd):
    os.system(cmd)

def safe_function():
    return "safe"

def read_file(path):
    return open(path).read()
"""
        
        findings = auditor.scan_file("test.py", code)
        
        assert len(findings) == 3
        assert sum(1 for f in findings if f["vulnerable"]) == 2
        assert findings[0]["risk_score"] == 8
        assert findings[2]["risk_score"] == 7
    
    def test_create_github_issues(self, mock_llm, mock_github):
        """Test creating GitHub issues for vulnerabilities"""
        auditor = RepositoryAuditor(
            llm=mock_llm,
            github_manager=mock_github,
            create_issues=True
        )
        
        # Mock findings
        findings = [
            {
                "file": "app/auth.py",
                "function": "login",
                "start_line": 10,
                "end_line": 20,
                "vulnerable": True,
                "risk_score": 9,
                "type": "SQL Injection",
                "description": "Vulnerable to SQL injection"
            },
            {
                "file": "app/utils.py",
                "function": "helper",
                "start_line": 5,
                "end_line": 8,
                "vulnerable": True,
                "risk_score": 3,  # Below threshold
                "type": "Minor Issue",
                "description": "Low risk"
            },
            {
                "file": "app/safe.py",
                "function": "safe_func",
                "start_line": 1,
                "end_line": 5,
                "vulnerable": False,
                "risk_score": 0,
                "type": "none",
                "description": "Safe"
            }
        ]
        
        created = auditor.create_github_issues(
            repo_url="https://github.com/test/repo",
            findings=findings,
            min_risk_score=5
        )
        
        # Only high-risk vulnerability should create issue
        assert len(created) == 1
        mock_github.create_issue.assert_called_once()
    
    def test_issue_deduplication(self, mock_llm, mock_github):
        """Test that duplicate issues are not created"""
        # Mock existing issue
        mock_github.get_existing_issues.return_value = [
            {
                "number": 1,
                "title": "[Security] SQL Injection in login()",
                "url": "https://github.com/test/repo/issues/1"
            }
        ]
        
        auditor = RepositoryAuditor(
            llm=mock_llm,
            github_manager=mock_github,
            create_issues=True
        )
        
        findings = [
            {
                "file": "app/auth.py",
                "function": "login",
                "start_line": 10,
                "end_line": 20,
                "vulnerable": True,
                "risk_score": 9,
                "type": "SQL Injection",
                "description": "Vulnerable"
            }
        ]
        
        created = auditor.create_github_issues(
            repo_url="https://github.com/test/repo",
            findings=findings,
            min_risk_score=5
        )
        
        # Should not create duplicate
        assert len(created) == 0
        mock_github.create_issue.assert_not_called()
    
    def test_generate_report(self, mock_llm):
        """Test generating summary report"""
        auditor = RepositoryAuditor(llm=mock_llm, create_issues=False)
        
        findings = [
            {
                "file": "test1.py",
                "function": "critical_func",
                "vulnerable": True,
                "risk_score": 10,
                "type": "Critical Issue"
            },
            {
                "file": "test2.py",
                "function": "high_func",
                "vulnerable": True,
                "risk_score": 7,
                "type": "High Issue"
            },
            {
                "file": "test3.py",
                "function": "safe_func",
                "vulnerable": False,
                "risk_score": 0,
                "type": "none"
            }
        ]
        
        report = auditor.generate_report(findings)
        
        assert "Total Functions Analyzed: 3" in report
        assert "Vulnerabilities Found: 2" in report
        assert "Critical (8-10): 1" in report
        assert "High (7)" in report  # Flexible matching for spacing


def test_real_vulnerability_detection():
    """
    Integration test with real LLM (requires API key)
    Tests actual vulnerability detection on known vulnerable code
    """
    # Skip if no API key
    from app.core.config import get_settings
    settings = get_settings()
    
    if not settings.groq_api_key:
        pytest.skip("No GROQ_API_KEY configured")
    
    from app.core.llm import get_llm
    
    auditor = RepositoryAuditor(llm=get_llm(), create_issues=False)
    
    # Known vulnerable code
    vulnerable_code = """
def unsafe_execute(user_input):
    import os
    # DANGEROUS: Command injection vulnerability
    os.system(f"echo {user_input}")
    return True
"""
    
    findings = auditor.scan_file("vulnerable.py", vulnerable_code)
    
    # Should detect vulnerability
    assert len(findings) == 1
    assert findings[0]["vulnerable"] is True
    assert findings[0]["risk_score"] >= 7
    print(f"Detected: {findings[0]['type']} with risk score {findings[0]['risk_score']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
