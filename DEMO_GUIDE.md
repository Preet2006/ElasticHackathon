# 🛡️ CodeJanitor 2.0 - Interactive Command Center

**Phase 5: Human-in-the-Loop Security Automation**

The ultimate security cockpit that puts YOU in control of automated vulnerability remediation.

## 🎯 What Is This?

`demo_interactive.py` is the **interactive command center** for CodeJanitor. It provides a beautiful Rich TUI that lets you:

1. **Audit** any GitHub repository for security vulnerabilities
2. **Prioritize** issues using AI risk scoring or manual selection
3. **Execute** fixes with full visibility into Red Team → Blue Team → PR workflow
4. **Control** every step with Fix/Skip/Exit actions

## 🚀 Quick Start

### Prerequisites

```bash
# 1. Ensure Docker is running
docker --version

# 2. Set your GitHub token (for PR creation)
export GITHUB_TOKEN="your_github_token_here"  # Linux/Mac
$env:GITHUB_TOKEN="your_github_token_here"     # Windows PowerShell

# 3. Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.\.venv\Scripts\activate   # Windows
```

### Run the Interactive Demo

```bash
python demo_interactive.py
```

## 📖 User Guide

### Step 1: Repository Input

```
Enter GitHub repository: username/vulnerable-repo
```

Accepts multiple formats:
- `username/repo`
- `github.com/username/repo`
- `https://github.com/username/repo`

### Step 2: The Audit

Watch as CodeJanitor:
- ✅ Clones the repository
- ✅ Builds a knowledge graph of dependencies
- ✅ Scans for vulnerabilities

You'll see a beautiful table showing:
- **ID**: Issue number for selection
- **Type**: SQL Injection, Command Injection, etc.
- **Severity**: CRITICAL, HIGH, MEDIUM, LOW
- **File**: Vulnerable file path
- **Line**: Line number
- **Risk Score**: AI-calculated risk (0-100)

### Step 3: Prioritization Strategy

Choose your approach:

**Option A - System Prioritization (Recommended)**
- AI sorts vulnerabilities by risk score
- Critical issues handled first
- Smart ordering based on exploitability

**Option B - Manual Selection**
- YOU choose which issue to tackle
- Enter the ID from the risk report table
- Perfect for targeted fixes

### Step 4: The Execution Loop

For each vulnerability, you control the action:

#### **[F]ix** - Full Automation

Watch the magic happen:

**🔴 Red Team Phase:**
```
Step 1: RECON - Analyzing vulnerability...
Step 2: PLAN - Crafting attack strategy...
Step 3: EXPLOIT - Generating proof-of-concept...
✅ Exploit confirmed: SQL injection successful!
```

**🔵 Blue Team Phase:**
```
Step 1: ANALYZE - Understanding the vulnerability...
Step 2: PATCH - Generating secure fix...
Step 3: VERIFY - Testing with Red Team's exploit...
✅ Patch verified! Exploit now fails on fixed code.
```

**🚀 Git Phase:**
```
Step 1: BRANCH - Creating security-fix-123 branch...
Step 2: COMMIT - Committing patched code...
Step 3: PUSH - Pushing to remote...
Step 4: PR - Creating pull request...
✅ Pull Request Created!
🔗 URL: https://github.com/username/repo/pull/456
```

#### **[S]kip** - Move to Next Issue

Skip this vulnerability and proceed to the next one. Useful for:
- Low-priority issues you want to handle later
- False positives you need to investigate manually
- Issues that require architectural changes

#### **[E]xit** - Stop Execution

Exit the automation loop gracefully. You'll see a summary:
- ✅ Fixed: Number of successfully patched issues
- ⏭️ Skipped: Number of skipped issues
- 📊 Total: Total issues found

## 🎨 UI Features

### Rich Tables
Beautiful, color-coded vulnerability reports with:
- Cyan IDs for easy reference
- Yellow vulnerability types
- Color-coded severity (Red=Critical, Yellow=Medium)
- Blue file paths
- Numerical risk scores

### Bordered Panels
- **Red borders**: Red Team attack phase
- **Blue borders**: Blue Team defense phase
- **Green borders**: Git operations
- **Cyan borders**: Target issue display

### Progress Indicators
- Spinners for long-running operations
- Task completion checkmarks
- Real-time status updates

### Smart Input
- Default values for quick workflows
- Input validation with helpful error messages
- Keyboard shortcuts (F/S/E)

## 🔧 Architecture

### Components Used

```python
from app.core.orchestrator import JanitorOrchestrator
from app.agents.auditor import RepositoryAuditor
from app.agents.red_team import RedTeamAgent
from app.agents.blue_team import BlueTeamAgent
from app.tools.sandbox import DockerSandbox
from app.tools.git_ops import GitOps
from app.core.knowledge import CodeKnowledgeBase
from app.core.prioritizer import IssuePrioritizer
```

### Workflow Orchestration

```
User Input → Docker Check → Clone Repo → Build Graph
     ↓
Audit Files → Display Report → Choose Strategy
     ↓
For Each Issue:
     ↓
Display Target → User Action → Execute Fix
     ↓
Red Team (Docker) → Blue Team (Docker) → Create PR
     ↓
Summary Report
```

## 🛠️ Advanced Usage

### Custom Risk Scoring

The system prioritizes vulnerabilities based on:
- **Severity**: Critical > High > Medium > Low
- **Type**: SQL Injection, Command Injection, etc.
- **Exploitability**: Can Red Team verify it?
- **Context**: Dependencies and impact radius

### Docker Health Check

