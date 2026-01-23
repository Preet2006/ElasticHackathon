'use client';

import { Shield, LayoutDashboard, Activity, Settings, Circle } from 'lucide-react';
import { motion } from 'framer-motion';
import { useState } from 'react';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/' },
  { icon: Activity, label: 'Live Ops', href: '/live-ops' },
  { icon: Settings, label: 'Settings', href: '/settings' },
];

export default function Sidebar() {
  const [activeIndex, setActiveIndex] = useState(0);

  return (
    <motion.aside 
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="fixed left-0 top-0 h-screen w-64 bg-zinc-900/50 border-r border-white/10 backdrop-blur-xl z-50"
    >
      {/* Header */}
      <div className="p-6 border-b border-white/10">
        <motion.div 
          className="flex items-center gap-3"
          whileHover={{ scale: 1.02 }}
        >
          <Shield className="w-8 h-8 text-green-400 animate-pulse-glow" />
          <div>
            <h1 className="text-xl font-bold glow-green">CodeJanitor</h1>
            <p className="text-xs text-zinc-400 font-mono">v2.0 PHASE-8</p>
          </div>
        </motion.div>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-2">
        {navItems.map((item, index) => {
          const Icon = item.icon;
          const isActive = activeIndex === index;
          
          return (
            <motion.button
              key={item.label}
              onClick={() => setActiveIndex(index)}
              whileHover={{ x: 4 }}
              whileTap={{ scale: 0.98 }}
              className={`
                w-full flex items-center gap-3 px-4 py-3 rounded-lg
                transition-all duration-200
                ${isActive 
                  ? 'bg-green-500/10 border border-green-500/20 text-green-400' 
                  : 'text-zinc-400 hover:text-zinc-100 hover:bg-white/5'
                }
              `}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
              {isActive && (
                <motion.div
                  layoutId="activeIndicator"
                  className="ml-auto w-2 h-2 rounded-full bg-green-400"
                  initial={false}
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                />
              )}
            </motion.button>
          );
        })}
      </nav>

      {/* System Status */}
      <div className="absolute bottom-0 left-0 right-0 p-6 border-t border-white/10 bg-zinc-900/80">
        <div className="space-y-3">
          <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider">System Status</p>
          
          <motion.div 
            className="flex items-center justify-between"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <div className="flex items-center gap-2">
              <Circle className="w-2 h-2 fill-green-400 text-green-400 animate-pulse" />
              <span className="text-sm text-zinc-300">Docker</span>
            </div>
            <span className="text-xs font-mono text-green-400">ONLINE</span>
          </motion.div>

          <motion.div 
            className="flex items-center justify-between"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            <div className="flex items-center gap-2">
              <Circle className="w-2 h-2 fill-green-400 text-green-400 animate-pulse" />
              <span className="text-sm text-zinc-300">LLM</span>
            </div>
            <span className="text-xs font-mono text-green-400">CONNECTED</span>
          </motion.div>

          <motion.div 
            className="flex items-center justify-between"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            <div className="flex items-center gap-2">
              <Circle className="w-2 h-2 fill-blue-400 text-blue-400 animate-pulse" />
              <span className="text-sm text-zinc-300">Network</span>
            </div>
            <span className="text-xs font-mono text-blue-400">HOST MODE</span>
          </motion.div>
        </div>
      </div>
    </motion.aside>
  );
}
