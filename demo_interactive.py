#!/usr/bin/env python3
"""
CodeJanitor 2.0 - Interactive Command Center
Phase 5: Human-in-the-Loop Security Automation

Usage:
    python demo_interactive.py
"""

import os
import sys
import re
import tempfile
import shutil
import logging
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.syntax import Syntax
from rich import box
from rich.text import Text

# Import CodeJanitor components
from app.core.orchestrator import JanitorOrchestrator
from app.agents.auditor import RepositoryAuditor
from app.agents.red_team import RedTeamAgent
from app.agents.blue_team import BlueTeamAgent
from app.tools.sandbox import DockerSandbox
from app.tools.git_ops import GitOps
from app.core.knowledge import CodeKnowledgeBase
from app.core.prioritizer import IssuePrioritizer
from app.core.llm import get_llm

console = Console()
logger = logging.getLogger(__name__)


class InteractiveCockpit:
    """
    Interactive CLI for CodeJanitor - The Human-in-the-Loop Security System
    """
    
    def __init__(self):
        self.console = Console()
        self.sandbox = None
        self.orchestrator = None
        self.temp_dir = None
        
    def print_banner(self):
        """Display the CodeJanitor banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗ ██████╗ ██████╗ ███████╗     ██╗ █████╗ ███╗   ██╗║
║  ██╔════╝██╔═══██╗██╔══██╗██╔════╝     ██║██╔══██╗████╗  ██║║
║  ██║     ██║   ██║██║  ██║█████╗       ██║███████║██╔██╗ ██║║
║  ██║     ██║   ██║██║  ██║██╔══╝  ██   ██║██╔══██║██║╚██╗██║║
║  ╚██████╗╚██████╔╝██████╔╝███████╗╚█████╔╝██║  ██║██║ ╚████║║
║   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝║
║                                                              ║
║              🛡️  Automated Security Remediation  🛡️           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        self.console.print(banner, style="bold cyan")
        self.console.print("\n[bold yellow]Phase 5: Interactive Command Center[/bold yellow]")
        self.console.print("[dim]Red Team 🔴 → Blue Team 🔵 → Pull Request 🚀[/dim]\n")
    
    def check_docker_health(self) -> bool:
        """
        Check if Docker is available and image exists
        
        Returns:
            bool: True if healthy, False otherwise
        """
        self.console.print("\n[bold cyan]🔍 Checking Docker Environment...[/bold cyan]")
        
        try:
            sandbox = DockerSandbox()
            if sandbox.health_check():
                self.console.print("✅ Docker daemon: [green]Running[/green]")
                self.console.print("✅ Sandbox image: [green]Ready[/green]")
                self.sandbox = sandbox
                return True
            else:
                self.console.print("❌ Docker health check failed", style="red")
                return False
                
        except Exception as e:
            self.console.print(f"❌ Docker error: {e}", style="red")
            
            if "image" in str(e).lower() or "not found" in str(e).lower():
                self.console.print("\n[yellow]⚠️  Sandbox image not found[/yellow]")
                rebuild = Confirm.ask("Would you like to rebuild the Docker image?")
                
                if rebuild:
                    return self.rebuild_docker_image()
            
            return False
    
    def rebuild_docker_image(self) -> bool:
        """Rebuild the Docker sandbox image"""
        self.console.print("\n[bold cyan]🔨 Building Docker Image...[/bold cyan]")
        
        try:
            import subprocess
            
            # Check if Dockerfile exists
            dockerfile_path = Path("docker/Dockerfile")
            if not dockerfile_path.exists():
                self.console.print("❌ Dockerfile not found at docker/Dockerfile", style="red")
                return False
            
            # Build the image
            result = subprocess.run(
                ["docker", "build", "-t", "codejanitor-sandbox", "-f", str(dockerfile_path), "."],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.console.print("✅ Docker image built successfully", style="green")
                self.sandbox = DockerSandbox()
                return True
            else:
                self.console.print(f"❌ Build failed: {result.stderr}", style="red")
                return False
                
        except Exception as e:
            self.console.print(f"❌ Failed to build image: {e}", style="red")
            return False
    
    def get_repo_input(self) -> Optional[str]:
        """
        Get GitHub repository from user
        
        Returns:
            str: Repository in format 'username/repo' or None
        """
        self.console.print("\n[bold cyan]📦 Repository Input[/bold cyan]")
        
        while True:
            repo = Prompt.ask(
                "[yellow]Enter GitHub repository[/yellow]",
                default="",
                show_default=False
            )
            
            if not repo:
                if Confirm.ask("Exit CodeJanitor?"):
                    return None
                continue
            
            # Extract username/repo from various formats
            # Handles: username/repo, github.com/username/repo, https://github.com/username/repo
            patterns = [
                r'github\.com[:/]([^/]+/[^/\s]+?)(?:\.git)?$',  # URL format
                r'^([^/]+/[^/\s]+)$'  # Direct format
            ]
            
            for pattern in patterns:
                match = re.search(pattern, repo)
                if match:
                    clean_repo = match.group(1).strip('/')
                    self.console.print(f"✅ Repository: [green]{clean_repo}[/green]")
                    return clean_repo
            
            self.console.print("❌ Invalid format. Use: [cyan]username/repo[/cyan]", style="red")
    
    def _get_severity(self, risk_score: float) -> str:
        """Convert risk score to severity level"""
        if risk_score >= 8:
            return "critical"
        elif risk_score >= 6:
            return "high"
        elif risk_score >= 4:
            return "medium"
        else:
            return "low"
    
    def run_audit(self, repo: str) -> List[Dict]:
        """
        Run the security audit on the repository
        
        Args:
            repo: Repository in format 'username/repo'
            
        Returns:
            List of vulnerability issues
        """
        self.console.print("\n[bold cyan]🔍 Security Audit Phase[/bold cyan]")
        
        try:
            # Create temporary directory for cloning
            self.temp_dir = tempfile.mkdtemp(prefix="janitor_")
            repo_path = Path(self.temp_dir) / "repo"
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                # Clone repository
                task1 = progress.add_task("[cyan]Cloning repository...", total=None)
                
                # Use GitOps to clone
                git_ops = GitOps(token=os.getenv("GITHUB_TOKEN", ""))
                repo_url = f"https://github.com/{repo}.git"
                git_ops.clone_repo(repo_url, str(repo_path))
                progress.update(task1, completed=True)
                
                # Initialize components
                task2 = progress.add_task("[cyan]Building knowledge graph...", total=None)
                knowledge_base = CodeKnowledgeBase()
                knowledge_base.build_graph(repo_path)
                progress.update(task2, completed=True)
                
                # Run audit
                task3 = progress.add_task("[cyan]Scanning for vulnerabilities...", total=None)
                
                # Create GitHub manager if token is available
                github_manager = None
                github_token = os.getenv("GITHUB_TOKEN")
                if github_token:
                    from app.tools.github import GitHubManager
                    github_manager = GitHubManager(token=github_token)
                
                auditor = RepositoryAuditor(
                    github_manager=github_manager,
                    create_issues=False
                )
                
                # Scan all Python files
                issues = []
                for py_file in repo_path.rglob("*.py"):
                    if ".venv" not in str(py_file) and "venv" not in str(py_file):
                        try:
                            relative_path = str(py_file.relative_to(repo_path))
                            
                            # Read file contents
                            with open(py_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Scan file with actual content
                            file_issues = auditor.scan_file(relative_path, content)
                            
                            # Add file path and convert to issue format
                            for issue in file_issues:
                                if issue.get("vulnerable", False):
                                    issues.append({
                                        "file": relative_path,
                                        "type": issue.get("type", "Unknown"),
                                        "severity": self._get_severity(issue.get("risk_score", 0)),
                                        "line": issue.get("start_line", 0),
                                        "risk_score": issue.get("risk_score", 0),
                                        "description": issue.get("description", ""),
                                        "function": issue.get("function", ""),
                                        "id": len(issues) + 1
                                    })
                        except Exception as e:
                            logger.error(f"Failed to scan {py_file}: {e}")
                            continue
                
                progress.update(task3, completed=True)
            
            # Initialize orchestrator with all components
            self.orchestrator = JanitorOrchestrator(
                sandbox=self.sandbox,
                auditor=auditor,
                red_team=RedTeamAgent(sandbox=self.sandbox, llm=get_llm()),
                prioritizer=IssuePrioritizer(),
                knowledge_base=knowledge_base,
                blue_team=BlueTeamAgent(sandbox=self.sandbox, knowledge_base=knowledge_base, llm=get_llm()),
                git_ops=git_ops,
                repo_path=str(repo_path)
            )
            
            self.console.print(f"\n✅ Found [bold yellow]{len(issues)}[/bold yellow] potential vulnerabilities")
            return issues
            
        except Exception as e:
            self.console.print(f"\n❌ Audit failed: {e}", style="red")
            import traceback
            self.console.print(traceback.format_exc(), style="dim")
            return []
    
    def display_risk_report(self, issues: List[Dict]) -> Table:
        """
        Display vulnerability report as a Rich table
        
        Args:
            issues: List of vulnerability issues
            
        Returns:
            Rich Table object
        """
        table = Table(
            title="🔐 Vulnerability Risk Report",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("ID", style="cyan", justify="center")
        table.add_column("Type", style="yellow")
        table.add_column("Severity", justify="center")
        table.add_column("File", style="blue")
        table.add_column("Line", justify="center")
        table.add_column("Risk Score", justify="center")
        
        for idx, issue in enumerate(issues, 1):
            # Color code severity
            severity = issue.get("severity", "medium")
            if severity == "critical":
                severity_style = "[red bold]CRITICAL[/red bold]"
                risk_score = issue.get("risk_score", 90)
            elif severity == "high":
                severity_style = "[red]HIGH[/red]"
                risk_score = issue.get("risk_score", 70)
            elif severity == "medium":
                severity_style = "[yellow]MEDIUM[/yellow]"
                risk_score = issue.get("risk_score", 50)
            else:
                severity_style = "[dim]LOW[/dim]"
                risk_score = issue.get("risk_score", 30)
            
            table.add_row(
                str(idx),
                issue.get("type", "Unknown"),
                severity_style,
                issue.get("file", "N/A"),
                str(issue.get("line", "?")),
                f"{risk_score:.1f}"
            )
        
        return table
    
    def choose_prioritization_strategy(self, issues: List[Dict]) -> List[Dict]:
        """
        Let user choose how to prioritize issues
        
        Args:
            issues: List of all issues
            
        Returns:
            Prioritized list of issues
        """
        self.console.print("\n[bold cyan]🎯 Prioritization Strategy[/bold cyan]")
        
        self.console.print("\nHow would you like to handle these vulnerabilities?")
        self.console.print("[bold green]A[/bold green] - System Prioritization (AI sorts by risk)")
        self.console.print("[bold yellow]B[/bold yellow] - Manual Selection (Choose specific issue ID)")
        
        choice = Prompt.ask(
            "\n[yellow]Select strategy[/yellow]",
            choices=["A", "B", "a", "b"],
            default="A"
        ).upper()
        
        if choice == "A":
            # System prioritization
            self.console.print("\n[cyan]🤖 Using AI Risk Scoring...[/cyan]")
            
            # Sort by risk score (descending)
            sorted_issues = sorted(
                issues,
                key=lambda x: x.get("risk_score", 0),
                reverse=True
            )
            
            return sorted_issues
        
        else:
            # Manual selection
            self.console.print("\n[cyan]👤 Manual Selection Mode[/cyan]")
            
            while True:
                issue_id = Prompt.ask(
                    "\n[yellow]Enter issue ID to tackle first[/yellow]",
                    default="1"
                )
                
                try:
                    idx = int(issue_id) - 1
                    if 0 <= idx < len(issues):
                        # Move selected issue to front
                        selected = issues[idx]
                        remaining = [iss for i, iss in enumerate(issues) if i != idx]
                        return [selected] + remaining
                    else:
                        self.console.print(f"❌ Invalid ID. Choose 1-{len(issues)}", style="red")
                except ValueError:
                    self.console.print("❌ Please enter a number", style="red")
    
    def display_target_issue(self, issue: Dict, index: int, total: int):
        """Display the current target issue"""
        title = f"🎯 Target Issue [{index}/{total}]"
        
        content = f"""[bold yellow]Type:[/bold yellow] {issue.get('type', 'Unknown')}
