"""
Orchestrator - Coordinates Auditor → Red Team → Blue Team → PR workflow
Provides user control for verification and fixing
Includes Knowledge Graph for context-aware analysis
"""

from typing import List, Dict, Optional
from pathlib import Path
import logging
import tempfile
import shutil
from app.agents.auditor import RepositoryAuditor
from app.agents.red_team import RedTeamAgent
from app.agents.blue_team import BlueTeamAgent
from app.core.prioritizer import IssuePrioritizer
from app.core.knowledge import CodeKnowledgeBase
from app.tools.github import GitHubManager
from app.tools.git_ops import GitOps
from app.core.llm import get_llm

logger = logging.getLogger(__name__)


class OrchestratorError(Exception):
    """Base exception for orchestrator errors"""
    pass


class JanitorOrchestrator:
    """
    Main orchestrator for CodeJanitor workflow
    
    Workflow:
    1. Build Knowledge Graph: Map all dependencies
    2. Audit: Scan code for vulnerabilities (with context from graph)
    3. Prioritize: Sort by risk score
    4. Validate: Red Team verifies high-priority issues (with full context)
    5. Update: Calculate final scores based on verification
    6. Action: Create GitHub issues or generate fixes (future)
    """
    
    def __init__(
        self,
        auditor: Optional[RepositoryAuditor] = None,
        red_team: Optional[RedTeamAgent] = None,
        blue_team: Optional[BlueTeamAgent] = None,
        prioritizer: Optional[IssuePrioritizer] = None,
        github_manager: Optional[GitHubManager] = None,
        git_ops: Optional[GitOps] = None,
        knowledge_base: Optional[CodeKnowledgeBase] = None,
        sandbox = None,
        repo_path: Optional[str] = None
    ):
        """
        Initialize orchestrator
        
        Args:
            auditor: Repository auditor
            red_team: Red team agent
            blue_team: Blue team agent
            prioritizer: Issue prioritizer
            github_manager: GitHub manager (optional)
            git_ops: Git operations handler (optional)
            knowledge_base: Code knowledge base (optional, created if not provided)
            sandbox: Docker sandbox (optional)
            repo_path: Repository path (optional)
        """
        self.auditor = auditor or RepositoryAuditor(llm=get_llm())
        self.red_team = red_team or RedTeamAgent()
        self.blue_team = blue_team or BlueTeamAgent()
        self.prioritizer = prioritizer or IssuePrioritizer()
        self.github_manager = github_manager
        self.git_ops = git_ops
        self.knowledge_base = knowledge_base or CodeKnowledgeBase()
        self.sandbox = sandbox
        self.repo_path = repo_path
        
        logger.info("JanitorOrchestrator initialized with Blue Team auto-fix")
    
    def scan_and_prioritize(
        self,
        directory: Path,
        file_pattern: str = "**/*.py",
        exclude_patterns: Optional[List[str]] = None,
        build_knowledge_graph: bool = True
    ) -> List[Dict]:
        """
        Scan directory and return prioritized list of issues
        
        Args:
            directory: Directory to scan
            file_pattern: Glob pattern for files
            exclude_patterns: Patterns to exclude
            build_knowledge_graph: Whether to build dependency graph first
            
        Returns:
            List of prioritized issues
        """
        logger.info(f"Starting scan of {directory}")
        
        # Step 0: Build knowledge graph (if enabled)
        if build_knowledge_graph:
            logger.info("Building knowledge graph...")
            self.knowledge_base.build_graph(directory)
            stats = self.knowledge_base.get_graph_stats()
            logger.info(f"Knowledge graph built: {stats['total_files']} files, "
                       f"{stats['total_imports']} imports")
        
        # Step 1: Audit (scan for vulnerabilities)
        findings = self.auditor.scan_directory(
            directory=directory,
            file_pattern=file_pattern,
            exclude_patterns=exclude_patterns
        )
        
        logger.info(f"Audit complete: {len(findings)} functions analyzed")
        
        # Step 2: Prioritize (sort by risk)
        prioritized = self.prioritize_risks(findings)
        
        logger.info(f"Prioritization complete: {len(prioritized)} issues ranked")
        
        return prioritized
    
    def prioritize_risks(self, scan_results: List[Dict]) -> List[Dict]:
        """
        Sort vulnerabilities by risk score (descending)
        
        Args:
            scan_results: List of findings from auditor
            
        Returns:
            Sorted list (highest risk first)
        """
        # Filter to only vulnerable findings
        vulnerable = [f for f in scan_results if f.get("vulnerable", False)]
        
        # Sort by risk score
        sorted_issues = self.prioritizer.prioritize_issues(vulnerable)
        
        logger.info(
            f"Prioritized {len(sorted_issues)} issues - "
            f"Critical: {sum(1 for i in sorted_issues if i.get('risk_score', 0) >= 8)}"
        )
        
        return sorted_issues
    
    def validate_issue(
        self,
        issue: Dict,
        file_content: Optional[str] = None,
        use_kill_chain: bool = True
    ) -> Dict:
        """
        Validate a specific issue using Red Team
        
        Args:
            issue: Issue dictionary from audit
            file_content: Optional file content (will read from disk if not provided)
            use_kill_chain: Whether to use Kill Chain methodology (default: True)
            
        Returns:
            Updated issue with verification results
        """
        logger.info(f"Validating issue in {issue.get('function', 'unknown')}")
        
        # Get file content with context from knowledge graph
        if file_content is None:
            try:
                file_path = issue["file"]
                
                # Try to get context-aware content (file + dependencies)
                if hasattr(self, 'knowledge_base') and self.knowledge_base:
                    # Get full context including imported files
                    file_content = self.knowledge_base.get_context(file_path, depth=1)
                    if file_content:
                        logger.info(f"Using context-aware content for {file_path} "
                                   f"({len(file_content)} chars)")
                    else:
                        # Fallback to reading the file directly
                        with open(file_path, "r", encoding="utf-8") as f:
                            file_content = f.read()
                else:
                    # No knowledge base, read file directly
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                        
            except Exception as e:
                logger.error(f"Failed to read file {issue['file']}: {e}")
                issue["verified"] = False
                issue["verification_error"] = str(e)
                return issue
        
        # Prepare vulnerability details
        vuln_details = {
            "type": issue.get("type", "Unknown"),
            "description": issue.get("description", ""),
            "function_code": file_content  # Full context including dependencies
        }
        
        # Choose validation method
        if use_kill_chain:
            # NEW: Use Kill Chain methodology (shows RECON → PLAN → EXPLOIT thinking)
            verification = self.red_team.run_validation(
                target_file=issue["file"],
                vulnerability_details=vuln_details,
                context_code=file_content
            )
            
            # Store the thought process for visibility
            if isinstance(verification, dict) and "thought_process" in verification:
                tp = verification.get("thought_process", {})
                if tp and isinstance(tp, dict):  # Ensure it's a real dict, not a Mock
                    issue["thought_process"] = tp
                    
                    # Log the Kill Chain for transparency
                    if "recon" in tp:
                        logger.info(f"🔍 RECON: {tp['recon'][:150]}...")
                    if "plan" in tp:
                        logger.info(f"🎯 PLAN: {tp['plan'][:150]}...")
        else:
            # LEGACY: Old method (direct exploit generation without Kill Chain)
            verification = self.red_team.verify_vulnerability(
                filename=issue["file"],
                function_code=file_content,
                vulnerability_type=issue["type"],
                description=issue.get("description", "")
            )
        
        # Update issue with verification results
        issue["verified"] = verification.get("verified", False) if isinstance(verification, dict) else verification.verified
        issue["exploit_output"] = verification.get("output", "") if isinstance(verification, dict) else verification.output
        
        # Store exploit code if available (ensure it always exists)
        exploit_code = ""
        if isinstance(verification, dict):
            if "exploit_code" in verification:
                exploit_code = verification["exploit_code"]
            elif "thought_process" in verification and isinstance(verification["thought_process"], dict):
                exploit_code = verification["thought_process"].get("exploit_code", "")
        else:
            # Mock object
            exploit_code = getattr(verification, "exploit_code", "")
        
        issue["exploit_code"] = exploit_code
        
        if isinstance(verification, dict) and verification.get("error"):
            issue["verification_error"] = verification["error"]
        elif hasattr(verification, "error"):
            issue["verification_error"] = verification.error
        
        # Calculate final risk score
        try:
            risk_calc = self.prioritizer.calculate_risk(
                auditor_score=issue.get("risk_score", 0),
                red_team_verified=issue.get("verified", False),
                vulnerability_type=issue["type"],
                has_exploit_proof=bool(exploit_code)
            )
            
            # Update issue with prioritization results
            issue["final_score"] = risk_calc.get("final_score", issue.get("risk_score", 0)) if isinstance(risk_calc, dict) else risk_calc.final_score
            issue["severity_rating"] = risk_calc.get("severity_rating", "Unknown") if isinstance(risk_calc, dict) else risk_calc.severity_rating
            
            # Handle label and action_recommended (may be in risk_calc)
            if isinstance(risk_calc, dict):
                issue["label"] = risk_calc.get("label", "UNKNOWN")
                issue["action_recommended"] = risk_calc.get("action_recommended", "Review manually")
            else:
                issue["label"] = getattr(risk_calc, "label", "UNKNOWN")
                issue["action_recommended"] = getattr(risk_calc, "action_recommended", "Review manually")
        except Exception as e:
            # If prioritizer fails (e.g., Mock), just keep original score
            logger.warning(f"Prioritization failed: {e}")
            issue["final_score"] = issue.get("risk_score", 0)
            issue["severity_rating"] = "Unknown"
            issue["label"] = "UNKNOWN"
            issue["action_recommended"] = "Review manually"
        
        # Safe logging with Mock-aware access
        verified_status = verification.get("verified", False) if isinstance(verification, dict) else getattr(verification, "verified", False)
        final_score = issue.get("final_score", 0)
        
        logger.info(
            f"Validation complete: {issue['function']} - "
            f"Verified: {verified_status}, "
            f"Final Score: {final_score}/10"
        )
        
        return issue
    
    def validate_all_issues(
        self,
        issues: List[Dict],
        strategy: str = "smart",
        max_validations: Optional[int] = None
    ) -> List[Dict]:
        """
        Validate multiple issues based on strategy
        
        Args:
            issues: List of issues to potentially validate
            strategy: Verification strategy ("all", "smart", "critical", "none")
            max_validations: Maximum number of issues to validate
            
        Returns:
            List of issues with validation results
        """
        validated_issues = []
        validations_count = 0
        
        for issue in issues:
            # Check if we should validate this issue
            should_validate = self.prioritizer.should_verify_issue(issue, strategy)
            
            # Check max validations limit
            if max_validations and validations_count >= max_validations:
                should_validate = False
            
            if should_validate:
                validated_issue = self.validate_issue(issue)
                validated_issues.append(validated_issue)
                validations_count += 1
            else:
                # Just add calculated risk without validation
                risk_calc = self.prioritizer.calculate_risk(
                    auditor_score=issue.get("risk_score", 0),
                    red_team_verified=False,
                    vulnerability_type=issue.get("type", ""),
                    has_exploit_proof=False
                )
                issue.update(risk_calc)
                validated_issues.append(issue)
        
        logger.info(f"Validated {validations_count} out of {len(issues)} issues")
        
        # Re-prioritize after validation
        return self.prioritizer.prioritize_issues(validated_issues)
    
    def run_full_audit_and_prioritize(
        self,
        directory: Path,
        verify_strategy: str = "smart",
        max_verifications: Optional[int] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict:
        """
        Complete workflow: Scan → Prioritize → Validate → Report
        
        Args:
            directory: Directory to scan
            verify_strategy: How to choose issues for verification
            max_verifications: Maximum number to verify
            exclude_patterns: File patterns to exclude
            
        Returns:
            Dictionary with:
            - issues: List of prioritized issues
            - summary: Summary statistics
            - report: Text report
        """
        logger.info(f"Starting full audit of {directory}")
        
        # Step 1: Scan and prioritize
        issues = self.scan_and_prioritize(
            directory=directory,
            exclude_patterns=exclude_patterns
        )
        
        if not issues:
            logger.info("No vulnerabilities found")
            return {
                "issues": [],
                "summary": {
                    "total": 0,
                    "verified": 0,
                    "critical": 0
                },
                "report": "✓ No vulnerabilities found!"
            }
        
        # Step 2: Validate based on strategy
        validated_issues = self.validate_all_issues(
            issues=issues,
            strategy=verify_strategy,
            max_validations=max_verifications
        )
        
        # Step 3: Generate summary
        summary = {
            "total": len(validated_issues),
            "verified": sum(1 for i in validated_issues if i.get("verified", False)),
            "critical": sum(1 for i in validated_issues if i.get("final_score", 0) >= 8),
            "high": sum(1 for i in validated_issues if 7 <= i.get("final_score", 0) < 8),
            "medium": sum(1 for i in validated_issues if 5 <= i.get("final_score", 0) < 7),
            "false_positives": sum(1 for i in validated_issues if i.get("final_score", 0) == 0)
        }
        
        # Step 4: Generate report
        report = self.prioritizer.generate_priority_report(validated_issues)
        
        logger.info(
            f"Audit complete: {summary['total']} issues, "
            f"{summary['verified']} verified, "
            f"{summary['critical']} critical"
        )
        
        return {
            "issues": validated_issues,
            "summary": summary,
            "report": report
        }
    
    def create_github_issues_for_verified(
        self,
        repo_url: str,
        issues: List[Dict],
        verified_only: bool = True,
        min_score: int = 7
    ) -> List[Dict]:
        """
        Create GitHub issues for validated vulnerabilities
        
        Args:
            repo_url: GitHub repository URL
            issues: List of issues
            verified_only: Only create issues for verified vulnerabilities
            min_score: Minimum risk score
            
        Returns:
            List of created GitHub issues
        """
        if not self.github_manager:
            raise OrchestratorError("GitHub manager not configured")
        
        # Filter issues
        filtered = self.prioritizer.filter_actionable_issues(
            issues=issues,
            min_score=min_score,
            verified_only=verified_only
        )
        
        logger.info(f"Creating GitHub issues for {len(filtered)} vulnerabilities")
        
        # Create issues
        created = []
        for issue in filtered:
            try:
                github_issue = self.github_manager.create_issue(
                    repo_url=repo_url,
                    title=f"[Security] {issue['type']} in {issue['function']}()",
                    body=self._format_issue_body(issue),
                    labels=self._get_issue_labels(issue)
                )
                created.append(github_issue)
            except Exception as e:
                logger.error(f"Failed to create issue for {issue['function']}: {e}")
        
        return created
    
    def _format_issue_body(self, issue: Dict) -> str:
        """Format issue as GitHub issue body"""
        verified_badge = "✅ VERIFIED" if issue.get("verified", False) else "❌ Unverified"
        
        body = f"""## 🔴 Security Vulnerability Detected

**Status:** {verified_badge}
**Risk Score:** {issue.get('final_score', issue.get('risk_score', 0))}/10
**Priority:** {issue.get('priority', 'Unknown')}
**Type:** {issue.get('type', 'Unknown')}
**File:** `{issue.get('file', 'Unknown')}`
**Function:** `{issue.get('function', 'Unknown')}()`
**Lines:** {issue.get('start_line', '?')}-{issue.get('end_line', '?')}

### Description

{issue.get('description', 'No description available')}

### Recommendation

{issue.get('action_recommended', 'Review and fix this vulnerability')}
"""
        
        if issue.get("verified", False) and issue.get("exploit_code"):
            body += """

### Red Team Verification

This vulnerability has been verified by the Red Team with a working exploit.

**Exploit Output:**
```
{output}
```
""".format(output=issue.get('exploit_output', '')[:500])
        
        body += """

---

*This issue was automatically created by [CodeJanitor 2.0](https://github.com/your-org/codejanitor) 🤖*
"""
        
        return body
    
    def _get_issue_labels(self, issue: Dict) -> List[str]:
        """Get appropriate labels for GitHub issue"""
        labels = ["security", "codejanitor"]
        
        priority = issue.get("priority", "")
        if priority == "CRITICAL":
            labels.append("critical")
        elif priority == "HIGH":
            labels.append("high-priority")
        
        if issue.get("verified", False):
            labels.append("verified")
        
        return labels
    
    def run_fix_job(
        self,
        repo_url: str,
        target_file: str,
        issue_number: int,
        vulnerability_type: str,
        vulnerability_description: str = ""
    ) -> Dict:
        """
        Complete fix workflow: Red Team → Blue Team → PR
        
        Args:
            repo_url: Repository URL
            target_file: Path to vulnerable file (relative to repo root)
            issue_number: GitHub issue number
            vulnerability_type: Type of vulnerability
            vulnerability_description: Description of vulnerability
            
        Returns:
            Dictionary with fix results
        """
        logger.info(f"🚀 Starting fix job for issue #{issue_number}")
        
        # Create temporary working directory
        work_dir = Path(tempfile.mkdtemp(prefix="codejanitor_fix_"))
        
        try:
            # Step 1: Clone repository
            if not self.git_ops:
                raise OrchestratorError("Git operations not configured")
            
            logger.info(f"📥 Cloning repository...")
            repo = self.git_ops.clone_repo(repo_url, work_dir)
            
            # Step 2: Read vulnerable file
            vulnerable_file = work_dir / target_file
            if not vulnerable_file.exists():
                raise OrchestratorError(f"File not found: {target_file}")
            
            vulnerable_content = vulnerable_file.read_text(encoding='utf-8')
            logger.info(f"📄 Read vulnerable file: {target_file}")
            
            # Step 3: Build knowledge graph for context
            logger.info("🧠 Building knowledge graph...")
            self.knowledge_base.build_graph(work_dir)
            
            # Step 4: Generate exploit (Red Team)
            logger.info("🔴 Red Team: Generating exploit...")
            red_team_result = self.red_team.run_validation(
                target_file=str(vulnerable_file),
                vulnerability_details={
                    "type": vulnerability_type,
                    "description": vulnerability_description,
                    "function_code": vulnerable_content
                }
            )
            
            if not red_team_result.get("verified"):
                logger.warning("⚠️ Red Team could not verify vulnerability - skipping fix")
                return {
                    "success": False,
                    "error": "Vulnerability not verified by Red Team",
                    "pr_url": None
                }
            
            exploit_code = red_team_result["thought_process"]["exploit_code"]
            logger.info("✅ Exploit generated and verified")
            
            # Step 5: Generate and verify patch (Blue Team)
            logger.info("🔵 Blue Team: Generating patch...")
            blue_team_result = self.blue_team.patch_and_verify(
                target_file=str(vulnerable_file),
                current_content=vulnerable_content,
                exploit_code=exploit_code,
                vulnerability_type=vulnerability_type,
                vulnerability_description=vulnerability_description
            )
            
            if not blue_team_result["success"]:
                logger.error(f"❌ Blue Team failed to generate valid patch: {blue_team_result['error']}")
                return {
                    "success": False,
                    "error": blue_team_result["error"],
                    "pr_url": None
                }
            
            logger.info(f"✅ Patch verified after {blue_team_result['attempts']} attempts")
            
            # Step 6: Create PR with patched code
            logger.info("📤 Creating pull request...")
            pr_url = self.git_ops.create_pr_for_fix(
                repo_url=repo_url,
                file_path=target_file,
                patched_content=blue_team_result["patched_content"],
                issue_number=issue_number,
                vulnerability_type=vulnerability_type,
                work_dir=work_dir
            )
            
            logger.info(f"✅ Pull request created: {pr_url}")
            
            return {
                "success": True,
                "pr_url": pr_url,
                "attempts": blue_team_result["attempts"],
                "error": ""
            }
            
        except Exception as e:
            logger.error(f"Fix job failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "pr_url": None
            }
        finally:
            # Cleanup temporary directory
            try:
                shutil.rmtree(work_dir)
                logger.info("🧹 Cleaned up temporary directory")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")


def create_orchestrator(**kwargs) -> JanitorOrchestrator:
    """
    Factory function to create a JanitorOrchestrator
    
    Args:
        **kwargs: Arguments for JanitorOrchestrator
        
    Returns:
        JanitorOrchestrator instance
    """
    return JanitorOrchestrator(**kwargs)