The CLI automatically:
- ✅ Checks if Docker daemon is running
- ✅ Verifies codejanitor-sandbox image exists
- ✅ Offers to rebuild image if missing

### Temporary Workspace

All operations use temporary directories:
- Clones repo to temp location
- Runs operations in isolation
- Automatically cleans up on exit

## 🐛 Troubleshooting

### "Docker daemon not running"
```bash
# Start Docker Desktop (Windows/Mac)
# Or start Docker service (Linux)
sudo systemctl start docker
```

### "Sandbox image not found"
The CLI will offer to rebuild. You can also manually:
```bash
docker build -t codejanitor-sandbox -f docker/Dockerfile .
```

### "GITHUB_TOKEN not set"
```bash
# Generate token at: https://github.com/settings/tokens
# Needs: repo, workflow permissions

export GITHUB_TOKEN="ghp_your_token_here"  # Linux/Mac
$env:GITHUB_TOKEN="ghp_your_token_here"     # Windows
```

### "PR creation failed"
- Verify token has `repo` and `workflow` permissions
- Check if you have write access to the repository
- Ensure repository is not archived

## 📊 Example Session

```
╔══════════════════════════════════════════════════════════════╗
║                   CODE JANITOR 2.0                           ║
╚══════════════════════════════════════════════════════════════╝

🔍 Checking Docker Environment...
✅ Docker daemon: Running
✅ Sandbox image: Ready

📦 Repository Input
Enter GitHub repository: myorg/vulnerable-app
✅ Repository: myorg/vulnerable-app

🔍 Security Audit Phase
[################] Cloning repository...
[################] Building knowledge graph...
[################] Scanning for vulnerabilities...

✅ Found 7 potential vulnerabilities

🔐 Vulnerability Risk Report
┌────┬─────────────────┬──────────┬────────────┬──────┬────────────┐
│ ID │ Type            │ Severity │ File       │ Line │ Risk Score │
├────┼─────────────────┼──────────┼────────────┼──────┼────────────┤
│ 1  │ SQL Injection   │ CRITICAL │ login.py   │ 45   │ 95.0       │
│ 2  │ Command Inj     │ HIGH     │ exec.py    │ 23   │ 85.0       │
│ 3  │ Path Traversal  │ MEDIUM   │ files.py   │ 67   │ 60.0       │
└────┴─────────────────┴──────────┴────────────┴──────┴────────────┘

🎯 Prioritization Strategy
A - System Prioritization (AI sorts by risk)
B - Manual Selection (Choose specific issue ID)

Select strategy [A]: A

🤖 Using AI Risk Scoring...

🎯 Target Issue [1/7]
Type: SQL Injection
Severity: CRITICAL
File: login.py
Line: 45
Risk Score: 95.0

⚡ Action Menu
[F]ix - Launch Red Team → Blue Team → Create PR
[S]kip - Ignore this issue and move to next
[E]xit - Stop the entire process

Choose action [F]: F

⚔️  Red Team 🔴
Step 1: RECON - Analyzing vulnerability...
Step 2: PLAN - Crafting attack strategy...
Step 3: EXPLOIT - Generating proof-of-concept...
✅ Red Team Success!

🛡️  Blue Team 🔵
Step 1: ANALYZE - Understanding the vulnerability...
Step 2: PATCH - Generating secure fix...
Step 3: VERIFY - Testing with Red Team's exploit...
✅ Blue Team Success!

🔀 GitHub Integration 🚀
Step 1: BRANCH - Creating security-fix-1 branch...
Step 2: COMMIT - Committing patched code...
Step 3: PUSH - Pushing to remote...
Step 4: PR - Creating pull request...
✅ Pull Request Created!
🔗 URL: https://github.com/myorg/vulnerable-app/pull/42

📋 Execution Summary
✅ Fixed: 1
⏭️ Skipped: 0
📊 Total: 7

✨ CodeJanitor session complete!
```

## 🎓 Best Practices

### 1. Start with System Prioritization
Let the AI handle critical issues first. Switch to manual mode for specific targets.

### 2. Review Before Merging
Always review the generated PR before merging. The Blue Team generates secure code, but human oversight is valuable.

### 3. Use Skip Wisely
Skip issues that:
- Require architectural changes
- Need business logic understanding
- Are potential false positives

### 4. Monitor Docker Resources
The sandbox creates containers for each operation. Clean up old containers periodically:
```bash
docker system prune
```

### 5. Test in Development First
Run CodeJanitor on development branches before production repositories.

## 🔐 Security Notes

- All code execution happens in **isolated Docker containers**
- Containers have **no network access** during exploit/patch testing
- **Memory limits** prevent resource exhaustion
- **Timeouts** prevent infinite loops
- Temporary files are **automatically cleaned up**

## 🚀 What's Next?

After Phase 5, you have a complete, production-ready security automation system!

**Optional Enhancements:**
- Add webhook integration for automatic scanning on new commits
- Implement Slack/Discord notifications
- Add metrics dashboard
- Support additional languages (JavaScript, Java, Go)
- CI/CD integration for automated PR review

## 📝 License

See main project LICENSE file.

## 🙏 Acknowledgments

Built with:
- **Rich** - Beautiful terminal UI
- **Docker** - Secure sandbox execution
- **LangChain** - LLM orchestration
- **Tree-sitter** - Code parsing
- **NetworkX** - Dependency graphs
- **PyGithub** - GitHub API
- **GitPython** - Git operations

---

**CodeJanitor 2.0** - *Because security doesn't sleep* 🛡️
