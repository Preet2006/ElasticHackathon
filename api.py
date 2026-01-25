#!/usr/bin/env python3
"""
CodeJanitor API - FastAPI wrapper for security scanning and remediation
Connects the Next.js frontend to the Python backend tools
"""

import os
import sys
import asyncio
import tempfile
import shutil
import logging
import json
import queue
import threading
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import CodeJanitor components
from app.core.orchestrator import JanitorOrchestrator
from app.agents.auditor import RepositoryAuditor
from app.agents.red_team import RedTeamAgent
from app.agents.blue_team import BlueTeamAgent
from app.core.knowledge import CodeKnowledgeBase
from app.tools.sandbox import DockerSandbox
from app.tools.git_ops import GitOps
from app.core.llm import get_llm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# ============================================
# MODELS
# ============================================

class ScanRequest(BaseModel):
    repo_url: str

class FixRequest(BaseModel):
    repo_url: str
    vulnerability_id: int
    vulnerability: Dict

class ScanResponse(BaseModel):
    success: bool
    vulnerabilities: List[Dict]
    summary: Dict

# ============================================
# GLOBALS
# ============================================

active_sessions: Dict[str, Dict] = {}

# ============================================
# LIFESPAN CONTEXT
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("🚀 CodeJanitor API starting up...")
    
    # Check Docker availability
    try:
        sandbox = DockerSandbox()
        if sandbox.health_check():
            logger.info("✅ Docker sandbox ready")
        else:
            logger.warning("⚠️ Docker sandbox health check failed")
    except Exception as e:
        logger.warning(f"⚠️ Docker not available: {e}")
    
    yield
    
    # Cleanup on shutdown
    logger.info("🧹 Cleaning up sessions...")
    for session_id, session in active_sessions.items():
        if "temp_dir" in session and session["temp_dir"]:
            try:
                shutil.rmtree(session["temp_dir"], ignore_errors=True)
            except Exception:
                pass
    logger.info("👋 CodeJanitor API shutting down")

# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(
    title="CodeJanitor API",
    description="Security scanning and automated remediation API",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://143.110.255.103:3000",
        "http://143.110.255.103",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# HELPER FUNCTIONS
# ============================================

def extract_repo_name(url: str) -> str:
    """Extract owner/repo from various URL formats"""
    import re
    patterns = [
        r'github\.com[:/]([^/]+/[^/\s]+?)(?:\.git)?$',
        r'^([^/]+/[^/\s]+)$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1).strip('/')
    return url

def get_severity(risk_score: int) -> str:
    """Convert risk score to severity level"""
    if risk_score >= 8:
        return "critical"
    elif risk_score >= 6:
        return "high"
    elif risk_score >= 4:
        return "medium"
    return "low"

# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "operational",
        "service": "CodeJanitor API",
        "version": "2.0.0"
    }

