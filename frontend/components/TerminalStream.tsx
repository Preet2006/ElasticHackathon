'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Terminal } from 'lucide-react';
import { useEffect, useState } from 'react';

interface TerminalStreamProps {
  title: string;
  color: 'red' | 'blue' | 'green';
  logs: string[];
  isActive?: boolean;
}

export default function TerminalStream({ 
  title, 
  color, 
  logs,
  isActive = true 
}: TerminalStreamProps) {
  const [displayedLogs, setDisplayedLogs] = useState<string[]>([]);
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [showCursor, setShowCursor] = useState(true);

  // Color mappings
  const colorClasses = {
    red: {
      border: 'border-red-500/20',
      text: 'text-red-500',
      glow: 'glow-red',
      shadow: 'shadow-[0_0_15px_rgba(239,68,68,0.1)]',
    },
    blue: {
      border: 'border-blue-500/20',
      text: 'text-blue-500',
      glow: 'glow-blue',
      shadow: 'shadow-[0_0_15px_rgba(59,130,246,0.1)]',
    },
    green: {
      border: 'border-green-500/20',
      text: 'text-green-500',
      glow: 'glow-green',
      shadow: 'shadow-[0_0_15px_rgba(34,197,94,0.1)]',
    },
  };

  const colors = colorClasses[color];

  // Simulate typing effect
  useEffect(() => {
    if (!isActive) return;

    if (currentLineIndex < logs.length) {
      const timer = setTimeout(() => {
        setDisplayedLogs(prev => [...prev, logs[currentLineIndex]]);
        setCurrentLineIndex(prev => prev + 1);
      }, 300 + Math.random() * 200); // Random delay for realistic effect

      return () => clearTimeout(timer);
    }
  }, [currentLineIndex, logs, isActive]);

  // Blinking cursor
  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);

    return () => clearInterval(cursorInterval);
  }, []);

  // Reset when logs change
  useEffect(() => {
    setDisplayedLogs([]);
    setCurrentLineIndex(0);
  }, [logs]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`
        bg-black border ${colors.border} rounded-lg overflow-hidden
        ${colors.shadow} terminal-glow
      `}
    >
      {/* Terminal Header */}
      <div className={`px-4 py-3 border-b ${colors.border} bg-zinc-900/30 flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          <Terminal className={`w-4 h-4 ${colors.text}`} />
          <span className={`font-mono text-sm font-semibold ${colors.text} ${colors.glow}`}>
            {title}
          </span>
        </div>
        <div className="flex gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500/50" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
          <div className="w-3 h-3 rounded-full bg-green-500/50" />
        </div>
      </div>

      {/* Terminal Content */}
      <div className="p-4 h-[400px] overflow-y-auto font-mono text-sm custom-scrollbar">
        <AnimatePresence>
          {displayedLogs.map((log, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className="mb-2"
            >
              <span className="text-zinc-500 mr-2">{`>`}</span>
              <span className={colors.text}>{log}</span>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Blinking Cursor */}
        {isActive && (
          <motion.span
            animate={{ opacity: showCursor ? 1 : 0 }}
            className={`inline-block w-2 h-4 ${colors.text} bg-current ml-1`}
          />
        )}

        {/* Scanning effect overlay */}
        {isActive && currentLineIndex < logs.length && (
          <motion.div
            className={`absolute left-0 right-0 h-px ${colors.text} opacity-30`}
            animate={{ y: [0, 400, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          />
        )}
      </div>
    </motion.div>
  );
}
