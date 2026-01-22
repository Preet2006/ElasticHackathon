"""
Tests for Red Team validation and Prioritization Engine
Verifies exploit generation, Docker execution, and risk scoring
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.agents.red_team import RedTeamAgent
from app.core.prioritizer import IssuePrioritizer
from app.core.orchestrator import JanitorOrchestrator


class TestRedTeamAgent:
    """Test Red Team vulnerability verification"""
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM"""
        llm = Mock()
        return llm
    
    @pytest.fixture
    def mock_sandbox(self):
        """Create mock sandbox"""
        sandbox = Mock()
        return sandbox
    
    def test_red_team_initialization(self, mock_llm, mock_sandbox):
        """Test Red Team agent initializes correctly"""
        agent = RedTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        assert agent is not None
        assert agent.llm == mock_llm
        assert agent.sandbox == mock_sandbox
    
    def test_exploit_generation(self, mock_llm, mock_sandbox):
        """Test that exploit code is generated"""
        # Mock LLM to return exploit code
        exploit_code = """
# Exploit for crash vulnerability
def trigger_crash():
    raise ValueError("EXPLOIT_SUCCESS")

trigger_crash()
"""
        mock_llm.invoke.return_value = exploit_code
        
        # Mock sandbox execution
        mock_sandbox.run_python.return_value = ("EXPLOIT_SUCCESS", "", 0)
        
        agent = RedTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        vulnerable_function = """
def panic():
    raise ValueError("Crash!")
"""
        
        result = agent.verify_vulnerability(
            filename="test.py",
            function_code=vulnerable_function,
            vulnerability_type="Crash Vulnerability"
        )
        
        assert "exploit_code" in result
        assert len(result["exploit_code"]) > 0
        mock_llm.invoke.assert_called_once()
    
    def test_docker_execution(self, mock_llm, mock_sandbox):
        """Test that exploits run in Docker sandbox"""
        mock_llm.invoke.return_value = "print('EXPLOIT_SUCCESS')"
        mock_sandbox.run_python.return_value = ("EXPLOIT_SUCCESS\n", "", 0)
        
        agent = RedTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        result = agent.verify_vulnerability(
            filename="test.py",
            function_code="def vuln(): pass",
            vulnerability_type="Test Vulnerability"
        )
        
        # Verify sandbox was called
        mock_sandbox.run_python.assert_called_once()
        
        # Verify exploit ran successfully
        assert result["verified"] is True
        assert "EXPLOIT_SUCCESS" in result["output"]
    
    def test_verified_vulnerability(self, mock_llm, mock_sandbox):
        """Test detection of successful exploit"""
        mock_llm.invoke.return_value = "print('EXPLOIT_SUCCESS')"
        mock_sandbox.run_python.return_value = ("EXPLOIT_SUCCESS\n", "", 0)
        
        agent = RedTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        result = agent.verify_vulnerability(
            filename="test.py",
            function_code="def vulnerable(): pass",
            vulnerability_type="SQL Injection"
        )
        
        assert result["verified"] is True
        assert result["output"] != ""
    
    def test_failed_exploit(self, mock_llm, mock_sandbox):
        """Test detection of failed exploit"""
        mock_llm.invoke.return_value = "print('EXPLOIT_FAILED')"
        mock_sandbox.run_python.return_value = ("EXPLOIT_FAILED\n", "", 0)
        
        agent = RedTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        result = agent.verify_vulnerability(
            filename="test.py",
            function_code="def safe(): return True",
            vulnerability_type="SQL Injection"
        )
        
        assert result["verified"] is False
    
    def test_sql_injection_indicators(self, mock_llm, mock_sandbox):
        """Test SQL injection detection from output"""
        mock_llm.invoke.return_value = "print('test')"
        # Simulate SQL injection output
        mock_sandbox.run_python.return_value = ("SELECT * FROM users", "", 0)
        
        agent = RedTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        result = agent.verify_vulnerability(
            filename="test.py",
            function_code="def query(x): return f'SELECT * FROM users WHERE id={x}'",
            vulnerability_type="SQL Injection"
        )
        
        # Should detect SQL in output as verification
        assert result["verified"] is True
    
    def test_command_injection_indicators(self, mock_llm, mock_sandbox):
        """Test command injection detection from output"""
        mock_llm.invoke.return_value = "print('test')"
        # Simulate command execution output
        mock_sandbox.run_python.return_value = ("uid=1000(user)", "", 0)
        
        agent = RedTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        result = agent.verify_vulnerability(
            filename="test.py",
            function_code="def exec_cmd(cmd): import os; os.system(cmd)",
            vulnerability_type="Command Injection"
        )
        
        assert result["verified"] is True


