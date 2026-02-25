#!/usr/bin/env python3
"""
CodeJanitor 2.0 API – Elasticsearch Agent Builder Hackathon Edition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Cloud-hosted FastAPI toolset for AI-powered security scanning,
exploit verification, and automated patching.

LLM provider : Groq  (llama-3.3-70b-versatile)
Knowledge store: Elasticsearch Cloud (code-knowledge index)

Endpoints
---------
POST /scan            – Clone repo, index into ES, scan for vulns
POST /verify-exploit  – Red Team sandbox exploit verification
POST /apply-patch     – Blue Team patch + PR automation
GET  /findings/{sid}  – List stored findings for a session
DELETE /session/{sid}  – Cleanup temp files for a session
GET  /                – Health check
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import shutil
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel, Field

load_dotenv()

# ── CodeJanitor imports ──────────────────────────────────────────────────────
from app.agents.auditor import RepositoryAuditor
from app.agents.blue_team import BlueTeamAgent
from app.agents.red_team import RedTeamAgent
from app.core.config import get_settings
from app.core.knowledge import ElasticKnowledgeBase
from app.core.llm import get_llm
from app.tools.git_ops import GitOps
from app.tools.sandbox import DockerSandbox

# ── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ScanRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repo URL or owner/repo shorthand")

class VerifyExploitRequest(BaseModel):
    session_id: str = Field(..., description="Session ID returned by /scan")
    finding_id: int  = Field(..., description="Finding ID to verify (1-based)")

class ApplyPatchRequest(BaseModel):
    session_id: str = Field(..., description="Session ID returned by /scan")
    finding_id: int  = Field(..., description="Finding ID to patch (1-based)")

class FindingItem(BaseModel):
    id: int
    file: str
    title: str
    type: str
    severity: str
    line: int
    riskScore: int
    description: str
    function: str

class ScanResponse(BaseModel):
    success: bool
    session_id: str
    vulnerabilities: List[Dict[str, Any]]
    summary: Dict[str, Any]

class VerifyExploitResponse(BaseModel):
    success: bool
    finding_id: int
    verified: bool
    thought_process: Dict[str, Any] = {}
    output: str = ""
    attempts: int = 0
    error: str = ""

class ApplyPatchResponse(BaseModel):
    success: bool
    finding_id: int
    patched: bool = False
    patch_verified: bool = False
    pr_url: Optional[str] = None
    error: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY SESSION STORE
# ═══════════════════════════════════════════════════════════════════════════════

active_sessions: Dict[str, Dict] = {}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

_SEVERITY_MAP = [(8, "critical"), (6, "high"), (4, "medium")]

def _severity(risk: int) -> str:
    for threshold, label in _SEVERITY_MAP:
        if risk >= threshold:
            return label
    return "low"


def _extract_repo(url: str) -> str:
    """Normalise GitHub URL → ``owner/repo``."""
    import re
    for pat in [
        r"github\.com[:/]([^/]+/[^/\s]+?)(?:\.git)?$",
        r"^([^/]+/[^/\s]+)$",
    ]:
        m = re.search(pat, url)
        if m:
            return m.group(1).strip("/")
    return url


def _get_session(session_id: str) -> Dict:
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found. Run /scan first.",
        )
    return active_sessions[session_id]


def _get_finding(session: Dict, finding_id: int) -> Dict:
    for f in session.get("findings", []):
        if f["id"] == finding_id:
            return f
    raise HTTPException(
        status_code=404,
        detail=f"Finding #{finding_id} not found in this session.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# LIFESPAN
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("CodeJanitor API starting  (model=%s)", settings.llm_model)

    # Quick Docker check
    try:
        if DockerSandbox().health_check():
            logger.info("Docker sandbox ready")
        else:
            logger.warning("Docker sandbox health-check failed")
    except Exception as exc:
        logger.warning("Docker not available: %s", exc)

    yield

    # Cleanup
    logger.info("Shutting down – cleaning sessions...")
    for sid, sess in active_sessions.items():
        td = sess.get("temp_dir")
        if td:
            shutil.rmtree(td, ignore_errors=True)
    logger.info("Goodbye")


# ═══════════════════════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="CodeJanitor API",
    description="Elasticsearch-backed AI security toolset (Groq + llama-3.3-70b)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # wide-open for hackathon demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

# ── health ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Health check."""
    settings = get_settings()
    return {
        "status": "operational",
        "service": "CodeJanitor API",
        "version": "2.0.0",
        "llm_model": settings.llm_model,
        "es_connected": bool(settings.es_cloud_id),
    }


