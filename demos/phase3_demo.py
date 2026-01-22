#!/usr/bin/env python3
"""
Phase 3 Demo: Red Team Verification + Prioritization Engine
Shows how vulnerabilities are verified with exploits and prioritized
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.auditor import RepositoryAuditor
from app.agents.red_team import RedTeamAgent
from app.core.prioritizer import IssuePrioritizer
from app.core.orchestrator import JanitorOrchestrator
from app.core.config import get_settings

console = Console()


def create_demo_files():
    """Create sample vulnerable files for testing"""
    demo_dir = Path("demo_code_phase3")
    demo_dir.mkdir(exist_ok=True)
    
    # File 1: SQL Injection (HIGH RISK - Verifiable)
    sql_vuln = '''
def get_user_by_id(user_id):
    """Fetch user from database - VULNERABLE to SQL injection"""
    import sqlite3
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # DANGEROUS: String concatenation allows SQL injection
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    return cursor.fetchone()
'''
    
    # File 2: Command Injection (CRITICAL - Verifiable)
    cmd_vuln = '''
def ping_server(hostname):
    """Check if server is reachable - VULNERABLE to command injection"""
    import os
    
    # DANGEROUS: Direct shell execution with user input
    result = os.system(f"ping -c 1 {hostname}")
    
    return result == 0
'''
    
    # File 3: Path Traversal (MEDIUM RISK - Verifiable)
    path_vuln = '''
def read_user_file(filename):
    """Read user-uploaded file - VULNERABLE to path traversal"""
    base_dir = "/var/uploads"
    
    # DANGEROUS: No validation of filename
    filepath = f"{base_dir}/{filename}"
    
    with open(filepath, 'r') as f:
        return f.read()
'''
    
    # File 4: False Positive (LOW RISK - Not Verifiable)
    safe_code = '''
def calculate_discount(price, discount_percent):
    """Calculate discounted price - SAFE"""
    if not (0 <= discount_percent <= 100):
        raise ValueError("Discount must be between 0 and 100")
    
    discount_amount = price * (discount_percent / 100)
    final_price = price - discount_amount
    
    return round(final_price, 2)
'''
    
    (demo_dir / "sql_vulnerable.py").write_text(sql_vuln)
    (demo_dir / "cmd_vulnerable.py").write_text(cmd_vuln)
    (demo_dir / "path_vulnerable.py").write_text(path_vuln)
    (demo_dir / "safe_code.py").write_text(safe_code)
    
    return demo_dir


def display_vulnerability(issue, index):
    """Display a vulnerability in a formatted panel"""
    verified_badge = "✅ VERIFIED" if issue.get("verified") else "❓ UNVERIFIED"
    
    table = Table(show_header=False, box=None)
    table.add_row("File:", f"[cyan]{issue['file']}[/cyan]")
    table.add_row("Function:", f"[yellow]{issue['function']}[/yellow]")
    table.add_row("Type:", f"[red]{issue['type']}[/red]")
    table.add_row("Initial Score:", f"{issue.get('risk_score', 0)}/10")
    
    if "final_score" in issue:
        table.add_row("Final Score:", f"[bold]{issue['final_score']}/10[/bold]")
        table.add_row("Priority:", f"[bold red]{issue.get('priority', 'N/A')}[/bold red]")
    
    table.add_row("Status:", verified_badge)
    
    if issue.get("verified") and issue.get("exploit_code"):
        table.add_row("", "")
        table.add_row("Exploit:", "[green]Generated and tested ✓[/green]")
    
    title = f"🔍 Issue #{index + 1}"
    if issue.get("verified"):
        title += " [CRITICAL - VERIFIED]"
    
    console.print(Panel(table, title=title, border_style="red" if issue.get("verified") else "yellow"))


def main():
    """Run Phase 3 demo"""
    console.print(Panel.fit(
        "[bold cyan]CodeJanitor 2.0 - Phase 3 Demo[/bold cyan]\n"
        "[yellow]Red Team Verification + Intelligent Prioritization[/yellow]",
        border_style="cyan"
    ))
    
    console.print("\n[bold]Setting up demo environment...[/bold]")
    
    # Create demo files
    demo_dir = create_demo_files()
    console.print(f"✓ Created demo files in: [cyan]{demo_dir}[/cyan]\n")
    
    # Initialize components
    console.print("[bold]Initializing CodeJanitor components...[/bold]")
    
    auditor = RepositoryAuditor()
    red_team = RedTeamAgent()
    prioritizer = IssuePrioritizer()
    orchestrator = JanitorOrchestrator(
        auditor=auditor,
        red_team=red_team,
        prioritizer=prioritizer
    )
    
    console.print("✓ Auditor ready")
    console.print("✓ Red Team ready")
    console.print("✓ Prioritizer ready")
    console.print("✓ Orchestrator ready\n")
    
    # Step 1: Initial Audit
    console.print(Panel("[bold yellow]STEP 1: Initial Security Audit[/bold yellow]", border_style="yellow"))
    console.print("Scanning code for potential vulnerabilities...\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing code...", total=None)
        issues = auditor.scan_directory(demo_dir)
        progress.remove_task(task)
    
    console.print(f"[green]✓ Found {len(issues)} potential issues[/green]\n")
    
    # Display initial findings
    for i, issue in enumerate(issues):
        console.print(f"[cyan]Issue #{i+1}:[/cyan] {issue['type']} in {issue['file']}")
        console.print(f"  Initial Risk Score: {issue['risk_score']}/10\n")
    
    # Step 2: Red Team Verification
    console.print(Panel("[bold red]STEP 2: Red Team Verification[/bold red]", border_style="red"))
    console.print("Attempting to exploit vulnerabilities with active testing...\n")
    
    verified_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for i, issue in enumerate(issues):
            task_desc = f"Testing {issue['file']} - {issue['function']}..."
            task = progress.add_task(task_desc, total=None)
            
            # Only verify high-risk issues (smart strategy)
            if issue["risk_score"] >= 6:
                validated = orchestrator.validate_issue(issue)
                issues[i].update(validated)
                
                if validated.get("verified"):
                    verified_count += 1
                    console.print(f"  [green]✓ VERIFIED:[/green] {issue['type']} is exploitable!")
                else:
                    console.print(f"  [yellow]○ Not verified:[/yellow] Could not exploit {issue['type']}")
            else:
                console.print(f"  [dim]○ Skipped:[/dim] Low risk score ({issue['risk_score']}/10)")
            
            progress.remove_task(task)
    
    console.print(f"\n[bold green]✓ Verified {verified_count} real vulnerabilities[/bold green]\n")
    
    # Step 3: Prioritization
    console.print(Panel("[bold magenta]STEP 3: Intelligent Prioritization[/bold magenta]", border_style="magenta"))
    console.print("Calculating final risk scores based on verification results...\n")
    
    # Calculate final scores
    for issue in issues:
        if "verified" in issue:
            risk_calc = prioritizer.calculate_risk(
                auditor_score=issue["risk_score"],
                red_team_verified=issue.get("verified", False),
                vulnerability_type=issue["type"],
                has_exploit_proof=bool(issue.get("exploit_code"))
            )
            issue.update(risk_calc)
    
    # Sort by priority
    prioritized = prioritizer.prioritize_issues(issues)
    
    console.print("[green]✓ Prioritization complete[/green]\n")
    
    # Step 4: Display Final Report
    console.print(Panel("[bold cyan]STEP 4: Prioritized Action List[/bold cyan]", border_style="cyan"))
    console.print("Issues sorted by real risk (verified threats first):\n")
    
    for i, issue in enumerate(prioritized):
        display_vulnerability(issue, i)
    
    # Summary Table
    console.print("\n")
    summary = Table(title="[bold]Final Summary[/bold]", show_header=True, header_style="bold cyan")
    summary.add_column("Category", style="cyan")
    summary.add_column("Count", justify="right", style="yellow")
    summary.add_column("Action", style="green")
    
    critical_count = sum(1 for i in prioritized if i.get("final_score", 0) >= 8)
    verified_count = sum(1 for i in prioritized if i.get("verified"))
    unverified_count = len(prioritized) - verified_count
    
    summary.add_row("Total Issues Found", str(len(prioritized)), "Review all")
    summary.add_row("Verified Exploitable", str(verified_count), "FIX IMMEDIATELY 🔴")
    summary.add_row("Unverified Potential", str(unverified_count), "Manual review")
    summary.add_row("Critical (Score 8+)", str(critical_count), "High priority")
    
    console.print(summary)
    
    # Recommendations
    console.print("\n")
    console.print(Panel(
        "[bold green]✓ Phase 3 Complete![/bold green]\n\n"
        "[yellow]What CodeJanitor 2.0 Phase 3 Provides:[/yellow]\n"
        "1. Active vulnerability verification with real exploits\n"
        "2. Intelligent prioritization based on verification results\n"
        "3. Clear action recommendations for each issue\n"
        "4. Reduced false positives through exploit testing\n\n"
        "[cyan]Next Steps:[/cyan]\n"
        "• Focus on VERIFIED vulnerabilities first\n"
        "• Review unverified high-risk issues manually\n"
        "• Use the prioritized list to guide your security work\n"
        "• Phase 4 will add auto-fix capabilities for verified issues",
        title="[bold]Demo Complete[/bold]",
        border_style="green"
    ))
    
    console.print(f"\n[dim]Demo files saved in: {demo_dir}[/dim]")
    console.print("[dim]You can examine the vulnerable code to see what was detected.[/dim]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
