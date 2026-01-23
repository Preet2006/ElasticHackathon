'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle2, 
  Zap, 
  Github,
  TrendingUp,
  Activity,
  Code2,
  Lock,
  Sparkles,
  Terminal,
  ArrowRight
} from 'lucide-react';
import TerminalStream from '@/components/TerminalStream';

// Mock Data - Matches EXACTLY what CLI backend detects from Preet2006/testing
const mockVulnerabilities = [
  {
    id: 1,
    title: 'Path Traversal in backup_service.py',
    severity: 'high',
    file: 'backup_service.py',
    line: 5,
    type: 'Path Traversal',
    riskScore: 6.0,
    status: 'detected',
  },
  {
    id: 2,
    title: 'Command Injection in backup_service.py',
    severity: 'critical',
    file: 'backup_service.py',
    line: 11,
    type: 'Command Injection',
    riskScore: 9.0,
    status: 'detected',
  },
  {
    id: 3,
    title: 'Insecure Deserialization in user_loader.py',
    severity: 'critical',
    file: 'user_loader.py',
    line: 6,
    type: 'Insecure Deserialization',
    riskScore: 9.0,
    status: 'detected',
  },
  {
    id: 4,
    title: 'XXE (XML External Entity) attack in xml_auth.py',
    severity: 'critical',
    file: 'xml_auth.py',
    line: 4,
    type: 'XXE',
    riskScore: 8.0,
    status: 'detected',
  },
];

const redTeamLogs = [
  '[RECON] Analyzing target codebase structure...',
  '[DETECT] Found user input in OS command: backup_service.py:12',
  '[EXPLOIT] Crafting command injection payload...',
  '[PAYLOAD] Testing: /tmp/test; whoami',
  '[EXECUTE] Sending malicious input to target...',
  '[SUCCESS] Command executed! Output received: DESKTOP-USER\\admin',
  '[VERIFY] Root access confirmed ✓',
  '[REPORT] Vulnerability exploitable - HIGH RISK',
];

const blueTeamLogs = [
  '[INIT] Blue Team Defense Protocol activated...',
  '[ANALYZE] Reviewing exploit method and code context...',
  '[PATCH] Generating fix: Replace os.system() with subprocess.run()',
  '[PATCH] Adding input validation: whitelist approved commands',
  '[PATCH] Implementing proper escaping for shell arguments',
  '[TEST] Running exploit against patched code...',
  '[VERIFY] Attack vector neutralized ✓',
  '[SUCCESS] Patch deployed - vulnerability resolved',
];

