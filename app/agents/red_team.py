"""
Red Team Agent - Vulnerability Verification through Active Exploitation
Generates and executes exploit code to verify if vulnerabilities are real

Uses "Kill Chain" Methodology: RECON -> PLAN -> EXPLOIT
The agent must show its reasoning process, not just output code.
"""

from typing import Dict, Optional, List
import logging
import json
import re
from app.tools.sandbox import DockerSandbox
from app.core.llm import LLMClient, get_llm

logger = logging.getLogger(__name__)


class RedTeamError(Exception):
    """Base exception for red team operations"""
    pass


class RedTeamAgent:
    """
    Red Team agent that actively tests vulnerabilities using Kill Chain methodology
    
    Features:
    - RECON: Analyze code and dependencies (using Graph RAG context)
    - PLAN: Describe attack vector and payload strategy
    - EXPLOIT: Generate and execute proof-of-concept code
    - Execute exploits in isolated sandbox
    - Determine if vulnerability is real or false positive
    - Provide complete thought process for transparency
    """
    
    def __init__(self, llm: Optional[LLMClient] = None, sandbox: Optional[DockerSandbox] = None):
        """
        Initialize Red Team agent
        
        Args:
            llm: LLM client for exploit generation
            sandbox: Docker sandbox for exploit execution
        """
        self.llm = llm or get_llm()
        self.sandbox = sandbox or DockerSandbox()
        logger.info("RedTeamAgent initialized with Kill Chain methodology")
    
    def run_validation(
        self,
        target_file: str,
        vulnerability_details: Dict,
        context_code: Optional[str] = None
    ) -> Dict:
        """
        Validate vulnerability using Kill Chain methodology (RECON → PLAN → EXPLOIT)
        WITH ITERATIVE REASONING - learns from failed attempts
        
        This is the NEW primary validation method that shows the agent's thinking.
        
        Args:
            target_file: Path to the file with vulnerability
            vulnerability_details: Dict with 'type', 'description', 'function_code'
            context_code: Optional context from CodeKnowledgeBase (target + dependencies)
            
        Returns:
            Dictionary with:
            - verified: bool - Whether exploit succeeded
            - thought_process: dict - Contains 'recon', 'plan', 'exploit_code'
            - output: str - Execution output
            - error: str - Error message if any
            - attempts: int - Number of attempts made
        """
        try:
            logger.info(f"🎯 Starting Kill Chain validation for {target_file}")
            
            # Use context if provided, otherwise fall back to function code
            code_to_analyze = context_code or vulnerability_details.get('function_code', '')
            
            # PHASE 6: Iterative Reasoning with Failure Memory
            max_attempts = 3
            attempt_history = []  # Track failed attempts
            
            for attempt_num in range(1, max_attempts + 1):
                logger.info(f"📋 Attempt {attempt_num}/{max_attempts}: RECON + PLAN")
                
                # Step 1: Get Kill Chain analysis from LLM (with failure history)
                kill_chain_result = self._execute_kill_chain(
                    target_file=target_file,
                    code=code_to_analyze,
                    vulnerability_type=vulnerability_details.get('type', 'Unknown'),
                    description=vulnerability_details.get('description', ''),
                    attempt_history=attempt_history  # NEW: Pass failure history
                )
                
                if not kill_chain_result["success"]:
                    error_msg = kill_chain_result.get("error", "Failed to execute kill chain")
                    attempt_history.append({
                        "attempt": attempt_num,
                        "strategy": "LLM generation failed",
                        "error": error_msg,
                        "result": "FAILED"
                    })
                    continue  # Try again
                
                thought_process = kill_chain_result["thought_process"]
                
                # Log the thinking process
                recon_text = thought_process.get('recon', 'No recon available')[:200]
                plan_text = thought_process.get('plan', 'No plan available')[:200]
                logger.info(f"RECON: {recon_text}...")
                logger.info(f"PLAN: {plan_text}...")
                print(f"\nRECON: {recon_text}...")
                print(f"PLAN: {plan_text}...")
                
                # Step 2: Execute the exploit
                logger.info("Phase 2: EXPLOIT")
                exploit_code = thought_process['exploit_code']
                
                execution_result = self._execute_exploit(
                    exploit_code=exploit_code,
                    target_file=target_file,
                    vulnerable_code=code_to_analyze
                )
                
                # Step 3: Verify success
                verified = self._analyze_exploit_result(
                    execution_result,
                    vulnerability_details.get('type', 'Unknown')
                )
                
                if verified:
                    # SUCCESS! Return immediately
                    result_status = "EXPLOIT_SUCCESS"
                    logger.info(f"✅ {result_status} on attempt {attempt_num}")
                    
                    return {
                        "verified": True,
                        "thought_process": thought_process,
                        "output": execution_result["stdout"],
                        "error": "",
                        "attempts": attempt_num
                    }
                else:
                    # FAILURE: Record what didn't work
                    result_status = "EXPLOIT_FAILED"
                    logger.warning(f"❌ {result_status} on attempt {attempt_num}")
                    
                    # Extract the key strategy from the plan
                    strategy_summary = plan_text[:150]  # First 150 chars of plan
                    
                    attempt_history.append({
                        "attempt": attempt_num,
                        "strategy": strategy_summary,
                        "exploit_snippet": exploit_code[:200],  # First 200 chars
                        "stdout": execution_result["stdout"][:200],
                        "stderr": execution_result["stderr"][:200],
                        "exit_code": execution_result["exit_code"],
                        "result": "FAILED"
                    })
                    
                    if attempt_num < max_attempts:
                        logger.info(f"🔄 Retrying with different strategy...")
            
            # All attempts failed
            logger.error(f"💥 All {max_attempts} attempts failed")
            return {
                "verified": False,
                "thought_process": thought_process if 'thought_process' in locals() else {},
                "output": execution_result["stdout"] if 'execution_result' in locals() else "",
                "error": "All exploitation attempts failed after iterative reasoning",
                "attempts": max_attempts,
                "attempt_history": attempt_history
            }
            
        except Exception as e:
            logger.error(f"Critical error in validation: {e}")
            return {
                "verified": False,
                "thought_process": {},
                "output": "",
                "error": str(e)
            }
            
            # Step 1: Get Kill Chain analysis from LLM
            logger.info("📋 Phase 1: RECON + PLAN")
            kill_chain_result = self._execute_kill_chain(
                target_file=target_file,
                code=code_to_analyze,
                vulnerability_type=vulnerability_details.get('type', 'Unknown'),
                description=vulnerability_details.get('description', '')
            )
            
            if not kill_chain_result["success"]:
                return {
                    "verified": False,
                    "thought_process": {},
                    "output": "",
                    "error": kill_chain_result.get("error", "Failed to execute kill chain")
                }
            
            thought_process = kill_chain_result["thought_process"]
            
            # Log the thinking process (CRITICAL: These logs show the agent's reasoning)
            recon_text = thought_process.get('recon', 'No recon available')[:200]
            plan_text = thought_process.get('plan', 'No plan available')[:200]
            logger.info(f"RECON: {recon_text}...")
            logger.info(f"PLAN: {plan_text}...")
            print(f"\nRECON: {recon_text}...")  # Also print to stdout for test capture
            print(f"PLAN: {plan_text}...")
            
            # Step 2: Execute the exploit
            logger.info("Phase 2: EXPLOIT")
            exploit_code = thought_process['exploit_code']
            
            execution_result = self._execute_exploit(
                exploit_code=exploit_code,
                target_file=target_file,
                vulnerable_code=code_to_analyze
            )
            
            # Step 3: Verify success
            verified = self._analyze_exploit_result(
                execution_result,
                vulnerability_details.get('type', 'Unknown')
            )
            
            result_status = "EXPLOIT_SUCCESS" if verified else "EXPLOIT_FAILED"
            logger.info(f"RESULT: {result_status}")
            
            return {
                "verified": verified,
                "thought_process": thought_process,
                "output": execution_result["stdout"],
                "error": execution_result["stderr"] if execution_result["exit_code"] != 0 else ""
            }
            
        except Exception as e:
            logger.error(f"Kill Chain validation failed: {e}")
            return {
                "verified": False,
                "thought_process": {},
                "output": "",
                "error": str(e)
            }
    
    def _execute_kill_chain(
        self,
        target_file: str,
        code: str,
        vulnerability_type: str,
        description: str,
        attempt_history: List[Dict] = None
    ) -> Dict:
        """
        Execute Kill Chain analysis: RECON -> PLAN -> EXPLOIT
        WITH FAILURE MEMORY - learns from previous failed attempts
        
        Args:
            target_file: Path to the vulnerable file (e.g., 'auth.py')
            code: Code to analyze (with dependencies from Graph RAG)
            vulnerability_type: Type of vulnerability
            description: Vulnerability description
            attempt_history: List of previous failed attempts (for iterative reasoning)
            
        Returns:
            Dictionary with success status and thought_process
        """
        # Build failure context if we have history
        failure_context = ""
        if attempt_history and len(attempt_history) > 0:
            failure_context = "\n\n⚠️ PREVIOUS FAILED ATTEMPTS - DO NOT REPEAT THESE:\n"
            for attempt in attempt_history:
                failure_context += f"\nAttempt #{attempt['attempt']}:\n"
                failure_context += f"Strategy: {attempt['strategy']}\n"
                if 'exploit_snippet' in attempt:
                    failure_context += f"Exploit Code (first 200 chars): {attempt['exploit_snippet']}\n"
                if 'stderr' in attempt and attempt['stderr']:
                    failure_context += f"Error: {attempt['stderr']}\n"
                failure_context += f"Result: {attempt['result']}\n"
            
            failure_context += "\n🧠 ANALYSIS REQUIRED:\n"
            failure_context += "- WHY did the previous attempts fail? (Syntax error? Wrong payload? Missing setup?)\n"
            failure_context += "- What was WRONG with the approach?\n"
            failure_context += "- What DIFFERENT strategy should you try now?\n"
            failure_context += "- DO NOT repeat the same exploit code or similar approaches!\n"
        
        system_prompt = """You are an Elite Red Team Operator. You must follow the Kill Chain methodology.

Your response MUST be valid JSON with this exact structure:
{
    "recon": "Your reconnaissance analysis here. Analyze the code, identify data flow, spot the vulnerability location, understand imports and dependencies.",
    "plan": "Your attack plan here. Describe HOW to trigger the vulnerability. What input? What payload? What function calls?",
    "exploit_code": "Complete Python exploit code here. Must test the actual vulnerable function by importing and calling it."
}

CRITICAL RULES FOR EXPLOIT CODE:
1. Output ONLY valid JSON (no markdown, no extra text)
2. The exploit MUST import and call the vulnerable function from the target file
3. DO NOT redefine or copy the vulnerable function - you must test the actual code
4. Start with: import sys; sys.path.insert(0, '.'); from <filename> import <function>
5. For database vulnerabilities: The function may create its own connection - just call it and check if malicious input works
6. For file system vulnerabilities: Create temporary test files if needed
7. Print "EXPLOIT_SUCCESS" when the vulnerability is confirmed (e.g., SQL injection bypasses auth, command injection executes, etc.)
8. Print "EXPLOIT_FAILED" if the exploit does not work
9. Use try/except to catch errors
10. WRITE MULTI-LINE PYTHON CODE - DO NOT use semicolons to compress into one line
11. Each statement must be on its own line with proper indentation

Remember: Create any files/databases the vulnerable function expects. Test the actual vulnerability works."""

        # Extract filename without path for import statement
        from pathlib import Path
        filename_only = Path(target_file).stem  # e.g., 'auth.py' -> 'auth'
        
        user_prompt = f"""Analyze this vulnerability using the Kill Chain:

**Target File:** {target_file}
**Vulnerability Type:** {vulnerability_type}
**Description:** {description}

**Code (with context from dependencies):**
{code}

{failure_context}

Follow the Kill Chain:
1. RECON: Analyze the code. What imports are used? Where is the vulnerability? How does data flow? Identify the vulnerable function name.
2. PLAN: How will you exploit it? What input triggers the bug? What is the attack vector?
3. EXPLOIT: Write proof-of-concept code that IMPORTS the vulnerable function from '{target_file}'.

CRITICAL: Your exploit_code MUST start with:
import sys
sys.path.insert(0, '.')
from {filename_only} import <function_name>

Then call the imported function with malicious input. DO NOT redefine the function in your exploit.
Print "EXPLOIT_SUCCESS" if the vulnerability works, "EXPLOIT_FAILED" if not.

Return your response as valid JSON with keys: recon, plan, exploit_code"""

        try:
            response = self.llm.invoke(user_prompt, system_message=system_prompt)
            
            # Try to parse JSON
            response_text = response.strip()
            
            # Remove markdown code fences if present
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1]
            if response_text.startswith("```"):
                response_text = response_text.split("```", 1)[1]
            if response_text.endswith("```"):
                response_text = response_text.rsplit("```", 1)[0]
            
            response_text = response_text.strip()
            
            # Try direct parsing first
            try:
                thought_process = json.loads(response_text)
            except json.JSONDecodeError as e:
                # If that fails, try extracting JSON with regex
                logger.warning(f"JSON decode failed, attempting extraction: {e}")
                
                # Extract individual fields with regex as fallback
                recon_match = re.search(r'"recon"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text, re.DOTALL)
                plan_match = re.search(r'"plan"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text, re.DOTALL)
                exploit_match = re.search(r'"exploit_code"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text, re.DOTALL)
                
                if recon_match and plan_match and exploit_match:
                    thought_process = {
                        "recon": recon_match.group(1).replace('\\"', '"').replace('\\n', '\n'),
                        "plan": plan_match.group(1).replace('\\"', '"').replace('\\n', '\n'),
                        "exploit_code": exploit_match.group(1).replace('\\"', '"').replace('\\n', '\n')
                    }
                    logger.info("Successfully extracted Kill Chain using regex fallback")
                else:
                    raise e  # Re-raise if we couldn't extract
            
            # Validate required keys
            required_keys = ["recon", "plan", "exploit_code"]
            for key in required_keys:
                if key not in thought_process:
                    return {
                        "success": False,
                        "thought_process": {},
                        "error": f"Missing required key: {key}"
                    }
            
            return {
                "success": True,
                "thought_process": thought_process,
                "error": ""
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Kill Chain JSON: {e}")
            logger.error(f"Response was: {response[:500]}")
            return {
                "success": False,
                "thought_process": {},
                "error": f"Invalid JSON response: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Failed to execute kill chain: {e}")
            return {
                "success": False,
                "thought_process": {},
                "error": str(e)
            }
    
    def verify_vulnerability(
        self,
        filename: str,
        function_code: str,
        vulnerability_type: str,
        description: str = ""
    ) -> Dict:
        """
        Verify if a vulnerability is real by generating and running an exploit
        (LEGACY METHOD - Use run_validation() for Kill Chain methodology)
        
        Args:
            filename: Name of the file containing vulnerability
            function_code: The vulnerable function code
            vulnerability_type: Type of vulnerability (e.g., "SQL Injection")
            description: Description of the vulnerability
            
        Returns:
            Dictionary with:
            - verified: bool - Whether exploit succeeded
            - output: str - Execution output
            - exploit_code: str - Generated exploit code
            - error: str - Error message if generation/execution failed
        """
        try:
            # Generate exploit code
            logger.info(f"Generating exploit for {vulnerability_type} in {filename}")
            exploit_result = self._generate_exploit(
                function_code,
                vulnerability_type,
                description
            )
            
            if not exploit_result["success"]:
                return {
                    "verified": False,
                    "output": "",
                    "exploit_code": exploit_result.get("code", ""),
                    "error": exploit_result.get("error", "Failed to generate exploit")
                }
            
            exploit_code = exploit_result["code"]
            
            # Execute exploit in sandbox
            logger.info(f"Executing exploit in sandbox for {filename}")
            execution_result = self._execute_exploit(exploit_code)
            
            # Determine if vulnerability is verified
            verified = self._analyze_exploit_result(
                execution_result,
                vulnerability_type
            )
            
            logger.info(f"Verification result for {filename}: {'VERIFIED' if verified else 'NOT VERIFIED'}")
            
            return {
                "verified": verified,
                "output": execution_result["stdout"],
                "exploit_code": exploit_code,
                "error": execution_result["stderr"] if execution_result["exit_code"] != 0 else ""
            }
            
        except Exception as e:
            logger.error(f"Failed to verify vulnerability: {e}")
            return {
                "verified": False,
                "output": "",
                "exploit_code": "",
                "error": str(e)
            }
    
    def _generate_exploit(
        self,
        function_code: str,
        vulnerability_type: str,
        description: str
    ) -> Dict:
        """
        Generate exploit code using LLM
        
        Args:
            function_code: The vulnerable function
            vulnerability_type: Type of vulnerability
            description: Vulnerability description
            
        Returns:
            Dictionary with success status and exploit code
        """
        system_prompt = """You are a Senior Penetration Tester specializing in exploit development.
Your task is to generate a Python proof-of-concept exploit that demonstrates the vulnerability.

CRITICAL RULES:
1. Generate ONLY executable Python code (no markdown, no explanations)
2. Mock any external dependencies (databases, APIs, etc.)
3. The exploit should clearly demonstrate the vulnerability
4. Print "EXPLOIT_SUCCESS" if the vulnerability is exploitable
5. Print "EXPLOIT_FAILED" if the vulnerability cannot be exploited
6. Handle errors gracefully

The exploit should be self-contained and runnable."""

        user_prompt = f"""Generate a Python exploit for this vulnerability:

**Vulnerability Type:** {vulnerability_type}
**Description:** {description}

**Vulnerable Code:**
{function_code}

Generate a complete Python script that:
1. Mocks any dependencies (database connections, file systems, etc.)
2. Calls the vulnerable function with a malicious payload
3. Prints "EXPLOIT_SUCCESS" if the exploit works
4. Prints "EXPLOIT_FAILED" if the exploit fails or function is actually safe

Return ONLY the Python code, no markdown formatting."""

        try:
            response = self.llm.invoke(user_prompt, system_message=system_prompt)
            
            # Clean up response
            exploit_code = response.strip()
            
            # Remove markdown code fences if present
            if exploit_code.startswith("```python"):
                exploit_code = exploit_code.split("```python")[1]
            if exploit_code.startswith("```"):
                exploit_code = exploit_code.split("```", 1)[1]
            if exploit_code.endswith("```"):
                exploit_code = exploit_code.rsplit("```", 1)[0]
            
            exploit_code = exploit_code.strip()
            
            # Validate it's Python code
            if not exploit_code or len(exploit_code) < 10:
                return {
                    "success": False,
                    "code": "",
                    "error": "Generated exploit code too short"
                }
            
            return {
                "success": True,
                "code": exploit_code,
                "error": ""
            }
            
        except Exception as e:
            logger.error(f"Failed to generate exploit: {e}")
            return {
                "success": False,
                "code": "",
                "error": str(e)
            }
    
    def _execute_exploit(
        self,
        exploit_code: str,
        target_file: str = None,
        vulnerable_code: str = None
    ) -> Dict:
        """
        Execute exploit code in sandbox
        
        Args:
            exploit_code: Python exploit code
            target_file: Target file name (e.g., 'auth.py')
            vulnerable_code: Vulnerable code to make available for import
            
        Returns:
            Dictionary with stdout, stderr, exit_code
        """
        try:
            # Prepare dependencies if we have the vulnerable code
            dependencies = {}
            if target_file and vulnerable_code:
                from pathlib import Path
                filename = Path(target_file).name
                
                # Clean the vulnerable code - remove knowledge graph headers
                # Headers look like: "=== Target: filename ===" or "=== Context: filename ==="
                clean_code = vulnerable_code
                import re
                
                # Split by the target marker and take only the code after it
                if "=== Target:" in clean_code:
                    # Find the target section
                    parts = clean_code.split(f"=== Target: {target_file} ===")
                    if len(parts) > 1:
                        clean_code = parts[1].strip()
                
                # Also remove any context headers that might be in the middle
                clean_code = re.sub(r'===\s+(Context|Target):\s+.+?\s+===\s*\n', '', clean_code)
                
                dependencies[filename] = clean_code
            
            stdout, stderr, exit_code = self.sandbox.run_python(
                code=exploit_code,
                dependencies=dependencies if dependencies else None,
                timeout=10
            )
            
            logger.info(f"Exploit stdout: {stdout[:500]}")
            logger.info(f"Exploit stderr: {stderr[:200]}")
            logger.info(f"Exploit exit_code: {exit_code}")
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code
            }
            
        except Exception as e:
            logger.error(f"Failed to execute exploit: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1
            }
    
    def _analyze_exploit_result(
        self,
        execution_result: Dict,
        vulnerability_type: str
    ) -> bool:
        """
        Analyze exploit execution result to determine if vulnerability is real
        
        Args:
            execution_result: Result from exploit execution
            vulnerability_type: Type of vulnerability
            
        Returns:
            True if vulnerability is verified, False otherwise
        """
        stdout = execution_result.get("stdout", "").lower()
        stderr = execution_result.get("stderr", "").lower()
        exit_code = execution_result.get("exit_code", 1)
        
        # DEBUG: Show what we're analyzing
        logger.info(f"Analyzing exploit result:")
        logger.info(f"  stdout (first 200 chars): {stdout[:200]}")
        logger.info(f"  stderr (first 200 chars): {stderr[:200]}")
        logger.info(f"  exit_code: {exit_code}")
        
        # Check for explicit success marker
        if "exploit_success" in stdout:
            logger.info("Found EXPLOIT_SUCCESS marker")
            return True
        
        # Check for explicit failure marker
        if "exploit_failed" in stdout:
            logger.warning("Found EXPLOIT_FAILED marker")
            return False
        
        # If exploit crashed, it might still indicate vulnerability
        # but we'll be conservative and mark as unverified
        if exit_code != 0:
            # Check if error suggests vulnerability was triggered
            vulnerability_indicators = [
                "injection",
                "traversal",
                "overflow",
                "unauthorized",
                "malicious"
            ]
            
            output = stdout + stderr
            if any(indicator in output for indicator in vulnerability_indicators):
                logger.warning(f"Exploit crashed but shows vulnerability indicators")
                return True
            
            return False
        
        # Check for vulnerability-specific success indicators
        success_indicators = {
            "sql injection": ["select", "union", "drop table", "'; --"],
            "command injection": ["uid=", "total", "directory of", "ping"],
            "path traversal": ["etc/passwd", "root:", "windows", "system32"],
            "xss": ["<script>", "alert(", "onerror="],
            "xxe": ["<!entity", "<!doctype"],
            "ssrf": ["connection", "request", "http://"]
        }
        
        vuln_type_lower = vulnerability_type.lower()
        for vuln_key, indicators in success_indicators.items():
            if vuln_key in vuln_type_lower:
                if any(indicator in stdout for indicator in indicators):
                    return True
        
        # Default: if no clear indicators, mark as unverified
        return False
    
    def generate_exploit_report(self, verification_result: Dict, vulnerability_info: Dict) -> str:
        """
        Generate a detailed report of the verification attempt
        
        Args:
            verification_result: Result from verify_vulnerability
            vulnerability_info: Original vulnerability information
            
        Returns:
            Formatted report string
        """
        status = "VERIFIED" if verification_result["verified"] else "NOT VERIFIED"
        
        error_text = ""
        if verification_result['error']:
            error_text = f"Error: {verification_result['error']}"
        
        report = f"""
Red Team Verification Report
============================

Status: {status}
Vulnerability: {vulnerability_info.get('type', 'Unknown')}
File: {vulnerability_info.get('file', 'Unknown')}
Function: {vulnerability_info.get('function', 'Unknown')}

Exploit Output:
{verification_result['output'][:500]}

{error_text}
"""
        return report


def create_red_team_agent(**kwargs) -> RedTeamAgent:
    """
    Factory function to create a RedTeamAgent
    
    Args:
        **kwargs: Arguments for RedTeamAgent
        
    Returns:
        RedTeamAgent instance
    """
    return RedTeamAgent(**kwargs)
