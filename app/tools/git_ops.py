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
    
    def fork_repo(self, repo_name: str) -> str:
        """
        Fork a repository to the authenticated user's account.
        If fork already exists, returns the existing fork.
        
        Args:
            repo_name: Repository name (owner/repo)
            
        Returns:
            Fork's full name (your_username/repo)
        """
        if not self.github:
            raise GitOpsError("GitHub token required for forking")
        
        try:
            # Get the original repo
            original_repo = self.github.get_repo(repo_name)
            authenticated_user = self.github.get_user()
            
            logger.info(f"Forking {repo_name} to {authenticated_user.login}...")
            
            # Check if fork already exists
            try:
                fork_name = f"{authenticated_user.login}/{original_repo.name}"
                existing_fork = self.github.get_repo(fork_name)
                logger.info(f"Fork already exists: {fork_name}")
                return fork_name
            except Exception:
                pass  # Fork doesn't exist, create it
            
            # Create the fork
            fork = authenticated_user.create_fork(original_repo)
            logger.info(f"Fork created: {fork.full_name}")
            
            # Wait a moment for GitHub to process the fork
            import time
            time.sleep(2)
            
            return fork.full_name
            
        except Exception as e:
            logger.error(f"Failed to fork repository: {e}")
            raise GitOpsError(f"Fork failed: {e}")
    
    def clone_repo(self, repo_url: str, target_dir: Path) -> Repo:
        """
        Clone a repository with authentication
        
        Args:
            repo_url: URL of the repository
            target_dir: Target directory for cloning
            
        Returns:
            Repo: GitPython Repo object
        """
        try:
            # Add token to URL for authenticated clone
            if self.token and 'github.com' in repo_url:
                # Convert https://github.com/owner/repo.git to https://token@github.com/owner/repo.git
                auth_url = repo_url.replace('https://github.com', f'https://{self.token}@github.com')
                logger.info(f"Cloning repository with authentication to {target_dir}")
            else:
                auth_url = repo_url
                logger.info(f"Cloning repository {repo_url} to {target_dir}")
            
            repo = Repo.clone_from(auth_url, target_dir)
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
            remote_url = origin.url
            logger.info(f"Remote URL: {remote_url[:50]}...")  # Log first 50 chars (hide token)
            
            if branch_name:
                logger.info(f"Pushing branch {branch_name} to origin")
                # Use refspec to push with upstream tracking
                push_info = origin.push(refspec=f'{branch_name}:{branch_name}', set_upstream=True)
                
                # Check push result
                for info in push_info:
                    logger.info(f"Push result: {info.summary}")
                    if info.flags & info.ERROR:
                        raise GitOpsError(f"Push failed: {info.summary}")
            else:
                logger.info(f"Pushing current branch")
                push_info = origin.push()
                for info in push_info:
                    logger.info(f"Push result: {info.summary}")
                    
            logger.info("Changes pushed successfully")
        except Exception as e:
            logger.error(f"Failed to push changes: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
        Create a pull request or return existing PR if one already exists
        
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
            
            # Try to create the PR
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base
            )
            logger.info(f"PR created: {pr.html_url}")
            return pr.html_url
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if PR already exists for this branch
            if "already exists" in error_msg.lower() or "422" in error_msg:
                logger.info(f"PR already exists for branch {head}, fetching existing PR...")
                try:
                    repo = self.github.get_repo(repo_name)
                    # Get all open PRs and find the one for this branch
                    pulls = repo.get_pulls(state='open', head=f"{repo.owner.login}:{head}")
                    for pr in pulls:
                        logger.info(f"Found existing PR: {pr.html_url}")
                        return pr.html_url
                    
                    # If no open PR found, check closed PRs
                    pulls = repo.get_pulls(state='closed', head=f"{repo.owner.login}:{head}")
                    for pr in pulls:
                        logger.info(f"Found existing closed PR: {pr.html_url}")
                        return pr.html_url
                        
                except Exception as fetch_err:
                    logger.error(f"Failed to fetch existing PR: {fetch_err}")
            
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
        Complete workflow: Fork, Clone, patch, commit, push, create PR
        Uses fork-based workflow to allow PRs to any public repository.
        
        Args:
            repo_url: Repository URL (original repo)
            file_path: Path to file to patch (relative to repo root)
            patched_content: Fixed code content
            issue_number: Issue number being fixed
            vulnerability_type: Type of vulnerability
            work_dir: Working directory for clone
            
        Returns:
            PR URL if successful
        """
        branch_name = f"codejanitor/fix-{issue_number}"
        
        try:
            # Extract repo name from URL (owner/repo)
            # e.g., https://github.com/owner/repo.git -> owner/repo
            original_repo_name = repo_url.split('github.com/')[-1].replace('.git', '')
            
            logger.info(f"=== PR WORKFLOW START (Fork-based) ===")
            logger.info(f"Original Repo: {original_repo_name}")
            logger.info(f"File: {file_path}")
            logger.info(f"Branch: {branch_name}")
            logger.info(f"Patched content length: {len(patched_content)} chars")
            
            if not patched_content or len(patched_content) == 0:
                raise GitOpsError("Patched content is empty - cannot create PR")
            
            # Step 1: Fork the repository (or get existing fork)
            logger.info(f"Step 1: Forking repository...")
            fork_repo_name = self.fork_repo(original_repo_name)
            fork_url = f"https://github.com/{fork_repo_name}.git"
            logger.info(f"Step 1: Fork ready: {fork_repo_name}")
            
            # Step 2: Clone the FORK (not the original)
            logger.info(f"Step 2: Cloning fork...")
            repo = self.clone_repo(fork_url, work_dir)
            logger.info(f"Step 2: Fork cloned successfully")
            
            # Step 3: Create fix branch
            logger.info(f"Step 3: Creating branch {branch_name}...")
            self.create_branch(repo, branch_name)
            logger.info(f"Step 3: Branch created")
            
            # Step 4: Write patched content
            logger.info(f"Step 4: Writing patched content to {file_path}...")
            target_file = work_dir / file_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(patched_content, encoding='utf-8')
            logger.info(f"Step 4: File written ({target_file})")
            
            # Step 5: Commit changes
            logger.info(f"Step 5: Committing changes...")
            commit_msg = f"fix: {vulnerability_type} security vulnerability\n\nFixes #{issue_number}"
            self.commit_changes(repo, commit_msg, [file_path])
            logger.info(f"Step 5: Changes committed")
            
            # Step 6: Push to FORK (we have write access to our fork)
            logger.info(f"Step 6: Pushing to fork...")
            self.push_changes(repo, branch_name)
            logger.info(f"Step 6: Push successful")
            
            # Step 7: Create PR from fork to original repo
            logger.info(f"Step 7: Creating pull request (fork → original)...")
            
            # Get the fork owner (authenticated user)
            fork_owner = fork_repo_name.split('/')[0]
            
            pr_title = f"🔒 Security Fix: {vulnerability_type}"
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

---
*Generated by [CodeJanitor](https://github.com/codejanitor) - AI Security Scanner*

Fixes #{issue_number}
"""
            
            # Create PR from fork:branch to original:main
            pr_url = self.create_pull_request(
                repo_name=original_repo_name,  # PR goes to original repo
                title=pr_title,
                body=pr_body,
                head=f"{fork_owner}:{branch_name}",  # from fork's branch
                base="main"  # to original's main
            )
            
            logger.info(f"Step 7: PR created successfully: {pr_url}")
            logger.info(f"=== PR WORKFLOW COMPLETE ===")
            
            return pr_url
            
        except Exception as e:
            logger.error(f"=== PR WORKFLOW FAILED ===")
            logger.error(f"Failed to create PR workflow: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