export default function Dashboard() {
  const [repoUrl, setRepoUrl] = useState('');
  const [selectedVuln, setSelectedVuln] = useState<number | null>(null);
  const [showLiveOps, setShowLiveOps] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [showVulnerabilities, setShowVulnerabilities] = useState(false);
  const [liveMetrics, setLiveMetrics] = useState({ scanned: 0, threats: 0, fixed: 0 });

  // Animated metrics counter
  useEffect(() => {
    if (showVulnerabilities) {
      const interval = setInterval(() => {
        setLiveMetrics(prev => ({
          scanned: Math.min(prev.scanned + 47, 1247),
          threats: Math.min(prev.threats + 1, 4),
          fixed: Math.min(prev.fixed + 1, 3)
        }));
      }, 50);
      return () => clearInterval(interval);
    }
  }, [showVulnerabilities]);

  const handleScan = () => {
    if (!repoUrl.trim()) {
      alert('Please enter a repository URL or type "local"');
      return;
    }

    setIsScanning(true);
    setShowVulnerabilities(false);

    // Simulate scanning delay
    setTimeout(() => {
      setIsScanning(false);
      setShowVulnerabilities(true);
      
      // Scroll to vulnerabilities
      setTimeout(() => {
        document.getElementById('vulnerabilities')?.scrollIntoView({ 
          behavior: 'smooth',
          block: 'start'
        });
      }, 100);
    }, 2000);
  };

  const handleAutoRemediate = (vulnId: number) => {
    setSelectedVuln(vulnId);
    setShowLiveOps(true);
    
    // Auto-scroll to live ops section
    setTimeout(() => {
      document.getElementById('live-ops')?.scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
      });
    }, 100);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'high':
        return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      default:
        return 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20';
    }
  };

  return (
    <div className="min-h-screen p-8 space-y-8">
      {/* Hero Section */}
      <motion.section
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-zinc-900/80 via-zinc-900/50 to-emerald-900/20 border border-white/10 p-12"
      >
        {/* Animated Background Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:4rem_4rem]" />
        
        {/* Floating Particles Effect */}
        <div className="absolute inset-0 overflow-hidden">
          {[...Array(20)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-1 h-1 bg-green-400/20 rounded-full"
              initial={{ 
                x: Math.random() * 1000,
                y: Math.random() * 400,
              }}
              animate={{
                y: [null, Math.random() * 400],
                opacity: [0.2, 0.5, 0.2],
              }}
              transition={{
                duration: Math.random() * 3 + 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          ))}
        </div>
        
        <div className="relative z-10">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="mb-6"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="relative">
                <Shield className="w-14 h-14 text-green-400" />
                <motion.div
                  className="absolute inset-0"
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 0, 0.5],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                >
                  <Shield className="w-14 h-14 text-green-400" />
                </motion.div>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="text-5xl font-bold bg-gradient-to-r from-green-400 to-emerald-300 bg-clip-text text-transparent">
                    CodeJanitor 2.0
                  </h1>
                  <Sparkles className="w-6 h-6 text-green-400" />
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="px-2 py-1 bg-green-500/10 border border-green-500/20 rounded text-green-400 font-mono">
                    AUTONOMOUS
                  </span>
                  <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded text-blue-400 font-mono">
                    AI-POWERED
                  </span>
                  <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/20 rounded text-purple-400 font-mono">
                    REAL-TIME
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
          
          <p className="text-zinc-300 text-xl mb-3 max-w-3xl leading-relaxed">
            Enterprise-grade autonomous security remediation system powered by advanced AI
          </p>
          <p className="text-zinc-400 text-base mb-8 max-w-3xl">
            🔴 Red Team exploitation • 🔵 Blue Team patching • 🚀 Automated Pull Requests
          </p>

          {/* Scan Input */}
          <div className="flex gap-4 max-w-4xl">
            <div className="flex-1 relative group">
              <Github className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500 group-focus-within:text-green-400 transition-colors" />
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleScan()}
                placeholder="github.com/username/repo or 'Preet2006/testing' for demo"
                className="w-full pl-12 pr-4 py-4 bg-black/50 border border-white/10 rounded-xl 
                         text-zinc-100 placeholder-zinc-500 font-mono text-sm
                         focus:border-green-500/50 focus:outline-none focus:ring-2 focus:ring-green-500/20
                         focus:bg-black/70 transition-all backdrop-blur-sm
                         hover:border-white/20"
              />
              <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-green-500/5 to-emerald-500/5 opacity-0 group-focus-within:opacity-100 transition-opacity pointer-events-none" />
            </div>
            
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleScan}
              disabled={isScanning}
              className={`px-10 py-4 font-bold rounded-xl
                       shadow-[0_0_25px_rgba(34,197,94,0.4)] hover:shadow-[0_0_35px_rgba(34,197,94,0.6)]
                       transition-all duration-200 flex items-center gap-2 whitespace-nowrap
                       ${isScanning 
                         ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed shadow-none' 
                         : 'bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-400 hover:to-emerald-400 text-black'
                       }`}
            >
              {isScanning ? (
                <>
                  <Activity className="w-5 h-5 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <Shield className="w-5 h-5" />
                  Start Scan
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </motion.button>
          </div>
          
          {/* Quick Demo Badge */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-4 flex items-center gap-2 text-sm text-zinc-500"
          >
            <Sparkles className="w-4 h-4 text-yellow-400" />
            <span>Try demo: <code className="text-green-400 bg-green-500/10 px-2 py-0.5 rounded">Preet2006/testing</code></span>
          </motion.div>
        </div>
      </motion.section>

      {/* Feature Cards */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.6 }}
        className="grid grid-cols-3 gap-4"
      >
        <motion.div
          whileHover={{ scale: 1.02 }}
          className="bg-gradient-to-br from-red-500/10 to-red-500/5 border border-red-500/20 rounded-xl p-5 backdrop-blur-sm"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 bg-red-500/10 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-zinc-100 mb-1">Red Team Agent</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Autonomous exploitation engine validates real-world attack vectors
              </p>
            </div>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02 }}
          className="bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/20 rounded-xl p-5 backdrop-blur-sm"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Shield className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-zinc-100 mb-1">Blue Team Defense</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                AI-powered patching system generates production-ready fixes
              </p>
            </div>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02 }}
          className="bg-gradient-to-br from-green-500/10 to-green-500/5 border border-green-500/20 rounded-xl p-5 backdrop-blur-sm"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 bg-green-500/10 rounded-lg">
              <Github className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-zinc-100 mb-1">Auto PR Creation</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Seamless GitHub integration with verified security patches
              </p>
            </div>
          </div>
        </motion.div>
      </motion.section>

      {/* Stats Grid */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.6 }}
        className="grid grid-cols-3 gap-6"
      >
        <motion.div
          whileHover={{ y: -4 }}
          className="bg-zinc-900/50 border border-white/10 rounded-xl p-6 backdrop-blur-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <AlertTriangle className="w-8 h-8 text-red-500" />
            <TrendingUp className="w-5 h-5 text-red-400" />
          </div>
          <motion.p 
            className="text-4xl font-bold text-zinc-100 mb-2"
            key={liveMetrics.threats}
          >
            {liveMetrics.threats}
          </motion.p>
          <p className="text-sm text-zinc-400 font-medium">Threats Detected</p>
          <div className="mt-3 h-1 bg-zinc-800 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-gradient-to-r from-red-500 to-orange-500"
              initial={{ width: 0 }}
              animate={{ width: showVulnerabilities ? '75%' : '0%' }}
              transition={{ duration: 1 }}
            />
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          className="bg-zinc-900/50 border border-white/10 rounded-xl p-6 backdrop-blur-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <Code2 className="w-8 h-8 text-blue-400" />
            <Terminal className="w-5 h-5 text-blue-300 animate-pulse" />
          </div>
          <motion.p 
            className="text-4xl font-bold text-zinc-100 mb-2"
            key={liveMetrics.scanned}
          >
            {liveMetrics.scanned}
          </motion.p>
          <p className="text-sm text-zinc-400 font-medium">Lines Scanned</p>
          <div className="mt-3 h-1 bg-zinc-800 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-gradient-to-r from-blue-500 to-cyan-500"
              initial={{ width: 0 }}
              animate={{ width: showVulnerabilities ? '95%' : '0%' }}
              transition={{ duration: 1.2 }}
            />
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          className="bg-zinc-900/50 border border-white/10 rounded-xl p-6 backdrop-blur-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <CheckCircle2 className="w-8 h-8 text-green-500" />
            <Lock className="w-5 h-5 text-green-400" />
          </div>
          <motion.p 
            className="text-4xl font-bold text-zinc-100 mb-2"
            key={liveMetrics.fixed}
          >
            {liveMetrics.fixed}
          </motion.p>
          <p className="text-sm text-zinc-400 font-medium">Auto-Fixed</p>
          <div className="mt-3 h-1 bg-zinc-800 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-gradient-to-r from-green-500 to-emerald-500"
              initial={{ width: 0 }}
              animate={{ width: showVulnerabilities ? '60%' : '0%' }}
              transition={{ duration: 0.8 }}
            />
          </div>
        </motion.div>
      </motion.section>

      {/* Vulnerability Feed */}
      <AnimatePresence>
        {showVulnerabilities && (
          <motion.section
            id="vulnerabilities"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-2xl font-bold text-zinc-100 mb-6 flex items-center gap-2">
              <AlertTriangle className="w-6 h-6 text-red-500" />
              Detected Vulnerabilities
            </h2>

            <div className="space-y-4">
              {mockVulnerabilities.map((vuln, index) => (
                <motion.div
                  key={vuln.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ x: 4 }}
                  className="bg-zinc-900/50 border border-white/10 rounded-lg p-6 backdrop-blur-sm
                           hover:border-red-500/20 transition-all duration-200"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className={`px-3 py-1 rounded-full text-xs font-mono uppercase border ${getSeverityColor(vuln.severity)}`}>
                          {vuln.severity}
                        </span>
                        <span className="text-xs font-mono text-zinc-500">{vuln.type}</span>
                      </div>
                      
                      <h3 className="text-lg font-semibold text-zinc-100 mb-2">
                        {vuln.title}
                      </h3>
                      
                      <div className="flex items-center gap-4 text-sm text-zinc-400 font-mono">
                        <span>{vuln.file}</span>
                        <span className="text-zinc-600">•</span>
                        <span>Line {vuln.line}</span>
                        <span className="text-zinc-600">•</span>
                        <span className="text-yellow-400">Risk: {vuln.riskScore}</span>
                      </div>
                    </div>

                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => handleAutoRemediate(vuln.id)}
                      className="flex items-center gap-2 px-6 py-3 bg-green-500/10 hover:bg-green-500/20 
                               text-green-400 border border-green-500/20 rounded-lg font-semibold
                               transition-all duration-200 shadow-[0_0_15px_rgba(34,197,94,0.1)]
                               hover:shadow-[0_0_20px_rgba(34,197,94,0.2)]"
                    >
                      <Zap className="w-4 h-4" />
                      Auto-Remediate
                    </motion.button>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Live Operations View */}
      <AnimatePresence>
        {showLiveOps && (
          <motion.section
            id="live-ops"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.5 }}
            className="pt-12"
          >
            <motion.h2 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-3xl font-bold text-zinc-100 mb-8 flex items-center gap-3"
            >
              <Activity className="w-8 h-8 text-green-400 animate-pulse" />
              Live Operations Mode
              <span className="text-sm font-mono text-green-400 bg-green-500/10 px-3 py-1 rounded-full border border-green-500/20">
                ACTIVE
              </span>
            </motion.h2>

            <div className="grid grid-cols-2 gap-6">
              {/* Red Team Terminal */}
              <TerminalStream
                title="🔴 RED TEAM - EXPLOIT ENGINE"
                color="red"
                logs={redTeamLogs}
                isActive={true}
              />

              {/* Blue Team Terminal */}
              <TerminalStream
                title="🔵 BLUE TEAM - DEFENSE PROTOCOL"
                color="blue"
                logs={blueTeamLogs}
                isActive={true}
              />
            </div>

            {/* Results Summary */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 2 }}
              className="mt-8 bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/20 
                       rounded-lg p-6 backdrop-blur-sm"
            >
              <div className="flex items-center gap-4">
                <CheckCircle2 className="w-12 h-12 text-green-400" />
                <div>
                  <h3 className="text-xl font-bold text-zinc-100 mb-1">
                    Vulnerability Successfully Patched
                  </h3>
                  <p className="text-zinc-400">
                    Exploit neutralized and fix verified. Pull request created with comprehensive security improvements.
                  </p>
                </div>
              </div>
            </motion.div>
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  );
}
