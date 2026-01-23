'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Zap, ArrowRight, Loader2 } from 'lucide-react';

interface CommandBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isLoading?: boolean;
  placeholder?: string;
}

export default function CommandBar({ 
  value, 
  onChange, 
  onSubmit, 
  isLoading = false,
  placeholder = "Enter repository URL..."
}: CommandBarProps) {
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut: Cmd+K to focus
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="w-full max-w-2xl mx-auto"
    >
      <div
        className={`
          relative group
          transition-all duration-500 ease-out
          ${isFocused 
            ? 'shadow-[0_0_60px_rgba(0,255,65,0.15)]' 
            : 'shadow-none'
          }
        `}
      >
        {/* Glow Effect */}
        <AnimatePresence>
          {isFocused && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute -inset-[1px] rounded-2xl bg-gradient-to-r from-[#00FF41]/20 via-[#00FF41]/10 to-[#00FF41]/20 blur-sm"
            />
          )}
        </AnimatePresence>

        {/* Main Container */}
        <div
          className={`
            relative flex items-center gap-4 px-6 py-4
            bg-zinc-900/80 backdrop-blur-xl rounded-2xl
            border transition-all duration-300
            ${isFocused 
              ? 'border-[#00FF41]/30' 
              : 'border-white/5 hover:border-white/10'
            }
          `}
        >
          {/* Search Icon */}
          <Search 
            className={`
              w-5 h-5 transition-colors duration-300
              ${isFocused ? 'text-[#00FF41]' : 'text-zinc-500'}
            `}
          />

          {/* Input */}
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={(e) => e.key === 'Enter' && !isLoading && onSubmit()}
            placeholder={placeholder}
            className="
              flex-1 bg-transparent outline-none
              text-zinc-100 placeholder-zinc-600
              font-mono text-sm
            "
          />

          {/* Keyboard Shortcut Hint */}
          <div className="hidden sm:flex items-center gap-1 text-zinc-600 text-xs">
            <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded border border-white/5 font-mono">
              ⌘
            </kbd>
            <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded border border-white/5 font-mono">
              K
            </kbd>
          </div>

          {/* Submit Button */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onSubmit}
            disabled={isLoading || !value.trim()}
            className={`
              relative flex items-center gap-2 px-5 py-2.5
              rounded-xl font-medium text-sm
              transition-all duration-300
              ${isLoading || !value.trim()
                ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                : 'bg-[#00FF41]/10 text-[#00FF41] hover:bg-[#00FF41]/20 border border-[#00FF41]/20'
              }
            `}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Scanning</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                <span>Scan</span>
                <ArrowRight className="w-3 h-3 opacity-50" />
              </>
            )}

            {/* Pulse Animation when ready */}
            {!isLoading && value.trim() && (
              <motion.div
                className="absolute inset-0 rounded-xl bg-[#00FF41]/5"
                animate={{
                  opacity: [0, 0.5, 0],
                  scale: [1, 1.05, 1],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              />
            )}
          </motion.button>
        </div>
      </div>

      {/* Helper Text */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="text-center mt-4 text-zinc-600 text-xs font-mono"
      >
        Try: <span className="text-zinc-400">Preet2006/testing</span> for a demo scan
      </motion.p>
    </motion.div>
  );
}
