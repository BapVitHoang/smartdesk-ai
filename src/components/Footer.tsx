import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer id="app-footer" className="bg-white border-t border-slate-200 px-4 py-2 flex flex-wrap items-center justify-between text-xs text-slate-500 shrink-0">
      <div className="flex items-center gap-3">
        <span>
          <strong className="text-slate-700">SmartDesk AI</strong> © 2025 • Enterprise Edition
        </span>
        <span className="hidden sm:inline text-slate-300">•</span>
        <span className="hidden sm:inline">Stack: React 19 + FastAPI Async + Tailwind CSS + Gemini RAG</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
        <span className="text-slate-600 font-medium">All Systems Operational</span>
      </div>
    </footer>
  );
};
