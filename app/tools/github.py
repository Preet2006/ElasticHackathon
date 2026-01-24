"""
GitHub integration for issue management and repository operations
"""

from github import Github, GithubException
from typing import List, Dict, Optional
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GitHubError(Exception):
    """Base exception for GitHub operations"""
    pass


class GitHubManager:
    """
    GitHub API manager for issue creation and management
    
    Features:
    - Create issues with labels
    - Fetch existing issues for deduplication
    - Repository operations
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub manager
        
        Args:
            token: GitHub personal access token (uses config if not provided)
        """
        settings = get_settings()
        self.token = token or settings.github_token
        
        if not self.token:
            raise GitHubError(
                "No GitHub token provided. Set GITHUB_TOKEN environment variable or pass token parameter."
            )
        
        try:
            self.client = Github(self.token)
            # Test authentication
            self.user = self.client.get_user()
            logger.info(f"GitHub client initialized for user: {self.user.login}")
        except GithubException as e:
            raise GitHubError(f"Failed to authenticate with GitHub: {e}") from e
    
    def _parse_repo_url(self, repo_url: str) -> str:
        """
        Extract owner/repo from various GitHub URL formats
        
        Args:
            repo_url: GitHub repository URL or owner/repo string
            
        Returns:
            owner/repo string
            
        Examples:
            "https://github.com/owner/repo" -> "owner/repo"
            "owner/repo" -> "owner/repo"
        """
        # Remove trailing .git
        repo_url = repo_url.rstrip('.git')
        
        # Handle different URL formats
        if "github.com" in repo_url:
            # Extract from URL
            parts = repo_url.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
        
        # Assume it's already in owner/repo format
        return repo_url
    
    def create_issue(
        self,
        repo_url: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None
    ) -> Dict:
        """
        Create a GitHub issue
        
        Args:
            repo_url: Repository URL or owner/repo string
            title: Issue title
            body: Issue description (supports Markdown)
            labels: List of label names
            
        Returns:
            Dictionary with issue details (number, url, title)
            
        Raises:
            GitHubError: If issue creation fails
        """
        try:
            repo_name = self._parse_repo_url(repo_url)
            repo = self.client.get_repo(repo_name)
            
            # Create issue
            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels or []
            )
            
            logger.info(f"Created issue #{issue.number}: {title}")
            
            return {
                "number": issue.number,
                "url": issue.html_url,
                "title": issue.title,
                "state": issue.state
            }
            
        except GithubException as e:
            logger.error(f"Failed to create issue: {e}")
            raise GitHubError(f"Failed to create issue: {e}") from e
    
    def get_existing_issues(
        self,
        repo_url: str,
        state: str = "open",
        labels: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get existing issues from repository
        
        Args:
            repo_url: Repository URL or owner/repo string
            state: Issue state ('open', 'closed', 'all')
            labels: Filter by labels
            
        Returns:
            List of issue dictionaries with title, number, and url
        """
        try:
            repo_name = self._parse_repo_url(repo_url)
            repo = self.client.get_repo(repo_name)
            
            # Fetch issues
            issues = repo.get_issues(state=state, labels=labels or [])
            
            issue_list = []
            for issue in issues:
                # Skip pull requests (they show up as issues in GitHub API)
                if issue.pull_request:
                    continue
                
                issue_list.append({
                    "number": issue.number,
                    "title": issue.title,
                    "url": issue.html_url,
                    "state": issue.state,
                    "labels": [label.name for label in issue.labels],
                    "created_at": issue.created_at.isoformat()
                })
            
            logger.info(f"Found {len(issue_list)} {state} issues")
            return issue_list
            
        except GithubException as e:
            logger.error(f"Failed to fetch issues: {e}")
            raise GitHubError(f"Failed to fetch issues: {e}") from e
    
    def issue_exists(self, repo_url: str, title: str) -> bool:
        """
        Check if an issue with the given title already exists
        
        Args:
            repo_url: Repository URL
            title: Issue title to search for
            
        Returns:
            True if issue exists, False otherwise
        """
        try:
            issues = self.get_existing_issues(repo_url, state="open")
            return any(issue["title"] == title for issue in issues)
        except Exception as e:
            logger.warning(f"Failed to check for existing issue: {e}")
            return False
    
    def add_comment(self, repo_url: str, issue_number: int, comment: str) -> Dict:
        """
        Add a comment to an existing issue
        
        Args:
            repo_url: Repository URL
            issue_number: Issue number
            comment: Comment text (Markdown supported)
            
        Returns:
            Comment details
        """
        try:
            repo_name = self._parse_repo_url(repo_url)
            repo = self.client.get_repo(repo_name)
            issue = repo.get_issue(issue_number)
            
            issue_comment = issue.create_comment(comment)
            
            logger.info(f"Added comment to issue #{issue_number}")
            
            return {
                "id": issue_comment.id,
                "url": issue_comment.html_url
            }
            
        except GithubException as e:
            logger.error(f"Failed to add comment: {e}")
            raise GitHubError(f"Failed to add comment: {e}") from e
    
    def close_issue(self, repo_url: str, issue_number: int, comment: Optional[str] = None) -> None:
        """
        Close an issue
        
        Args:
            repo_url: Repository URL
            issue_number: Issue number
            comment: Optional closing comment
        """
        try:
            repo_name = self._parse_repo_url(repo_url)
            repo = self.client.get_repo(repo_name)
            issue = repo.get_issue(issue_number)
            
            if comment:
                issue.create_comment(comment)
            
            issue.edit(state="closed")
            logger.info(f"Closed issue #{issue_number}")
            
        except GithubException as e:
            logger.error(f"Failed to close issue: {e}")
            raise GitHubError(f"Failed to close issue: {e}") from e
    
    def get_repository_info(self, repo_url: str) -> Dict:
        """
        Get repository information
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Repository details
        """
        try:
            repo_name = self._parse_repo_url(repo_url)
            repo = self.client.get_repo(repo_name)
            
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "default_branch": repo.default_branch,
                "url": repo.html_url,
                "stars": repo.stargazers_count,
                "language": repo.language
            }
            
        except GithubException as e:
            logger.error(f"Failed to get repository info: {e}")
            raise GitHubError(f"Failed to get repository info: {e}") from e
    
    def create_pull_request(
        self,
        repo_url: str,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> Dict:
        """
        Create a pull request
        
        Args:
            repo_url: Repository URL or owner/repo string
            title: PR title
            body: PR description (supports Markdown)
            head: Branch name containing changes
            base: Target branch (default: "main")
            
        Returns:
            Dictionary with PR details (number, url, title)
            
        Raises:
            GitHubError: If PR creation fails
        """
        try:
            repo_name = self._parse_repo_url(repo_url)
            repo = self.client.get_repo(repo_name)
            
            # Try main first, fallback to master
            try:
                repo.get_branch(base)
            except:
                logger.info(f"Branch '{base}' not found, trying 'master'")
                base = "master"
            
            # Create pull request
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base
            )
            
            logger.info(f"Created PR #{pr.number}: {title}")
            
            return {
                "number": pr.number,
                "html_url": pr.html_url,
                "title": pr.title,
                "state": pr.state
            }
            
        except GithubException as e:
            logger.error(f"Failed to create PR: {e}")
            raise GitHubError(f"Failed to create PR: {e}") from e


def create_github_manager(token: Optional[str] = None) -> GitHubManager:
    """
    Factory function to create a GitHubManager
    
    Args:
        token: GitHub token
        
    Returns:
        GitHubManager instance
    """
    return GitHubManager(token=token)
