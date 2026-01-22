"""
Test suite for Phase 6: Iterative Reasoning & Failure Memory

Tests that both Red Team and Blue Team learn from failures and
try different strategies instead of repeating the same approach.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agents.red_team import RedTeamAgent
from app.agents.blue_team import BlueTeamAgent


class TestRedTeamIterativeReasoning:
    """Test Red Team's ability to learn from failed exploitation attempts"""
    
    def test_red_team_tries_different_exploits_on_failure(self):
        """Test that Red Team generates different exploit strategies after failures"""
        
        # Create mock LLM that returns different exploits each time
        mock_llm = Mock()
        
        # First attempt: Simple SQL injection
        mock_llm.invoke.side_effect = [
            # Attempt 1: Simple single quote injection
            '''{"recon": "SQL injection via string concat", 
                "plan": "Try basic single quote bypass",
                "exploit_code": "import sys\\nsys.path.insert(0, '.')\\nfrom auth import login\\nlogin(\\"' OR '1'='1\\", \\"any\\")\\nprint('EXPLOIT_FAILED')"}''',
            
            # Attempt 2: Different approach - double quote injection (SUCCEEDS)
            '''{"recon": "SQL injection via string concat", 
                "plan": "Try double quote bypass since single quote failed",
                "exploit_code": "import sys\\nsys.path.insert(0, '.')\\nfrom auth import login\\nlogin('\\" OR \\"1\\"=\\"1', 'any')\\nprint('EXPLOIT_SUCCESS')"}'''
        ]
        
        # Mock sandbox that fails first time, succeeds second time
        mock_sandbox = Mock()
        mock_sandbox.run_python.side_effect = [
            ("EXPLOIT_FAILED", "", 0),  # Attempt 1 fails
            ("EXPLOIT_SUCCESS", "", 0)   # Attempt 2 succeeds
        ]
        
        # Create Red Team with mocks
        red_team = RedTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        # Run validation
        result = red_team.run_validation(
            target_file="auth.py",
            vulnerability_details={
                "type": "SQL Injection",
                "description": "String concatenation in SQL query",
                "function_code": "def login(user, pass): query = f'SELECT * FROM users WHERE user={user}'"
            },
            context_code="def login(user, pass): query = f'SELECT * FROM users WHERE user={user}'"
        )
        
        # Assertions
        assert result["verified"] == True, "Should eventually succeed"
        assert result["attempts"] == 2, "Should take 2 attempts"
        
        # Verify LLM was called twice with failure history on second call
        assert mock_llm.invoke.call_count == 2
        
        # Check that second call includes failure history
        second_call_prompt = mock_llm.invoke.call_args_list[1][0][0]
        assert "PREVIOUS FAILED ATTEMPTS" in second_call_prompt, "Should include failure history"
        assert "Try basic single quote" in second_call_prompt, "Should mention previous strategy"
    
    def test_red_team_gives_up_after_max_attempts(self):
        """Test that Red Team stops after maximum attempts"""
        
        mock_llm = Mock()
        # All attempts fail
        mock_llm.invoke.return_value = '''{"recon": "Test", "plan": "Test", 
            "exploit_code": "print('EXPLOIT_FAILED')"}'''
        
        mock_sandbox = Mock()
        mock_sandbox.run_python.return_value = (
            "EXPLOIT_FAILED",
            "",
            0
        )
        
        red_team = RedTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        result = red_team.run_validation(
            target_file="test.py",
            vulnerability_details={"type": "Test", "description": "Test", "function_code": "test"},
            context_code="test"
        )
        
        assert result["verified"] == False, "Should fail after all attempts"
        assert result["attempts"] == 3, "Should try maximum 3 times"
        assert "attempt_history" in result, "Should include attempt history"
        assert len(result["attempt_history"]) == 3, "Should have 3 failed attempts recorded"


