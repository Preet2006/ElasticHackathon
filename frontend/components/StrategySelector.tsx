'use client';

import { motion } from 'framer-motion';
import { Cpu, MousePointer2, Sparkles, ChevronRight } from 'lucide-react';

interface StrategySelectorProps {
  onSelectAuto: () => void;
  onSelectManual: () => void;
  threatCount: number;
}

export default function StrategySelector({ 
  onSelectAuto, 
  onSelectManual,
  threatCount 
}: StrategySelectorProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
      />

      {/* Modal Card */}
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -20, scale: 0.95 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-xl mx-4"
      >
        {/* Glow Effect */}
        <div className="absolute -inset-1 bg-gradient-to-r from-[#00FF41]/10 via-transparent to-[#00FF41]/10 rounded-2xl blur-xl opacity-50" />
        
        <div className="
          relative p-8
          bg-zinc-950 rounded-2xl
          border border-white/10
          shadow-2xl
        ">
          {/* Header */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.1, type: 'spring', stiffness: 200 }}
              className="
                inline-flex items-center justify-center w-14 h-14 mb-4
                bg-[#00FF41]/5 rounded-2xl border border-[#00FF41]/10
              "
            >
              <Sparkles className="w-7 h-7 text-[#00FF41]" />
            </motion.div>
            
            <h2 className="text-2xl font-semibold text-white mb-2 tracking-tight">
              Select Prioritization Strategy
            </h2>
            <p className="text-zinc-500 text-sm">
              {threatCount} vulnerabilities detected. Choose how to proceed.
            </p>
          </div>

          {/* Options */}
          <div className="space-y-3">
            {/* Option A: Auto */}
            <motion.button
              onClick={onSelectAuto}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              className="
                group w-full p-5 text-left
                bg-zinc-900/50 rounded-xl
                border border-white/5
                hover:border-[#00FF41]/30 hover:bg-zinc-900
                hover:shadow-[0_0_30px_rgba(0,255,65,0.05)]
                transition-all duration-300
              "
            >
              <div className="flex items-center gap-4">
                <div className="
                  flex items-center justify-center w-12 h-12
                  bg-[#00FF41]/5 rounded-xl
                  border border-[#00FF41]/10
                  group-hover:border-[#00FF41]/30
                  transition-colors
                ">
                  <Cpu className="w-5 h-5 text-[#00FF41]" />
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-white font-medium">System Prioritization</span>
                    <span className="px-1.5 py-0.5 text-[9px] font-mono text-[#00FF41] bg-[#00FF41]/10 rounded border border-[#00FF41]/20">
                      AI
                    </span>
                  </div>
                  <p className="text-sm text-zinc-500">
                    Auto-remediates Critical risks first based on AI risk scoring
                  </p>
                </div>

                <ChevronRight className="w-5 h-5 text-zinc-600 group-hover:text-[#00FF41] group-hover:translate-x-1 transition-all" />
              </div>
            </motion.button>

            {/* Option B: Manual */}
            <motion.button
              onClick={onSelectManual}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              className="
                group w-full p-5 text-left
                bg-zinc-900/50 rounded-xl
                border border-white/5
                hover:border-blue-500/30 hover:bg-zinc-900
                hover:shadow-[0_0_30px_rgba(59,130,246,0.05)]
                transition-all duration-300
              "
            >
              <div className="flex items-center gap-4">
                <div className="
                  flex items-center justify-center w-12 h-12
                  bg-blue-500/5 rounded-xl
                  border border-blue-500/10
                  group-hover:border-blue-500/30
                  transition-colors
                ">
                  <MousePointer2 className="w-5 h-5 text-blue-400" />
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-white font-medium">Manual Selection</span>
                    <span className="px-1.5 py-0.5 text-[9px] font-mono text-blue-400 bg-blue-500/10 rounded border border-blue-500/20">
                      OPERATOR
                    </span>
                  </div>
                  <p className="text-sm text-zinc-500">
                    Choose specific targets for remediation manually
                  </p>
                </div>

                <ChevronRight className="w-5 h-5 text-zinc-600 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
              </div>
            </motion.button>
          </div>

          {/* Footer */}
          <div className="mt-6 pt-6 border-t border-white/5">
            <p className="text-[11px] text-zinc-600 text-center font-mono">
              TIP: System prioritization processes CRITICAL vulnerabilities first
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
