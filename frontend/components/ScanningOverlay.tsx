'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search, FileCode, Shield, Loader2 } from 'lucide-react';

interface ScanningOverlayProps {
  repoName: string;
  onComplete: () => void;
}

const scanStages = [
  { text: 'Initializing security scanner...', icon: Shield },
  { text: 'Cloning repository...', icon: FileCode },
  { text: 'Analyzing source files...', icon: Search },
  { text: 'Running vulnerability detection...', icon: Shield },
  { text: 'Calculating risk scores...', icon: FileCode },
  { text: 'Generating threat report...', icon: Search },
];

export default function ScanningOverlay({ repoName, onComplete }: ScanningOverlayProps) {
  const [currentStage, setCurrentStage] = useState(0);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    // Progress animation
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + 2;
      });
    }, 40);

    // Stage progression
    const stageInterval = setInterval(() => {
      setCurrentStage(prev => {
        if (prev >= scanStages.length - 1) {
          clearInterval(stageInterval);
          setTimeout(onComplete, 500);
          return prev;
        }
        return prev + 1;
      });
    }, 350);

    // Log messages
    const logMessages = [
      `$ git clone ${repoName}`,
      'Cloning into temporary directory...',
      'Receiving objects: 100% (142/142)',
      '$ python3 -m codejanitor scan .',
      '[INIT] Loading vulnerability patterns...',
      '[SCAN] Analyzing Python files...',
      '[SCAN] Checking for injection vulnerabilities...',
      '[SCAN] Checking for XSS vulnerabilities...',
      '[SCAN] Checking for path traversal...',
      '[DONE] Scan complete. Generating report...',
    ];

    let logIndex = 0;
    const logInterval = setInterval(() => {
      if (logIndex < logMessages.length) {
        setLogs(prev => [...prev, logMessages[logIndex]]);
        logIndex++;
      } else {
        clearInterval(logInterval);
      }
    }, 200);

    return () => {
      clearInterval(progressInterval);
      clearInterval(stageInterval);
      clearInterval(logInterval);
    };
  }, [repoName, onComplete]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="w-full"
    >
      {/* Scanner Card */}
      <div className="
        relative p-8 rounded-2xl
        bg-zinc-950 border border-white/10
        shadow-2xl overflow-hidden
      ">
        {/* Animated Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#00FF41]/5 via-transparent to-blue-500/5" />
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-transparent via-[#00FF41]/5 to-transparent"
          animate={{ x: ['-100%', '100%'] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        />

        <div className="relative z-10">
          {/* Header */}
          <div className="flex items-center gap-4 mb-6">
            <div className="relative">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              >
                <Loader2 className="w-8 h-8 text-[#00FF41]" />
              </motion.div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Security Scan in Progress</h3>
              <p className="text-sm text-zinc-500 font-mono">{repoName}</p>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-zinc-400">{scanStages[currentStage]?.text}</span>
              <span className="text-xs font-mono text-[#00FF41]">{progress}%</span>
            </div>
            <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-[#00FF41] to-emerald-400"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.1 }}
              />
            </div>
          </div>

          {/* Terminal Output */}
          <div className="
            h-48 p-4 rounded-xl
            bg-black/50 border border-white/5
            font-mono text-xs overflow-y-auto
          ">
            {logs.map((log, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className={`leading-relaxed ${
                  log?.startsWith('$') ? 'text-[#00FF41]' :
                  log?.startsWith('[') ? 'text-yellow-400' :
                  'text-zinc-500'
                }`}
              >
                {log || ''}
              </motion.div>
            ))}
            <motion.span
              animate={{ opacity: [1, 0, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
              className="text-[#00FF41]"
            >
              ▊
            </motion.span>
          </div>

          {/* Stage Indicators */}
          <div className="flex items-center justify-center gap-2 mt-6">
            {scanStages.map((_, index) => (
              <motion.div
                key={index}
                className={`w-2 h-2 rounded-full transition-colors ${
                  index <= currentStage ? 'bg-[#00FF41]' : 'bg-zinc-700'
                }`}
                animate={index === currentStage ? { scale: [1, 1.3, 1] } : {}}
                transition={{ duration: 0.5, repeat: Infinity }}
              />
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
