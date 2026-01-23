'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle2, 
  Zap,
  Activity,
  Code2,
  FileWarning,
  GitPullRequest,
  ExternalLink
} from 'lucide-react';

import CommandBar from '@/components/CommandBar';
import { BentoGrid, BentoCard } from '@/components/BentoGrid';
import TerminalWindow from '@/components/TerminalWindow';

// ============================================
// DATA
// ============================================

const mockVulnerabilities = [
  {
    id: 1,
    title: 'Insecure Deserialization',
    file: 'user_loader.py',
    line: 6,
    type: 'Deserialization',
    riskScore: 8.0,
  },
  {
    id: 2,
    title: 'Command Injection',
    file: 'backup_service.py',
    line: 11,
    type: 'Injection',
    riskScore: 8.0,
  },
  {
    id: 3,
    title: 'XXE Attack Vector',
    file: 'xml_auth.py',
    line: 4,
    type: 'XXE',
    riskScore: 8.0,
  },
];

const redTeamLogs = [
  '[RECON] Mapping attack surface...',
  '[DETECT] Identified unsafe pickle.loads() at user_loader.py:6',
  '[EXPLOIT] Crafting malicious serialized payload...',
  '[PAYLOAD] __reduce__ method injected with os.system()',
  '[EXECUTE] Payload delivered via user input channel',
  '[SUCCESS] Remote code execution achieved ✓',
  '[VERIFY] Shell access confirmed on target system',
  '[REPORT] Critical vulnerability verified - CVSS 9.8',
];