class TestIssuePrioritizer:
    """Test issue prioritization logic"""
    
    def test_prioritizer_initialization(self):
        """Test prioritizer initializes"""
        prioritizer = IssuePrioritizer()
        assert prioritizer is not None
    
    def test_verified_vulnerability_boost(self):
        """Test verified vulnerabilities get score boost"""
        prioritizer = IssuePrioritizer()
        
        # Verified vulnerability
        result = prioritizer.calculate_risk(
            auditor_score=7,
            red_team_verified=True,
            vulnerability_type="SQL Injection"
        )
        
        # Score should be boosted
        assert result["final_score"] >= 9
        assert "VERIFIED" in result["label"]
        assert result["priority"] == "CRITICAL"
    
    def test_verified_with_exploit_is_critical(self):
        """Test verified vulnerability with exploit is always 10/10"""
        prioritizer = IssuePrioritizer()
        
        result = prioritizer.calculate_risk(
            auditor_score=6,
            red_team_verified=True,
            vulnerability_type="SQL Injection",
            has_exploit_proof=True
        )
        
        assert result["final_score"] == 10
        assert "EXPLOIT" in result["label"]
        assert result["priority"] == "CRITICAL"
    
    def test_unverified_high_score(self):
        """Test unverified but high initial score"""
        prioritizer = IssuePrioritizer()
        
        result = prioritizer.calculate_risk(
            auditor_score=9,
            red_team_verified=False,
            vulnerability_type="SQL Injection"
        )
        
        assert result["label"] == "High - Unverified"
        assert "Manual review" in result["action_recommended"]
    
    def test_false_positive_demotion(self):
        """Test low score unverified gets demoted"""
        prioritizer = IssuePrioritizer()
        
        result = prioritizer.calculate_risk(
            auditor_score=3,
            red_team_verified=False,
            vulnerability_type="Minor Issue"
        )
        
        assert result["final_score"] == 0
        assert "False Positive" in result["label"]
        assert "Skip" in result["action_recommended"]
    
    def test_prioritize_issues_sorting(self):
        """Test issues are sorted by score (highest first)"""
        prioritizer = IssuePrioritizer()
        
        issues = [
            {"risk_score": 2, "vulnerable": True},
            {"risk_score": 10, "vulnerable": True},
            {"risk_score": 5, "vulnerable": True},
            {"risk_score": 8, "vulnerable": True}
        ]
        
        sorted_issues = prioritizer.prioritize_issues(issues)
        
        # Should be sorted: 10, 8, 5, 2
        assert sorted_issues[0]["risk_score"] == 10
        assert sorted_issues[1]["risk_score"] == 8
        assert sorted_issues[2]["risk_score"] == 5
        assert sorted_issues[3]["risk_score"] == 2
    
    def test_filter_actionable_issues(self):
        """Test filtering by minimum score"""
        prioritizer = IssuePrioritizer()
        
        issues = [
            {"risk_score": 9, "vulnerable": True},
            {"risk_score": 4, "vulnerable": True},
            {"risk_score": 7, "vulnerable": True}
        ]
        
        filtered = prioritizer.filter_actionable_issues(issues, min_score=7)
        
        assert len(filtered) == 2  # Only 9 and 7
        assert all(i["risk_score"] >= 7 for i in filtered)
    
    def test_verification_strategy_smart(self):
        """Test smart verification strategy (only high-risk)"""
        prioritizer = IssuePrioritizer()
        
        high_risk = {"risk_score": 8}
        low_risk = {"risk_score": 5}
        
        assert prioritizer.should_verify_issue(high_risk, "smart") is True
        assert prioritizer.should_verify_issue(low_risk, "smart") is False
    
    def test_verification_strategy_all(self):
        """Test 'all' strategy verifies everything"""
        prioritizer = IssuePrioritizer()
        
        issue = {"risk_score": 2}
        
        assert prioritizer.should_verify_issue(issue, "all") is True
    
    def test_verification_strategy_none(self):
        """Test 'none' strategy skips verification"""
        prioritizer = IssuePrioritizer()
        
        issue = {"risk_score": 10}
        
        assert prioritizer.should_verify_issue(issue, "none") is False


