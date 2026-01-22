# 🚀 Quick Start Guide - CodeJanitor Interactive Demo

## One-Minute Setup

```bash
# 1. Start Docker
docker --version  # Verify it's running

# 2. Set GitHub Token
export GITHUB_TOKEN="ghp_your_token"  # Linux/Mac
$env:GITHUB_TOKEN="ghp_your_token"    # Windows

# 3. Run
python demo_interactive.py
```

## Commands Cheat Sheet

| Action | Key | Description |
|--------|-----|-------------|
| **Fix** | F | Run Red Team → Blue Team → Create PR |
| **Skip** | S | Move to next vulnerability |
| **Exit** | E | Stop and show summary |

## Input Formats

```
✅ username/repo
✅ github.com/username/repo
✅ https://github.com/username/repo
```

## Prioritization Modes

| Mode | Key | Use Case |
|------|-----|----------|
| **System** | A | Let AI sort by risk (Recommended) |
| **Manual** | B | Pick specific issue ID |

## What You'll See

### 1️⃣ Risk Report Table
```
┌────┬─────────────────┬──────────┬────────────┬──────┬────────────┐
│ ID │ Type            │ Severity │ File       │ Line │ Risk Score │
├────┼─────────────────┼──────────┼────────────┼──────┼────────────┤
│ 1  │ SQL Injection   │ CRITICAL │ login.py   │ 45   │ 95.0       │
└────┴─────────────────┴──────────┴────────────┴──────┴────────────┘
```

### 2️⃣ Red Team (Attack) 🔴
```
Step 1: RECON - Analyzing vulnerability...
Step 2: PLAN - Crafting attack strategy...
Step 3: EXPLOIT - Generating proof-of-concept...
✅ Exploit confirmed!
```

### 3️⃣ Blue Team (Defense) 🔵
```
Step 1: ANALYZE - Understanding the vulnerability...
Step 2: PATCH - Generating secure fix...
Step 3: VERIFY - Testing with exploit...
✅ Patch verified!
```

### 4️⃣ GitHub PR 🚀
```
Step 1: BRANCH - Creating branch...
Step 2: COMMIT - Committing fix...
Step 3: PUSH - Pushing to remote...
Step 4: PR - Creating pull request...
✅ PR Created: https://github.com/...
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not running | Start Docker Desktop |
| Image not found | CLI will offer rebuild |
| No GITHUB_TOKEN | `export GITHUB_TOKEN="..."` |
| PR creation fails | Check token permissions |

## Test Repositories

Create a test repo with vulnerable code:

**login.py** (SQL Injection):
```python
def login(username, password, conn):
    query = f"SELECT * FROM users WHERE username='{username}'"
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchone()
```

**exec.py** (Command Injection):
```python
def run_command(user_input):
    import os
    return os.system(user_input)
```

**file_handler.py** (Path Traversal):
```python
def read_file(filename):
    with open(f"/app/files/{filename}", "r") as f:
        return f.read()
```

## Flow Diagram

```
Repository Input
      ↓
   Audit
      ↓
Risk Report Table
      ↓
Choose: System (A) or Manual (B)
      ↓
For Each Issue:
  ├── Display Target
  ├── Menu: [F]ix / [S]kip / [E]xit
  └── If Fix:
        ├── 🔴 Red Team (Exploit)
        ├── 🔵 Blue Team (Patch)
        └── 🚀 Create PR
      ↓
Execution Summary
```

## Example Session (30 seconds)

```bash
$ python demo_interactive.py

# Input
Enter repository: myorg/test-app

# Wait for audit
Scanning... ✓

# View report (7 issues found)
Choose strategy: A (System)

# Issue 1: SQL Injection
[F]ix / [S]kip / [E]xit: F

# Watch automation
🔴 Red Team... ✅
🔵 Blue Team... ✅
🚀 PR Created: https://...

# Issue 2: Command Injection
[F]ix / [S]kip / [E]xit: F

# Repeat...
```

## Tips

💡 **Start with System Mode** - Let AI prioritize critical issues first

💡 **Review PRs** - Always review before merging (trust but verify)

💡 **Use Skip** - For false positives or architectural changes

💡 **Monitor Docker** - Run `docker system prune` periodically

💡 **Dev First** - Test on development branches before production

## Quick Test

```bash
# Verify installation
python test_demo.py

# Should see:
✅ All imports successful!
✅ InteractiveCockpit instantiated!
✅ Banner display works!
```

## What Gets Created

For each fixed issue:
- ✅ New branch: `security-fix-{issue_number}`
- ✅ Commit: Patched code with secure implementation
- ✅ Pull Request: "🔒 Security Fix: {type} (Issue #{number})"
- ✅ PR Body: Verification status + "Fixes #{number}"

## System Requirements

- ✅ Python 3.10+
- ✅ Docker installed and running
- ✅ GitHub token with `repo` permissions
- ✅ 4GB RAM (for Docker containers)
- ✅ Internet connection (for repo cloning and LLM)

---

**Need help?** See [DEMO_GUIDE.md](DEMO_GUIDE.md) for full documentation.

**CodeJanitor 2.0** - Red Team 🔴 → Blue Team 🔵 → Pull Request 🚀
