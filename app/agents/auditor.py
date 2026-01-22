"""
Repository Auditor - The Security Scanner
Scans code files, extracts functions, and detects vulnerabilities
"""

from typing import List, Dict, Optional
from pathlib import Path
import logging
from app.tools.parsing import CodeParser
from app.tools.github import GitHubManager
from app.core.llm import LLMClient, get_llm

logger = logging.getLogger(__name__)


class AuditorError(Exception):
    """Base exception for auditor errors"""
    pass


class RepositoryAuditor:
    """
    Security auditor that scans repositories for vulnerabilities
    
    Features:
    - Parse Python files with Tree-sitter
    - Analyze functions for security vulnerabilities using LLM
    - Create GitHub issues with risk scores
    - Deduplicate issues to avoid spam
    """
    
    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        github_manager: Optional[GitHubManager] = None,
        create_issues: bool = False
    ):
        """
        Initialize repository auditor
        
        Args:
            llm: LLM client (creates default if not provided)
            github_manager: GitHub manager (optional, only needed if create_issues=True)
            create_issues: Whether to create GitHub issues for findings
        """
        self.llm = llm or get_llm()
        self.github_manager = github_manager
        self.create_issues = create_issues
        self.parser = CodeParser(language="python")
        
        if create_issues and not github_manager:
            raise AuditorError("GitHubManager required when create_issues=True")
        
        logger.info("RepositoryAuditor initialized")
    
    def scan_file(self, file_path: str, content: str) -> List[Dict]:
        """
        Scan a single file for vulnerabilities
        
        Args:
            file_path: Path to the file (for reporting)
            content: File content as string
            
        Returns:
            List of vulnerability findings with:
            - file: File path
            - function: Function name
            - vulnerable: Boolean
            - risk_score: 0-10
            - type: Vulnerability type
            - description: Detailed description
            - start_line: Function start line
            - end_line: Function end line
        """
        findings = []
        
        try:
            # Parse functions from file
            functions = self.parser.parse_functions(content)
            logger.info(f"Scanning {len(functions)} functions in {file_path}")
            
            for func in functions:
                try:
                    # Analyze function for vulnerabilities
                    analysis = self.llm.analyze_vulnerability(func["code"])
                    
                    # Add context to finding
                    finding = {
                        "file": file_path,
                        "function": func["name"],
                        "start_line": func["start_line"],
                        "end_line": func["end_line"],
                        **analysis
                    }
                    
                    findings.append(finding)
                    
                    # Log significant findings
                    if analysis["vulnerable"] and analysis["risk_score"] >= 7:
                        logger.warning(
                            f"HIGH RISK: {func['name']} in {file_path} - "
                            f"Risk {analysis['risk_score']}/10: {analysis['type']}"
                        )
                    elif analysis["vulnerable"]:
                        logger.info(
                            f"Vulnerability: {func['name']} in {file_path} - "
                            f"Risk {analysis['risk_score']}/10: {analysis['type']}"
                        )
                    
                except Exception as e:
                    logger.error(f"Failed to analyze function {func['name']}: {e}")
                    # Add error finding
                    findings.append({
                        "file": file_path,
                        "function": func["name"],
                        "start_line": func["start_line"],
                        "end_line": func["end_line"],
                        "vulnerable": False,
                        "risk_score": 0,
                        "type": "analysis_error",
                        "description": f"Failed to analyze: {str(e)}"
                    })
            
            return findings
            
        except Exception as e:
            logger.error(f"Failed to scan file {file_path}: {e}")
            raise AuditorError(f"Failed to scan file: {e}") from e
    
    def scan_directory(
        self,
        directory: Path,
        file_pattern: str = "**/*.py",
        exclude_patterns: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Scan all Python files in a directory
        
        Args:
            directory: Directory to scan
            file_pattern: Glob pattern for files to scan
            exclude_patterns: List of patterns to exclude (e.g., ["**/tests/**", "**/__pycache__/**"])
            
        Returns:
            List of all findings from all files
        """
        directory = Path(directory)
        exclude_patterns = exclude_patterns or ["**/__pycache__/**", "**/venv/**", "**/.venv/**"]
        
        all_findings = []
        files_scanned = 0
        
        logger.info(f"Scanning directory: {directory}")
        
        # Find all Python files
        for file_path in directory.glob(file_pattern):
            # Skip excluded paths
            if any(file_path.match(pattern) for pattern in exclude_patterns):
                logger.debug(f"Skipping excluded file: {file_path}")
                continue
            
            try:
                # Read file content
                content = file_path.read_text(encoding="utf-8")
                
                # Scan file
                findings = self.scan_file(str(file_path), content)
                all_findings.extend(findings)
                files_scanned += 1
                
                logger.info(f"Scanned {file_path} - {len(findings)} functions analyzed")
                
            except Exception as e:
                logger.error(f"Failed to scan {file_path}: {e}")
                continue
        
        logger.info(
            f"Scan complete: {files_scanned} files, {len(all_findings)} functions analyzed, "
            f"{sum(1 for f in all_findings if f['vulnerable'])} vulnerabilities found"
        )
        
        return all_findings
    
    def create_github_issues(
        self,
        repo_url: str,
        findings: List[Dict],
        min_risk_score: int = 5
    ) -> List[Dict]:
        """
        Create GitHub issues for vulnerability findings
        
        Args:
            repo_url: GitHub repository URL
            findings: List of vulnerability findings
            min_risk_score: Minimum risk score to create issue (0-10)
            
        Returns:
            List of created issues
        """
        if not self.github_manager:
            raise AuditorError("GitHub manager not configured")
        
        created_issues = []
        
        # Filter findings by risk score and vulnerable status
        significant_findings = [
            f for f in findings
            if f["vulnerable"] and f["risk_score"] >= min_risk_score
        ]
        
        logger.info(
            f"Creating issues for {len(significant_findings)} findings "
            f"(min risk score: {min_risk_score})"
        )
        
        # Get existing issues for deduplication
        try:
            existing_issues = self.github_manager.get_existing_issues(
                repo_url,
                state="open",
                labels=["security", "codejanitor"]
            )
            existing_titles = {issue["title"] for issue in existing_issues}
        except Exception as e:
            logger.warning(f"Failed to fetch existing issues: {e}")
            existing_titles = set()
        
        for finding in significant_findings:
            # Create issue title
            title = f"[Security] {finding['type']} in {finding['function']}()"
            
            # Check for duplicate
            if title in existing_titles:
                logger.info(f"Skipping duplicate issue: {title}")
                continue
            
            # Create issue body
            body = self._format_issue_body(finding)
            
            # Determine labels
            labels = ["security", "codejanitor"]
            if finding["risk_score"] >= 8:
                labels.append("critical")
            elif finding["risk_score"] >= 7:
                labels.append("high-priority")
            
            try:
                issue = self.github_manager.create_issue(
                    repo_url=repo_url,
                    title=title,
                    body=body,
                    labels=labels
                )
                created_issues.append(issue)
                logger.info(f"Created issue: {title}")
                
            except Exception as e:
                logger.error(f"Failed to create issue for {finding['function']}: {e}")
                continue
        
        logger.info(f"Created {len(created_issues)} GitHub issues")
        return created_issues
    
    def _format_issue_body(self, finding: Dict) -> str:
        """
        Format vulnerability finding as GitHub issue body
        
        Args:
            finding: Vulnerability finding dictionary
            
        Returns:
            Formatted Markdown issue body
        """
        risk_emoji = {
            (10, 9): "🔴",  # Critical
            (8, 7): "🟠",    # High
            (6, 5): "🟡",    # Medium
            (4, 0): "🟢"     # Low
        }
        
        emoji = next(
            emoji for (high, low), emoji in risk_emoji.items()
            if low <= finding["risk_score"] <= high
        )
        
        body = f"""## {emoji} Security Vulnerability Detected

**Risk Score:** {finding['risk_score']}/10
**Type:** {finding['type']}
**File:** `{finding['file']}`
**Function:** `{finding['function']}()`
**Lines:** {finding['start_line']}-{finding['end_line']}

### Description

{finding['description']}

### Recommendation

This vulnerability was detected by CodeJanitor 2.0's automated security audit. Please review the affected code and apply appropriate security fixes.

---

*This issue was automatically created by [CodeJanitor 2.0](https://github.com/your-org/codejanitor) 🤖*
"""
        return body
    
    def generate_report(self, findings: List[Dict]) -> str:
        """
        Generate a summary report of findings
        
        Args:
            findings: List of vulnerability findings
            
        Returns:
            Formatted report string
        """
        vulnerable_findings = [f for f in findings if f["vulnerable"]]
        
        if not vulnerable_findings:
            return "✓ No security vulnerabilities detected!"
        
        # Group by risk score
        critical = [f for f in vulnerable_findings if f["risk_score"] >= 8]
        high = [f for f in vulnerable_findings if 7 <= f["risk_score"] < 8]
        medium = [f for f in vulnerable_findings if 5 <= f["risk_score"] < 7]
        low = [f for f in vulnerable_findings if f["risk_score"] < 5]
        
        report = f"""
Security Audit Report
=====================

Total Functions Analyzed: {len(findings)}
Vulnerabilities Found: {len(vulnerable_findings)}

Severity Breakdown:
  🔴 Critical (8-10): {len(critical)}
  🟠 High (7):        {len(high)}
  🟡 Medium (5-6):    {len(medium)}
  🟢 Low (0-4):       {len(low)}

"""
        
        if critical:
            report += "\n🔴 CRITICAL VULNERABILITIES:\n"
            for f in critical:
                report += f"  • {f['function']}() in {f['file']} - {f['type']} (Risk: {f['risk_score']})\n"
        
        if high:
            report += "\n🟠 HIGH PRIORITY VULNERABILITIES:\n"
            for f in high:
                report += f"  • {f['function']}() in {f['file']} - {f['type']} (Risk: {f['risk_score']})\n"
        
        return report


def create_auditor(**kwargs) -> RepositoryAuditor:
    """
    Factory function to create a RepositoryAuditor
    
    Args:
        **kwargs: Arguments for RepositoryAuditor
        
    Returns:
        RepositoryAuditor instance
    """
    return RepositoryAuditor(**kwargs)
