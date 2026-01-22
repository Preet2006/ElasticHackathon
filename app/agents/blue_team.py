"""
Blue Team Agent - Automated Security Patching with Test-Driven Repair
Fixes vulnerabilities and verifies patches by running exploits against patched code
"""

from typing import Dict, Optional, List
import logging
from pathlib import Path
from app.tools.sandbox import DockerSandbox
from app.core.llm import LLMClient, get_llm
from app.core.knowledge import CodeKnowledgeBase

logger = logging.getLogger(__name__)


class BlueTeamError(Exception):
    """Base exception for blue team operations"""
    pass


class BlueTeamAgent:
    """
    Blue Team agent that fixes vulnerabilities using Test-Driven Repair
    
    Workflow:
    1. Receive vulnerable code + exploit from Red Team
    2. Generate patch using LLM with Graph RAG context
    3. Run Red Team's exploit against patched code
    4. Verify fix: Exploit should FAIL on patched code
    5. Return patched code if verified
    
    Features:
    - Context-aware patching (uses imported dependencies)
    - Test-driven verification (exploit must fail)
    - Iterative repair (can retry if first patch fails)
    """
    
    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        sandbox: Optional[DockerSandbox] = None,
        knowledge_base: Optional[CodeKnowledgeBase] = None
    ):
        """
        Initialize Blue Team agent
        
        Args:
            llm: LLM client for patch generation
            sandbox: Docker sandbox for verification
            knowledge_base: Code knowledge base for context
        """
        self.llm = llm or get_llm()
        self.sandbox = sandbox or DockerSandbox()
        self.knowledge_base = knowledge_base or CodeKnowledgeBase()
        logger.info("BlueTeamAgent initialized with Test-Driven Repair")
    
    def patch_and_verify(
        self,
        target_file: str,
        current_content: str,
        exploit_code: str,
        vulnerability_type: str,
        vulnerability_description: str = "",
        max_attempts: int = 3
    ) -> Dict:
        """
        Generate and verify a security patch using Test-Driven Repair
        WITH ITERATIVE REASONING - learns from failed patches
        
        Args:
            target_file: Path to vulnerable file
            current_content: Current vulnerable code
            exploit_code: Red Team's exploit that proves the bug
            vulnerability_type: Type of vulnerability (e.g., "SQL Injection")
            vulnerability_description: Description of the vulnerability
            max_attempts: Maximum patch attempts (default: 3)
            
        Returns:
            Dictionary with:
            - success: bool - Whether patch was successful
            - patched_content: str - The fixed code (if successful)
            - verification_output: str - Exploit output on patched code
            - attempts: int - Number of attempts made
            - error: str - Error message if failed
        """
        logger.info(f"🛡️ Starting patch generation for {target_file}")
        
        # Step 0: Verify the exploit works on vulnerable code
        logger.info("Step 0: Verifying exploit works on vulnerable code...")
        baseline_result = self._run_exploit_verification(
            target_file, current_content, exploit_code
        )
        
        if "EXPLOIT_SUCCESS" not in baseline_result.get("output", ""):
            logger.warning("⚠️ Exploit doesn't succeed on vulnerable code - skipping patch")
            return {
                "success": False,
                "patched_content": "",
                "verification_output": baseline_result.get("output", ""),
                "attempts": 0,
                "error": "Exploit doesn't work on original code (false positive)"
            }
        
        logger.info("✅ Exploit confirmed on vulnerable code. Proceeding with patch...")
        
        # Step 1: Get context from Graph RAG
        context = ""
        if self.knowledge_base:
            try:
                context = self.knowledge_base.get_context(target_file, depth=1)
                if context:
                    logger.info(f"📚 Using context ({len(context)} chars)")
            except Exception as e:
                logger.warning(f"Could not get context: {e}")
        
        # PHASE 6: Iterative Reasoning with Failure Memory
        failed_patches = []  # Track failed patch attempts
        
        # Step 2: Attempt to generate and verify patch
        for attempt in range(1, max_attempts + 1):
            logger.info(f"🔧 Patch attempt {attempt}/{max_attempts}")
            
            try:
                # Generate patch (with failure history)
                patch_result = self._generate_patch(
                    target_file=target_file,
                    vulnerable_code=current_content,
                    vulnerability_type=vulnerability_type,
                    vulnerability_description=vulnerability_description,
                    context=context,
                    failed_patches=failed_patches  # NEW: Pass failure history
                )
                
                if not patch_result["success"]:
                    logger.error(f"Failed to generate patch: {patch_result['error']}")
                    failed_patches.append({
                        "attempt": attempt,
                        "error": "LLM generation failed",
                        "details": patch_result['error'],
                        "result": "GENERATION_FAILED"
                    })
                    continue
                
                patched_content = patch_result["patched_code"]
                
                # Log the patched code snippet for debugging
                logger.info(f"Generated patch (first 300 chars): {patched_content[:300]}...")
                print(f"\n📝 Generated patch preview:\n{patched_content[:400]}...\n")
                
                # Verify patch by running exploit
                logger.info("🧪 Running exploit against patched code...")
                verification = self._run_exploit_verification(
                    target_file, patched_content, exploit_code
                )
                
                # Check if exploit failed (meaning patch worked!)
                exploit_output = verification.get("output", "")
                exit_code = verification.get("exit_code", 0)
                
                if "EXPLOIT_SUCCESS" not in exploit_output:
                    # Exploit failed! Patch worked!
                    logger.info(f"✅ Patch verified! Exploit failed on patched code (attempt {attempt})")
                    return {
                        "success": True,
                        "patched_content": patched_content,
                        "verification_output": exploit_output,
                        "attempts": attempt,
                        "error": ""
                    }
                else:
                    # FAILURE: Exploit still works - record what didn't work
                    logger.warning(f"❌ Patch failed verification - exploit still works (attempt {attempt})")
                    print(f"❌ Patch failed verification - exploit still works (attempt {attempt})")
                    
                    # Record the failed patch for learning
                    failed_patches.append({
                        "attempt": attempt,
                        "patched_code": patched_content[:500],  # First 500 chars
                        "exploit_output": exploit_output[:300],
                        "verification_stderr": verification.get("stderr", "")[:200],
                        "exit_code": exit_code,
                        "result": "EXPLOIT_STILL_WORKS"
                    })
                    
            except Exception as e:
                logger.error(f"Patch attempt {attempt} failed: {e}")
                failed_patches.append({
                    "attempt": attempt,
                    "error": str(e),
                    "result": "EXCEPTION"
                })
                continue
        
        # All attempts exhausted
        logger.error(f"💥 Failed to generate working patch after {max_attempts} attempts")
        return {
            "success": False,
            "patched_content": "",
            "verification_output": "",
            "attempts": max_attempts,
            "error": f"Could not generate valid patch after {max_attempts} attempts"
        }
    
    def _generate_patch(
        self,
        target_file: str,
        vulnerable_code: str,
        vulnerability_type: str,
        vulnerability_description: str,
        context: str = "",
        failed_patches: List[Dict] = None
    ) -> Dict:
        """
        Generate a security patch using LLM
        WITH FAILURE MEMORY - learns from previous failed patches
        
        Args:
            target_file: File path
            vulnerable_code: Current vulnerable code
            vulnerability_type: Type of vulnerability
            vulnerability_description: Vulnerability description
            context: Additional context from Graph RAG
            failed_patches: List of previous failed patch attempts (for iterative reasoning)
            
        Returns:
            Dictionary with success status and patched code
        """
        # Build failure context if we have history
        failure_context = ""
        if failed_patches and len(failed_patches) > 0:
            failure_context = "\n\n⚠️ PREVIOUS FAILED PATCHES - DO NOT REPEAT THESE APPROACHES:\n"
            for failed in failed_patches:
                failure_context += f"\nAttempt #{failed['attempt']}:\n"
                if 'patched_code' in failed:
                    failure_context += f"Patch Code (first 500 chars):\n{failed['patched_code']}\n"
                if 'exploit_output' in failed:
                    failure_context += f"Result: Exploit STILL WORKED. Output: {failed['exploit_output']}\n"
                if 'error' in failed:
                    failure_context += f"Error: {failed['error']}\n"
                failure_context += f"Status: {failed['result']}\n"
            
            failure_context += "\n🧠 CRITICAL ANALYSIS REQUIRED:\n"
            failure_context += "- WHY did the previous patches fail to stop the exploit?\n"
            failure_context += "- What was INSUFFICIENT about those approaches?\n"
            failure_context += "- What DIFFERENT, STRONGER approach should you try?\n"
            failure_context += "- Examples:\n"
            failure_context += "  * If 'logging' didn't work → Delete the statement entirely or disable output\n"
            failure_context += "  * If 'input validation' didn't work → Use parameterized queries or safe APIs\n"
            failure_context += "  * If 'escaping' didn't work → Use allowlists or remove the functionality\n"
            failure_context += "- DO NOT repeat similar approaches that already failed!\n"
        
        system_prompt = """You are an Expert Security Engineer specializing in vulnerability remediation.
            target_file: File path
            vulnerable_code: Current vulnerable code
            vulnerability_type: Type of vulnerability
            vulnerability_description: Vulnerability description
            context: Additional context from Graph RAG
            previous_attempt: Whether this is a retry
            
        Returns:
            Dictionary with success status and patched code
        """
        system_prompt = """You are an Expert Security Engineer specializing in vulnerability remediation.
Your task is to fix security vulnerabilities while maintaining functionality.

CRITICAL RULES:
1. Return ONLY the complete fixed code (no markdown, no explanations)
2. Maintain all imports and dependencies exactly as they were
3. Preserve function signatures and behavior (except the vulnerability)
4. Use secure coding practices (parameterized queries, input validation, etc.)
5. Do NOT add comments explaining the fix - just fix the code
6. Ensure the code is syntactically correct and runnable
7. The fix must completely eliminate the vulnerability, not just make it harder to exploit

SECURE CODING EXAMPLES:

**SQL Injection** - Use parameterized queries:
❌ WRONG: query = f"SELECT * FROM users WHERE name = '{name}'"
✅ CORRECT: cursor.execute("SELECT * FROM users WHERE name = ?", (name,))

**Command Injection** - Use subprocess with list, never shell=True:
❌ WRONG: os.system(f"ping {host}")
✅ CORRECT: subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)

**Path Traversal** - Validate paths and use os.path functions:
❌ WRONG: open("/uploads/" + filename)
✅ CORRECT: 
    safe_path = os.path.abspath(os.path.join("/uploads", filename))
    if not safe_path.startswith("/uploads/"):
        raise ValueError("Invalid path")
    open(safe_path)

**Insecure Deserialization** - Use JSON instead of pickle:
❌ WRONG: pickle.loads(base64.b64decode(token))
✅ CORRECT: json.loads(base64.b64decode(token).decode())

**Weak Hashing** - Use bcrypt/argon2 not MD5:
❌ WRONG: hashlib.md5(password.encode()).hexdigest()
✅ CORRECT: bcrypt.hashpw(password.encode(), bcrypt.gensalt())

**Hardcoded Credentials** - Use environment variables:
❌ WRONG: API_KEY = "sk_live_abc123"
✅ CORRECT: API_KEY = os.getenv("STRIPE_API_KEY", "")

**Debug Logging** - Remove or use proper logging levels:
❌ WRONG: print(f"DEBUG: {sensitive_data}")
✅ CORRECT: # Remove debug statement or use logging.debug() with careful formatting

Remember: The exploit MUST fail after your patch is applied!"""

        additional_context = ""
        if context:
            additional_context = f"\n\n**Context (imported dependencies):**\n{context[:1000]}"
        
        user_prompt = f"""Fix this security vulnerability:

**File:** {target_file}
**Vulnerability Type:** {vulnerability_type}
**Description:** {vulnerability_description}

**Vulnerable Code:**
```python
{vulnerable_code}
```{additional_context}{failure_context}

Return ONLY the fixed Python code with NO markdown formatting."""

        try:
            response = self.llm.invoke(user_prompt, system_message=system_prompt)
            
            # Clean up response
            patched_code = response.strip()
            
            # Remove markdown code fences if present
            if patched_code.startswith("```python"):
                patched_code = patched_code.split("```python")[1]
            if patched_code.startswith("```"):
                patched_code = patched_code.split("```", 1)[1]
            if patched_code.endswith("```"):
                patched_code = patched_code.rsplit("```", 1)[0]
            
            patched_code = patched_code.strip()
            
            # Validate it's not empty
            if not patched_code or len(patched_code) < 10:
                return {
                    "success": False,
                    "patched_code": "",
                    "error": "Generated patch too short"
                }
            
            return {
                "success": True,
                "patched_code": patched_code,
                "error": ""
            }
            
        except Exception as e:
            logger.error(f"Failed to generate patch: {e}")
            return {
                "success": False,
                "patched_code": "",
                "error": str(e)
            }
    
    def _run_exploit_verification(
        self,
        target_file: str,
        code_content: str,
        exploit_code: str
    ) -> Dict:
        """
        Run exploit against code to verify patch
        
        Args:
            target_file: Target file name
            code_content: Code to test (vulnerable or patched)
            exploit_code: Exploit script
            
        Returns:
            Dictionary with stdout, stderr, exit_code
        """
        try:
            # Extract just the filename
            filename = Path(target_file).name
            
            # Run exploit in sandbox with target file as dependency
            stdout, stderr, exit_code = self.sandbox.run_python(
                code=exploit_code,
                dependencies={filename: code_content},
                timeout=10
            )
            
            return {
                "output": stdout,
                "stderr": stderr,
                "exit_code": exit_code
            }
            
        except Exception as e:
            logger.error(f"Failed to run verification: {e}")
            return {
                "output": "",
                "stderr": str(e),
                "exit_code": 1
            }
    
    def generate_patch_report(
        self,
        result: Dict,
        target_file: str,
        vulnerability_type: str
    ) -> str:
        """
        Generate a human-readable patch report
        
        Args:
            result: Result from patch_and_verify
            target_file: Target file
            vulnerability_type: Vulnerability type
            
        Returns:
            Formatted report string
        """
        status = "✅ PATCH VERIFIED" if result["success"] else "❌ PATCH FAILED"
        
        report = f"""
Blue Team Patch Report
======================

Status: {status}
Vulnerability: {vulnerability_type}
File: {target_file}
Attempts: {result['attempts']}

{f"Error: {result['error']}" if result.get('error') else 'Patch successfully verified!'}

Verification Output:
{result.get('verification_output', 'No output')[:500]}
"""
        return report


def create_blue_team_agent(**kwargs) -> BlueTeamAgent:
    """
    Factory function to create a BlueTeamAgent
    
    Args:
        **kwargs: Arguments for BlueTeamAgent
        
    Returns:
        BlueTeamAgent instance
    """
    return BlueTeamAgent(**kwargs)