const blueTeamLogs = [
  '[INIT] Defense protocol activated...',
  '[ANALYZE] Reviewing exploit chain and entry points',
  '[PATCH] Replacing pickle with json for data handling',
  '[PATCH] Adding input validation layer',
  '[PATCH] Implementing allowlist for expected data types',
  '[TEST] Running exploit against patched code...',
  '[VERIFY] Attack vector neutralized ✓',
  '[SUCCESS] Secure patch generated and verified',
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
// MAIN COMPONENT
// ============================================

export default function Dashboard() {
  const [repoUrl, setRepoUrl] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanComplete, setScanComplete] = useState(false);
  const [showLiveOps, setShowLiveOps] = useState(false);
  const [selectedVuln, setSelectedVuln] = useState<number | null>(null);
  const [metrics, setMetrics] = useState({ threats: 0, scanned: 0, fixed: 0, riskScore: 0 });
  const [scannedRepo, setScannedRepo] = useState('');

  // Extract repo owner and name from URL
  const extractRepoInfo = (url: string) => {
    // Handle formats: username/repo, github.com/username/repo, https://github.com/username/repo
    const cleanUrl = url.replace('https://', '').replace('http://', '').replace('github.com/', '');
    const match = cleanUrl.match(/^([^/]+)\/([^/]+)/);
    if (match) {
      return { owner: match[1], repo: match[2].replace('.git', '') };
    }
    return null;
  };

  const handleScan = () => {
    if (!repoUrl.trim()) return;
    
    setIsScanning(true);
    setScanComplete(false);
    setMetrics({ threats: 0, scanned: 0, fixed: 0, riskScore: 0 });
    setScannedRepo(repoUrl);

    // Simulate scan
    setTimeout(() => {
      setIsScanning(false);
      setScanComplete(true);
      
      // Animate metrics
      let count = 0;
      const interval = setInterval(() => {
        count++;
        setMetrics({
          threats: Math.min(count, 3),
          scanned: Math.min(count * 400, 1247),
          fixed: 0,
          riskScore: Math.min(count * 2, 8.0),
        });
        if (count >= 4) clearInterval(interval);
      }, 100);
    }, 2000);
  };

  const handleRemediate = (vulnId: number) => {
    setSelectedVuln(vulnId);
    setShowLiveOps(true);
    
    // Scroll to ops section
    setTimeout(() => {
      document.getElementById('live-ops')?.scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
      });
    }, 100);
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
              isLoading={isScanning}
              placeholder="github.com/username/repository"
            />
          </motion.div>

          {/* ============================================ */}
          {/* BENTO GRID - STATS */}
          {/* ============================================ */}
          <AnimatePresence>
            {(isScanning || scanComplete) && (
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
            {scanComplete && (
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
                  </h2>
                  <span className="text-xs font-mono text-zinc-700">
                    {mockVulnerabilities.length} issues
                  </span>
                </div>

                <div className="space-y-2">
                  {mockVulnerabilities.map((vuln, index) => (
                    <motion.div
                      key={vuln.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.4 + index * 0.1 }}
                      whileHover={{ scale: 1.005 }}
                      className="
                        group relative p-5
                        bg-zinc-900/30 backdrop-blur-sm rounded-xl
                        border border-white/[0.03]
                        hover:border-red-500/10 hover:bg-zinc-900/50
                        transition-all duration-500
                      "
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          {/* Severity Indicator */}
                          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-red-500/5 border border-red-500/10">
                            <AlertTriangle className="w-4 h-4 text-red-500/80" />
                          </div>

                          {/* Info */}
                          <div>
                            <div className="flex items-center gap-3 mb-1">
                              <span className="text-zinc-200 font-medium text-sm">{vuln.title}</span>
                              <span className="px-1.5 py-0.5 text-[9px] font-mono text-red-400/80 bg-red-500/5 rounded border border-red-500/10">
                                CRITICAL
                              </span>
                            </div>
                            <div className="flex items-center gap-3 text-xs text-zinc-600 font-mono">
                              <span>{vuln.file}</span>
                              <span className="text-zinc-800">•</span>
                              <span>Line {vuln.line}</span>
                              <span className="text-zinc-800">•</span>
                              <span className="text-yellow-600/80">Risk {vuln.riskScore}</span>
                            </div>
                          </div>
                        </div>

                        {/* Action Button */}
                        <motion.button
                          whileHover={{ scale: 1.03 }}
                          whileTap={{ scale: 0.97 }}
                          onClick={() => handleRemediate(vuln.id)}
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
                          <span>Remediate</span>
                        </motion.button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.section>
            )}
          </AnimatePresence>

          {/* ============================================ */}
          {/* LIVE OPS - TERMINALS */}
          {/* ============================================ */}
          <AnimatePresence>
            {showLiveOps && (
              <motion.section
                id="live-ops"
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.6 }}
                className="space-y-6 pt-4"
              >
                {/* Section Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900/50 rounded-full border border-white/[0.03]">
                      <motion.div
                        className="w-1.5 h-1.5 rounded-full bg-[#00FF41]"
                        animate={{ opacity: [1, 0.3, 1] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      />
                      <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">Live Operations</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-700">
                    Vulnerability #{selectedVuln}
                  </span>
                </div>

                {/* Terminal Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <TerminalWindow
                    title="RED TEAM"
                    logs={redTeamLogs}
                    variant="red"
                    isActive={true}
                    typingSpeed={40}
                  />
                  <TerminalWindow
                    title="BLUE TEAM"
                    logs={blueTeamLogs}
                    variant="blue"
                    isActive={true}
                    typingSpeed={45}
                  />
                </div>

                {/* Success Banner */}
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 8, duration: 0.5 }}
                  className="
                    relative overflow-hidden p-5
                    bg-[#00FF41]/[0.02]
                    border border-[#00FF41]/10 rounded-xl
                  "
                >
                  <div className="flex items-center gap-4">
                    <div className="p-2.5 bg-[#00FF41]/5 rounded-lg border border-[#00FF41]/10">
                      <GitPullRequest className="w-5 h-5 text-[#00FF41]/80" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-zinc-200 font-medium text-sm mb-0.5">
                        Pull Request Created
                      </h3>
                      <p className="text-xs text-zinc-600">
                        Vulnerability patched and verified. Ready for review.
                      </p>
                    </div>
                    <motion.a
                      href={(() => {
                        const repoInfo = extractRepoInfo(scannedRepo);
                        if (repoInfo) {
                          return `https://github.com/${repoInfo.owner}/${repoInfo.repo}/pulls`;
                        }
                        return 'https://github.com';
                      })()}
                      target="_blank"
                      rel="noopener noreferrer"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className="
                        flex items-center gap-2 px-3 py-1.5
                        text-xs font-medium text-zinc-400
                        bg-zinc-900/50 border border-white/5 rounded-lg
                        hover:bg-zinc-800/50 hover:text-zinc-300
                        transition-all duration-300
                      "
                    >
                      <span>View PR</span>
                      <ExternalLink className="w-3 h-3" />
                    </motion.a>
                  </div>
                </motion.div>
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
