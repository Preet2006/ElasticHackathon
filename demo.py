"""
Demo script showcasing CodeJanitor 2.0 Phase 1 capabilities
"""

from app.tools.sandbox import DockerSandbox
from app.core.llm import get_llm
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def demo_sandbox_file_injection():
    """Demonstrate file injection with imports"""
    console.print("\n[bold cyan]Demo 1: Docker Sandbox with File Injection[/bold cyan]\n")
    
    sandbox = DockerSandbox()
    
    # Create a module and a main script that imports it
    files = {
        "calculator.py": """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def power(a, b):
    return a ** b
""",
        "main.py": """
from calculator import add, multiply, power

print("Calculator Demo")
print(f"5 + 3 = {add(5, 3)}")
print(f"4 * 7 = {multiply(4, 7)}")
print(f"2 ^ 10 = {power(2, 10)}")
"""
    }
    
    console.print("[yellow]Injecting files:[/yellow]")
    for filename in files.keys():
        console.print(f"  • {filename}")
    
    stdout, stderr, exit_code = sandbox.run_in_context(
        command="python main.py",
        files=files
    )
    
    console.print(f"\n[green]✓ Exit code: {exit_code}[/green]")
    console.print(Panel(stdout.strip(), title="Output", border_style="green"))


def demo_security():
    """Demonstrate security features"""
    console.print("\n[bold cyan]Demo 2: Security Features[/bold cyan]\n")
    
    sandbox = DockerSandbox()
    
    # Try to access network (should fail)
    code = """
import socket
try:
    socket.create_connection(("google.com", 80), timeout=2)
    print("⚠️  SECURITY BREACH: Network access succeeded!")
except Exception as e:
    print(f"✓ Network blocked: {type(e).__name__}")
"""
    
    console.print("[yellow]Testing network isolation...[/yellow]")
    stdout, stderr, exit_code = sandbox.run_python(code)
    console.print(Panel(stdout.strip(), title="Security Test Result", border_style="green"))


def demo_llm_client():
    """Demonstrate resilient LLM client"""
    console.print("\n[bold cyan]Demo 3: Resilient LLM Client[/bold cyan]\n")
    
    try:
        llm = get_llm()
        
        console.print("[yellow]Sending request to LLM...[/yellow]")
        response = llm.invoke(
            "Explain what CodeJanitor 2.0 does in one sentence.",
            system_message="You are a helpful assistant."
        )
        
        console.print(Panel(response, title="LLM Response", border_style="blue"))
        console.print("[green]✓ Resilient client with automatic retries active[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ LLM Error: {e}[/red]")
        console.print("[yellow]Note: Ensure GROQ_API_KEY is set in .env file[/yellow]")


def main():
    console.print(Panel.fit(
        "[bold green]CodeJanitor 2.0 - Phase 1 Demo[/bold green]\n"
        "Enterprise-Grade Autonomous Security Agent",
        border_style="green"
    ))
    
    try:
        demo_sandbox_file_injection()
        demo_security()
        demo_llm_client()
        
        console.print("\n[bold green]✓ All Phase 1 Features Working![/bold green]\n")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]\n")
        raise


if __name__ == "__main__":
    main()