# ── POST /scan ───────────────────────────────────────────────────────────────

@app.post("/scan", response_model=ScanResponse)
async def scan_repository(request: ScanRequest):
    """
    Clone a GitHub repository, index every Python file into the
    ``code-knowledge`` Elasticsearch index, then run the Auditor agent
    (Groq / llama-3.3-70b) to detect security vulnerabilities.

    Returns a **session_id** that must be passed to ``/verify-exploit``
    and ``/apply-patch``.
    """
    temp_dir = None
    try:
        repo = _extract_repo(request.repo_url)
        session_id = repo.replace("/", "_")
        logger.info("POST /scan – repo=%s  session=%s", repo, session_id)

        # 1. Clone
        temp_dir = tempfile.mkdtemp(prefix="janitor_")
        repo_path = Path(temp_dir) / "repo"
        settings = get_settings()
        git_ops = GitOps(token=settings.github_token)
        git_ops.clone_repo(f"https://github.com/{repo}.git", str(repo_path))

        # 2. Index into Elasticsearch
        logger.info("Indexing into Elasticsearch…")
        kb = ElasticKnowledgeBase(project_name=repo)
        kb.build_graph(repo_path, project_name=repo)
        stats = kb.get_graph_stats()
        logger.info("Indexed %d files, %d import edges", stats["total_files"], stats["total_imports"])

        # 3. Audit with Groq LLM
        logger.info("Scanning with Groq (model=%s)…", settings.llm_model)
        llm = get_llm()
        auditor = RepositoryAuditor(llm=llm)

        findings: List[Dict] = []
        scanned = 0

        for py_file in repo_path.rglob("*.py"):
            rel = str(py_file.relative_to(repo_path))
            if ".git" in rel or "__pycache__" in rel:
                continue
            scanned += 1
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                for issue in auditor.scan_file(rel, content):
                    if issue.get("vulnerable"):
                        findings.append({
                            "id": len(findings) + 1,
                            "file": rel,
                            "title": issue.get("type", "Unknown"),
                            "type": issue.get("type", "Unknown"),
                            "severity": _severity(issue.get("risk_score", 0)),
                            "line": issue.get("start_line", 0),
                            "riskScore": issue.get("risk_score", 0),
                            "description": issue.get("description", ""),
                            "function": issue.get("function", ""),
                        })
            except Exception as exc:
                logger.error("Failed to scan %s: %s", py_file, exc)

        findings.sort(key=lambda x: x.get("riskScore", 0), reverse=True)

        # 4. Store session
        active_sessions[session_id] = {
            "temp_dir": temp_dir,
            "repo_path": str(repo_path),
            "repo": repo,
            "knowledge_base": kb,
            "findings": findings,
            "git_ops": git_ops,
        }

        logger.info("Scan complete: %d vulns in %d files", len(findings), scanned)

        return ScanResponse(
            success=True,
            session_id=session_id,
            vulnerabilities=findings,
            summary={
                "total": len(findings),
                "critical": sum(1 for f in findings if f["severity"] == "critical"),
                "high":     sum(1 for f in findings if f["severity"] == "high"),
                "medium":   sum(1 for f in findings if f["severity"] == "medium"),
                "low":      sum(1 for f in findings if f["severity"] == "low"),
                "scanned_files": scanned,
                "es_stats": stats,
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Scan failed: %s", exc)
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ── POST /verify-exploit ─────────────────────────────────────────────────────

@app.post("/verify-exploit", response_model=VerifyExploitResponse)
async def verify_exploit(request: VerifyExploitRequest):
    """
    Retrieve code context from Elasticsearch and call **RedTeamAgent**
    to generate + execute a sandbox exploit against the finding.

    Uses Groq (llama-3.3-70b) for exploit generation and Docker for
    sandboxed execution.
    """
    session = _get_session(request.session_id)
    finding = _get_finding(session, request.finding_id)
    repo_path = Path(session["repo_path"])
    kb: ElasticKnowledgeBase = session["knowledge_base"]

    logger.info(
        "POST /verify-exploit – session=%s finding=#%d (%s)",
        request.session_id, request.finding_id, finding["type"],
    )

    try:
        # Read file
        target = repo_path / finding["file"]
        if not target.exists():
            return VerifyExploitResponse(
                success=False, finding_id=request.finding_id,
                verified=False, error=f"File not found: {finding['file']}",
            )
        code = target.read_text(encoding="utf-8", errors="ignore")

        # ES context
        context = kb.get_context(finding["file"], depth=1) or code

        # Red Team
        llm = get_llm()
        red = RedTeamAgent(llm=llm, sandbox=DockerSandbox())
        result = red.run_validation(
            target_file=finding["file"],
            vulnerability_details={
                "type": finding["type"],
                "description": finding["description"],
                "function_code": code,
            },
            context_code=context,
        )

        return VerifyExploitResponse(
            success=True,
            finding_id=request.finding_id,
            verified=result.get("verified", False),
            thought_process=result.get("thought_process", {}),
            output=result.get("output", ""),
            attempts=result.get("attempts", 0),
        )

    except Exception as exc:
        logger.error("Exploit verification failed: %s", exc)
        return VerifyExploitResponse(
            success=False, finding_id=request.finding_id,
            verified=False, error=str(exc),
        )


# ── POST /apply-patch ────────────────────────────────────────────────────────

@app.post("/apply-patch", response_model=ApplyPatchResponse)
async def apply_patch(request: ApplyPatchRequest):
    """
    Call **BlueTeamAgent** (Groq) to generate a security patch, verify it
    against the Red Team exploit in a Docker sandbox, then open a Pull
    Request via ``git_ops.py``.
    """
    session = _get_session(request.session_id)
    finding = _get_finding(session, request.finding_id)
    repo_path = Path(session["repo_path"])
    repo = session["repo"]
    kb: ElasticKnowledgeBase = session["knowledge_base"]
    git_ops: GitOps = session.get("git_ops") or GitOps(token=get_settings().github_token)

    logger.info(
        "POST /apply-patch – session=%s finding=#%d (%s)",
        request.session_id, request.finding_id, finding["type"],
    )

    try:
        target = repo_path / finding["file"]
        if not target.exists():
            return ApplyPatchResponse(
                success=False, finding_id=request.finding_id,
                error=f"File not found: {finding['file']}",
            )
        code = target.read_text(encoding="utf-8", errors="ignore")

        # ── Step 1: Red Team exploit (needed by Blue Team for TDR) ────────
        llm = get_llm()
        sandbox = DockerSandbox()
        red = RedTeamAgent(llm=llm, sandbox=sandbox)
        context = kb.get_context(finding["file"], depth=1) or code

        exploit_result = red.run_validation(
            target_file=finding["file"],
            vulnerability_details={
                "type": finding["type"],
                "description": finding["description"],
                "function_code": code,
            },
            context_code=context,
        )

        if not exploit_result.get("verified"):
            return ApplyPatchResponse(
                success=False, finding_id=request.finding_id,
                error="Red Team could not verify vulnerability – may be a false positive.",
            )

        exploit_code = exploit_result.get("thought_process", {}).get("exploit_code", "")

        # ── Step 2: Blue Team patch + sandbox verification ────────────────
        blue = BlueTeamAgent(llm=llm, sandbox=sandbox, knowledge_base=kb)
        patch_result = blue.patch_and_verify(
            target_file=finding["file"],
            current_content=code,
            exploit_code=exploit_code,
            vulnerability_type=finding["type"],
            vulnerability_description=finding["description"],
        )

        if not patch_result.get("success"):
            return ApplyPatchResponse(
                success=False, finding_id=request.finding_id,
                error=patch_result.get("error", "Patch generation/verification failed"),
            )

        # ── Step 3: PR via git_ops ────────────────────────────────────────
        pr_url = None
        try:
            work_dir = Path(tempfile.mkdtemp(prefix="janitor_pr_"))
            pr_url = git_ops.create_pr_for_fix(
                repo_url=f"https://github.com/{repo}.git",
                file_path=finding["file"],
                patched_content=patch_result["patched_content"],
                issue_number=request.finding_id,
                vulnerability_type=finding["type"],
                work_dir=work_dir,
            )
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception as pr_exc:
            logger.error("PR creation failed: %s", pr_exc)

        return ApplyPatchResponse(
            success=True,
            finding_id=request.finding_id,
            patched=True,
            patch_verified=True,
            pr_url=pr_url,
        )

    except Exception as exc:
        logger.error("apply-patch failed: %s", exc)
        return ApplyPatchResponse(
            success=False, finding_id=request.finding_id, error=str(exc),
        )


# ── GET /findings/{session_id} ───────────────────────────────────────────────

@app.get("/findings/{session_id}")
async def get_findings(session_id: str):
    """Return findings stored in a scan session."""
    session = _get_session(session_id)
    return {"session_id": session_id, "findings": session.get("findings", [])}


# ── DELETE /session/{session_id} ─────────────────────────────────────────────

@app.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """Cleanup temp files for a session."""
    if session_id in active_sessions:
        sess = active_sessions.pop(session_id)
        td = sess.get("temp_dir")
        if td:
            shutil.rmtree(td, ignore_errors=True)
        return {"success": True, "message": f"Session {session_id} cleaned up"}
    return {"success": False, "message": "Session not found"}


# ══════════════════════════════════════════════════════════════════════════════
# LEGACY COMPAT ENDPOINTS (frontend still uses /api/scan, /api/fix)
# ══════════════════════════════════════════════════════════════════════════════

class LegacyScanRequest(BaseModel):
    repo_url: str

class LegacyFixRequest(BaseModel):
    repo_url: str
    vulnerability_id: int
    vulnerability: Dict

@app.post("/api/scan")
async def legacy_scan(request: LegacyScanRequest):
    """Legacy frontend-compatible scan (delegates to /scan)."""
    result = await scan_repository(ScanRequest(repo_url=request.repo_url))
    return result

@app.post("/api/fix")
async def legacy_fix(request: LegacyFixRequest):
    """Legacy frontend-compatible fix (streaming NDJSON)."""
    repo = _extract_repo(request.repo_url)
    session_id = repo.replace("/", "_")

    log_queue: queue.Queue = queue.Queue()
    done_event = threading.Event()

    def emit(phase: str, message: str, log_type: str = "info"):
        log_queue.put(json.dumps({"phase": phase, "message": message, "type": log_type}) + "\n")

    def _run():
        try:
            vuln = request.vulnerability
            settings = get_settings()

            # ensure session
            if session_id not in active_sessions:
                emit("init", "Creating session…")
                td = tempfile.mkdtemp(prefix="janitor_fix_")
                rp = Path(td) / "repo"
                go = GitOps(token=settings.github_token)
                go.clone_repo(f"https://github.com/{repo}.git", str(rp))
                kb = ElasticKnowledgeBase(project_name=repo)
                kb.build_graph(rp, project_name=repo)
                active_sessions[session_id] = {
                    "temp_dir": td, "repo_path": str(rp), "repo": repo,
                    "knowledge_base": kb, "findings": [], "git_ops": go,
                }

            sess = active_sessions[session_id]
            rp = Path(sess["repo_path"])
            kb = sess["knowledge_base"]

            emit("init", "Initializing agents…")
            sandbox = DockerSandbox()
            llm = get_llm()
            red = RedTeamAgent(llm=llm, sandbox=sandbox)
            blue = BlueTeamAgent(llm=llm, sandbox=sandbox, knowledge_base=kb)
            go = sess.get("git_ops") or GitOps(token=settings.github_token)

            fp = rp / vuln.get("file", "")
            if not fp.exists():
                emit("error", f"File not found: {vuln.get('file')}", "error")
                log_queue.put(json.dumps({"success": False, "error": "File not found"}) + "\n")
                return

            code = fp.read_text(encoding="utf-8", errors="ignore")
            context = kb.get_context(vuln.get("file", ""), depth=1) or code

            # Red Team
            emit("red_team", "RED TEAM // EXPLOITATION")
            result = red.run_validation(
                target_file=vuln.get("file", ""),
                vulnerability_details={"type": vuln.get("type", ""), "description": vuln.get("description", ""), "function_code": code},
                context_code=context,
            )
            if not result.get("verified"):
                emit("red_team", "Exploit failed – false positive", "warning")
                log_queue.put(json.dumps({"success": False, "error": "Not verified"}) + "\n")
                return
            emit("red_team", "Exploit CONFIRMED", "success")
            exploit_code = result.get("thought_process", {}).get("exploit_code", "")

            # Blue Team
            emit("blue_team", "BLUE TEAM // PATCHING")
            patch = blue.patch_and_verify(
                target_file=vuln.get("file", ""), current_content=code,
                exploit_code=exploit_code, vulnerability_type=vuln.get("type", ""),
                vulnerability_description=vuln.get("description", ""),
            )
            if not patch.get("success"):
                emit("blue_team", "Patch FAILED", "error")
                log_queue.put(json.dumps({"success": False, "error": patch.get("error", "Patch failed")}) + "\n")
                return
            emit("blue_team", "Patch VERIFIED", "success")

            # PR
            emit("pr", "Creating Pull Request…")
            pr_url = None
            try:
                wd = Path(tempfile.mkdtemp(prefix="janitor_pr_"))
                pr_url = go.create_pr_for_fix(
                    repo_url=f"https://github.com/{repo}.git", file_path=vuln.get("file", ""),
                    patched_content=patch["patched_content"], issue_number=request.vulnerability_id,
                    vulnerability_type=vuln.get("type", ""), work_dir=wd,
                )
                shutil.rmtree(wd, ignore_errors=True)
                emit("pr", f"PR: {pr_url}", "success")
            except Exception as e:
                emit("pr", f"PR failed: {e}", "error")

            log_queue.put(json.dumps({"success": True, "pr_url": pr_url}) + "\n")

        except Exception as e:
            emit("error", str(e), "error")
            log_queue.put(json.dumps({"success": False, "error": str(e)}) + "\n")
        finally:
            done_event.set()

    threading.Thread(target=_run, daemon=True).start()

    async def _stream():
        while not done_event.is_set() or not log_queue.empty():
            try:
                yield log_queue.get(timeout=0.1)
            except queue.Empty:
                await asyncio.sleep(0.05)
        while not log_queue.empty():
            try:
                yield log_queue.get_nowait()
            except queue.Empty:
                break

    return StreamingResponse(
        _stream(), media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MCP (Model Context Protocol) – Elastic Agent Builder integration
# ═══════════════════════════════════════════════════════════════════════════════

mcp = FastApiMCP(
    app,
    name="CodeJanitor",
    description="AI-powered security scanner with Red Team exploit verification and Blue Team automated patching. Backed by Elasticsearch and Groq LLM.",
)
mcp.mount()  # creates /mcp endpoint


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    print(f"\n  CodeJanitor API – http://localhost:{port}")
    print(f"  Docs:  http://localhost:{port}/docs\n")
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True, log_level="info")
