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
            
            # Debug: Log what code we're analyzing
            logger.info(f"📝 Code to analyze ({len(code_to_analyze)} chars):")
            logger.info(f"   First 500 chars: {code_to_analyze[:500]!r}")
            
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
    "exploit_code": "Complete Python exploit code here. Must VERIFY the vulnerability exists, not just call the function."
}

CRITICAL RULES FOR EXPLOIT CODE:
1. Output ONLY valid JSON (no markdown, no extra text)
2. The exploit MUST actually VERIFY the vulnerability exists - don't just call the function and assume success
3. DO NOT redefine or copy the vulnerable function - you must test the actual code
4. Start with: import sys; sys.path.insert(0, '.')
5. Print "EXPLOIT_SUCCESS" ONLY when the vulnerability is actually confirmed to exist
6. Print "EXPLOIT_FAILED" if the vulnerability does NOT exist (code is secure)
7. Use try/except to catch errors
8. WRITE MULTI-LINE PYTHON CODE - DO NOT use semicolons to compress into one line

VERIFICATION STRATEGIES BY VULNERABILITY TYPE:

For INSECURE RANDOMNESS (random module instead of secrets):
- Read the source file and check if it imports 'random' module
- Check if the code uses random.choice, random.randint, etc.
- Example:
  with open('filename.py', 'r') as f:
      content = f.read()
  if 'import random' in content and 'random.' in content:
      print("EXPLOIT_SUCCESS: Code uses insecure random module")
  else:
      print("EXPLOIT_FAILED: Code uses secure randomness")

For HARDCODED CREDENTIALS:
- Read the source file and look for hardcoded strings like passwords, API keys
- Check for patterns: password = "...", api_key = "sk_...", etc.
- Example:
  import re
  with open('filename.py', 'r') as f:
      content = f.read()
  if re.search(r'(password|api_key|secret|token)\s*=\s*["\'][^"\']+["\']', content):
      print("EXPLOIT_SUCCESS: Found hardcoded credentials")
  else:
      print("EXPLOIT_FAILED: No hardcoded credentials found")

For SQL INJECTION:
- Call the function with SQL injection payload like "'; DROP TABLE--"
- Check if error message reveals SQL syntax or if injection worked

For COMMAND INJECTION:
- Call the function with payload like "; id" or "| whoami"
- Check if command output appears in result

For WEAK HASHING (MD5, SHA1):
- Read source and check for hashlib.md5, hashlib.sha1
- Example:
  with open('filename.py', 'r') as f:
      content = f.read()
  if 'md5' in content.lower() or 'sha1' in content.lower():
      print("EXPLOIT_SUCCESS: Weak hash algorithm found")
  else:
      print("EXPLOIT_FAILED: No weak hashing found")

IMPORTANT: Your exploit must be a VERIFICATION test - it should return EXPLOIT_FAILED if the code has been patched/fixed."""

        # Extract filename without path for import statement
        from pathlib import Path
        filename_only = Path(target_file).stem  # e.g., 'auth.py' -> 'auth'
        filename_with_ext = Path(target_file).name  # e.g., 'auth.py'
        
        user_prompt = f"""Analyze this vulnerability using the Kill Chain:

**Target File:** {target_file}
**Vulnerability Type:** {vulnerability_type}
**Description:** {description}

**Code (with context from dependencies):**
{code}
{failure_context}

Follow the Kill Chain:
1. RECON: Analyze the code. What imports are used? Where is the vulnerability? How does data flow?
2. PLAN: How will you VERIFY this vulnerability exists? What check proves it's vulnerable vs secure?
3. EXPLOIT: Write verification code that CHECKS if the vulnerability exists in the source file.

CRITICAL REQUIREMENTS:
- Your exploit must READ the source file '{filename_with_ext}' and CHECK for the vulnerability pattern
- Print "EXPLOIT_SUCCESS" ONLY if the vulnerability pattern is found
- Print "EXPLOIT_FAILED" if the code is secure (vulnerability not present)
- DO NOT just call the function and assume success - actually verify the insecure pattern exists

