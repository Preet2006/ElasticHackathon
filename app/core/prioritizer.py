"""
Issue Prioritization Engine
Calculates final risk scores based on verification and provides action recommendations
"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class IssuePrioritizer:
    """
    Prioritization engine for security issues
    
    Features:
    - Calculate final risk scores based on verification
    - Boost scores for verified vulnerabilities
    - Demote false positives
    - Provide action recommendations
    - Sort issues by priority
    """
    
    def __init__(self):
        """Initialize the prioritization engine"""
        logger.info("IssuePrioritizer initialized")
    
    def calculate_risk(
        self,
        auditor_score: int,
        red_team_verified: bool,
        vulnerability_type: str,
        has_exploit_proof: bool = False
    ) -> Dict:
        """
        Calculate final risk score and provide action recommendation
        
        Args:
            auditor_score: Initial risk score from auditor (0-10)
            red_team_verified: Whether Red Team verified the vulnerability
            vulnerability_type: Type of vulnerability
            has_exploit_proof: Whether there's working exploit code
            
        Returns:
            Dictionary with:
            - final_score: int (0-10)
            - label: str (status label)
            - action_recommended: str (what to do)
            - priority: str (CRITICAL, HIGH, MEDIUM, LOW)
        """
        final_score = auditor_score
        
        # Boost score if verified by Red Team
        if red_team_verified:
            # Verified vulnerabilities are always serious
            final_score = min(10, auditor_score + 2)
            
            if has_exploit_proof:
                # Working exploit = maximum priority
                final_score = 10
                label = "CRITICAL - VERIFIED WITH EXPLOIT"
                action = "Fix immediately - working exploit exists"
            else:
                label = "CRITICAL - VERIFIED"
                action = "Fix immediately"
                
        elif auditor_score >= 8:
            # High initial score but not verified
            label = "High - Unverified"
            action = "Manual review recommended - likely vulnerable"
            
        elif auditor_score >= 5:
            # Medium risk, not verified
            final_score = max(1, auditor_score - 1)  # Slight demotion
            label = "Medium - Unverified"
            action = "Review when resources available"
            
        else:
            # Low score and not verified
            label = "False Positive - Low Risk"
            action = "Skip - likely false positive"
            final_score = 0
        
        # Determine priority level
        if final_score >= 8:
            priority = "CRITICAL"
        elif final_score >= 7:
            priority = "HIGH"
        elif final_score >= 5:
            priority = "MEDIUM"
        else:
            priority = "LOW"
        
        return {
            "final_score": final_score,
            "label": label,
            "action_recommended": action,
            "priority": priority
        }
    
    def prioritize_issues(self, issues: List[Dict]) -> List[Dict]:
        """
        Sort issues by priority (highest risk first)
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Sorted list of issues (highest priority first)
        """
        # Sort by final_score if present, otherwise by risk_score
        def get_score(issue):
            return issue.get("final_score", issue.get("risk_score", 0))
        
        sorted_issues = sorted(issues, key=get_score, reverse=True)
        
        logger.info(
            f"Prioritized {len(issues)} issues - "
            f"Critical: {sum(1 for i in sorted_issues if get_score(i) >= 8)}, "
            f"High: {sum(1 for i in sorted_issues if 7 <= get_score(i) < 8)}, "
            f"Medium: {sum(1 for i in sorted_issues if 5 <= get_score(i) < 7)}"
        )
        
        return sorted_issues
    
    def filter_actionable_issues(
        self,
        issues: List[Dict],
        min_score: int = 5,
        verified_only: bool = False
    ) -> List[Dict]:
        """
        Filter issues to only actionable ones
        
        Args:
            issues: List of issues
            min_score: Minimum risk score to include
            verified_only: If True, only include verified issues
            
        Returns:
            Filtered list of issues
        """
        filtered = []
        
        for issue in issues:
            score = issue.get("final_score", issue.get("risk_score", 0))
            
            # Check score threshold
            if score < min_score:
                continue
            
            # Check verification if required
            if verified_only and not issue.get("verified", False):
                continue
            
            filtered.append(issue)
        
        logger.info(
            f"Filtered {len(issues)} issues to {len(filtered)} actionable items "
            f"(min_score={min_score}, verified_only={verified_only})"
        )
        
        return filtered
    
    def generate_priority_report(self, issues: List[Dict]) -> str:
        """
        Generate a priority report for issues
        
        Args:
            issues: List of issues
            
        Returns:
            Formatted report string
        """
        sorted_issues = self.prioritize_issues(issues)
        
        # Count by priority
        critical = [i for i in sorted_issues if i.get("final_score", i.get("risk_score", 0)) >= 8]
        high = [i for i in sorted_issues if 7 <= i.get("final_score", i.get("risk_score", 0)) < 8]
        medium = [i for i in sorted_issues if 5 <= i.get("final_score", i.get("risk_score", 0)) < 7]
        low = [i for i in sorted_issues if i.get("final_score", i.get("risk_score", 0)) < 5]
        
        report = f"""
Priority Report
===============

Total Issues: {len(sorted_issues)}
  🔴 Critical (8-10): {len(critical)}
  🟠 High (7):        {len(high)}
  🟡 Medium (5-6):    {len(medium)}
  🟢 Low (0-4):       {len(low)}

Verified Issues: {sum(1 for i in sorted_issues if i.get('verified', False))}
False Positives: {sum(1 for i in sorted_issues if i.get('final_score', i.get('risk_score', 0)) == 0)}

"""
        
        if critical:
            report += "\n🔴 CRITICAL ISSUES (Fix Immediately):\n"
            for idx, issue in enumerate(critical[:5], 1):  # Top 5
                verified = "✅" if issue.get("verified", False) else "❌"
                report += f"  {idx}. [{verified}] {issue.get('function', 'unknown')}() - {issue.get('type', 'unknown')}\n"
                report += f"     File: {issue.get('file', 'unknown')}\n"
                report += f"     Action: {issue.get('action_recommended', 'Review')}\n"
        
        if high:
            report += "\n🟠 HIGH PRIORITY:\n"
            for idx, issue in enumerate(high[:3], 1):  # Top 3
                verified = "✅" if issue.get("verified", False) else "❌"
                report += f"  {idx}. [{verified}] {issue.get('function', 'unknown')}() - {issue.get('type', 'unknown')}\n"
        
        return report
    
    def should_verify_issue(self, issue: Dict, strategy: str = "smart") -> bool:
        """
        Determine if an issue should be verified by Red Team
        
        Args:
            issue: Issue dictionary
            strategy: Verification strategy:
                - "all": Verify everything
                - "smart": Only verify high-risk issues (score >= 7)
                - "critical": Only verify critical issues (score >= 8)
                - "none": Don't verify anything
                
        Returns:
            True if issue should be verified
        """
        score = issue.get("risk_score", 0)
        
        if strategy == "all":
            return True
        elif strategy == "smart":
            return score >= 7
        elif strategy == "critical":
            return score >= 8
        elif strategy == "none":
            return False
        else:
            # Default to smart
            return score >= 7


def create_prioritizer() -> IssuePrioritizer:
    """
    Factory function to create an IssuePrioritizer
    
    Returns:
        IssuePrioritizer instance
    """
    return IssuePrioritizer()
