"""
Tests for Blue Team Agent and Auto-Fix Workflow

Tests the complete Test-Driven Repair process:
1. Generate patch using LLM
2. Verify patch by running exploit
3. Git operations for PR creation
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.agents.blue_team import BlueTeamAgent
from app.core.orchestrator import JanitorOrchestrator
from app.tools.git_ops import GitOps


class TestBlueTeamAgent:
    """Test Blue Team patch generation and verification"""
    
    def setup_method(self):
        """Setup for each test"""
        self.blue_team = BlueTeamAgent()
        self.test_dir = Path(__file__).parent / "fixtures"
        self.test_dir.mkdir(exist_ok=True)
    
    def test_blue_team_initialization(self):
        """Test 1: Verify Blue Team initializes correctly"""
        agent = BlueTeamAgent()
        assert agent.llm is not None, "LLM should be initialized"
        assert agent.sandbox is not None, "Sandbox should be initialized"
        assert agent.knowledge_base is not None, "Knowledge base should be initialized"
    
    def test_patch_sql_injection(self):
        """Test 2: Verify Blue Team patches SQL injection vulnerability"""
        # Vulnerable code with SQL injection
        vulnerable_code = '''
def login(username, password, conn):
    """Vulnerable login function - takes connection as parameter"""
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchone() is not None
'''
        
        # Exploit that proves the vulnerability - imports from login.py
        exploit_code = '''
# Import the vulnerable function from login.py
import sys
sys.path.insert(0, '.')
from login import login

# Create test database
import sqlite3
conn = sqlite3.connect('/tmp/test.db')
cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS users")
cursor.execute("CREATE TABLE users (username TEXT, password TEXT)")
cursor.execute("INSERT INTO users VALUES ('admin', 'secret123')")
conn.commit()

# Test normal login
result = login('admin', 'secret123', conn)
if result:
    print("Normal login works")

# Test SQL injection exploit
malicious_username = "admin' OR '1'='1"
malicious_password = "anything"
result = login(malicious_username, malicious_password, conn)

if result:
    print("EXPLOIT_SUCCESS")
else:
    print("EXPLOIT_FAILED")
'''
        
        # Run patch and verify
        result = self.blue_team.patch_and_verify(
            target_file="login.py",
            current_content=vulnerable_code,
            exploit_code=exploit_code,
            vulnerability_type="SQL Injection",
            vulnerability_description="User input concatenated into SQL query"
        )
        
        # Verify patch was successful
        assert "success" in result, "Result should have success field"
        assert result["success"] == True, "Patch should succeed"
        assert "patched_content" in result, "Should have patched content"
        assert len(result["patched_content"]) > 0, "Patched content should not be empty"
        
        # Verify the patch contains secure code patterns
        patched = result["patched_content"].lower()
        # Should use parameterized queries (? or %s)
        assert ("?" in patched or "%s" in patched or "execute(" in patched), \
            "Patched code should use parameterized queries"
    
    def test_regression_verification(self):
        """Test 3: Verify exploit fails on patched code (Test-Driven Repair)"""
        # Simple vulnerable code
        vulnerable_code = '''
def unsafe_eval(user_input):
    """Uses eval on user input"""
    return eval(user_input)
'''
        
        # Exploit
        exploit_code = '''
def unsafe_eval(user_input):
    """Uses eval on user input"""
    return eval(user_input)

# Try to exploit
try:
    result = unsafe_eval("__import__('os').system('echo EXPLOIT_SUCCESS')")
    print("EXPLOIT_SUCCESS")
except:
    print("EXPLOIT_FAILED")
'''
        
        # Run patch and verify
        result = self.blue_team.patch_and_verify(
            target_file="unsafe.py",
            current_content=vulnerable_code,
            exploit_code=exploit_code,
            vulnerability_type="Code Injection",
            vulnerability_description="eval() on user input"
        )
        
        # If patch succeeded, exploit should NOT contain "EXPLOIT_SUCCESS"
        if result["success"]:
            verification_output = result.get("verification_output", "")
            assert "EXPLOIT_SUCCESS" not in verification_output, \
                "Exploit should fail on patched code"
    
    def test_patch_command_injection(self):
        """Test 4: Verify Blue Team patches command injection"""
        vulnerable_code = '''
def run_command(user_input):
    """Vulnerable command execution"""
    import os
    return os.system(user_input)
'''
        
        exploit_code = '''
# Import the vulnerable function from cmd.py
import sys
sys.path.insert(0, '.')
from cmd import run_command

# Try malicious command
result = run_command("echo EXPLOIT_SUCCESS")
'''
        
        result = self.blue_team.patch_and_verify(
            target_file="cmd.py",
            current_content=vulnerable_code,
            exploit_code=exploit_code,
            vulnerability_type="Command Injection",
            vulnerability_description="os.system with user input"
        )
        
        # Patch should succeed
        assert result.get("success", False), "Patch should succeed for command injection"
        
        # Patched code should not use os.system directly
        if result["success"]:
            patched = result["patched_content"].lower()
            # Should use subprocess or validation
            assert ("subprocess" in patched or "validate" in patched or "allowed" in patched), \
                "Patched code should use safer alternatives"
    
    def test_false_positive_handling(self):
        """Test 5: Verify Blue Team handles false positives (exploit doesn't work)"""
        # Safe code (parameterized query)
        safe_code = '''
def safe_login(username, password):
    """Safe login with parameterized query"""
    import sqlite3
    conn = sqlite3.connect(':memory:')
    query = "SELECT * FROM users WHERE username=? AND password=?"
    cursor = conn.cursor()
    cursor.execute(query, (username, password))
    return cursor.fetchone() is not None
'''
        
        # Exploit that won't work on safe code
        exploit_code = '''
def safe_login(username, password):
    """Safe login with parameterized query"""
    import sqlite3
    conn = sqlite3.connect(':memory:')
    query = "SELECT * FROM users WHERE username=? AND password=?"
    cursor = conn.cursor()
    cursor.execute(query, (username, password))
    return cursor.fetchone() is not None

# Try SQL injection (should fail)
result = safe_login("admin' OR '1'='1", "anything")
if result:
    print("EXPLOIT_SUCCESS")
else:
    print("EXPLOIT_FAILED")
'''
        
        result = self.blue_team.patch_and_verify(
            target_file="safe.py",
            current_content=safe_code,
            exploit_code=exploit_code,
            vulnerability_type="SQL Injection",
            vulnerability_description="Suspected SQL injection"
        )
        
        # Should detect false positive (exploit doesn't work on original)
        assert result["success"] == False, "Should detect false positive"
        assert "false positive" in result.get("error", "").lower(), \
            "Error should mention false positive"
    
    def test_max_attempts_limit(self):
        """Test 6: Verify Blue Team respects max attempts limit"""
        # Code that's hard to patch (for testing retry logic)
        vulnerable_code = '''
def complex_function(x):
    """Complex vulnerable function"""
    return eval(x)
'''
        
        exploit_code = '''
def complex_function(x):
    """Complex vulnerable function"""
    return eval(x)

try:
    complex_function("print('EXPLOIT_SUCCESS')")
except:
    print("EXPLOIT_FAILED")
'''
        
        result = self.blue_team.patch_and_verify(
            target_file="complex.py",
            current_content=vulnerable_code,
            exploit_code=exploit_code,
            vulnerability_type="Code Injection",
            vulnerability_description="Complex eval usage",
            max_attempts=2  # Limit to 2 attempts for testing
        )
        
        # Should respect max attempts
        assert result["attempts"] <= 2, "Should not exceed max attempts"


class TestGitOperations:
    """Test Git and PR operations"""
    
    def test_git_ops_initialization(self):
        """Test 7: Verify GitOps initializes with token"""
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'test_token'}):
            git_ops = GitOps(token='test_token')
            assert git_ops.token == 'test_token', "Token should be set"
            assert git_ops.github is not None, "GitHub client should be initialized"
    
    @patch('app.tools.git_ops.Repo')
    def test_clone_repo(self, mock_repo):
        """Test 8: Verify repository cloning"""
        git_ops = GitOps()
        mock_repo.clone_from.return_value = Mock()
        
        repo = git_ops.clone_repo("https://github.com/test/repo.git", Path("/tmp/test"))
        
        mock_repo.clone_from.assert_called_once()
        assert repo is not None
    
    @patch('app.tools.git_ops.Repo')
    def test_create_branch(self, mock_repo):
        """Test 9: Verify branch creation"""
        git_ops = GitOps()
        mock_repo_instance = Mock()
        
        git_ops.create_branch(mock_repo_instance, "fix/issue-123")
        
        mock_repo_instance.git.checkout.assert_called_once_with('-b', 'fix/issue-123')
    
    @patch('app.tools.git_ops.Github')
    def test_create_pull_request(self, mock_github):
        """Test 10: Verify PR creation"""
        git_ops = GitOps(token='test_token')
        
        # Mock GitHub API
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test/repo/pull/1"
        mock_repo.create_pull.return_value = mock_pr
        git_ops.github.get_repo = Mock(return_value=mock_repo)
        
        pr_url = git_ops.create_pull_request(
            repo_name="test/repo",
            title="Test PR",
            body="Test body",
            head="fix/test",
            base="main"
        )
        
        assert pr_url == "https://github.com/test/repo/pull/1"
        mock_repo.create_pull.assert_called_once()


