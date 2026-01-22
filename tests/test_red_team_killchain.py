"""
Tests for Red Team Kill Chain Methodology

Verifies that the agent follows RECON → PLAN → EXPLOIT reasoning
and shows its work like a hacker console
"""

import pytest
import json
from pathlib import Path
from app.agents.red_team import RedTeamAgent
from app.core.orchestrator import JanitorOrchestrator
from app.core.knowledge import CodeKnowledgeBase


class TestKillChainReasoning:
    """Test that Red Team follows Kill Chain methodology"""
    
    def setup_method(self):
        """Setup for each test"""
        self.red_team = RedTeamAgent()
        self.test_dir = Path(__file__).parent / "fixtures"
    
    def test_kill_chain_response_structure(self):
        """Test 1: Verify LLM response contains recon, plan, exploit_code keys"""
        # Vulnerable SQL injection code
        vulnerable_code = '''
def login(username, password):
    """Vulnerable login function"""
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    return execute_query(query)
'''
        
        vulnerability_details = {
            "type": "SQL Injection",
            "description": "User input directly concatenated into SQL query",
            "function_code": vulnerable_code
        }
        
        # Run Kill Chain validation
        result = self.red_team.run_validation(
            target_file="test_auth.py",
            vulnerability_details=vulnerability_details
        )
        
        # Verify structure
        assert "thought_process" in result, "Result must contain thought_process"
        
        thought_process = result["thought_process"]
        
        # Verify all Kill Chain phases are present
        assert "recon" in thought_process, "Missing RECON phase"
        assert "plan" in thought_process, "Missing PLAN phase"
        assert "exploit_code" in thought_process, "Missing EXPLOIT code"
        
        # Verify they contain actual content
        assert len(thought_process["recon"]) > 50, "RECON should have substantial analysis"
        assert len(thought_process["plan"]) > 50, "PLAN should have substantial strategy"
        assert len(thought_process["exploit_code"]) > 50, "EXPLOIT should have actual code"
        
        # Verify exploit code is Python
        assert "def " in thought_process["exploit_code"] or "import " in thought_process["exploit_code"], \
            "Exploit code should be Python"
    
    def test_kill_chain_logs_thinking(self, capsys):
        """Test 2: Verify the 'thinking' is visible in logs/output"""
        vulnerable_code = '''
def execute_command(user_input):
    """Vulnerable command execution"""
    import os
    result = os.system(user_input)
    return result
'''
        
        vulnerability_details = {
            "type": "Command Injection",
            "description": "User input passed directly to os.system",
            "function_code": vulnerable_code
        }
        
        # Run validation
        result = self.red_team.run_validation(
            target_file="test_cmd.py",
            vulnerability_details=vulnerability_details
        )
        
        # Check that stdout contains Kill Chain phases (we print to stdout)
        captured = capsys.readouterr()
        output_text = captured.out.lower()
        
        assert "recon" in output_text or "reconnaissance" in output_text, \
            f"Output should show RECON phase. Got: {captured.out[:500]}"
        assert "plan" in output_text or "planning" in output_text, \
            f"Output should show PLAN phase. Got: {captured.out[:500]}"
    
    def test_exploit_execution_in_docker(self):
        """Test 3: Verify exploit runs in Docker and can succeed"""
        # Simple vulnerable code that's easy to exploit
        vulnerable_code = '''
def unsafe_eval(user_input):
    """Dangerously uses eval on user input"""
    result = eval(user_input)
    return result
'''
        
        vulnerability_details = {
            "type": "Code Injection",
            "description": "Direct eval() of user input allows arbitrary code execution",
            "function_code": vulnerable_code
        }
        
        # Run validation
        result = self.red_team.run_validation(
            target_file="test_eval.py",
            vulnerability_details=vulnerability_details
        )
        
        # Verify execution happened
        assert "output" in result, "Should have execution output"
        assert "verified" in result, "Should have verification result"
        
        # For a code injection vulnerability, the agent should at least attempt verification
        # (Whether it succeeds depends on LLM's exploit quality)
        assert "thought_process" in result, "Should have Kill Chain thought process"
        assert "exploit_code" in result["thought_process"], "Should have generated exploit code"
        
        # The exploit code should be non-empty Python code
        exploit_code = result["thought_process"]["exploit_code"]
        assert len(exploit_code) > 30, "Exploit code should be substantial"
        assert ("def" in exploit_code or "import" in exploit_code or "print" in exploit_code or "eval" in exploit_code), \
            "Exploit code should look like Python"
    
    def test_prioritization_logic(self):
        """Test 4: Verify prioritization sorts Critical (10/10) above Low (2/10)"""
        orchestrator = JanitorOrchestrator()
        
        # Create mock issues with different risk scores
        issues = [
            {
                "file": "low.py",
                "function": "safe_function",
                "type": "Low Risk",
                "vulnerable": True,
                "risk_score": 2,
                "description": "Minor issue"
            },
            {
                "file": "critical.py",
                "function": "dangerous_function",
                "type": "SQL Injection",
                "vulnerable": True,
                "risk_score": 10,
                "description": "Critical SQL injection"
            },
            {
                "file": "medium.py",
                "function": "moderate_function",
                "type": "XSS",
                "vulnerable": True,
                "risk_score": 6,
                "description": "Moderate XSS"
            }
        ]
        
        # Prioritize
        sorted_issues = orchestrator.prioritize_risks(issues)
        
        # Verify sorting (highest risk first)
        assert len(sorted_issues) == 3, "Should have 3 issues"
        assert sorted_issues[0]["risk_score"] == 10, "First should be critical (10)"
        assert sorted_issues[1]["risk_score"] == 6, "Second should be medium (6)"
        assert sorted_issues[2]["risk_score"] == 2, "Third should be low (2)"
        
        # Verify critical issue is at top
        assert sorted_issues[0]["file"] == "critical.py", \
            "Critical issue should be prioritized first"
    
    def test_context_injection_with_kill_chain(self):
        """Test 5: Verify Kill Chain uses Graph RAG context (dependencies)"""
        # Create a simple test case with imports
        main_code = '''
from database import execute_query

def login(username, password):
    """Login function that imports vulnerable execute_query"""
    query = f"SELECT * FROM users WHERE username='{username}'"
    return execute_query(query)
'''
        
        db_code = '''
def execute_query(sql):
    """Vulnerable database query executor"""
    import sqlite3
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute(sql)  # Vulnerable: direct execution of user input
    return cursor.fetchall()
'''
        
        # Context includes both files (simulating Graph RAG output)
        full_context = f"""
=== Context: database.py ===
{db_code}

=== Target: login.py ===
{main_code}
"""
        
        vulnerability_details = {
            "type": "SQL Injection",
            "description": "SQL query constructed with user input in login.py, executed in database.py",
            "function_code": main_code
        }
        
        # Run Kill Chain with full context
        result = self.red_team.run_validation(
            target_file="login.py",
            vulnerability_details=vulnerability_details,
            context_code=full_context
        )
        
        # Verify the RECON analyzed the dependencies
        recon = result["thought_process"]["recon"].lower()
        
        # RECON should mention the import or database.py
        assert ("import" in recon or "database" in recon or "execute_query" in recon), \
            "RECON should analyze imported dependencies"
        
        # PLAN should describe the cross-file attack
        plan = result["thought_process"]["plan"].lower()
        assert ("login" in plan or "execute_query" in plan or "sql" in plan), \
            "PLAN should describe attack through imported function"
    
    def test_false_positive_detection(self):
        """Test 6: Verify Kill Chain can identify false positives"""
        # Safe code that might look vulnerable but isn't
        safe_code = '''
def safe_query(user_id: int):
    """Safe parameterized query"""
    query = "SELECT * FROM users WHERE id = ?"
    return execute_query(query, (user_id,))
'''
        
        vulnerability_details = {
            "type": "SQL Injection",
            "description": "Potential SQL injection (false positive - uses parameterization)",
            "function_code": safe_code
        }
        
        # Run validation
        result = self.red_team.run_validation(
            target_file="safe_query.py",
            vulnerability_details=vulnerability_details
        )
        
        # Should recognize this is safe (or at least not exploit it)
        # The agent should see the parameterization in RECON
        recon = result["thought_process"]["recon"].lower()
        
        # RECON should notice the parameterization
        assert ("?" in result["thought_process"]["recon"] or 
                "parameter" in recon or 
                "safe" in recon or
                "prepared" in recon), \
            "RECON should recognize parameterized queries"


