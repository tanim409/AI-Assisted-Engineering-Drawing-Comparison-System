import React, { useEffect } from 'react';
import { ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import { ChangeItem } from '../types/comparison';

interface NavigationToolbarProps {
  changes: ChangeItem[];
  selectedChangeId: string | null;
  onSelectChange: (changeId: string) => void;
  selectedCategoryFilter: string;
  onCategoryFilterChange: (cat: string) => void;
}

export const NavigationToolbar: React.FC<NavigationToolbarProps> = ({
  changes,
  selectedChangeId,
  onSelectChange,
  selectedCategoryFilter,
  onCategoryFilterChange,
}) => {
  // Filter out `no_change` items
  const activeChanges = React.useMemo(() => {
    const list = changes.filter((c) => c.category !== 'no_change');
    if (selectedCategoryFilter === 'all') return list;
    return list.filter((c) => c.category === selectedCategoryFilter);
  }, [changes, selectedCategoryFilter]);

  const currentIndex = activeChanges.findIndex((c) => c.id === selectedChangeId);
  const totalCount = activeChanges.length;

  const handlePrev = React.useCallback(() => {
    if (totalCount === 0) return;
    const nextIdx = currentIndex <= 0 ? totalCount - 1 : currentIndex - 1;
    onSelectChange(activeChanges[nextIdx].id);
  }, [currentIndex, totalCount, activeChanges, onSelectChange]);

  const handleNext = React.useCallback(() => {
    if (totalCount === 0) return;
    const nextIdx = currentIndex >= totalCount - 1 ? 0 : currentIndex + 1;
    onSelectChange(activeChanges[nextIdx].id);
  }, [currentIndex, totalCount, activeChanges, onSelectChange]);

  // Keyboard shortcut listeners (← / →)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept keypresses inside inputs or textareas
      if (
        document.activeElement?.tagName === 'INPUT' ||
        document.activeElement?.tagName === 'TEXTAREA' ||
        document.activeElement?.tagName === 'SELECT'
      ) {
        return;
      }

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handlePrev();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleNext();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlePrev, handleNext]);

  return (
    <div
      id="navigation-toolbar"
      className="bg-white/90 backdrop-blur-md border border-[#E5E5E5] rounded-[9999px] px-4 py-1.5 flex items-center gap-3 shadow-xs text-xs select-none"
    >
      <button
        type="button"
        id="btn-nav-prev"
        onClick={handlePrev}
        disabled={totalCount === 0}
        className="inline-flex items-center gap-1 px-3 py-1 rounded-[9999px] bg-white border border-[#E5E5E5] text-[#0A0A0A] hover:bg-[#F5F5F5] active:scale-95 disabled:opacity-40 transition-all cursor-pointer font-medium shadow-xs text-xs"
        title="Previous change (← ArrowLeft)"
      >
        <ChevronLeft className="w-3.5 h-3.5" />
        <span>Prev</span>
      </button>

      <div className="flex items-center gap-1 px-2.5 py-0.5 bg-[#FAFAFA] rounded-[9999px] border border-[#E5E5E5] text-xs font-medium text-[#525252]">
        <span>Change</span>
        <span className="text-amber-700 font-semibold font-mono">
          {currentIndex >= 0 ? currentIndex + 1 : 0}
        </span>
        <span className="text-[#A3A3A3]">of</span>
        <span className="font-semibold text-[#0A0A0A]">{totalCount}</span>
      </div>

      <button
        type="button"
        id="btn-nav-next"
        onClick={handleNext}
        disabled={totalCount === 0}
        className="inline-flex items-center gap-1 px-3 py-1 rounded-[9999px] bg-white border border-[#E5E5E5] text-[#0A0A0A] hover:bg-[#F5F5F5] active:scale-95 disabled:opacity-40 transition-all cursor-pointer font-medium shadow-xs text-xs"
        title="Next change (→ ArrowRight)"
      >
        <span>Next</span>
        <ChevronRight className="w-3.5 h-3.5" />
      </button>

      <div className="h-4 w-[1px] bg-[#E5E5E5] mx-1" />

      <div className="flex items-center gap-1.5 text-xs text-[#525252]">
        <Filter className="w-3.5 h-3.5 text-[#737373]" />
        <select
          value={selectedCategoryFilter}
          onChange={(e) => onCategoryFilterChange(e.target.value)}
          className="bg-transparent text-[#0A0A0A] font-medium focus:outline-none cursor-pointer text-xs"
        >
          <option value="all">All categories</option>
          <option value="dimension_change">Dimension</option>
          <option value="addition">Addition</option>
          <option value="removal">Removal</option>
          <option value="text_change">Text</option>
          <option value="symbol_change">Symbol</option>
        </select>
      </div>
    </div>
  );
};