[bold yellow]Severity:[/bold yellow] {issue.get('severity', 'unknown').upper()}
[bold yellow]File:[/bold yellow] {issue.get('file', 'N/A')}
[bold yellow]Line:[/bold yellow] {issue.get('line', '?')}
[bold yellow]Risk Score:[/bold yellow] {issue.get('risk_score', 0):.1f}

[bold yellow]Description:[/bold yellow]
{issue.get('description', 'No description available')}
"""
        
        panel = Panel(
            content,
            title=title,
            border_style="cyan",
            box=box.DOUBLE
        )
        
        self.console.print("\n")
        self.console.print(panel)
    
    def show_action_menu(self) -> str:
        """
        Show the action menu and get user choice
        
        Returns:
            str: User's choice (F/S/E)
        """
        self.console.print("\n[bold cyan]⚡ Action Menu[/bold cyan]")
        self.console.print("[bold green][F]ix[/bold green] - Launch Red Team → Blue Team → Create PR")
        self.console.print("[bold yellow][S]kip[/bold yellow] - Ignore this issue and move to next")
        self.console.print("[bold red][E]xit[/bold red] - Stop the entire process")
        
        choice = Prompt.ask(
            "\n[yellow]Choose action[/yellow]",
            choices=["F", "S", "E", "f", "s", "e"],
            default="F"
        ).upper()
        
        return choice
    
    def execute_fix_workflow(self, issue: Dict, repo: str) -> bool:
        """
        Execute the full Red Team → Blue Team → PR workflow
        
        Args:
            issue: Vulnerability issue to fix
            repo: Repository name
            
        Returns:
            bool: True if successful
        """
        try:
            # Red Team Phase
            self.console.print("\n")
            red_panel = Panel(
                "[bold]🔴 Red Team: Exploitation Phase[/bold]\n\n"
                "Step 1: [cyan]RECON[/cyan] - Analyzing vulnerability...\n"
                "Step 2: [cyan]PLAN[/cyan] - Crafting attack strategy...\n"
                "Step 3: [cyan]EXPLOIT[/cyan] - Generating proof-of-concept...",
                title="⚔️  Red Team",
                border_style="red bold",
                box=box.HEAVY
            )
            self.console.print(red_panel)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("[red]Executing Red Team attack...", total=None)
                
                # Get Red Team and read file
                red_team = self.orchestrator.red_team
                file_path = Path(self.orchestrator.repo_path) / issue.get("file", "")
                
                if not file_path.exists():
                    self.console.print(f"❌ File not found: {file_path}", style="red")
                    return False
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Get function code from the auditor's parsing
                from app.tools.parsing import CodeParser
                parser = CodeParser(language="python")
                functions = parser.parse_functions(code)
                
                # Find the vulnerable function
                function_code = code  # Default to full file
                for func in functions:
                    if func['name'] == issue.get('function', ''):
                        function_code = func['code']
                        break
                
                # Prepare vulnerability details
                vulnerability_details = {
                    'type': issue.get('type', 'Unknown'),
                    'description': issue.get('description', ''),
                    'function_code': function_code
                }
                
                # Get context from knowledge base if available
                context_code = None
                if self.orchestrator.knowledge_base:
                    try:
                        context_code = self.orchestrator.knowledge_base.get_context(
                            issue.get('file', ''),
                            depth=1
                        )
                    except Exception as e:
                        logger.warning(f"Failed to get context: {e}")
                
                # Run validation with Kill Chain methodology
                exploit_result = red_team.run_validation(
                    target_file=issue.get('file', ''),
                    vulnerability_details=vulnerability_details,
                    context_code=context_code
                )
                
                progress.update(task, completed=True)
            
            if not exploit_result.get("verified", False):
                self.console.print("\n[yellow]⚠️  Red Team: Exploit verification failed (possible false positive)[/yellow]")
                return False
            
            self.console.print("\n[bold red]✅ Red Team Success![/bold red]")
            
            # Get exploit code from thought process
            thought_process = exploit_result.get('thought_process', {})
            exploit_code = thought_process.get('exploit_code', '')
            self.console.print(f"[dim]Exploit confirmed: {exploit_result.get('output', '')[:100]}...[/dim]")
            
            # Blue Team Phase
            self.console.print("\n")
            blue_panel = Panel(
                "[bold]🔵 Blue Team: Remediation Phase[/bold]\n\n"
                "Step 1: [cyan]ANALYZE[/cyan] - Understanding the vulnerability...\n"
                "Step 2: [cyan]PATCH[/cyan] - Generating secure fix...\n"
                "Step 3: [cyan]VERIFY[/cyan] - Testing with Red Team's exploit...",
                title="🛡️  Blue Team",
                border_style="blue bold",
                box=box.HEAVY
            )
            self.console.print(blue_panel)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("[blue]Executing Blue Team patch...", total=None)
                
                # Generate and verify patch
                blue_team = self.orchestrator.blue_team
                patch_result = blue_team.patch_and_verify(
                    target_file=issue.get("file", ""),
                    current_content=code,
                    exploit_code=exploit_code,
                    vulnerability_type=issue.get("type", ""),
                    vulnerability_description=issue.get("description", "")
                )
                
                progress.update(task, completed=True)
            
            if not patch_result.get("success", False):
                self.console.print("\n[red]❌ Blue Team: Patch failed[/red]")
                self.console.print(f"[dim]{patch_result.get('error', 'Unknown error')}[/dim]")
                
                # Still create GitHub issue for tracking even if patch failed
                self.console.print("\n[yellow]📝 Creating GitHub issue for manual review...[/yellow]")
                if self.orchestrator.auditor and self.orchestrator.auditor.github_manager:
                    try:
                        issue_result = self.orchestrator.auditor.github_manager.create_issue(
                            repo_url=f"https://github.com/{repo}",
                            title=f"Security: {issue.get('type', 'Vulnerability')} in {issue.get('file', '')}",
                            body=f"""## Vulnerability Details