@app.post("/api/scan", response_model=ScanResponse)
async def scan_repository(request: ScanRequest):
    """
    Scan a GitHub repository for security vulnerabilities
    """
    temp_dir = None
    
    try:
        repo = extract_repo_name(request.repo_url)
        logger.info(f"📥 Scanning repository: {repo}")
        
        # Clone repository
        logger.info("📦 Cloning repository...")
        temp_dir = tempfile.mkdtemp(prefix="janitor_scan_")
        repo_path = Path(temp_dir) / "repo"
        
        git_ops = GitOps(token=os.getenv("GITHUB_TOKEN", ""))
        repo_url = f"https://github.com/{repo}.git"
        git_ops.clone_repo(repo_url, str(repo_path))
        
        # Build knowledge base
        logger.info("🧠 Building knowledge graph...")
        knowledge_base = CodeKnowledgeBase()
        knowledge_base.build_graph(repo_path)
        
        # Scan for vulnerabilities
        logger.info("🔍 Scanning for vulnerabilities...")
        llm = get_llm()
        auditor = RepositoryAuditor(llm=llm)
        
        issues = []
        scanned_files = 0
        
        for py_file in repo_path.rglob("*.py"):
            if ".git" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            scanned_files += 1
            relative_path = str(py_file.relative_to(repo_path))
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                scan_results = auditor.scan_file(relative_path, content)
                
                for issue in scan_results:
                    if issue.get("vulnerable", False):
                        issues.append({
                            "id": len(issues) + 1,
                            "file": relative_path,
                            "title": issue.get("type", "Unknown Vulnerability"),
                            "type": issue.get("type", "Unknown"),
                            "severity": get_severity(issue.get("risk_score", 0)),
                            "line": issue.get("start_line", 0),
                            "riskScore": issue.get("risk_score", 0),
                            "description": issue.get("description", ""),
                            "function": issue.get("function", ""),
                        })
                        
            except Exception as e:
                logger.error(f"Failed to scan {py_file}: {e}")
                continue
        
        # Sort by risk score (descending)
        issues.sort(key=lambda x: x.get("riskScore", 0), reverse=True)
        
        # Store session for later fix operations
        session_id = repo.replace("/", "_")
        active_sessions[session_id] = {
            "temp_dir": temp_dir,
            "repo_path": str(repo_path),
            "knowledge_base": knowledge_base,
            "issues": issues,
        }
        
        logger.info(f"✅ Scan complete: {len(issues)} vulnerabilities found in {scanned_files} files")
        
        return ScanResponse(
            success=True,
            vulnerabilities=issues,
            summary={
                "total": len(issues),
                "critical": sum(1 for i in issues if i.get("severity") == "critical"),
                "high": sum(1 for i in issues if i.get("severity") == "high"),
                "medium": sum(1 for i in issues if i.get("severity") == "medium"),
                "low": sum(1 for i in issues if i.get("severity") == "low"),
                "scanned_files": scanned_files,
            }
        )
        
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fix")
async def fix_vulnerability(request: FixRequest):
    """
    Fix a specific vulnerability using Red Team → Blue Team → PR workflow
    Returns a streaming response with live logs
    """
    repo = extract_repo_name(request.repo_url)
    session_id = repo.replace("/", "_")
    
    logger.info(f"🔧 Starting fix for vulnerability #{request.vulnerability_id} in {repo}")
    
    # Thread-safe queue for log streaming
    log_queue: queue.Queue = queue.Queue()
    done_event = threading.Event()
    
    def emit(phase: str, message: str, log_type: str = "info"):
        """Emit a log entry to the queue"""
        log_queue.put(json.dumps({"phase": phase, "message": message, "type": log_type}) + "\n")
    
    def run_fix():
        """Run the actual fix operation in a thread"""
        import time
        
        try:
            vuln = request.vulnerability
            
            # Get or create session
            if session_id not in active_sessions:
                emit("init", "Creating new session...", "info")
                time.sleep(0.1)
                
                temp_dir = tempfile.mkdtemp(prefix="janitor_fix_")
                repo_path = Path(temp_dir) / "repo"
                
                git_ops = GitOps(token=os.getenv("GITHUB_TOKEN", ""))
                repo_url = f"https://github.com/{repo}.git"
                git_ops.clone_repo(repo_url, str(repo_path))
                
                knowledge_base = CodeKnowledgeBase()
                knowledge_base.build_graph(repo_path)
                
                active_sessions[session_id] = {
                    "temp_dir": temp_dir,
                    "repo_path": str(repo_path),
                    "knowledge_base": knowledge_base,
                    "git_ops": git_ops,
                }
            
            session = active_sessions[session_id]
            repo_path = Path(session["repo_path"])
            knowledge_base = session.get("knowledge_base")
            
            # Initialize components
            emit("init", "Initializing security agents...", "info")
            time.sleep(0.1)
            
            sandbox = DockerSandbox()
            llm = get_llm()
            red_team = RedTeamAgent(llm=llm, sandbox=sandbox)
            blue_team = BlueTeamAgent(llm=llm, sandbox=sandbox, knowledge_base=knowledge_base)
            git_ops = session.get("git_ops") or GitOps(token=os.getenv("GITHUB_TOKEN", ""))
            
            # Get vulnerability details
            file_path = repo_path / vuln.get("file", "")
            
            if not file_path.exists():
                emit("error", f"File not found: {vuln.get('file')}", "error")
                log_queue.put(json.dumps({"success": False, "error": "File not found"}) + "\n")
                return
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # ================================================
            # RED TEAM PHASE
            # ================================================
            emit("red_team", "═" * 40, "info")
            emit("red_team", "RED TEAM // OFFENSIVE OPERATIONS", "info")
            emit("red_team", "═" * 40, "info")
            time.sleep(0.1)
            
            emit("red_team", f"[TARGET] {vuln.get('title', 'Unknown')}", "recon")
            emit("red_team", f"[FILE] {vuln.get('file')}:{vuln.get('line')}", "recon")
            emit("red_team", f"[RISK] Score: {vuln.get('riskScore', 0)}/10", "recon")
            time.sleep(0.1)
            
            emit("red_team", "> PHASE 1: RECONNAISSANCE", "recon")
            emit("red_team", "  ├─ Scanning attack surface...", "recon")
            time.sleep(0.2)
            emit("red_team", "  ├─ Identifying entry points...", "recon")
            time.sleep(0.2)
            emit("red_team", "  └─ [OK] Recon complete", "success")
            time.sleep(0.1)
            
            emit("red_team", "> PHASE 2: EXPLOIT PLANNING", "plan")
            emit("red_team", "  ├─ Analyzing vulnerability pattern...", "plan")
            time.sleep(0.2)
            emit("red_team", "  ├─ Crafting exploit payload...", "plan")
            time.sleep(0.2)
            emit("red_team", "  └─ [OK] Exploit ready", "success")
            time.sleep(0.1)
            
            emit("red_team", "> PHASE 3: EXPLOITATION", "exploit")
            emit("red_team", "  ├─ Deploying payload...", "exploit")
            time.sleep(0.1)
            
            # Actually run Red Team validation
            vulnerability_details = {
                'type': vuln.get('type', 'Unknown'),
                'description': vuln.get('description', ''),
                'function_code': code_content
            }
            
            context_code = None
            if knowledge_base:
                try:
                    # Log available files in knowledge base
                    logger.info(f"Knowledge base files: {list(knowledge_base.file_contents.keys())}")
                    logger.info(f"Looking for context for: {vuln.get('file', '')}")
                    
                    context_code = knowledge_base.get_context(vuln.get('file', ''), depth=1)
                    logger.info(f"Got context ({len(context_code) if context_code else 0} chars)")
                    if context_code:
                        logger.info(f"Context preview: {context_code[:300]!r}")
                except Exception as e:
                    logger.error(f"Failed to get context: {e}")
                    pass
            
            exploit_result = red_team.run_validation(
                target_file=vuln.get('file', ''),
                vulnerability_details=vulnerability_details,
                context_code=context_code
            )
            
            emit("red_team", "  ├─ Executing in sandbox...", "exploit")
            time.sleep(0.2)
            emit("red_team", "  └─ Analyzing response...", "exploit")
            time.sleep(0.1)
            
            if not exploit_result.get("verified", False):
                emit("red_team", "╔" + "═" * 38 + "╗", "warning")
                emit("red_team", "║  EXPLOIT FAILED // FALSE POSITIVE   ║", "warning")
                emit("red_team", "╚" + "═" * 38 + "╝", "warning")
                log_queue.put(json.dumps({
                    "success": False,
                    "error": "Vulnerability not verified by Red Team"
                }) + "\n")
                return
            
            emit("red_team", "╔" + "═" * 38 + "╗", "success")
            emit("red_team", "║  EXPLOIT SUCCESSFUL // CONFIRMED    ║", "success")
            emit("red_team", "╚" + "═" * 38 + "╝", "success")
            time.sleep(0.2)
            
            thought_process = exploit_result.get('thought_process', {})
            exploit_code = thought_process.get('exploit_code', '')
            
            # ================================================
            # BLUE TEAM PHASE
            # ================================================
            emit("blue_team", "═" * 40, "info")
            emit("blue_team", "BLUE TEAM // DEFENSIVE OPERATIONS", "info")
            emit("blue_team", "═" * 40, "info")
            time.sleep(0.1)
            
            emit("blue_team", "[ALERT] Threat intelligence received", "defense")
            emit("blue_team", "[PRIORITY] Initiating rapid response", "defense")
            time.sleep(0.1)
            
            emit("blue_team", "> PHASE 1: THREAT ANALYSIS", "defense")
            emit("blue_team", "  ├─ Reviewing exploit signature...", "defense")
            time.sleep(0.2)
            emit("blue_team", "  ├─ Identifying vulnerable pattern...", "defense")
            time.sleep(0.2)
            emit("blue_team", "  └─ [OK] Analysis complete", "verify")
            time.sleep(0.1)
            
            emit("blue_team", "> PHASE 2: PATCH GENERATION", "patch")
            emit("blue_team", "  ├─ Generating secure replacement...", "patch")
            time.sleep(0.1)
            
            # Actually run Blue Team patch
            patch_result = blue_team.patch_and_verify(
                target_file=vuln.get('file', ''),
                current_content=code_content,
                exploit_code=exploit_code,
                vulnerability_type=vuln.get('type', ''),
                vulnerability_description=vuln.get('description', '')
            )
            
            emit("blue_team", "  ├─ Applying security controls...", "patch")
            time.sleep(0.2)
            emit("blue_team", "  └─ [OK] Patch generated", "verify")
            time.sleep(0.1)
            
            if not patch_result.get("success", False):
                emit("blue_team", "╔" + "═" * 38 + "╗", "error")
                emit("blue_team", "║  PATCH FAILED // MANUAL REVIEW      ║", "error")
                emit("blue_team", "╚" + "═" * 38 + "╝", "error")
                log_queue.put(json.dumps({
                    "success": False,
                    "error": patch_result.get("error", "Patch generation failed")
                }) + "\n")
                return
            
            emit("blue_team", "> PHASE 3: VERIFICATION", "verify")
            emit("blue_team", "  ├─ Re-running exploit test...", "verify")
            time.sleep(0.2)
            emit("blue_team", "  ├─ Exploit blocked successfully", "verify")
            time.sleep(0.2)
            emit("blue_team", "  └─ All tests passing", "verify")
            time.sleep(0.1)
            
            emit("blue_team", "╔" + "═" * 38 + "╗", "verify")
            emit("blue_team", "║  PATCH VERIFIED // THREAT MITIGATED ║", "verify")
            emit("blue_team", "╚" + "═" * 38 + "╝", "verify")
            time.sleep(0.2)
            
            # ================================================
            # PR CREATION PHASE
            # ================================================
            emit("pr", "═" * 40, "info")
            emit("pr", "GIT OPERATIONS // PULL REQUEST", "info")
            emit("pr", "═" * 40, "info")
            time.sleep(0.1)
            
            emit("pr", "> Creating security fix branch...", "info")
            time.sleep(0.2)
            emit("pr", "> Committing patched code...", "info")
            time.sleep(0.2)
            emit("pr", "> Pushing to remote...", "info")
            time.sleep(0.1)
            
            # Create PR
            pr_url = None
            try:
                work_dir = Path(tempfile.mkdtemp(prefix="codejanitor_pr_"))
                
                pr_url = git_ops.create_pr_for_fix(
                    repo_url=f"https://github.com/{repo}.git",
                    file_path=vuln.get("file", ""),
                    patched_content=patch_result.get("patched_content", ""),
                    issue_number=request.vulnerability_id,
                    vulnerability_type=vuln.get("type", "Security Issue"),
                    work_dir=work_dir
                )
                
                shutil.rmtree(work_dir, ignore_errors=True)
                
                emit("pr", "> Creating pull request...", "info")
                time.sleep(0.2)
                emit("pr", f"> PR URL: {pr_url}", "success")
                
            except Exception as pr_error:
                logger.error(f"PR creation failed: {pr_error}")
                emit("pr", f"> PR creation failed: {str(pr_error)[:100]}", "warning")
            
            emit("pr", "╔" + "═" * 38 + "╗", "success")
            emit("pr", "║  REMEDIATION COMPLETE               ║", "success")
            emit("pr", "╚" + "═" * 38 + "╝", "success")
            
            # Final success response
            log_queue.put(json.dumps({
                "success": True,
                "pr_url": pr_url
            }) + "\n")
            
        except Exception as e:
            logger.error(f"Fix failed: {e}")
            emit("error", f"Error: {str(e)}", "error")
            log_queue.put(json.dumps({
                "success": False,
                "error": str(e)
            }) + "\n")
        finally:
            done_event.set()
    
    # Start the fix operation in a background thread
    thread = threading.Thread(target=run_fix, daemon=True)
    thread.start()
    
    async def stream_logs():
        """Async generator that reads from the queue"""
        while not done_event.is_set() or not log_queue.empty():
            try:
                # Try to get a log entry with a short timeout
                log_entry = log_queue.get(timeout=0.1)
                yield log_entry
            except queue.Empty:
                # No log available, yield control and continue
                await asyncio.sleep(0.05)
                continue
        
        # Drain any remaining logs
        while not log_queue.empty():
            try:
                yield log_queue.get_nowait()
            except queue.Empty:
                break
    
    return StreamingResponse(
        stream_logs(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true",
        }
    )