Example structure:
```python
import sys
sys.path.insert(0, '.')

# Read the source file to check for vulnerability
with open('{filename_with_ext}', 'r') as f:
    content = f.read()

# Check for the specific vulnerability pattern
if <vulnerability_pattern_found>:
    print("EXPLOIT_SUCCESS: <reason>")
else:
    print("EXPLOIT_FAILED: <reason>")
```

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
            vulnerable_code: Vulnerable code to make available for import (may include Knowledge Graph context)
            
        Returns:
            Dictionary with stdout, stderr, exit_code
        """
        try:
            # Prepare dependencies if we have the vulnerable code
            dependencies = {}
            if target_file and vulnerable_code:
                from pathlib import Path
                import re
                
                filename = Path(target_file).name
                
                # Parse all files from Knowledge Graph context format
                # Format: "=== Context: filename ===" or "=== Target: filename ==="
                # followed by the file content
                
                # First check if this is Knowledge Graph formatted content
                if "===" in vulnerable_code and ("Target:" in vulnerable_code or "Context:" in vulnerable_code):
                    logger.debug("Parsing Knowledge Graph context format")
                    
                    # Extract all file sections using regex
                    # Pattern matches: === Context: path/to/file.py === or === Target: path/to/file.py ===
                    pattern = r'===\s*(Context|Target):\s*(.+?)\s*===\s*\n'
                    
                    # Split by the pattern to get file contents
                    parts = re.split(pattern, vulnerable_code)
                    
                    # parts will be: [header_type1, filepath1, content1, header_type2, filepath2, content2, ...]
                    # Skip the first empty part if it exists
                    i = 0
                    if parts and not parts[0].strip():
                        i = 1
                    elif parts and not re.match(r'(Context|Target)', parts[0]):
                        i = 1
                    
                    while i + 2 < len(parts):
                        header_type = parts[i]  # "Context" or "Target"
                        file_path = parts[i + 1].strip()  # e.g., "api_service.py"
                        content = parts[i + 2]  # The actual code
                        
                        # Get just the filename for the sandbox
                        dep_filename = Path(file_path).name
                        
                        # Clean up the content - remove any trailing headers
                        content = content.strip()
                        
                        if content:
                            dependencies[dep_filename] = content
                            logger.debug(f"Extracted file: {dep_filename} ({len(content)} chars)")
                        
                        i += 3
                    
                    # If we couldn't extract anything, fall back to using the raw code
                    if not dependencies:
                        logger.warning("Failed to parse Knowledge Graph format, using raw code")
                        dependencies[filename] = vulnerable_code
                else:
                    # Not Knowledge Graph format, use as-is
                    logger.debug("Using raw vulnerable code (not Knowledge Graph format)")
                    dependencies[filename] = vulnerable_code
                
                # Log what we're injecting
                logger.info(f"Injecting {len(dependencies)} files into sandbox: {list(dependencies.keys())}")
                for fname, content in dependencies.items():
                    logger.info(f"  {fname}: {len(content)} chars")
                    logger.info(f"    First 200 chars: {content[:200]!r}")
                    logger.info(f"    Last 100 chars: {content[-100:]!r}")
            
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
        
        # Check for explicit success marker (highest priority)
        if "exploit_success" in stdout:
            logger.info("Found EXPLOIT_SUCCESS marker")
            return True
        
        # Check for explicit failure marker
        if "exploit_failed" in stdout:
            logger.warning("Found EXPLOIT_FAILED marker")
            return False
        
        # If exploit crashed with error, it failed
        if exit_code != 0:
            logger.info(f"Exploit crashed with exit_code {exit_code}")
            return False
        
        # Check for common success indicators in output
        success_indicators = [
            "uid=",  # Command injection
            "root:",  # Path traversal
            "etc/passwd",
            "<script>",  # XSS
            "<!entity",  # XXE
        ]
        
        if any(indicator in stdout for indicator in success_indicators):
            logger.info(f"Found success indicator in output")
            return True
        
        # If code ran successfully (exit 0) with output, consider it success
        if exit_code == 0 and stdout.strip():
            logger.info(f"Code executed successfully with output")
            return True
        
        # Default: if no clear indicators, mark as unverified
        logger.info(f"No exploit success indicators found")
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
