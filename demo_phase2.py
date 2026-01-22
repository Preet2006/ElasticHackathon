"""
Phase 2 Demo - The Auditor in Action
Demonstrates vulnerability detection with Tree-sitter and LLM analysis
"""

from app.agents.auditor import RepositoryAuditor
from app.core.llm import get_llm
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

console = Console()


def demo_parse_functions():
    """Demo 1: Extract functions with Tree-sitter"""
    console.print("\n[bold cyan]Demo 1: Tree-sitter Function Extraction[/bold cyan]\n")
    
    from app.tools.parsing import CodeParser
    
    code = """
def calculate_total(items):
    '''Calculate total price'''
    return sum(item.price for item in items)

def process_payment(card_number, amount):
    # WARNING: This stores card data insecurely
    log_payment(card_number, amount)
    return charge_card(card_number, amount)

def send_email(to, subject, body):
    '''Send email notification'''
    import smtplib
    # Implementation here
    pass
"""
    
    parser = CodeParser()
    functions = parser.parse_functions(code)
    
    console.print(f"[green]✓ Extracted {len(functions)} functions:[/green]\n")
    
    for func in functions:
        console.print(f"  • [yellow]{func['name']}()[/yellow] (lines {func['start_line']}-{func['end_line']})")
        if func.get("docstring"):
            console.print(f"    Doc: {func['docstring']}")


def demo_vulnerability_detection():
    """Demo 2: Detect vulnerabilities with LLM"""
    console.print("\n[bold cyan]Demo 2: LLM-Powered Vulnerability Detection[/bold cyan]\n")
    
    try:
        auditor = RepositoryAuditor(llm=get_llm(), create_issues=False)
        
        # Create test file with known vulnerabilities
        vulnerable_code = """
def unsafe_query(username):
    # SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return db.execute(query)

def unsafe_file_read(filename):
    # Path traversal vulnerability
    return open(f"/data/{filename}").read()

def unsafe_command(user_input):
    # Command injection vulnerability
    import os
    os.system(f"ping {user_input}")

def safe_function(a, b):
    # This should be safe
    return a + b
"""
        
        console.print("[yellow]Analyzing code for vulnerabilities...[/yellow]\n")
        
        findings = auditor.scan_file("vulnerable_demo.py", vulnerable_code)
        
        # Create results table
        table = Table(title="Vulnerability Scan Results")
        table.add_column("Function", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Risk", justify="center")
        table.add_column("Type", style="yellow")
        
        for finding in findings:
            status = "🔴 Vulnerable" if finding["vulnerable"] else "✓ Safe"
            status_style = "red" if finding["vulnerable"] else "green"
            
            risk_display = f"{finding['risk_score']}/10"
            risk_style = "red" if finding['risk_score'] >= 7 else "yellow" if finding['risk_score'] >= 5 else "green"
            
            table.add_row(
                finding["function"],
                f"[{status_style}]{status}[/{status_style}]",
                f"[{risk_style}]{risk_display}[/{risk_style}]",
                finding["type"]
            )
        
        console.print(table)
        
        # Show details of most critical finding
        critical_findings = [f for f in findings if f["vulnerable"] and f["risk_score"] >= 7]
        if critical_findings:
            console.print("\n[bold red]Critical Vulnerability Details:[/bold red]")
            critical = critical_findings[0]
            
            details = f"""
Function: {critical['function']}()
Type: {critical['type']}
Risk Score: {critical['risk_score']}/10

Description:
{critical['description']}
"""
            console.print(Panel(details, border_style="red"))
        
        # Generate report
        report = auditor.generate_report(findings)
        console.print("\n[bold]Security Audit Report:[/bold]")
        console.print(Panel(report, border_style="blue"))
        
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        console.print("[yellow]Note: Ensure GROQ_API_KEY is set in .env file[/yellow]")


def demo_github_integration():
    """Demo 3: GitHub issue creation (dry run)"""
    console.print("\n[bold cyan]Demo 3: GitHub Issue Management[/bold cyan]\n")
    
    from app.tools.github import GitHubManager
    
    try:
        github = GitHubManager()
        
        console.print(f"[green]✓ Authenticated as: {github.user.login}[/green]\n")
        
        # Example of how issues would be created
        console.print("[yellow]Issue Creation Example:[/yellow]\n")
        
        example_issue = """
Title: [Security] SQL Injection in unsafe_query()

Body:
## 🔴 Security Vulnerability Detected

**Risk Score:** 9/10
**Type:** SQL Injection
**File:** `app/database.py`
**Function:** `unsafe_query()`
**Lines:** 10-15

### Description
User input directly interpolated into SQL query without sanitization.
This allows attackers to execute arbitrary SQL commands.

### Recommendation
Use parameterized queries or an ORM to prevent SQL injection.
"""
        console.print(Panel(example_issue, title="Example GitHub Issue", border_style="yellow"))
        
        console.print("\n[green]✓ GitHub integration ready[/green]")
        console.print("[dim]Note: Use create_issues=True in auditor to actually create issues[/dim]")
        
    except Exception as e:
        console.print(f"[yellow]⚠ GitHub not configured: {e}[/yellow]")
        console.print("[dim]Set GITHUB_TOKEN in .env to enable issue creation[/dim]")


def main():
    console.print(Panel.fit(
        "[bold green]CodeJanitor 2.0 - Phase 2 Demo[/bold green]\n"
        "The Auditor: Tree-sitter + LLM Security Analysis",
        border_style="green"
    ))
    
    try:
        demo_parse_functions()
        demo_vulnerability_detection()
        demo_github_integration()
        
        console.print("\n[bold green]✓ Phase 2 Complete: The Auditor is Operational![/bold green]\n")
        
        console.print("[bold]What's Working:[/bold]")
        console.print("  • Tree-sitter parsing for function extraction")
        console.print("  • LLM-powered vulnerability detection")
        console.print("  • Risk scoring (0-10 scale)")
        console.print("  • GitHub issue creation with deduplication")
        console.print("  • Comprehensive audit reports")
        
        console.print("\n[bold cyan]Next: Phase 3 - The Blue Team (Auto-Fix)[/bold cyan]")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
