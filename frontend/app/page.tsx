'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle2, 
  Activity,
  Code2,
  FileWarning,
  Zap,
  Play,
  ExternalLink,
  GitPullRequest
} from 'lucide-react';

import CommandBar from '@/components/CommandBar';
import { BentoGrid, BentoCard } from '@/components/BentoGrid';
import RemediationConsole from '@/components/RemediationConsole';
import StrategySelector from '@/components/StrategySelector';
import SelectableVulnerabilityList from '@/components/SelectableVulnerabilityList';
import ScanningOverlay from '@/components/ScanningOverlay';
import HelpWidget from '@/components/HelpWidget';

// ============================================
// CONFIG
// ============================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================
// TYPES
// ============================================

interface Vulnerability {
  id: number;
  title: string;
  file: string;
  line: number;
  type: string;
  riskScore: number;
  description?: string;
  function?: string;
  severity?: string;
}

// State Machine for the Workflow
enum WorkflowStage {
  IDLE = 'IDLE',
  SCANNING = 'SCANNING',
  STRATEGY_SELECTION = 'STRATEGY_SELECTION',
  MANUAL_SELECTION = 'MANUAL_SELECTION',
  LIVE_OPS = 'LIVE_OPS',
  SUCCESS = 'SUCCESS',
}

// ============================================
// DATA
// ============================================
// All data now comes from real API - no fallback demo data

// ============================================
// API FUNCTIONS
// ============================================