**Type:** {issue.get('type', 'Unknown')}
**Severity:** {issue.get('severity', 'Unknown')}
**File:** {issue.get('file', '')}
**Line:** {issue.get('line', 'N/A')}
**Risk Score:** {issue.get('risk_score', 0)}/10

**Description:**
{issue.get('description', 'No description available')}

**Status:** Automated patch failed after {patch_result.get('attempts', 3)} attempts. Manual review required.

**Red Team Verification:**
Exploit successfully verified this vulnerability.

**Exploit Output:**
```
{exploit_result.get('output', '')[:500]}
```

---
*This issue was automatically created by CodeJanitor*
""",
                            labels=["security", "automated-detection"]
                        )
                        if issue_result.get("success"):
                            self.console.print(f"[green]✅ GitHub issue created: {issue_result.get('issue_url', '')}[/green]")
                        else:
                            self.console.print(f"[yellow]⚠️ Failed to create issue: {issue_result.get('error', '')}[/yellow]")
                    except Exception as e:
                        self.console.print(f"[dim]Could not create GitHub issue: {e}[/dim]")
                return False
            
            self.console.print("\n[bold blue]✅ Blue Team Success![/bold blue]")
            self.console.print(f"[dim]Patch verified after {patch_result.get('attempts', 1)} attempt(s)[/dim]")
            
            # Git/PR Phase
            self.console.print("\n")
            git_panel = Panel(
                "[bold]🚀 Git Operations: Pull Request Creation[/bold]\n\n"
                "Step 1: [cyan]BRANCH[/cyan] - Creating security fix branch...\n"
                "Step 2: [cyan]COMMIT[/cyan] - Committing patched code...\n"
                "Step 3: [cyan]PUSH[/cyan] - Pushing to remote...\n"
                "Step 4: [cyan]PR[/cyan] - Creating pull request...",
                title="🔀 GitHub Integration",
                border_style="green bold",
                box=box.HEAVY
            )
            self.console.print(git_panel)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("[green]Creating pull request...", total=None)
                
                # Create PR
                git_ops = self.orchestrator.git_ops
                issue_number = issue.get("id", 1)
                
                # Create temporary work directory for Git operations
                import tempfile
                work_dir = Path(tempfile.mkdtemp(prefix="codejanitor_pr_"))
                
                pr_result = {}
                try:
                    pr_url = git_ops.create_pr_for_fix(
                        repo_url=f"https://github.com/{repo}.git",
                        file_path=issue.get("file", ""),
                        patched_content=patch_result.get("patched_content", ""),
                        issue_number=issue_number,
                        vulnerability_type=issue.get("type", "Security Issue"),
                        work_dir=work_dir
                    )
                    pr_result = {"success": True, "pr_url": pr_url}
                except Exception as pr_error:
                    pr_result = {"success": False, "error": str(pr_error)}
                finally:
                    # Clean up temp directory
                    import shutil
                    if work_dir.exists():
                        shutil.rmtree(work_dir, ignore_errors=True)
                
                progress.update(task, completed=True)
            
            if pr_result.get("success", False):
                self.console.print("\n[bold green]✅ Pull Request Created![/bold green]")
                self.console.print(f"[bold cyan]🔗 URL:[/bold cyan] {pr_result.get('pr_url', 'N/A')}")
                return True
            else:
                self.console.print("\n[yellow]⚠️  PR creation failed (but patch is ready)[/yellow]")
                self.console.print(f"[dim]{pr_result.get('error', 'Unknown error')}[/dim]")
                return False
                
        except Exception as e:
            self.console.print(f"\n❌ Workflow failed: {e}", style="red")
            import traceback
            self.console.print(traceback.format_exc(), style="dim")
            return False
    
    def run(self):
        """Main execution loop"""
        try:
            # Banner
            self.print_banner()
            
            # Docker health check
            if not self.check_docker_health():
                self.console.print("\n❌ Cannot proceed without Docker", style="bold red")
                return
            
            # Get repository
            repo = self.get_repo_input()
            if not repo:
                self.console.print("\n[yellow]Exiting CodeJanitor...[/yellow]")
                return
            
            # Run audit
            issues = self.run_audit(repo)
            
            if not issues:
                self.console.print("\n[green]✨ No vulnerabilities found! Repository is clean.[/green]")
                return
            
            # Display report
            self.console.print("\n")
            table = self.display_risk_report(issues)
            self.console.print(table)
            
            # Choose prioritization
            prioritized_issues = self.choose_prioritization_strategy(issues)
            
            # Execution loop
            self.console.print("\n[bold cyan]🔄 Starting Execution Loop[/bold cyan]")
            
            fixed_count = 0
            skipped_count = 0
            
            for idx, issue in enumerate(prioritized_issues, 1):
                # Display target
                self.display_target_issue(issue, idx, len(prioritized_issues))
                
                # Get action
                action = self.show_action_menu()
                
                if action == "F":
                    # Execute fix
                    success = self.execute_fix_workflow(issue, repo)
                    if success:
                        fixed_count += 1
                    
                elif action == "S":
                    # Skip
                    self.console.print("\n[yellow]⏭️  Skipping issue...[/yellow]")
                    skipped_count += 1
                    
                elif action == "E":
                    # Exit
                    self.console.print("\n[red]🛑 Stopping execution loop...[/red]")
                    break
            
            # Summary
            self.console.print("\n")
            summary_panel = Panel(
                f"[bold green]✅ Fixed:[/bold green] {fixed_count}\n"
                f"[bold yellow]⏭️  Skipped:[/bold yellow] {skipped_count}\n"
                f"[bold cyan]📊 Total:[/bold cyan] {len(prioritized_issues)}",
                title="📋 Execution Summary",
                border_style="cyan bold",
                box=box.DOUBLE
            )
            self.console.print(summary_panel)
            
            self.console.print("\n[bold green]✨ CodeJanitor session complete![/bold green]")
            
        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]⚠️  Interrupted by user[/yellow]")
        except Exception as e:
            self.console.print(f"\n❌ Fatal error: {e}", style="bold red")
            import traceback
            self.console.print(traceback.format_exc(), style="dim")
        finally:
            # Cleanup
            if self.temp_dir and Path(self.temp_dir).exists():
                self.console.print("\n[dim]Cleaning up temporary files...[/dim]")
                shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    """Entry point"""
    cockpit = InteractiveCockpit()
    cockpit.run()


if __name__ == "__main__":
    main()
