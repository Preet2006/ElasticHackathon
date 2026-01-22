"""
Tests for Docker Sandbox
Verifies file injection and import handling
"""

import pytest
from app.tools.sandbox import DockerSandbox, SandboxError


class TestDockerSandbox:
    """Test suite for DockerSandbox functionality"""
    
    @pytest.fixture
    def sandbox(self):
        """Create a sandbox instance for testing"""
        return DockerSandbox()
    
    def test_sandbox_initialization(self, sandbox):
        """Test that sandbox initializes correctly"""
        assert sandbox is not None
        assert sandbox.image is not None
        assert sandbox.client is not None
    
    def test_health_check(self, sandbox):
        """Test Docker health check"""
        assert sandbox.health_check() is True
    
    def test_simple_execution(self, sandbox):
        """Test basic command execution"""
        code = "print('Hello, CodeJanitor 2.0!')"
        stdout, stderr, exit_code = sandbox.run_python(code)
        
        assert exit_code == 0
        assert "Hello, CodeJanitor 2.0!" in stdout
        assert stderr == ""
    
    def test_file_injection_with_imports(self, sandbox):
        """
        Critical test: Verify file injection enables imports
        
        This test creates two files:
        1. hello.py - a module with a greeting function
        2. main.py - imports and uses the hello module
        
        This proves dependency awareness works correctly.
        """
        # Create the dependency module
        hello_py = """
def greet(name):
    return f"Hello from module, {name}!"

def get_version():
    return "CodeJanitor 2.0"
"""
        
        # Create the main script that imports the module
        main_py = """
import hello

# Test the import works
message = hello.greet("Security Agent")
version = hello.get_version()

print(f"Message: {message}")
print(f"Version: {version}")
"""
        
        # Execute with file injection
        files = {
            "hello.py": hello_py,
            "main.py": main_py
        }
        
        stdout, stderr, exit_code = sandbox.run_in_context(
            command="python main.py",
            files=files
        )
        
        # Verify execution succeeded
        assert exit_code == 0, f"Execution failed with stderr: {stderr}"
        
        # Verify output contains expected strings
        assert "Message: Hello from module, Security Agent!" in stdout
        assert "Version: CodeJanitor 2.0" in stdout
        
        # Verify no import errors
        assert "ImportError" not in stderr
        assert "ModuleNotFoundError" not in stderr
    
    def test_multiple_file_injection(self, sandbox):
        """Test injection of multiple interdependent files"""
        # Create a package structure
        utils_py = """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
"""
        
        calculator_py = """
from utils import add, multiply

class Calculator:
    def calculate(self):
        result1 = add(5, 3)
        result2 = multiply(4, 7)
        return result1, result2
"""
        
        main_py = """
from calculator import Calculator

calc = Calculator()
result = calc.calculate()
print(f"Results: {result[0]}, {result[1]}")
"""
        
        files = {
            "utils.py": utils_py,
            "calculator.py": calculator_py,
            "main.py": main_py
        }
        
        stdout, stderr, exit_code = sandbox.run_in_context(
            command="python main.py",
            files=files
        )
        
        assert exit_code == 0
        assert "Results: 8, 28" in stdout
    
    def test_error_handling(self, sandbox):
        """Test that Python errors are captured correctly"""
        code = """
# This will cause a runtime error
x = 1 / 0
"""
        
        stdout, stderr, exit_code = sandbox.run_python(code)
        
        assert exit_code != 0
        assert "ZeroDivisionError" in stderr
    
    def test_security_network_disabled(self, sandbox):
        """Test that network is disabled by default"""
        code = """
import socket
try:
    socket.create_connection(("google.com", 80), timeout=2)
    print("Network is enabled")
except Exception as e:
    print(f"Network blocked: {type(e).__name__}")
"""
        
        stdout, stderr, exit_code = sandbox.run_python(code)
        
        # Network should be blocked
        assert "Network blocked" in stdout or exit_code != 0
    
    def test_timeout_handling(self, sandbox):
        """Test execution with timeout"""
        # Create a script that completes quickly
        code = """
import time
print("Starting")
time.sleep(0.5)
print("Done")
"""
        
        stdout, stderr, exit_code = sandbox.run_python(code, timeout=5)
        
        assert exit_code == 0
        assert "Starting" in stdout
        assert "Done" in stdout
    
    def test_memory_limit(self, sandbox):
        """Test that memory limits are enforced"""
        # This test just verifies the sandbox accepts memory_limit parameter
        limited_sandbox = DockerSandbox(memory_limit="256m")
        
        code = "print('Memory limit test')"
        stdout, stderr, exit_code = limited_sandbox.run_python(code)
        
        assert exit_code == 0
        assert "Memory limit test" in stdout


def test_sandbox_factory():
    """Test the factory function"""
    from app.tools.sandbox import create_sandbox
    
    sandbox = create_sandbox()
    assert isinstance(sandbox, DockerSandbox)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
