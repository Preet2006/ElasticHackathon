# CodeJanitor 2.0 - Quick Reference

## Installation
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API keys
```

## Configuration (.env)
```env
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_token
DOCKER_IMAGE=python:3.11-slim
DOCKER_TIMEOUT=15
LOG_LEVEL=INFO
```

## Quick Commands

### Run Tests
```bash
# All tests
pytest tests/ -v

# Phase 1 only (Sandbox)
pytest tests/test_sandbox.py -v

# Phase 2 only (Auditor)
pytest tests/test_auditor.py -v
```

### Run Demos
```bash
# Phase 1 - Foundation
python demo.py

# Phase 2 - Auditor
python demo_phase2.py
```

## Python API

### 1. Parse Code
```python
from app.tools.parsing import CodeParser

parser = CodeParser()
functions = parser.parse_functions(code_string)

for func in functions:
    print(f"{func['name']} at lines {func['start_line']}-{func['end_line']}")
```

### 2. Analyze Vulnerability
```python
from app.core.llm import get_llm

llm = get_llm()
result = llm.analyze_vulnerability(function_code)

if result['vulnerable']:
    print(f"Risk: {result['risk_score']}/10 - {result['type']}")
```

### 3. Scan File
```python
from app.agents.auditor import RepositoryAuditor

auditor = RepositoryAuditor()
findings = auditor.scan_file("myfile.py", open("myfile.py").read())

for f in findings:
    if f['vulnerable']:
        print(f"⚠️  {f['function']}: {f['type']} (Risk {f['risk_score']})")
```

### 4. Scan Directory
```python
from pathlib import Path
from app.agents.auditor import RepositoryAuditor

auditor = RepositoryAuditor()
findings = auditor.scan_directory(
    directory=Path("./src"),
    exclude_patterns=["**/tests/**", "**/venv/**"]
)

report = auditor.generate_report(findings)
print(report)
```

### 5. Create GitHub Issues
```python
from app.agents.auditor import RepositoryAuditor
from app.tools.github import GitHubManager

github = GitHubManager()
auditor = RepositoryAuditor(
    github_manager=github,
    create_issues=True
)

findings = auditor.scan_directory(Path("./src"))
issues = auditor.create_github_issues(
    repo_url="owner/repo",
    findings=findings,
    min_risk_score=7  # Only high-risk
)

print(f"Created {len(issues)} issues")
```

### 6. Run Code in Sandbox
```python
from app.tools.sandbox import DockerSandbox

sandbox = DockerSandbox()

# Simple execution
stdout, stderr, exit_code = sandbox.run_python("print('Hello')")

# With file injection (imports)
files = {
    "utils.py": "def helper(): return 'helper'",
    "main.py": "from utils import helper\nprint(helper())"
}

stdout, stderr, exit_code = sandbox.run_in_context(
    command="python main.py",
    files=files
)
```

## Common Patterns

### Pattern 1: Quick Security Scan
```python
from app.agents.auditor import RepositoryAuditor
from pathlib import Path

auditor = RepositoryAuditor()
findings = auditor.scan_directory(Path("."))
vulnerable = [f for f in findings if f['vulnerable'] and f['risk_score'] >= 7]

if vulnerable:
    print(f"⚠️  Found {len(vulnerable)} high-risk vulnerabilities!")
    for v in vulnerable:
        print(f"  • {v['file']}:{v['function']} - {v['type']}")
else:
    print("✓ No high-risk vulnerabilities found")
```

### Pattern 2: Generate Security Report
```python
from app.agents.auditor import RepositoryAuditor
from pathlib import Path

auditor = RepositoryAuditor()
findings = auditor.scan_directory(Path("./src"))

report = auditor.generate_report(findings)
with open("security_report.txt", "w") as f:
    f.write(report)

print("Report saved to security_report.txt")
```

### Pattern 3: CI/CD Integration
```python
from app.agents.auditor import RepositoryAuditor
from pathlib import Path
import sys

auditor = RepositoryAuditor()
findings = auditor.scan_directory(Path("."))

# Fail build if critical vulnerabilities found
critical = [f for f in findings if f['vulnerable'] and f['risk_score'] >= 8]

if critical:
    print(f"❌ Build failed: {len(critical)} critical vulnerabilities found")
    sys.exit(1)
else:
    print("✓ Build passed: No critical vulnerabilities")
    sys.exit(0)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *required* | Groq API key for LLM |
| `GITHUB_TOKEN` | *optional* | GitHub PAT for issue creation |
| `LLM_MODEL` | llama-3.3-70b-versatile | LLM model to use |
| `LLM_TEMPERATURE` | 0.1 | Temperature for responses |
| `LLM_MAX_RETRIES` | 3 | Max retry attempts |
| `DOCKER_IMAGE` | python:3.11-slim | Docker image for sandbox |
| `DOCKER_TIMEOUT` | 15 | Execution timeout (seconds) |
| `DOCKER_MEMORY_LIMIT` | 512m | Memory limit |
| `LOG_LEVEL` | INFO | Logging level |

## Risk Score Guide

| Score | Severity | Action |
|-------|----------|--------|
| 0-4 | 🟢 Low | Monitor |
| 5-6 | 🟡 Medium | Review soon |
| 7 | 🟠 High | Fix this sprint |
| 8-10 | 🔴 Critical | Fix immediately |

## Common Vulnerability Types Detected

- SQL Injection
- Command Injection
- Path Traversal
- Cross-Site Scripting (XSS)
- XML External Entity (XXE)
- Server-Side Request Forgery (SSRF)
- Insecure Deserialization
- Hardcoded Credentials
- Weak Cryptography
- Authentication Issues

## Troubleshooting

### Docker not running
```bash
# Start Docker Desktop on Windows
# Or run: docker ps
```

### API key not found
```bash
# Check .env file exists
type .env

# Verify key is set
echo %GROQ_API_KEY%  # Windows
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### GitHub authentication failed
```bash
# Verify token has correct permissions
# Required scopes: repo, write:discussion
```

## File Structure

```
CodeJanitor/
├── app/
│   ├── core/
│   │   ├── config.py      # Settings
│   │   └── llm.py         # LLM client
│   ├── tools/
│   │   ├── sandbox.py     # Docker execution
│   │   ├── parsing.py     # Tree-sitter
│   │   ├── github.py      # GitHub API
│   │   └── git_ops.py     # Git operations
│   └── agents/
│       └── auditor.py     # Security auditor
├── tests/
│   ├── test_sandbox.py    # Phase 1 tests
│   └── test_auditor.py    # Phase 2 tests
├── demo.py                # Phase 1 demo
├── demo_phase2.py         # Phase 2 demo
└── .env                   # Configuration
```

## Phase Status

- ✅ **Phase 1**: Foundation (Sandbox + Resilience)
- ✅ **Phase 2**: The Auditor (Parsing + Detection)
- ⏳ **Phase 3**: The Blue Team (Auto-Fix)
- ⏳ **Phase 4**: Production (RAG + CLI)
