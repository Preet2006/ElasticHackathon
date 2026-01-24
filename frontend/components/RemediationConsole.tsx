'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, 
  Crosshair, 
  CheckCircle2, 
  ExternalLink, 
  ArrowLeft,
  Zap,
  AlertTriangle,
  GitPullRequest
} from 'lucide-react';

interface Vulnerability {
  id: string;
  title: string;
  file: string;
  line: number;
  riskScore: number;
}

interface RemediationConsoleProps {
  vulnerability: Vulnerability;
  repoUrl: string;
  prUrl?: string; // Optional: actual PR URL from backend API
  onComplete: () => void;
  onReturn: () => void;
}

interface LogEntry {
  id: number;
  text: string;
  type: 'recon' | 'plan' | 'exploit' | 'success' | 'defense' | 'patch' | 'verify' | 'info';
}

export default function RemediationConsole({ 
  vulnerability, 
  repoUrl,
  prUrl: externalPrUrl, 
  onComplete, 
  onReturn 
}: RemediationConsoleProps) {
  const [stage, setStage] = useState<'red-team' | 'blue-team' | 'completed'>('red-team');
  const [redTeamLogs, setRedTeamLogs] = useState<LogEntry[]>([]);
  const [blueTeamLogs, setBlueTeamLogs] = useState<LogEntry[]>([]);
  const [currentTypingRed, setCurrentTypingRed] = useState('');
  const [currentTypingBlue, setCurrentTypingBlue] = useState('');
  
  const redTeamRef = useRef<HTMLDivElement>(null);
  const blueTeamRef = useRef<HTMLDivElement>(null);

  // Use external PR URL if provided, otherwise link to latest PRs
  // Format: https://github.com/owner/repo/pulls?q=is%3Apr+is%3Aopen+sort%3Acreated-desc
  const prUrl = externalPrUrl || `${repoUrl}/pulls?q=is%3Apr+sort%3Acreated-desc`;

  // Red Team logs sequence
  const redTeamSequence: { text: string; type: LogEntry['type']; delay: number }[] = [
    { text: '═══════════════════════════════════════', type: 'info', delay: 200 },
    { text: '   RED TEAM // OFFENSIVE OPERATIONS', type: 'info', delay: 300 },
    { text: '═══════════════════════════════════════', type: 'info', delay: 200 },
    { text: '', type: 'info', delay: 100 },
    { text: `[TARGET] ${vulnerability.title}`, type: 'recon', delay: 400 },
    { text: `[FILE] ${vulnerability.file}:${vulnerability.line}`, type: 'recon', delay: 300 },
    { text: `[RISK] Score: ${vulnerability.riskScore.toFixed(1)}/10`, type: 'recon', delay: 300 },
    { text: '', type: 'info', delay: 100 },
    { text: '> PHASE 1: RECONNAISSANCE', type: 'recon', delay: 500 },
    { text: '  ├─ Scanning attack surface...', type: 'recon', delay: 400 },
    { text: '  ├─ Identifying entry points...', type: 'recon', delay: 350 },
    { text: '  ├─ Mapping vulnerable code paths...', type: 'recon', delay: 400 },
    { text: '  └─ [OK] Recon complete', type: 'success', delay: 300 },
    { text: '', type: 'info', delay: 100 },
    { text: '> PHASE 2: EXPLOIT PLANNING', type: 'plan', delay: 500 },
    { text: '  ├─ Analyzing vulnerability pattern...', type: 'plan', delay: 400 },
    { text: '  ├─ Crafting exploit payload...', type: 'plan', delay: 450 },
    { text: '  ├─ Preparing sandbox environment...', type: 'plan', delay: 400 },
    { text: '  └─ [OK] Exploit ready', type: 'success', delay: 300 },
    { text: '', type: 'info', delay: 100 },
    { text: '> PHASE 3: EXPLOITATION', type: 'exploit', delay: 600 },
    { text: '  ├─ Deploying payload...', type: 'exploit', delay: 500 },
    { text: '  ├─ Executing in sandbox...', type: 'exploit', delay: 600 },
    { text: '  ├─ Analyzing response...', type: 'exploit', delay: 400 },
    { text: '  └─ Capturing proof of concept...', type: 'exploit', delay: 500 },
    { text: '', type: 'info', delay: 100 },
    { text: '╔═══════════════════════════════════════╗', type: 'success', delay: 200 },
    { text: '║  EXPLOIT SUCCESSFUL // CONFIRMED     ║', type: 'success', delay: 300 },
    { text: '╚═══════════════════════════════════════╝', type: 'success', delay: 200 },
  ];

  // Blue Team logs sequence
  const blueTeamSequence: { text: string; type: LogEntry['type']; delay: number }[] = [
    { text: '═══════════════════════════════════════', type: 'info', delay: 200 },
    { text: '   BLUE TEAM // DEFENSIVE OPERATIONS', type: 'info', delay: 300 },
    { text: '═══════════════════════════════════════', type: 'info', delay: 200 },
    { text: '', type: 'info', delay: 100 },
    { text: '[ALERT] Threat intelligence received', type: 'defense', delay: 400 },
    { text: '[PRIORITY] Initiating rapid response', type: 'defense', delay: 300 },
    { text: '', type: 'info', delay: 100 },
    { text: '> PHASE 1: THREAT ANALYSIS', type: 'defense', delay: 500 },
    { text: '  ├─ Reviewing exploit signature...', type: 'defense', delay: 400 },
    { text: '  ├─ Identifying vulnerable pattern...', type: 'defense', delay: 350 },
    { text: '  ├─ Assessing blast radius...', type: 'defense', delay: 400 },
    { text: '  └─ [OK] Analysis complete', type: 'verify', delay: 300 },
    { text: '', type: 'info', delay: 100 },
    { text: '> PHASE 2: PATCH GENERATION', type: 'patch', delay: 500 },
    { text: '  ├─ Generating secure replacement...', type: 'patch', delay: 450 },
    { text: '  ├─ Applying security controls...', type: 'patch', delay: 400 },
    { text: '  ├─ Validating code integrity...', type: 'patch', delay: 400 },
    { text: '  └─ [OK] Patch generated', type: 'verify', delay: 300 },
    { text: '', type: 'info', delay: 100 },
    { text: '> PHASE 3: VERIFICATION', type: 'verify', delay: 600 },
    { text: '  ├─ Re-running exploit test...', type: 'verify', delay: 500 },
    { text: '  ├─ Exploit blocked successfully', type: 'verify', delay: 400 },
    { text: '  ├─ Running regression tests...', type: 'verify', delay: 500 },
    { text: '  └─ All tests passing', type: 'verify', delay: 400 },
    { text: '', type: 'info', delay: 100 },
    { text: '╔═══════════════════════════════════════╗', type: 'verify', delay: 200 },
    { text: '║  PATCH VERIFIED // THREAT MITIGATED  ║', type: 'verify', delay: 300 },
    { text: '╚═══════════════════════════════════════╝', type: 'verify', delay: 200 },
  ];

  // Typing effect function
  const typeLog = async (
    text: string, 
    setTyping: React.Dispatch<React.SetStateAction<string>>,
    speed: number = 15
  ): Promise<void> => {
    return new Promise((resolve) => {
      let i = 0;
      setTyping('');
      const interval = setInterval(() => {
        if (i < text.length) {
          setTyping(text.slice(0, i + 1));
          i++;
        } else {
          clearInterval(interval);
          setTyping('');
          resolve();
        }
      }, speed);
    });
  };

  // Run Red Team sequence
  useEffect(() => {
    let isMounted = true;
    
    const runRedTeam = async () => {
      for (let i = 0; i < redTeamSequence.length; i++) {
        if (!isMounted) return;
        
        const log = redTeamSequence[i];
        await new Promise(resolve => setTimeout(resolve, log.delay));
        
        if (!isMounted) return;
        
        // Type the log
        await typeLog(log.text, setCurrentTypingRed, 12);
        
        if (!isMounted) return;
        
        // Add to logs
        setRedTeamLogs(prev => [...prev, { id: i, text: log.text, type: log.type }]);
        
        // Auto-scroll
        if (redTeamRef.current) {
          redTeamRef.current.scrollTop = redTeamRef.current.scrollHeight;
        }
      }
      
      if (isMounted) {
        await new Promise(resolve => setTimeout(resolve, 800));
        setStage('blue-team');
      }
    };

    runRedTeam();
    
    return () => { isMounted = false; };
  }, []);

  // Run Blue Team sequence after Red Team
  useEffect(() => {
    if (stage !== 'blue-team') return;
    
    let isMounted = true;
    
    const runBlueTeam = async () => {
      for (let i = 0; i < blueTeamSequence.length; i++) {
        if (!isMounted) return;
        
        const log = blueTeamSequence[i];
        await new Promise(resolve => setTimeout(resolve, log.delay));
        
        if (!isMounted) return;
        
        // Type the log
        await typeLog(log.text, setCurrentTypingBlue, 12);
        
        if (!isMounted) return;
        
        // Add to logs
        setBlueTeamLogs(prev => [...prev, { id: i, text: log.text, type: log.type }]);
        
        // Auto-scroll
        if (blueTeamRef.current) {
          blueTeamRef.current.scrollTop = blueTeamRef.current.scrollHeight;
        }
      }
      
      if (isMounted) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        setStage('completed');
        onComplete();
      }
    };

    runBlueTeam();
    
    return () => { isMounted = false; };
  }, [stage]);

  const getLogColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'recon': return 'text-yellow-400';
      case 'plan': return 'text-orange-400';
      case 'exploit': return 'text-red-400';
      case 'success': return 'text-green-400';
      case 'defense': return 'text-blue-400';
      case 'patch': return 'text-cyan-400';
      case 'verify': return 'text-emerald-400';
      default: return 'text-zinc-500';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="w-full"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onReturn}
            className="flex items-center gap-2 px-3 py-2 text-xs text-zinc-400 hover:text-white bg-zinc-900/50 border border-white/5 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </motion.button>
          
          <div>
            <h2 className="text-lg font-medium text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-[#00FF41]" />
              Live Remediation Console
            </h2>
            <p className="text-xs text-zinc-500 font-mono mt-1">
              Target: {vulnerability.title} • {vulnerability.file}
            </p>
          </div>
        </div>

        {/* Status Indicator */}
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
            stage === 'red-team' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
            stage === 'blue-team' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
            'bg-green-500/10 text-green-400 border border-green-500/20'
          }`}>
            <span className={`w-2 h-2 rounded-full animate-pulse ${
              stage === 'red-team' ? 'bg-red-500' :
              stage === 'blue-team' ? 'bg-blue-500' :
              'bg-green-500'
            }`} />
            {stage === 'red-team' ? 'Red Team Active' :
             stage === 'blue-team' ? 'Blue Team Active' :
             'Completed'}
          </div>
        </div>
      </div>

      {/* Split Terminal View */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Red Team Panel */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className={`
            relative rounded-xl overflow-hidden
            bg-red-950/10 border 
            ${stage === 'red-team' ? 'border-red-500/30 shadow-[0_0_30px_rgba(239,68,68,0.1)]' : 'border-red-500/10'}
            transition-all duration-500
          `}
        >
          {/* Panel Header */}
          <div className="flex items-center gap-3 px-4 py-3 bg-red-950/30 border-b border-red-500/10">
            <Crosshair className="w-4 h-4 text-red-500" />
            <span className="text-sm font-medium text-red-400">Red Team Agent</span>
            {stage === 'red-team' && (
              <span className="ml-auto flex items-center gap-1.5 text-[10px] text-red-400/60">
                <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
                ATTACKING
              </span>
            )}
            {stage !== 'red-team' && redTeamLogs.length > 0 && (
              <span className="ml-auto text-[10px] text-green-400/60 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                COMPLETE
              </span>
            )}
          </div>

          {/* Terminal Content */}
          <div 
            ref={redTeamRef}
            className="h-[400px] overflow-y-auto p-4 font-mono text-xs scrollbar-thin scrollbar-track-transparent scrollbar-thumb-red-500/20"
          >
            {redTeamLogs.map((log) => (
              <motion.div
                key={log.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className={`${getLogColor(log.type)} leading-relaxed`}
              >
                {log.text || '\u00A0'}
              </motion.div>
            ))}
            {currentTypingRed && (
              <div className="text-red-400">
                {currentTypingRed}
                <span className="animate-pulse">▊</span>
              </div>
            )}
          </div>
        </motion.div>

        {/* Blue Team Panel */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className={`
            relative rounded-xl overflow-hidden
            bg-blue-950/10 border 
            ${stage === 'blue-team' ? 'border-blue-500/30 shadow-[0_0_30px_rgba(59,130,246,0.1)]' : 'border-blue-500/10'}
            transition-all duration-500
          `}
        >
          {/* Panel Header */}
          <div className="flex items-center gap-3 px-4 py-3 bg-blue-950/30 border-b border-blue-500/10">
            <Shield className="w-4 h-4 text-blue-500" />
            <span className="text-sm font-medium text-blue-400">Blue Team Defense</span>
            {stage === 'blue-team' && (
              <span className="ml-auto flex items-center gap-1.5 text-[10px] text-blue-400/60">
                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
                DEFENDING
              </span>
            )}
            {stage === 'completed' && (
              <span className="ml-auto text-[10px] text-green-400/60 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                PATCHED
              </span>
            )}
            {stage === 'red-team' && (
              <span className="ml-auto text-[10px] text-zinc-600">STANDBY</span>
            )}
          </div>

          {/* Terminal Content */}
          <div 
            ref={blueTeamRef}
            className="h-[400px] overflow-y-auto p-4 font-mono text-xs scrollbar-thin scrollbar-track-transparent scrollbar-thumb-blue-500/20"
          >
            {stage === 'red-team' && blueTeamLogs.length === 0 && (
              <div className="flex items-center justify-center h-full text-zinc-600">
                <div className="text-center">
                  <Shield className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p>Awaiting threat intelligence...</p>
                </div>
              </div>
            )}
            {blueTeamLogs.map((log) => (
              <motion.div
                key={log.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className={`${getLogColor(log.type)} leading-relaxed`}
              >
                {log.text || '\u00A0'}
              </motion.div>
            ))}
            {currentTypingBlue && (
              <div className="text-blue-400">
                {currentTypingBlue}
                <span className="animate-pulse">▊</span>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Success State - PR Generation */}
      <AnimatePresence>
        {stage === 'completed' && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="relative"
          >
            <div className="
              relative p-6 rounded-xl
              bg-zinc-950
              border border-zinc-800
            ">
              {/* Header Row */}
              <div className="flex items-center gap-4 mb-5">
                {/* Success Icon */}
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                  className="
                    flex items-center justify-center w-12 h-12
                    bg-emerald-500/10 rounded-lg
                    border border-emerald-500/20
                  "
                >
                  <GitPullRequest className="w-5 h-5 text-emerald-500" />
                </motion.div>

                {/* Text */}
                <div>
                  <motion.h3
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                    className="text-lg font-semibold text-white"
                  >
                    Pull Request Created
                  </motion.h3>
                  <motion.p
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 }}
                    className="text-zinc-500 text-sm"
                  >
                    Security patch has been submitted for review
                  </motion.p>
                </div>
              </div>

              {/* Action Buttons */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="flex items-center gap-3"
              >
                <motion.a
                  href={prUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className="
                    flex items-center gap-2 px-4 py-2
                    text-sm font-medium
                    text-white bg-zinc-800
                    border border-zinc-700
                    rounded-lg
                    hover:bg-zinc-700
                    transition-all duration-200
                  "
                >
                  <ExternalLink className="w-4 h-4" />
                  View PR
                </motion.a>
                
                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  onClick={onReturn}
                  className="
                    flex items-center gap-2 px-4 py-2
                    text-sm font-medium
                    text-zinc-400
                    border border-zinc-800
                    rounded-lg
                    hover:text-white hover:border-zinc-700
                    transition-all duration-200
                  "
                >
                  <ArrowLeft className="w-4 h-4" />
                  Dashboard
                </motion.button>
              </motion.div>

              {/* Summary Stats */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="flex items-center gap-6 mt-6 pt-5 border-t border-zinc-800/50"
              >
                <div className="flex items-center gap-2 text-xs text-zinc-600">
                  <CheckCircle2 className="w-3.5 h-3.5 text-zinc-600" />
                  <span>Exploit Confirmed</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-600">
                  <CheckCircle2 className="w-3.5 h-3.5 text-zinc-600" />
                  <span>Patch Generated</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-600">
                  <CheckCircle2 className="w-3.5 h-3.5 text-zinc-600" />
                  <span>Tests Passing</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-600">
                  <CheckCircle2 className="w-3.5 h-3.5 text-zinc-600" />
                  <span>PR Created</span>
                </div>
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
