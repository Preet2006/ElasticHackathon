'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, X, ChevronDown, HelpCircle } from 'lucide-react';

interface Question {
  id: string;
  question: string;
  answer: string;
}

const HELP_QUESTIONS: Question[] = [
  {
    id: 'start-scan',
    question: 'How do I start a scan?',
    answer: 'Paste your GitHub repository URL into the input box above and click "Scan Target". The scan typically completes in 30-60 seconds depending on repository size.',
  },
  {
    id: 'red-blue-team',
    question: 'What does the Red/Blue Team do?',
    answer: 'The Red Team finds vulnerabilities by analyzing your code and attempting exploits. The Blue Team then automatically generates secure code fixes and creates Pull Requests for you to review.',
  },
  {
    id: 'code-safety',
    question: 'Is my code safe?',
    answer: 'Yes. We run all scans in isolated Docker containers with no network access. Your source code is never stored permanently and is deleted immediately after analysis.',
  },
  {
    id: 'scan-duration',
    question: 'How long does a scan take?',
    answer: 'A typical scan takes 30-60 seconds for small repositories and 2-3 minutes for larger ones. The Red/Blue Team remediation process takes about 1-2 minutes per vulnerability.',
  },
  {
    id: 'vulnerability-types',
    question: 'What types of vulnerabilities can you detect?',
    answer: 'CodeJanitor detects common security issues including hardcoded credentials, SQL injection, weak cryptography, insecure randomness, path traversal, command injection, and more.',
  },
];

export default function HelpWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const togglePanel = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      setExpandedId(null); // Reset expanded state when opening
    }
  };

  const toggleQuestion = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <>
      {/* Floating Action Button */}
      <motion.button
        onClick={togglePanel}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="
          fixed bottom-6 right-6 z-50
          w-14 h-14
          bg-emerald-600 hover:bg-emerald-500
          text-white
          rounded-full
          shadow-lg shadow-emerald-600/20
          flex items-center justify-center
          transition-colors
          border border-emerald-500/20
        "
        aria-label="Help & Support"
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div
              key="close"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <X className="w-6 h-6" />
            </motion.div>
          ) : (
            <motion.div
              key="help"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <HelpCircle className="w-6 h-6" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Help Panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop for mobile */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={togglePanel}
              className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
            />

            {/* Panel */}
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="
                fixed bottom-24 right-6 z-40
                w-[calc(100vw-3rem)] sm:w-96
                max-h-[calc(100vh-12rem)]
                bg-zinc-900
                border border-zinc-800
                rounded-2xl
                shadow-2xl
                overflow-hidden
                flex flex-col
              "
            >
              {/* Header */}
              <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-emerald-500/10 rounded-xl flex items-center justify-center">
                    <MessageCircle className="w-5 h-5 text-emerald-500" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold text-base leading-tight">Quick Help</h3>
                    <p className="text-zinc-500 text-xs leading-relaxed">Get started in seconds</p>
                  </div>
                </div>
              </div>

              {/* Questions List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {HELP_QUESTIONS.map((item, index) => (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="overflow-hidden"
                  >
                    <button
                      onClick={() => toggleQuestion(item.id)}
                      className="
                        w-full text-left
                        px-4 py-3
                        bg-zinc-800/30 hover:bg-zinc-800/50
                        border border-zinc-800 hover:border-zinc-700
                        rounded-xl
                        transition-all
                        group
                      "
                    >
                      <div className="flex items-start justify-between gap-3">
                        <span className="text-white text-sm font-medium leading-relaxed flex-1">
                          {item.question}
                        </span>
                        <ChevronDown
                          className={`
                            w-4 h-4 text-zinc-500 transition-transform mt-0.5 flex-shrink-0
                            ${expandedId === item.id ? 'rotate-180' : ''}
                          `}
                        />
                      </div>
                    </button>

                    {/* Answer */}
                    <AnimatePresence>
                      {expandedId === item.id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="px-4 py-3 mt-1 bg-emerald-500/5 border border-emerald-500/10 rounded-xl">
                            <p className="text-zinc-400 text-sm leading-relaxed">
                              {item.answer}
                            </p>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))}
              </div>

              {/* Footer */}
              <div className="px-6 py-3 border-t border-zinc-800 bg-zinc-900/50">
                <p className="text-zinc-600 text-xs text-center leading-relaxed">
                  Need more help? Check our{' '}
                  <a
                    href="https://github.com/aadi230763/CODE-JANITOR"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-500 hover:text-emerald-400 underline"
                  >
                    documentation
                  </a>
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
