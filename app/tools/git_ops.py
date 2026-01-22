"""
Git operations for repository management
To be implemented in future phases
"""

from git import Repo
from github import Github
from typing import Optional
import logging
from pathlib import Path
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GitOpsError(Exception):
    """Base exception for Git operations"""
    pass


class GitOps:
    """
    Git operations handler
    
    Future features:
    - Clone repositories
    - Create branches
    - Commit changes
    - Push to remote
    - Create pull requests
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize Git operations handler
        
        Args:
            token: GitHub token (uses config if not provided)
        """
        settings = get_settings()
        self.token = token or settings.github_token
        
        if self.token:
            self.github = Github(self.token)
            logger.info("GitHub client initialized")
        else:
            self.github = None
            logger.warning("No GitHub token provided - GitHub operations will be limited")
    
    def clone_repo(self, repo_url: str, target_dir: Path) -> Repo:
        """
        Clone a repository
        
        Args:
            repo_url: URL of the repository
            target_dir: Target directory for cloning
            
        Returns:
            Repo: GitPython Repo object
        """
        try:
            logger.info(f"Cloning repository {repo_url} to {target_dir}")
            repo = Repo.clone_from(repo_url, target_dir)
            logger.info(f"Repository cloned successfully")
            return repo
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            raise GitOpsError(f"Clone failed: {e}")
    
    def create_branch(self, repo: Repo, branch_name: str) -> None:
        """
        Create a new branch
        
        Args:
            repo: GitPython Repo object
            branch_name: Name of the branch to create
        """
        try:
            logger.info(f"Creating branch: {branch_name}")
            repo.git.checkout('-b', branch_name)
            logger.info(f"Branch {branch_name} created")
        except Exception as e:
            logger.error(f"Failed to create branch: {e}")
            raise GitOpsError(f"Branch creation failed: {e}")
    
    def commit_changes(self, repo: Repo, message: str, files: list = None) -> None:
        """
        Commit changes to the repository
        
        Args:
            repo: GitPython Repo object
            message: Commit message
            files: List of files to commit (None = all)
        """
        try:
            logger.info(f"Committing changes: {message}")
            if files:
                repo.index.add(files)
            else:
                repo.git.add(A=True)
            repo.index.commit(message)
            logger.info("Changes committed successfully")
        except Exception as e:
            logger.error(f"Failed to commit changes: {e}")
            raise GitOpsError(f"Commit failed: {e}")
    
    def push_changes(self, repo: Repo, branch_name: str = None) -> None:
        """
        Push changes to remote
        
        Args:
            repo: GitPython Repo object
            branch_name: Branch to push (None = current branch)
        """
        try:
            origin = repo.remote(name='origin')
            if branch_name:
                logger.info(f"Pushing branch {branch_name}")
                origin.push(branch_name)
            else:
                logger.info(f"Pushing current branch")
                origin.push()
            logger.info("Changes pushed successfully")
        except Exception as e:
            logger.error(f"Failed to push changes: {e}")
            raise GitOpsError(f"Push failed: {e}")
    
    def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> Optional[str]:
        """
        Create a pull request
        
        Args:
            repo_name: Repository name (owner/repo)
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch
            
        Returns:
            PR URL if successful, None otherwise
        """
        if not self.github:
            logger.error("GitHub client not initialized - cannot create PR")
            raise GitOpsError("GitHub token required for PR creation")
        
        try:
            logger.info(f"Creating PR: {title}")
            repo = self.github.get_repo(repo_name)
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base
            )
            logger.info(f"PR created: {pr.html_url}")
            return pr.html_url
        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            raise GitOpsError(f"PR creation failed: {e}")
    
    def create_pr_for_fix(
        self,
        repo_url: str,
        file_path: str,
        patched_content: str,
        issue_number: int,
        vulnerability_type: str,
        work_dir: Path
    ) -> Optional[str]:
        """
        Complete workflow: Clone, patch, commit, push, create PR
        
        Args:
            repo_url: Repository URL
            file_path: Path to file to patch (relative to repo root)
            patched_content: Fixed code content
            issue_number: Issue number being fixed
            vulnerability_type: Type of vulnerability
            work_dir: Working directory for clone
            
        Returns:
            PR URL if successful
        """
        branch_name = f"fix/issue-{issue_number}"
        
        try:
            # Extract repo name from URL (owner/repo)
            # e.g., https://github.com/owner/repo.git -> owner/repo
            repo_name = repo_url.split('github.com/')[-1].replace('.git', '')
            
            # Clone repository
            repo = self.clone_repo(repo_url, work_dir)
            
            # Create fix branch
            self.create_branch(repo, branch_name)
            
            # Write patched content
            target_file = work_dir / file_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(patched_content, encoding='utf-8')
            
            # Commit changes
            commit_msg = f"Security fix for issue #{issue_number}: {vulnerability_type}"
            self.commit_changes(repo, commit_msg, [file_path])
            
            # Push to remote
            self.push_changes(repo, branch_name)
            
            # Create PR
            pr_title = f"🔒 Security Fix: {vulnerability_type} (Issue #{issue_number})"
            pr_body = f"""## Security Patch

This PR fixes a **{vulnerability_type}** vulnerability identified in issue #{issue_number}.

### Changes
- Fixed: `{file_path}`

### Verification
✅ Patch has been verified using Test-Driven Repair:
- Original exploit confirmed vulnerability exists
- Patch applied and tested
- Exploit fails on patched code (vulnerability eliminated)

### Review Notes
Please review the changes carefully. The patch has been automatically generated and verified, but human review is always recommended for security fixes.

Fixes #{issue_number}
"""
            
            pr_url = self.create_pull_request(
                repo_name=repo_name,
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base="main"
            )
            
            return pr_url
            
        except Exception as e:
            logger.error(f"Failed to create PR workflow: {e}")
            raise GitOpsError(f"PR workflow failed: {e}")


def create_git_ops(**kwargs) -> GitOps:
    """
    Factory function to create GitOps instance
    
    Args:
        **kwargs: Arguments for GitOps
        
    Returns:
        GitOps: Configured GitOps instance
    """
    return GitOps(**kwargs)