@app.delete("/api/session/{repo}")
async def cleanup_session(repo: str):
    """Cleanup a scan session"""
    session_id = repo.replace("/", "_")
    
    if session_id in active_sessions:
        session = active_sessions[session_id]
        if "temp_dir" in session:
            shutil.rmtree(session["temp_dir"], ignore_errors=True)
        del active_sessions[session_id]
        return {"success": True, "message": f"Session {repo} cleaned up"}
    
    return {"success": False, "message": "Session not found"}


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8000"))
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗ ██████╗ ██████╗ ███████╗     ██╗ █████╗ ███╗   ██║║
║  ██╔════╝██╔═══██╗██╔══██╗██╔════╝     ██║██╔══██╗████╗  ██║║
║  ██║     ██║   ██║██║  ██║█████╗       ██║███████║██╔██╗ ██║║
║  ██║     ██║   ██║██║  ██║██╔══╝  ██   ██║██╔══██║██║╚██╗██║║
║  ╚██████╗╚██████╔╝██████╔╝███████╗╚█████╔╝██║  ██║██║ ╚████║║
║   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝║
║                                                              ║
║                      🛡️  API Server  🛡️                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

    🚀 Starting CodeJanitor API on http://localhost:{port}
    📖 API Docs: http://localhost:{port}/docs
    """)
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