class TestJanitorOrchestrator:
    """Test orchestrator workflow"""
    
    @pytest.fixture
    def mock_auditor(self):
        """Create mock auditor"""
        auditor = Mock()
        auditor.scan_directory.return_value = [
            {
                "file": "test.py",
                "function": "vuln_func",
                "vulnerable": True,
                "risk_score": 9,
                "type": "SQL Injection",
                "description": "Test vulnerability"
            },
            {
                "file": "test2.py",
                "function": "safe_func",
                "vulnerable": True,
                "risk_score": 3,
                "type": "Minor Issue",
                "description": "Low risk"
            }
        ]
        return auditor
    
    @pytest.fixture
    def mock_red_team(self):
        """Create mock red team"""
        red_team = Mock()
        red_team.verify_vulnerability.return_value = {
            "verified": True,
            "output": "EXPLOIT_SUCCESS",
            "exploit_code": "print('exploit')",
            "error": ""
        }
        return red_team
    
    @pytest.fixture
    def mock_prioritizer(self):
        """Create mock prioritizer"""
        prioritizer = Mock()
        prioritizer.prioritize_issues = lambda issues: sorted(
            issues, 
            key=lambda i: i.get("risk_score", 0), 
            reverse=True
        )
        prioritizer.calculate_risk.return_value = {
            "final_score": 10,
            "label": "CRITICAL - VERIFIED",
            "action_recommended": "Fix immediately",
            "priority": "CRITICAL"
        }
        prioritizer.should_verify_issue.return_value = True
        return prioritizer
    
    def test_orchestrator_initialization(self, mock_auditor, mock_red_team, mock_prioritizer):
        """Test orchestrator initializes"""
        orchestrator = JanitorOrchestrator(
            auditor=mock_auditor,
            red_team=mock_red_team,
            prioritizer=mock_prioritizer
        )
        
        assert orchestrator is not None
    
    def test_prioritize_risks(self, mock_auditor, mock_red_team, mock_prioritizer):
        """Test risk prioritization"""
        orchestrator = JanitorOrchestrator(
            auditor=mock_auditor,
            red_team=mock_red_team,
            prioritizer=mock_prioritizer
        )
        
        issues = [
            {"risk_score": 2, "vulnerable": True},
            {"risk_score": 10, "vulnerable": True},
            {"risk_score": 5, "vulnerable": True}
        ]
        
        prioritized = orchestrator.prioritize_risks(issues)
        
        # Should be sorted highest first
        assert prioritized[0]["risk_score"] == 10
        assert prioritized[1]["risk_score"] == 5
        assert prioritized[2]["risk_score"] == 2
    
    def test_validate_issue(self, mock_auditor, mock_red_team, mock_prioritizer):
        """Test single issue validation (legacy mode)"""
        orchestrator = JanitorOrchestrator(
            auditor=mock_auditor,
            red_team=mock_red_team,
            prioritizer=mock_prioritizer
        )
        
        issue = {
            "file": "test.py",
            "function": "vuln_func",
            "risk_score": 8,
            "type": "SQL Injection",
            "code": "def vuln_func(): pass"
        }
        
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "test code"
            
            # Use legacy mode to test verify_vulnerability method
            validated = orchestrator.validate_issue(issue, use_kill_chain=False)
        
        assert "verified" in validated
        assert "final_score" in validated
        mock_red_team.verify_vulnerability.assert_called_once()
    
    def test_scan_and_prioritize_workflow(self, mock_auditor, mock_red_team, mock_prioritizer):
        """Test complete scan and prioritize workflow"""
        from pathlib import Path
        
        orchestrator = JanitorOrchestrator(
            auditor=mock_auditor,
            red_team=mock_red_team,
            prioritizer=mock_prioritizer
        )
        
        issues = orchestrator.scan_and_prioritize(Path("."))
        
        # Should call auditor
        mock_auditor.scan_directory.assert_called_once()
        
        # Should return prioritized results
        assert len(issues) > 0
        assert issues[0]["risk_score"] >= issues[-1]["risk_score"]


def test_real_red_team_exploit():
    """
    Integration test with real Red Team agent
    Tests actual exploit generation and Docker execution
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    if not settings.groq_api_key:
        pytest.skip("No GROQ_API_KEY configured")
    
    agent = RedTeamAgent()
    
    # Simple crash vulnerability
    vulnerable_code = """
def cause_crash():
    '''This function will crash when called'''
    raise ValueError("Intentional crash for testing")
    return True
"""
    
    result = agent.verify_vulnerability(
        filename="test_vuln.py",
        function_code=vulnerable_code,
        vulnerability_type="Crash Vulnerability",
        description="Function crashes when called"
    )
    
    # Should generate exploit code
    assert result["exploit_code"] != ""
    assert len(result["exploit_code"]) > 20
    
    # Output should show exploit ran
    assert result["output"] != "" or result["error"] != ""
    
    print(f"Exploit generated: {len(result['exploit_code'])} chars")
    print(f"Verified: {result['verified']}")
    print(f"Output: {result['output'][:200]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
