'use client';

import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

interface BentoCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  accent?: 'green' | 'red' | 'blue' | 'yellow' | 'neutral';
  delay?: number;
  className?: string;
}

const accentColors = {
  green: {
    icon: 'text-[#00FF41]',
    glow: 'group-hover:shadow-[0_0_30px_rgba(0,255,65,0.1)]',
    border: 'group-hover:border-[#00FF41]/20',
    badge: 'bg-[#00FF41]/10 text-[#00FF41]',
  },
  red: {
    icon: 'text-red-500',
    glow: 'group-hover:shadow-[0_0_30px_rgba(239,68,68,0.1)]',
    border: 'group-hover:border-red-500/20',
    badge: 'bg-red-500/10 text-red-500',
  },
  blue: {
    icon: 'text-blue-400',
    glow: 'group-hover:shadow-[0_0_30px_rgba(96,165,250,0.1)]',
    border: 'group-hover:border-blue-400/20',
    badge: 'bg-blue-400/10 text-blue-400',
  },
  yellow: {
    icon: 'text-yellow-400',
    glow: 'group-hover:shadow-[0_0_30px_rgba(250,204,21,0.1)]',
    border: 'group-hover:border-yellow-400/20',
    badge: 'bg-yellow-400/10 text-yellow-400',
  },
  neutral: {
    icon: 'text-zinc-400',
    glow: 'group-hover:shadow-[0_0_30px_rgba(161,161,170,0.05)]',
    border: 'group-hover:border-white/10',
    badge: 'bg-zinc-800 text-zinc-400',
  },
};

export function BentoCard({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  accent = 'neutral',
  delay = 0,
  className = ''
}: BentoCardProps) {
  const colors = accentColors[accent];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ scale: 1.01 }}
      className={`
        group relative p-6
        bg-zinc-900/50 backdrop-blur-md rounded-2xl
        border border-white/5
        transition-all duration-500 ease-out
        ${colors.glow} ${colors.border}
        ${className}
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className={`p-2.5 rounded-xl ${colors.badge}`}>
          <Icon className={`w-5 h-5`} />
        </div>
        {subtitle && (
          <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-wider">
            {subtitle}
          </span>
        )}
      </div>

      {/* Value */}
      <div className="space-y-1">
        <motion.p 
          className="text-4xl font-light text-white tracking-tight"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.2 }}
        >
          {value}
        </motion.p>
        <p className="text-sm text-zinc-500 font-medium">{title}</p>
      </div>

      {/* Subtle gradient overlay on hover */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
    </motion.div>
  );
}

interface BentoGridProps {
  children: React.ReactNode;
  className?: string;
}

export function BentoGrid({ children, className = '' }: BentoGridProps) {
  return (
    <div className={`grid grid-cols-2 md:grid-cols-4 gap-4 ${className}`}>
      {children}
    </div>
  );
}

// Large Card variant for featured content
export function BentoCardLarge({ 
  title, 
  value, 
  subtitle,
  icon: Icon, 
  accent = 'neutral',
  delay = 0,
  children,
  className = ''
}: BentoCardProps & { children?: React.ReactNode }) {
  const colors = accentColors[accent];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ scale: 1.005 }}
      className={`
        group relative p-6 col-span-2
        bg-zinc-900/50 backdrop-blur-md rounded-2xl
        border border-white/5
        transition-all duration-500 ease-out
        ${colors.glow} ${colors.border}
        ${className}
      `}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-4">
          <div className={`inline-flex p-2.5 rounded-xl ${colors.badge}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <p className="text-5xl font-light text-white tracking-tight mb-1">{value}</p>
            <p className="text-sm text-zinc-500">{title}</p>
          </div>
        </div>
        {children}
      </div>

      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
    </motion.div>
  );
}