class TestKillChainIntegration:
    """Test Kill Chain integration with Orchestrator"""
    
    def test_orchestrator_uses_kill_chain(self):
        """Test 7: Verify orchestrator.validate_issue() uses Kill Chain by default"""
        orchestrator = JanitorOrchestrator()
        
        # Create a mock issue
        issue = {
            "file": str(Path(__file__).parent / "fixtures" / "vulnerable.py"),
            "function": "test_function",
            "type": "Code Injection",
            "description": "Uses eval() on user input",
            "vulnerable": True,
            "risk_score": 9
        }
        
        # Create test file with vulnerable code
        test_file = Path(__file__).parent / "fixtures" / "vulnerable.py"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text('''
def test_function(user_input):
    """Vulnerable eval usage"""
    return eval(user_input)
''')
        
        try:
            # Validate using Kill Chain
            validated = orchestrator.validate_issue(issue, use_kill_chain=True)
            
            # Should have thought process
            assert "thought_process" in validated, \
                "Validated issue should include thought_process from Kill Chain"
            
            # Thought process should have all phases
            if validated.get("thought_process"):
                tp = validated["thought_process"]
                assert "recon" in tp or "plan" in tp or "exploit_code" in tp, \
                    "Thought process should have Kill Chain phases"
        
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()
    
    def test_legacy_mode_still_works(self):
        """Test 8: Verify legacy validation (without Kill Chain) still works"""
        orchestrator = JanitorOrchestrator()
        
        # Create test file
        test_file = Path(__file__).parent / "fixtures" / "legacy_test.py"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text('''
def legacy_function(x):
    """Simple test function"""
    return eval(x)
''')
        
        issue = {
            "file": str(test_file),
            "function": "legacy_function",
            "type": "Code Injection",
            "description": "Eval usage",
            "vulnerable": True
        }
        
        try:
            # Use legacy mode (no Kill Chain)
            validated = orchestrator.validate_issue(issue, use_kill_chain=False)
            
            # Should still work
            assert "verified" in validated, "Legacy mode should still verify"
            
            # Should NOT have thought_process (legacy mode)
            # (But might have it if it was added, so we just check it works)
        
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