class TestBlueTeamIterativePatching:
    """Test Blue Team's ability to learn from failed patches"""
    
    def test_blue_team_tries_different_patches_on_failure(self):
        """Test that Blue Team generates different patch strategies after failures"""
        
        # Mock LLM that returns different patches
        mock_llm = Mock()
        
        # First attempt: Use logging (doesn't work)
        # Second attempt: Delete the statement (works)
        mock_llm.invoke.side_effect = [
            # Attempt 1: Replace print with logging
            '''import logging
def debug_print(data):
    logging.debug(f"DEBUG: {data}")''',
            
            # Attempt 2: Delete the debug code entirely
            '''def debug_print(data):
    pass  # Debug logging disabled for production'''
        ]
        
        # Mock sandbox for exploit verification
        mock_sandbox = Mock()
        
        # Baseline: Exploit works on vulnerable code
        # Attempt 1: Exploit still works (logging.debug still outputs)
        # Attempt 2: Exploit fails (code deleted, nothing outputs)
        mock_sandbox.run_python.side_effect = [
            ("DEBUG: sensitive\nEXPLOIT_SUCCESS", "", 0),  # Baseline
            ("DEBUG: sensitive\nEXPLOIT_SUCCESS", "", 0),  # Patch 1 verification
            ("EXPLOIT_FAILED", "", 0)                        # Patch 2 verification
        ]
        
        # Create Blue Team with mocks
        blue_team = BlueTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        vulnerable_code = '''def debug_print(data):
    print(f"DEBUG: {data}")'''
        
        exploit_code = '''import sys
sys.path.insert(0, '.')
from utils import debug_print
debug_print("sensitive")
print("EXPLOIT_SUCCESS")'''
        
        result = blue_team.patch_and_verify(
            target_file="utils.py",
            current_content=vulnerable_code,
            exploit_code=exploit_code,
            vulnerability_type="insecure logging",
            vulnerability_description="Debug prints leak sensitive data"
        )
        
        # Assertions
        assert result["success"] == True, "Should eventually succeed"
        assert result["attempts"] == 2, "Should take 2 attempts"
        assert "EXPLOIT_SUCCESS" not in result["verification_output"], "Final patch should block exploit"
        
        # Verify LLM was called twice
        assert mock_llm.invoke.call_count == 2
        
        # Check that second call includes failure history
        second_call_prompt = mock_llm.invoke.call_args_list[1][0][0]
        assert "PREVIOUS FAILED PATCHES" in second_call_prompt, "Should include failure history"
        assert "EXPLOIT_STILL_WORKED" in second_call_prompt or "Exploit STILL WORKED" in second_call_prompt, \
            "Should explain previous patch failed"
    
    def test_blue_team_records_why_patch_failed(self):
        """Test that Blue Team captures exploit output showing why patch didn't work"""
        
        mock_llm = Mock()
        mock_llm.invoke.side_effect = [
            "def test(): logging.debug('test')",  # Patch 1
            "def test(): logging.info('test')",   # Patch 2
            "def test(): pass"                     # Patch 3
        ]
        
        mock_sandbox = Mock()
        # Baseline works, all patches fail
        mock_sandbox.run_python.side_effect = [
            ("EXPLOIT_SUCCESS", "", 0),  # Baseline
            ("DEBUG LOG\nEXPLOIT_SUCCESS", "", 0),  # Patch 1 fails
            ("INFO LOG\nEXPLOIT_SUCCESS", "", 0),   # Patch 2 fails
            ("EXPLOIT_SUCCESS", "", 0)              # Patch 3 fails
        ]
        
        blue_team = BlueTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        result = blue_team.patch_and_verify(
            target_file="test.py",
            current_content="def test(): print('debug')",
            exploit_code="print('EXPLOIT_SUCCESS')",
            vulnerability_type="test",
            max_attempts=3
        )
        
        assert result["success"] == False, "All patches should fail"
        assert result["attempts"] == 3, "Should try all 3 attempts"
        
        # Check that failed patches were recorded
        # The LLM prompts should show increasing failure history
        call_prompts = [call[0][0] for call in mock_llm.invoke.call_args_list]
        
        # First call has no failure history
        assert "PREVIOUS FAILED PATCHES" not in call_prompts[0]
        
        # Second call has first failure
        assert "PREVIOUS FAILED PATCHES" in call_prompts[1]
        assert "Attempt #1" in call_prompts[1]
        
        # Third call has two failures
        assert "Attempt #1" in call_prompts[2]
        assert "Attempt #2" in call_prompts[2]
    
    def test_blue_team_gives_up_after_max_attempts(self):
        """Test that Blue Team stops trying after maximum attempts"""
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = "def test(): pass"
        
        mock_sandbox = Mock()
        # Exploit always succeeds (patch never works)
        mock_sandbox.run_python.return_value = (
            "EXPLOIT_SUCCESS",
            "",
            0
        )
        
        blue_team = BlueTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        result = blue_team.patch_and_verify(
            target_file="test.py",
            current_content="test",
            exploit_code="print('EXPLOIT_SUCCESS')",
            vulnerability_type="test",
            max_attempts=3
        )
        
        assert result["success"] == False
        assert result["attempts"] == 3
        assert "Could not generate valid patch" in result["error"]


class TestFailureMemoryIntegration:
    """Integration tests showing failure memory working across attempts"""
    
    def test_failure_context_includes_key_details(self):
        """Test that failure context includes all important information"""
        
        mock_llm = Mock()
        mock_llm.invoke.side_effect = [
            "def test():\\n    logging.debug('patch attempt 1')",  # Patch 1 - long enough
            "def test():\\n    pass  # patch attempt 2"  # Patch 2 - Should see failure context
        ]
        
        mock_sandbox = Mock()
        mock_sandbox.run_python.side_effect = [
            ("EXPLOIT_SUCCESS", "", 0),  # Baseline
            ("Still vulnerable\nEXPLOIT_SUCCESS", "Some error", 0),  # Patch 1
            ("EXPLOIT_FAILED", "", 0)   # Patch 2
        ]
        
        blue_team = BlueTeamAgent(llm=mock_llm, sandbox=mock_sandbox)
        
        result = blue_team.patch_and_verify(
            target_file="test.py",
            current_content="test",
            exploit_code="print('EXPLOIT_SUCCESS')",
            vulnerability_type="test"
        )
        
        # Get the second LLM call to check failure context
        second_call_prompt = mock_llm.invoke.call_args_list[1][0][0]
        
        # Should include these critical details
        assert "Attempt #1" in second_call_prompt
        assert "logging.debug('patch attempt 1')" in second_call_prompt  # The failed patch code
        assert "Still vulnerable" in second_call_prompt  # The exploit output
        assert "CRITICAL ANALYSIS" in second_call_prompt
        assert "DO NOT repeat similar approaches" in second_call_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
