'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle2, 
  Zap,
  Activity,
  Code2,
  FileWarning,
  Flame
} from 'lucide-react';

import CommandBar from '@/components/CommandBar';
import { BentoGrid, BentoCard } from '@/components/BentoGrid';
import RemediationConsole from '@/components/RemediationConsole';

// ============================================
// DATA
// ============================================

const mockVulnerabilities = [
  {
    id: 1,
    title: 'Path Traversal',
    file: 'log_viewer.py',
    line: 6,
    type: 'Path Traversal',
    riskScore: 8.0,
  },
  {
    id: 2,
    title: 'Cross-Site Scripting (XSS)',
    file: 'template_render.py',
    line: 4,
    type: 'XSS',
    riskScore: 8.0,
  },
];

// ============================================
// ANIMATION VARIANTS
// ============================================

const stagger = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
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
}

type AppStage = 'idle' | 'scanning' | 'results' | 'remediating' | 'completed';

// ============================================
// MAIN COMPONENT
// ============================================

export default function Dashboard() {
  const [repoUrl, setRepoUrl] = useState('');
  const [stage, setStage] = useState<AppStage>('idle');
  const [selectedVuln, setSelectedVuln] = useState<Vulnerability | null>(null);
  const [metrics, setMetrics] = useState({ threats: 0, scanned: 0, fixed: 0, riskScore: 0 });
  const [scannedRepo, setScannedRepo] = useState('');
  const [remediatedIds, setRemediatedIds] = useState<Set<number>>(new Set());

  // Extract repo owner and name from URL
  const extractRepoInfo = (url: string) => {
    const cleanUrl = url.replace('https://', '').replace('http://', '').replace('github.com/', '');
    const match = cleanUrl.match(/^([^/]+)\/([^/]+)/);
    if (match) {
      return { owner: match[1], repo: match[2].replace('.git', '') };
    }
    return null;
  };

  // Get GitHub URL for PR
  const getGitHubUrl = () => {
    const repoInfo = extractRepoInfo(scannedRepo);
    if (repoInfo) {
      return `https://github.com/${repoInfo.owner}/${repoInfo.repo}`;
    }
    return 'https://github.com';
  };

  // Smart prioritization: Sort vulnerabilities by risk score (highest first)
  const sortedVulnerabilities = [...mockVulnerabilities].sort((a, b) => b.riskScore - a.riskScore);

  // Check if vulnerability is high priority (CRITICAL)
  const isHighPriority = (riskScore: number) => riskScore >= 8.0;

  const handleScan = () => {
    if (!repoUrl.trim()) return;
    
    setStage('scanning');
    setMetrics({ threats: 0, scanned: 0, fixed: 0, riskScore: 0 });
    setScannedRepo(repoUrl);
    setRemediatedIds(new Set());

    // Simulate scan
    setTimeout(() => {
      setStage('results');
      
      // Animate metrics
      let count = 0;
      const interval = setInterval(() => {
        count++;
        setMetrics({
          threats: Math.min(count, sortedVulnerabilities.length),
          scanned: Math.min(count * 300, 600),
          fixed: 0,
          riskScore: Math.min(count * 4, 8.0),
        });
        if (count >= sortedVulnerabilities.length) clearInterval(interval);
      }, 100);
    }, 2000);
  };

  const handleRemediate = (vuln: Vulnerability) => {
    setSelectedVuln(vuln);
    setStage('remediating');
    
    // Scroll to top smoothly
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleRemediationComplete = () => {
    if (selectedVuln) {
      setRemediatedIds(prev => {
        const newSet = new Set(Array.from(prev));
        newSet.add(selectedVuln.id);
        return newSet;
      });
      setMetrics(prev => ({ ...prev, fixed: prev.fixed + 1 }));
    }
    setStage('completed');
  };

  const handleReturnToDashboard = () => {
    setSelectedVuln(null);
    setStage('results');
  };

  // Get severity level based on risk score
  const getSeverity = (riskScore: number) => {
    if (riskScore >= 9.0) return { label: 'CRITICAL', color: 'red' };
    if (riskScore >= 7.0) return { label: 'HIGH', color: 'orange' };
    if (riskScore >= 4.0) return { label: 'MEDIUM', color: 'yellow' };
    return { label: 'LOW', color: 'blue' };
  };

  return (
    <div className="min-h-screen bg-black">
      {/* Subtle grid background */}
      <div className="fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[size:72px_72px] pointer-events-none" />
      
      {/* Radial gradient accent */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,rgba(0,255,65,0.03),transparent_50%)] pointer-events-none" />
      
      <div className="relative z-10 max-w-5xl mx-auto px-6 py-16">
        <motion.div
          variants={stagger}
          initial="hidden"
          animate="visible"
          className="space-y-16"
        >
          {/* ============================================ */}
          {/* HEADER */}
          {/* ============================================ */}
          <motion.header variants={fadeUp} className="text-center space-y-8 pt-8">
            {/* Logo */}
            <motion.div 
              className="flex items-center justify-center gap-3"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5 }}
            >
              <div className="relative">
                <Shield className="w-9 h-9 text-[#00FF41]" />
                <motion.div
                  className="absolute inset-0"
                  animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0, 0.5] }}
                  transition={{ duration: 2.5, repeat: Infinity }}
                >
                  <Shield className="w-9 h-9 text-[#00FF41]" />
                </motion.div>
              </div>
              <span className="text-xl font-medium text-white tracking-tight">
                CodeJanitor
              </span>
              <span className="px-2 py-0.5 text-[10px] font-mono text-[#00FF41]/80 bg-[#00FF41]/5 rounded border border-[#00FF41]/10">
                v2.0
              </span>
            </motion.div>

            {/* Headline */}
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

          {/* ============================================ */}
          {/* COMMAND BAR */}
          {/* ============================================ */}
          <motion.div variants={fadeUp}>
            <CommandBar
              value={repoUrl}
              onChange={setRepoUrl}
              onSubmit={handleScan}
              isLoading={stage === 'scanning'}
              placeholder="github.com/username/repository"
            />
          </motion.div>

          {/* ============================================ */}
          {/* BENTO GRID - STATS */}
          {/* ============================================ */}
          <AnimatePresence>
            {(stage === 'scanning' || stage === 'results') && (
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
                  <BentoCard
                    title="Risk Score"
                    value={metrics.riskScore.toFixed(1)}
                    subtitle="CVSS"
                    icon={Activity}
                    accent="yellow"
                    delay={0.4}
                  />
                </BentoGrid>
              </motion.section>
            )}
          </AnimatePresence>

          {/* ============================================ */}
          {/* VULNERABILITY LIST */}
          {/* ============================================ */}
          <AnimatePresence>
            {stage === 'results' && (
              <motion.section
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5, delay: 0.3 }}
                className="space-y-4"
              >
                <div className="flex items-center justify-between mb-6">
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

                <div className="space-y-2">
                  {sortedVulnerabilities
                    .filter(vuln => !remediatedIds.has(vuln.id))
                    .map((vuln, index) => {
                    const severity = getSeverity(vuln.riskScore);
                    const highPriority = isHighPriority(vuln.riskScore);
                    return (
                    <motion.div
                      key={vuln.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.4 + index * 0.1 }}
                      whileHover={{ scale: 1.005 }}
                      className={`
                        group relative p-5
                        bg-zinc-900/30 backdrop-blur-sm rounded-xl
                        border transition-all duration-500
                        ${highPriority 
                          ? 'border-red-500/20 hover:border-red-500/30 hover:bg-red-950/20' 
                          : 'border-white/[0.03] hover:border-red-500/10 hover:bg-zinc-900/50'
                        }
                      `}
                    >
                      {/* High Priority Indicator */}
                      {highPriority && (
                        <div className="absolute -top-2 -right-2">
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="flex items-center gap-1 px-2 py-0.5 bg-red-500/20 border border-red-500/30 rounded-full"
                          >
                            <Flame className="w-3 h-3 text-red-400" />
                            <span className="text-[9px] font-semibold text-red-400 uppercase">High Priority</span>
                          </motion.div>
                        </div>
                      )}

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          {/* Severity Indicator */}
                          <div className={`flex items-center justify-center w-10 h-10 rounded-lg ${
                            severity.color === 'red' ? 'bg-red-500/10 border-red-500/20' :
                            severity.color === 'orange' ? 'bg-orange-500/10 border-orange-500/20' :
                            severity.color === 'yellow' ? 'bg-yellow-500/10 border-yellow-500/20' :
                            'bg-blue-500/10 border-blue-500/20'
                          } border`}>
                            <AlertTriangle className={`w-4 h-4 ${
                              severity.color === 'red' ? 'text-red-500' :
                              severity.color === 'orange' ? 'text-orange-500' :
                              severity.color === 'yellow' ? 'text-yellow-500' :
                              'text-blue-500'
                            }`} />
                          </div>

                          {/* Info */}
                          <div>
                            <div className="flex items-center gap-3 mb-1">
                              <span className="text-zinc-200 font-medium text-sm">{vuln.title}</span>
                              <span className={`px-1.5 py-0.5 text-[9px] font-mono rounded border ${
                                severity.color === 'red' ? 'text-red-400 bg-red-500/10 border-red-500/20' :
                                severity.color === 'orange' ? 'text-orange-400 bg-orange-500/10 border-orange-500/20' :
                                severity.color === 'yellow' ? 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' :
                                'text-blue-400 bg-blue-500/10 border-blue-500/20'
                              }`}>
                                {severity.label}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 text-xs text-zinc-600 font-mono">
                              <span>{vuln.file}</span>
                              <span className="text-zinc-800">•</span>
                              <span>Line {vuln.line}</span>
                              <span className="text-zinc-800">•</span>
                              <span className="text-yellow-600/80">Risk {vuln.riskScore.toFixed(1)}</span>
                            </div>
                          </div>
                        </div>

                        {/* Action Button */}
                        <motion.button
                          whileHover={{ scale: 1.03 }}
                          whileTap={{ scale: 0.97 }}
                          onClick={() => handleRemediate(vuln)}
                          className="
                            flex items-center gap-2 px-4 py-2
                            text-xs font-medium
                            text-[#00FF41]/80 bg-[#00FF41]/5
                            border border-[#00FF41]/10 rounded-lg
                            hover:bg-[#00FF41]/10 hover:border-[#00FF41]/20
                            hover:shadow-[0_0_30px_rgba(0,255,65,0.1)]
                            transition-all duration-300
                          "
                        >
                          <Zap className="w-3.5 h-3.5" />
                          <span>Auto-Remediate</span>
                        </motion.button>
                      </div>
                    </motion.div>
                  );})}
                </div>

                {/* All Fixed Message */}
                {remediatedIds.size === sortedVulnerabilities.length && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-8 text-center bg-[#00FF41]/5 border border-[#00FF41]/20 rounded-xl"
                  >
                    <CheckCircle2 className="w-12 h-12 text-[#00FF41] mx-auto mb-4" />
                    <h3 className="text-xl font-medium text-white mb-2">All Vulnerabilities Remediated!</h3>
                    <p className="text-zinc-500 text-sm">Your repository is now secure. All patches have been submitted as PRs.</p>
                  </motion.div>
                )}
              </motion.section>
            )}
          </AnimatePresence>

          {/* ============================================ */}
          {/* REMEDIATION CONSOLE - LIVE OPS */}
          {/* ============================================ */}
          <AnimatePresence mode="wait">
            {(stage === 'remediating' || stage === 'completed') && selectedVuln && (
              <motion.section
                key="remediation-console"
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.6 }}
                className="pt-4"
              >
                <RemediationConsole
                  vulnerability={{
                    id: String(selectedVuln.id),
                    title: selectedVuln.title,
                    file: selectedVuln.file,
                    line: selectedVuln.line,
                    riskScore: selectedVuln.riskScore,
                  }}
                  repoUrl={getGitHubUrl()}
                  onComplete={handleRemediationComplete}
                  onReturn={handleReturnToDashboard}
                />
              </motion.section>
            )}
          </AnimatePresence>

          {/* ============================================ */}
          {/* FOOTER */}
          {/* ============================================ */}
          <motion.footer 
            variants={fadeUp}
            className="pt-16 pb-8 text-center"
          >
            <div className="h-px bg-gradient-to-r from-transparent via-white/5 to-transparent mb-8" />
            <p className="text-[10px] text-zinc-700 font-mono uppercase tracking-widest">
              Powered by AI • Secured by Design • Built for Developers
            </p>
          </motion.footer>
        </motion.div>
      </div>
    </div>
  );
}
