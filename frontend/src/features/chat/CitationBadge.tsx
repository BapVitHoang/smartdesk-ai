import React from 'react';
import { ExternalLink, BookOpen } from 'lucide-react';
import { Citation } from '../../types';

interface CitationBadgeProps {
  citation: Citation;
  onClick?: (citation: Citation) => void;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ citation, onClick }) => {
  return (
    <button
      type="button"
      onClick={() => onClick && onClick(citation)}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-medium border border-indigo-200/80 transition-all cursor-pointer shadow-2xs group text-left"
      title={citation.snippet || citation.title || citation.code}
    >
      <BookOpen className="w-3 h-3 text-indigo-500 shrink-0" />
      <span className="truncate max-w-[200px]">{citation.code}</span>
      <ExternalLink className="w-2.5 h-2.5 text-indigo-400 group-hover:text-indigo-600 shrink-0 ml-0.5" />
    </button>
  );
};
