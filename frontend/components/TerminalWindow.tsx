'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Circle, Minus, X, Zap } from 'lucide-react';

interface TerminalWindowProps {
  title: string;
  logs: string[];
  variant: 'red' | 'blue';
  isActive?: boolean;
  typingSpeed?: number;
}

export default function TerminalWindow({ 
  title, 
  logs, 
  variant,
  isActive = false,
  typingSpeed = 50
}: TerminalWindowProps) {
  const [displayedLogs, setDisplayedLogs] = useState<string[]>([]);
  const [currentLogIndex, setCurrentLogIndex] = useState(0);
  const [currentCharIndex, setCurrentCharIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const terminalRef = useRef<HTMLDivElement>(null);

  const colors = {
    red: {
      accent: 'text-red-500',
      border: 'border-red-500/20',
      glow: 'shadow-[0_0_40px_rgba(239,68,68,0.1)]',
      headerBg: 'bg-gradient-to-r from-red-500/10 to-transparent',
      badge: 'bg-red-500/10 text-red-400 border-red-500/20',
      prompt: 'text-red-400',
      dot: 'bg-red-500',
    },
    blue: {
      accent: 'text-blue-400',
      border: 'border-blue-500/20',
      glow: 'shadow-[0_0_40px_rgba(96,165,250,0.1)]',
      headerBg: 'bg-gradient-to-r from-blue-500/10 to-transparent',
      badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      prompt: 'text-blue-400',
      dot: 'bg-blue-500',
    },
  };

  const c = colors[variant];

  // Typing effect
  useEffect(() => {
    if (!isActive || currentLogIndex >= logs.length) {
      setIsTyping(false);
      return;
    }

    setIsTyping(true);
    const currentLog = logs[currentLogIndex];

    if (currentCharIndex < currentLog.length) {
      const timeout = setTimeout(() => {
        setCurrentCharIndex(prev => prev + 1);
      }, typingSpeed);
      return () => clearTimeout(timeout);
    } else {
      // Move to next log
      const timeout = setTimeout(() => {
        setDisplayedLogs(prev => [...prev, currentLog]);
        setCurrentLogIndex(prev => prev + 1);
        setCurrentCharIndex(0);
      }, 300);
      return () => clearTimeout(timeout);
    }
  }, [isActive, currentLogIndex, currentCharIndex, logs, typingSpeed]);

  // Auto-scroll
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [displayedLogs, currentCharIndex]);

  // Reset when logs change
  useEffect(() => {
    setDisplayedLogs([]);
    setCurrentLogIndex(0);
    setCurrentCharIndex(0);
  }, [logs]);

  const currentlyTyping = currentLogIndex < logs.length ? logs[currentLogIndex].slice(0, currentCharIndex) : '';

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.6 }}
      className={`
        relative overflow-hidden
        bg-black/60 backdrop-blur-xl rounded-2xl
        border border-white/5
        transition-all duration-500
        ${isActive ? c.glow : ''}
      `}
    >
      {/* Glassmorphism Header */}
      <div className={`
        relative px-4 py-3
        bg-zinc-900/80 backdrop-blur-md
        border-b border-white/5
        ${c.headerBg}
      `}>
        <div className="flex items-center justify-between">
          {/* Window Controls */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              <Circle className="w-3 h-3 text-zinc-700 fill-zinc-700" />
              <Circle className="w-3 h-3 text-zinc-700 fill-zinc-700" />
              <Circle className="w-3 h-3 text-zinc-700 fill-zinc-700" />
            </div>
          </div>

          {/* Title */}
          <div className="flex items-center gap-2">
            <Terminal className={`w-4 h-4 ${c.accent}`} />
            <span className="text-sm font-mono text-zinc-400">{title}</span>
          </div>

          {/* Status Badge */}
          <div className={`
            flex items-center gap-1.5 px-2 py-1 
            rounded-full text-xs font-mono
            border ${c.badge}
          `}>
            {isActive && (
              <motion.div
                className={`w-1.5 h-1.5 rounded-full ${c.dot}`}
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              />
            )}
            <span>{isActive ? 'LIVE' : 'IDLE'}</span>
          </div>
        </div>
      </div>

      {/* Terminal Content */}
      <div 
        ref={terminalRef}
        className="h-64 overflow-y-auto p-4 font-mono text-sm scrollbar-thin scrollbar-track-transparent scrollbar-thumb-zinc-800"
      >
        <AnimatePresence mode="popLayout">
          {displayedLogs.map((log, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className="flex items-start gap-2 mb-2"
            >
              <span className={`${c.prompt} select-none`}>›</span>
              <span className="text-zinc-300 leading-relaxed">{formatLog(log, variant)}</span>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Currently typing line */}
        {isTyping && currentlyTyping && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-start gap-2"
          >
            <span className={`${c.prompt} select-none`}>›</span>
            <span className="text-zinc-300">
              {formatLog(currentlyTyping, variant)}
              <motion.span
                animate={{ opacity: [1, 0] }}
                transition={{ duration: 0.5, repeat: Infinity }}
                className={`inline-block w-2 h-4 ml-0.5 ${variant === 'red' ? 'bg-red-500' : 'bg-blue-400'}`}
              />
            </span>
          </motion.div>
        )}

        {/* Idle state */}
        {!isActive && displayedLogs.length === 0 && (
          <div className="flex items-center justify-center h-full text-zinc-600">
            <div className="text-center">
              <Terminal className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-xs">Awaiting commands...</p>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// Helper function to format and highlight log output
function formatLog(log: string, variant: 'red' | 'blue'): React.ReactNode {
  const highlights: { [key: string]: string } = {
    '[RECON]': 'text-yellow-400',
    '[DETECT]': 'text-orange-400',
    '[EXPLOIT]': 'text-red-400',
    '[PAYLOAD]': 'text-purple-400',
    '[EXECUTE]': 'text-red-500',
    '[SUCCESS]': 'text-green-400',
    '[VERIFY]': 'text-cyan-400',
    '[REPORT]': 'text-zinc-400',
    '[INIT]': 'text-blue-400',
    '[ANALYZE]': 'text-cyan-400',
    '[PATCH]': 'text-green-400',
    '[TEST]': 'text-yellow-400',
    '✓': 'text-green-400',
    '✗': 'text-red-400',
  };

  let result = log;
  
  // Check for highlights and wrap them
  for (const [key, className] of Object.entries(highlights)) {
    if (log.includes(key)) {
      const parts = log.split(key);
      return (
        <>
          <span className={className}>{key}</span>
          <span>{parts[1]}</span>
        </>
      );
    }
  }

  return result;
}