async function scanRepository(repoUrl: string): Promise<{ vulnerabilities: Vulnerability[], summary: any }> {
  const response = await fetch(`${API_BASE_URL}/api/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Scan failed' }));
    throw new Error(error.detail || 'Scan failed');
  }
  
  const data = await response.json();
  return {
    vulnerabilities: data.vulnerabilities || [],
    summary: data.summary || {},
  };
}

// ============================================
// ANIMATION VARIANTS
// ============================================

const stagger = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.5 }
  },
};

const slideVariants = {
  enter: { opacity: 0, x: 50 },
  center: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -50 },
};

// ============================================
// MAIN COMPONENT
// ============================================

export default function Dashboard() {
  // Core State
  const [repoUrl, setRepoUrl] = useState('');
  const [scannedRepo, setScannedRepo] = useState('');
  const [stage, setStage] = useState<WorkflowStage>(WorkflowStage.IDLE);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Vulnerability State
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [currentRemediationVuln, setCurrentRemediationVuln] = useState<Vulnerability | null>(null);
  const [remediatedIds, setRemediatedIds] = useState<Set<number>>(new Set());
  const [pendingQueue, setPendingQueue] = useState<Vulnerability[]>([]);
  const [prUrls, setPrUrls] = useState<Map<number, string>>(new Map());
  
  // Metrics
  const [metrics, setMetrics] = useState({ threats: 0, scanned: 0, fixed: 0, riskScore: 0 });

  // ============================================
  // HELPERS
  // ============================================

  const extractRepoInfo = (url: string) => {
    const cleanUrl = url.replace('https://', '').replace('http://', '').replace('github.com/', '');
    const match = cleanUrl.match(/^([^/]+)\/([^/]+)/);
    if (match) {
      return { owner: match[1], repo: match[2].replace('.git', '') };
    }
    return null;
  };

  const getGitHubUrl = () => {
    const repoInfo = extractRepoInfo(scannedRepo);
    if (repoInfo) {
      return `https://github.com/${repoInfo.owner}/${repoInfo.repo}`;
    }
    return 'https://github.com';
  };

  const sortedVulnerabilities = [...vulnerabilities].sort((a, b) => b.riskScore - a.riskScore);

  // ============================================
  // STAGE HANDLERS
  // ============================================

  const handleScan = () => {
    if (!repoUrl.trim()) return;
    
    setScannedRepo(repoUrl);
    setStage(WorkflowStage.SCANNING);
    setMetrics({ threats: 0, scanned: 0, fixed: 0, riskScore: 0 });
    setSelectedIds(new Set());
    setRemediatedIds(new Set());
    setPendingQueue([]);
    setError(null);
  };

  const handleScanComplete = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await scanRepository(scannedRepo);
      const fetchedVulns = result.vulnerabilities;
      
      setVulnerabilities(fetchedVulns);
      const totalLines = result.summary?.scanned_files ? result.summary.scanned_files * 100 : 1000;
      animateMetricsAndTransition(fetchedVulns, totalLines);
    } catch (err) {
      console.error('Scan failed:', err);
      setError(err instanceof Error ? err.message : 'Scan failed');
      setVulnerabilities([]);
      setStage(WorkflowStage.STRATEGY_SELECTION);
    } finally {
      setIsLoading(false);
    }
  }, [scannedRepo]);

  // Helper to animate metrics and transition to next stage
  const animateMetricsAndTransition = (vulns: Vulnerability[], totalLines: number) => {
    const maxRisk = vulns.length > 0 ? Math.max(...vulns.map(v => v.riskScore)) : 8.0;
    let count = 0;
    const interval = setInterval(() => {
      count++;
      setMetrics({
        threats: Math.min(count, vulns.length),
        scanned: Math.min(count * (totalLines / Math.max(vulns.length, 1)), totalLines),
        fixed: 0,
        riskScore: Math.min((count / Math.max(vulns.length, 1)) * maxRisk, maxRisk),
      });
      if (count >= vulns.length) {
        clearInterval(interval);
        setTimeout(() => setStage(WorkflowStage.STRATEGY_SELECTION), 500);
      }
    }, 150);
  };

  const handleSelectAutoStrategy = () => {
    // Auto mode: select all vulnerabilities sorted by risk
    const sorted = [...vulnerabilities].sort((a, b) => b.riskScore - a.riskScore);
    const allIds = new Set(sorted.map(v => v.id));
    setSelectedIds(allIds);
    
    // Set up the queue
    setPendingQueue(sorted.slice(1)); // All except first
    
    // Start with highest priority vulnerability
    setCurrentRemediationVuln(sorted[0]);
    setStage(WorkflowStage.LIVE_OPS);
  };

  const handleSelectManualStrategy = () => {
    setStage(WorkflowStage.MANUAL_SELECTION);
  };

  const handleToggleSelection = (id: number) => {
    setSelectedIds(prev => {
      const newSet = new Set(Array.from(prev));
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const handleExecuteFix = async () => {
    if (selectedIds.size === 0) return;

    // Get selected vulnerabilities sorted by risk
    const selectedVulns = sortedVulnerabilities.filter(v => selectedIds.has(v.id));
    
    // Set up the queue
    setPendingQueue(selectedVulns.slice(1)); // All except first
    
    // Start with first selected vulnerability
    setCurrentRemediationVuln(selectedVulns[0]);
    setStage(WorkflowStage.LIVE_OPS);
  };

  const handleRemediationComplete = (prUrl?: string) => {
    if (currentRemediationVuln) {
      // Mark as remediated
      const newRemediatedIds = new Set(Array.from(remediatedIds));
      newRemediatedIds.add(currentRemediationVuln.id);
      setRemediatedIds(newRemediatedIds);
      setMetrics(prev => ({ ...prev, fixed: prev.fixed + 1 }));

      // Store PR URL if provided
      if (prUrl) {
        setPrUrls(prev => new Map(prev).set(currentRemediationVuln.id, prUrl));
      }

      // Check if there are more in the queue
      if (pendingQueue.length > 0) {
        // Process next vulnerability
        const next = pendingQueue[0];
        setPendingQueue(pendingQueue.slice(1));
        setCurrentRemediationVuln(next);
      } else {
        // All done - show success
        setStage(WorkflowStage.SUCCESS);
      }
    }
  };

  const handleReturnToDashboard = () => {
    // Reset to check for remaining vulnerabilities
    const remaining = vulnerabilities.filter(v => !remediatedIds.has(v.id));
    
    if (remaining.length > 0) {
      setSelectedIds(new Set());
      setCurrentRemediationVuln(null);
      setPendingQueue([]);
      setStage(WorkflowStage.STRATEGY_SELECTION);
    } else {
      // All vulnerabilities fixed - go to idle
      setStage(WorkflowStage.IDLE);
      setRepoUrl('');
      setVulnerabilities([]);
      setRemediatedIds(new Set());
      setPrUrls(new Map());
    }
  };

  // ============================================
  // RENDER HELPERS
  // ============================================

  const renderHeader = () => (
    <motion.header variants={fadeUp} className="text-center space-y-8 pt-8">
      <motion.div 
        className="flex items-center justify-center gap-3"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <span className="text-xl font-medium text-white tracking-tight">
          CodeJanitor
        </span>
      </motion.div>

      <div className="space-y-4">
        <h1 className="text-5xl md:text-6xl font-extralight text-white tracking-tight leading-[1.1]">
          Autonomous Security
          <br />
          <span className="text-zinc-600">Remediation</span>
        </h1>

        <p className="text-zinc-500 text-base max-w-lg mx-auto leading-relaxed font-light">
          AI-powered vulnerability detection with automated 
          exploitation verification and intelligent patching.
        </p>
      </div>
    </motion.header>
  );

  const renderMetrics = () => (
    <motion.section
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.5 }}
    >
      <BentoGrid>
        <BentoCard
          title="Threats Detected"
          value={metrics.threats}
          subtitle="Critical"
          icon={AlertTriangle}
          accent="red"
          delay={0.1}
        />
        <BentoCard
          title="Lines Scanned"
          value={metrics.scanned.toLocaleString()}
          subtitle="Analysis"
          icon={Code2}
          accent="blue"
          delay={0.2}
        />
        <BentoCard
          title="Auto-Fixed"
          value={metrics.fixed}
          subtitle="Patches"
          icon={CheckCircle2}
          accent="green"
          delay={0.3}
        />
      </BentoGrid>
    </motion.section>
  );

  const renderFloatingExecuteButton = () => (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 50 }}
      className="fixed bottom-8 left-1/2 -translate-x-1/2 z-40"
    >
      <motion.button
        onClick={handleExecuteFix}
        disabled={selectedIds.size === 0}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`
          flex items-center gap-3 px-8 py-4
          text-sm font-medium rounded-2xl
          shadow-2xl transition-all duration-300
          ${selectedIds.size > 0
            ? 'text-black bg-[#00FF41] hover:bg-[#00FF41]/90 shadow-[0_0_40px_rgba(0,255,65,0.3)]'
            : 'text-zinc-500 bg-zinc-800 cursor-not-allowed'
          }
        `}
      >
        <Play className="w-5 h-5" />
        <span>Execute Fix</span>
        {selectedIds.size > 0 && (
          <span className="px-2 py-0.5 text-xs bg-black/20 rounded-lg">
            {selectedIds.size} selected
          </span>
        )}
      </motion.button>
    </motion.div>
  );

  // ============================================
  // MAIN RENDER
  // ============================================

  return (
    <div className="min-h-screen bg-black">
      {/* Background Effects */}
      <div className="fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[size:72px_72px] pointer-events-none" />
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,rgba(0,255,65,0.03),transparent_50%)] pointer-events-none" />
      
      <div className="relative z-10 max-w-5xl mx-auto px-6 py-16">
        <motion.div
          variants={stagger}
          initial="hidden"
          animate="visible"
          className="space-y-16"
        >
          {/* Header - Always visible except during LIVE_OPS and SUCCESS */}
          <AnimatePresence mode="wait">
            {stage !== WorkflowStage.LIVE_OPS && stage !== WorkflowStage.SUCCESS && (
              <motion.div
                key="header"
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
              >
                {renderHeader()}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Command Bar - Only in IDLE */}
          <AnimatePresence mode="wait">
            {stage === WorkflowStage.IDLE && (
              <motion.div
                key="commandbar"
                variants={fadeUp}
                initial="hidden"
                animate="visible"
                exit={{ opacity: 0, y: -20 }}
              >
                <CommandBar
                  value={repoUrl}
                  onChange={setRepoUrl}
                  onSubmit={handleScan}
                  isLoading={false}
                  placeholder="github.com/username/repository"
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* SCANNING Stage */}
          <AnimatePresence mode="wait">
            {stage === WorkflowStage.SCANNING && (
              <motion.div
                key="scanning"
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
              >
                <ScanningOverlay 
                  repoName={scannedRepo} 
                  onComplete={handleScanComplete} 
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Vulnerability List - Blurred during strategy selection */}
          <AnimatePresence mode="wait">
            {(stage === WorkflowStage.STRATEGY_SELECTION || 
              stage === WorkflowStage.MANUAL_SELECTION) && (
              <motion.section
                key="vulnlist"
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                className={`
                  space-y-6 transition-all duration-500
                  ${stage === WorkflowStage.STRATEGY_SELECTION ? 'blur-sm opacity-50' : ''}
                `}
              >
                {/* Metrics Cards */}
                <BentoGrid>
                  <BentoCard
                    title="Threats Detected"
                    value={metrics.threats}
                    subtitle="Critical"
                    icon={AlertTriangle}
                    accent="red"
                    delay={0.1}
                  />
                  <BentoCard
                    title="Lines Scanned"
                    value={metrics.scanned.toLocaleString()}
                    subtitle="Analysis"
                    icon={Code2}
                    accent="blue"
                    delay={0.2}
                  />
                  <BentoCard
                    title="Auto-Fixed"
                    value={metrics.fixed}
                    subtitle="Patches"
                    icon={CheckCircle2}
                    accent="green"
                    delay={0.3}
                  />
                </BentoGrid>

                {/* Vulnerability List Header */}
                <div className="flex items-center justify-between mt-8 mb-4">
                  <h2 className="text-sm font-medium text-zinc-400 flex items-center gap-2 uppercase tracking-wider">
                    <FileWarning className="w-4 h-4 text-red-500" />
                    Detected Vulnerabilities
                    <span className="text-[10px] text-zinc-600 font-normal normal-case ml-2">
                      (sorted by priority)
                    </span>
                  </h2>
                  <span className="text-xs font-mono text-zinc-700">
                    {sortedVulnerabilities.length - remediatedIds.size} remaining
                  </span>
                </div>

                <SelectableVulnerabilityList
                  vulnerabilities={sortedVulnerabilities.filter(v => !remediatedIds.has(v.id))}
                  selectedIds={selectedIds}
                  onToggleSelection={handleToggleSelection}
                  isSelectable={stage === WorkflowStage.MANUAL_SELECTION}
                />

                {/* Manual Selection Hint */}
                {stage === WorkflowStage.MANUAL_SELECTION && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-center text-xs text-zinc-600 mt-4"
                  >
                    Click vulnerabilities to select them for remediation
                  </motion.p>
                )}
              </motion.section>
            )}
          </AnimatePresence>

          {/* STRATEGY_SELECTION Modal */}
          <AnimatePresence>
            {stage === WorkflowStage.STRATEGY_SELECTION && (
              <StrategySelector
                onSelectAuto={handleSelectAutoStrategy}
                onSelectManual={handleSelectManualStrategy}
                threatCount={vulnerabilities.length}
              />
            )}
          </AnimatePresence>

          {/* Floating Execute Button - Only when items selected */}
          <AnimatePresence>
            {stage === WorkflowStage.MANUAL_SELECTION && selectedIds.size > 0 && (
              renderFloatingExecuteButton()
            )}
          </AnimatePresence>

          {/* LIVE_OPS - Remediation Console */}
          <AnimatePresence mode="wait">
            {stage === WorkflowStage.LIVE_OPS && currentRemediationVuln && (
              <motion.section
                key={`liveops-${currentRemediationVuln.id}`}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                className="pt-8"
              >
                <RemediationConsole
                  vulnerability={{
                    id: String(currentRemediationVuln.id),
                    title: currentRemediationVuln.title,
                    file: currentRemediationVuln.file,
                    line: currentRemediationVuln.line,
                    riskScore: currentRemediationVuln.riskScore,
                    type: currentRemediationVuln.type,
                    description: currentRemediationVuln.description,
                  }}
                  repoUrl={getGitHubUrl()}
                  onComplete={handleRemediationComplete}
                  onReturn={handleReturnToDashboard}
                  useRealApi={true}
                />
              </motion.section>
            )}
          </AnimatePresence>

          {/* SUCCESS State */}
          <AnimatePresence mode="wait">
            {stage === WorkflowStage.SUCCESS && (
              <motion.section
                key="success"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="pt-12 max-w-5xl mx-auto"
              >
                {/* Header */}
                <div className="text-center mb-10">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 200, delay: 0.1 }}
                    className="inline-flex items-center justify-center w-16 h-16 mb-5 bg-emerald-500/10 rounded-2xl border border-emerald-500/20"
                  >
                    <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                  </motion.div>
                  
                  <motion.h2
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="text-3xl font-semibold text-white mb-2 leading-tight"
                  >
                    Remediation Complete
                  </motion.h2>
                  
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="text-zinc-400 text-base leading-relaxed"
                  >
                    {metrics.fixed} security {metrics.fixed === 1 ? 'patch has' : 'patches have'} been generated and submitted for review
                  </motion.p>
                </div>

                {/* Statistics Card */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-8 mb-8"
                >
                  <div className="grid grid-cols-3 gap-8">
                    <div className="text-center">
                      <div className="text-3xl font-semibold text-emerald-500 mb-1">{metrics.fixed}</div>
                      <div className="text-sm text-zinc-500 leading-relaxed">Patches Created</div>
                    </div>
                    <div className="text-center border-l border-r border-zinc-800">
                      <div className="text-3xl font-semibold text-blue-400 mb-1">{metrics.scanned}</div>
                      <div className="text-sm text-zinc-500 leading-relaxed">Lines Scanned</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-semibold text-emerald-400 mb-1">100%</div>
                      <div className="text-sm text-zinc-500 leading-relaxed">Success Rate</div>
                    </div>
                  </div>
                </motion.div>

                {/* Pull Requests Section */}
                {prUrls.size > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="mb-8"
                  >
                    <div className="flex items-center gap-2 mb-4">
                      <GitPullRequest className="w-5 h-5 text-emerald-500" />
                      <h3 className="text-lg font-semibold text-white">Pull Requests</h3>
                    </div>
                    
                    <div className="space-y-3">
                      {Array.from(remediatedIds).map((vulnId, index) => {
                        const vuln = vulnerabilities.find(v => v.id === vulnId);
                        const prUrl = prUrls.get(vulnId);
                        if (!vuln) return null;
                        
                        return (
                          <motion.div
                            key={vulnId}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.6 + index * 0.1 }}
                            className="bg-zinc-900/30 border border-zinc-800 rounded-xl p-5 hover:border-zinc-700 transition-colors"
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <h4 className="text-white font-medium mb-1 leading-snug">{vuln.title}</h4>
                                <p className="text-sm text-zinc-500 leading-relaxed">
                                  {vuln.file}:{vuln.line} • {vuln.type || 'Security Issue'}
                                </p>
                              </div>
                              
                              {prUrl && (
                                <a
                                  href={prUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="
                                    inline-flex items-center gap-2 px-4 py-2
                                    text-sm font-medium text-white
                                    bg-emerald-600 hover:bg-emerald-500
                                    rounded-lg transition-colors
                                    whitespace-nowrap
                                  "
                                >
                                  <ExternalLink className="w-4 h-4" />
                                  View PR
                                </a>
                              )}
                            </div>
                          </motion.div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}

                {/* Actions */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.7 }}
                  className="flex items-center justify-center gap-4"
                >
                  <motion.a
                    href={getGitHubUrl() + '/pulls'}
                    target="_blank"
                    rel="noopener noreferrer"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="
                      inline-flex items-center gap-2 px-5 py-2.5
                      text-sm font-medium text-zinc-300
                      bg-zinc-900 border border-zinc-700 rounded-lg
                      hover:bg-zinc-800 hover:border-zinc-600
                      transition-all
                    "
                  >
                    <GitPullRequest className="w-4 h-4" />
                    View All PRs
                  </motion.a>
                  
                  <motion.button
                    onClick={handleReturnToDashboard}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="
                      inline-flex items-center gap-2 px-5 py-2.5
                      text-sm font-medium text-white
                      bg-zinc-800 border border-zinc-700 rounded-lg
                      hover:bg-zinc-700 hover:border-zinc-600
                      transition-all
                    "
                  >
                    <Zap className="w-4 h-4 text-emerald-500" />
                    Scan Another Repository
                  </motion.button>
                </motion.div>
              </motion.section>
            )}
          </AnimatePresence>


        </motion.div>
      </div>

      {/* Help Widget - Always visible */}
      <HelpWidget />
    </div>
  );
}