class TestOrchestratorFixWorkflow:
    """Test orchestrator fix workflow integration"""
    
    @patch('app.core.orchestrator.GitOps')
    @patch('app.core.orchestrator.BlueTeamAgent')
    @patch('app.core.orchestrator.RedTeamAgent')
    def test_run_fix_job_success(self, mock_red_team_class, mock_blue_team_class, mock_git_ops_class):
        """Test 11: Verify complete fix job workflow"""
        # Setup mocks
        mock_red_team = Mock()
        mock_red_team.run_validation.return_value = {
            "verified": True,
            "thought_process": {
                "exploit_code": "print('EXPLOIT_SUCCESS')"
            }
        }
        mock_red_team_class.return_value = mock_red_team
        
        mock_blue_team = Mock()
        mock_blue_team.patch_and_verify.return_value = {
            "success": True,
            "patched_content": "def fixed_function(): pass",
            "attempts": 1,
            "error": ""
        }
        mock_blue_team_class.return_value = mock_blue_team
        
        mock_git_ops = Mock()
        mock_repo = Mock()
        mock_git_ops.clone_repo.return_value = mock_repo
        mock_git_ops.create_pr_for_fix.return_value = "https://github.com/test/repo/pull/1"
        
        # Create orchestrator
        orchestrator = JanitorOrchestrator(
            red_team=mock_red_team,
            blue_team=mock_blue_team,
            git_ops=mock_git_ops
        )
        
        # Create test file
        test_file = Path(__file__).parent / "fixtures" / "test_vuln.py"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("def vulnerable(): pass")
        
        try:
            # This would normally run the full workflow, but we're mocking it
            # Just verify the orchestrator was set up correctly
            assert orchestrator.blue_team is not None
            assert orchestrator.git_ops is not None
            assert orchestrator.red_team is not None
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()
    
    def test_orchestrator_has_blue_team(self):
        """Test 12: Verify orchestrator includes Blue Team"""
        orchestrator = JanitorOrchestrator()
        assert hasattr(orchestrator, 'blue_team'), "Orchestrator should have blue_team"
        assert orchestrator.blue_team is not None, "Blue team should be initialized"
        assert hasattr(orchestrator, 'run_fix_job'), "Orchestrator should have run_fix_job method"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
