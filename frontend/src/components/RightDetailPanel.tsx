import React, { useEffect, useRef, useMemo, useState } from 'react';
import { ChangeItem, ChangeReviewStatus, ReviewSummary } from '../types/comparison';
import {
  CheckCircle2,
  Flag,
  ChevronRight,
  ChevronLeft,
  Crosshair,
  Filter,
  AlertCircle,
  FileText,
  Sliders,
  Sparkles,
} from 'lucide-react';
import { getCategoryConfig } from '../config/categories';

/** Left-stripe + selected-border accent per category (hex for inline styles). */
const CATEGORY_STRIPE: Record<string, string> = {
  dimension_change: '#f59e0b',
  note_change: '#3b82f6',
  note_or_annotation_change: '#3b82f6',
  addition: '#10b981',
  removal: '#f43f5e',
  symbol_change: '#8b5cf6',
  symbol_or_code_change: '#8b5cf6',
  needs_human_review: '#eab308',
};

interface RightDetailPanelProps {
  changes: ChangeItem[];
  selectedChangeId: string | null;
  onSelectChange: (changeId: string) => void;
  onStatusChange: (changeId: string, status: ChangeReviewStatus) => void;
  isOpen: boolean;
  onToggleOpen: () => void;
  selectedCategoryFilter: string;
  onCategoryFilterChange: (cat: string) => void;
  reviewSummary?: ReviewSummary | null;
  activeTab?: 'changes' | 'summary';
  onTabChange?: (tab: 'changes' | 'summary') => void;
  overallSummary?: string;
  overallSimilarity?: number;
  totalRegionsDetected?: number;
}

export const RightDetailPanel: React.FC<RightDetailPanelProps> = ({
  changes,
  selectedChangeId,
  onSelectChange,
  onStatusChange,
  isOpen,
  onToggleOpen,
  selectedCategoryFilter,
  onCategoryFilterChange,
  reviewSummary,
  activeTab: activeTabProp,
  onTabChange,
  overallSummary,
  overallSimilarity,
  totalRegionsDetected,
}) => {
  const [localTab, setLocalTab] = useState<'changes' | 'summary'>('changes');
  const activeTab = activeTabProp ?? localTab;

  const handleTabChange = (tab: 'changes' | 'summary') => {
    setLocalTab(tab);
    onTabChange?.(tab);
  };

  const itemRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const listContainerRef = useRef<HTMLDivElement>(null);

  // Filter changes for display in the panel list
  const activeChanges = useMemo(() => {
    return changes.filter((c) => c.category !== 'no_change');
  }, [changes]);

  const filteredChanges = useMemo(() => {
    if (selectedCategoryFilter === 'all') return activeChanges;
    return activeChanges.filter((c) => c.category === selectedCategoryFilter);
  }, [activeChanges, selectedCategoryFilter]);

  const selectedChange = useMemo(() => {
    return activeChanges.find((c) => c.id === selectedChangeId) || null;
  }, [activeChanges, selectedChangeId]);

  // Review status metrics counts
  const approvedCount = changes.filter((c) => c.status === 'approved').length;
  const flaggedCount = changes.filter((c) => c.status === 'flagged').length;
  const pendingCount = changes.filter((c) => c.status === 'pending').length;

  const confirmedCount = reviewSummary?.confirmed ?? approvedCount;
  const falsePositiveCount = reviewSummary?.false_positive ?? flaggedCount;
  const unreviewedCount = reviewSummary?.unreviewed ?? pendingCount;

  // Content flag: every stored llm_classification came from the rule-based
  // fallback, so no AI descriptions exist for this comparison.
  const allLlmFallback =
    activeChanges.length > 0 &&
    activeChanges.every((c) => c.llmSource === 'fallback');
  const partialLlmFallback =
    !allLlmFallback && activeChanges.some((c) => c.llmSource === 'fallback');

  // Category breakdown calculation for Summary tab
  const categoryBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    changes.forEach((c) => {
      if (c.category === 'no_change') return;
      counts[c.category] = (counts[c.category] || 0) + 1;
    });

    const mainCategories = [
      { keys: ['dimension_change'], label: 'Dimension', defaultDot: 'bg-amber-500' },
      { keys: ['note_change', 'note_or_annotation_change'], label: 'Note', defaultDot: 'bg-blue-500' },
      { keys: ['addition'], label: 'Added', defaultDot: 'bg-emerald-500' },
      { keys: ['removal'], label: 'Removed', defaultDot: 'bg-rose-500' },
      { keys: ['symbol_change', 'symbol_or_code_change'], label: 'Symbol', defaultDot: 'bg-purple-500' },
    ];

    const resultList: Array<{ key: string; label: string; count: number; dotColor: string }> = [];
    const processedKeys = new Set<string>();

    mainCategories.forEach((cat) => {
      let count = 0;
      cat.keys.forEach((k) => {
        count += counts[k] || 0;
        processedKeys.add(k);
      });
      const config = getCategoryConfig(cat.keys[0]);
      resultList.push({
        key: cat.keys[0],
        label: cat.label,
        count,
        dotColor: config.dotColor || cat.defaultDot,
      });
    });

    // Catch any other categories present in counts
    Object.keys(counts).forEach((k) => {
      if (!processedKeys.has(k)) {
        const config = getCategoryConfig(k);
        resultList.push({
          key: k,
          label: config.shortLabel || config.label,
          count: counts[k],
          dotColor: config.dotColor,
        });
      }
    });

    return resultList;
  }, [changes]);

  // Scroll active item into view within the panel list
  useEffect(() => {
    if (selectedChangeId && itemRefs.current[selectedChangeId]) {
      itemRefs.current[selectedChangeId]?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [selectedChangeId]);

  if (!isOpen) {
    return (
      <div className="shrink-0 flex flex-col items-center py-4 bg-white border-l border-cyprus/15 w-12 h-full transition-all">
        <button
          onClick={onToggleOpen}
          className="p-2 rounded-[8px] text-[#525252] hover:text-[#0A0A0A] hover:bg-[#F5F5F5] transition-colors"
          title="Expand Change Details Panel"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="mt-8 flex flex-col items-center gap-6 text-xs font-medium text-[#737373] [writing-mode:vertical-lr] rotate-180">
          <span>Change review panel</span>
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <span>{activeChanges.length} items</span>
        </div>
      </div>
    );
  }

  return (
    <aside
      id="right-detail-panel"
      className="w-[380px] xl:w-[420px] shrink-0 border-l border-cyprus/15 bg-sand flex flex-col h-full overflow-hidden shadow-xs transition-all"
    >
      {/* 1. Header with Title, Collapse button & Review Metrics */}
      <div className="px-4 py-3 border-b border-[#E5E5E5] bg-[#FAFAFA] shrink-0 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-[#0A0A0A]" />
            <h3 className="font-semibold text-[15px] text-[#0A0A0A]">Change Review Panel</h3>
            <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-900 border border-amber-200/80 text-[11px] font-medium">
              {activeChanges.length} deltas
            </span>
          </div>
          <button
            onClick={onToggleOpen}
            className="p-1 rounded-[6px] text-[#525252] hover:text-[#0A0A0A] hover:bg-[#E5E5E5] transition-colors"
            title="Collapse Side Panel"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Relocated Review Status Metrics */}
        <div className="flex items-center gap-1.5 text-xs">
          <span
            className="flex-1 flex items-center justify-center gap-1.5 bg-emerald-50/90 text-emerald-950 py-1.5 px-2 rounded-full border border-emerald-300 font-bold text-xs shadow-2xs"
            title="Confirmed changes"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span><strong className="text-emerald-700 text-sm font-extrabold">{confirmedCount}</strong> Confirmed</span>
          </span>
          <span
            className="flex-1 flex items-center justify-center gap-1.5 bg-rose-50/90 text-rose-950 py-1.5 px-2 rounded-full border border-rose-300 font-bold text-xs shadow-2xs"
            title="False positive flags"
          >
            <Flag className="w-3.5 h-3.5 text-rose-600 shrink-0" />
            <span><strong className="text-rose-700 text-sm font-extrabold">{falsePositiveCount}</strong> False pos</span>
          </span>
          <span
            className="flex-1 flex items-center justify-center gap-1.5 bg-amber-50/90 text-amber-950 py-1.5 px-2 rounded-full border border-amber-300 font-bold text-xs shadow-2xs"
            title="Pending review"
          >
            <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
            <span><strong className="text-amber-700 text-sm font-extrabold">{unreviewedCount}</strong> Pending</span>
          </span>
        </div>
      </div>

      {/* 2. Top Tab Navigation: Changes vs Summary */}
      <div className="flex border-b border-[#E5E5E5] bg-[#FAFAFA] shrink-0 text-xs">
        <button
          type="button"
          onClick={() => handleTabChange('changes')}
          className={`flex-1 py-2 px-3 font-medium border-b-2 text-center transition-all cursor-pointer ${
            activeTab === 'changes'
              ? 'border-cyprus text-cyprus bg-white font-semibold'
              : 'border-transparent text-[#737373] hover:text-[#0A0A0A]'
          }`}
        >
          Changes ({activeChanges.length})
        </button>
        <button
          type="button"
          onClick={() => handleTabChange('summary')}
          className={`flex-1 py-2 px-3 font-medium border-b-2 text-center transition-all cursor-pointer ${
            activeTab === 'summary'
              ? 'border-cyprus text-cyprus bg-white font-semibold'
              : 'border-transparent text-[#737373] hover:text-[#0A0A0A]'
          }`}
        >
          Summary
        </button>
      </div>

      {/* 3. Panel Body: Changes Tab */}
      {activeTab === 'changes' && (
        <>
          {allLlmFallback && (
            <div className="mx-3 mt-3 rounded-[8px] border border-amber-300 bg-amber-50 px-3 py-2.5 shrink-0">
              <p className="text-xs font-semibold text-amber-900">
                AI descriptions unavailable
              </p>
              <p className="mt-0.5 text-xs text-amber-800 leading-relaxed">
                The model call failed for every region, so all descriptions below
                are rule-based text. Check the backend model API key and retry the
                comparison for AI-generated descriptions.
              </p>
            </div>
          )}
          {!allLlmFallback && partialLlmFallback && (
            <div className="mx-3 mt-3 rounded-[8px] border border-amber-200 bg-amber-50/60 px-3 py-2 shrink-0">
              <p className="text-xs text-amber-800">
                Some descriptions are rule-based text — the model call failed for
                those regions.
              </p>
            </div>
          )}
          {/* Selected Item Detail Card */}
          {selectedChange ? (
            <div className="m-3 rounded-[10px] border border-cyprus/15 bg-white p-4 space-y-2.5 shrink-0 max-h-[48%] overflow-y-auto">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-[13px] px-2 py-0.5 rounded-[6px] bg-[#0A0A0A] text-white">
                      {selectedChange.id}
                    </span>
                    <span className="font-mono text-xs text-[#4b5563]">Zone {selectedChange.zone}</span>
                  </div>
                  <h4 className="mt-1 text-sm font-bold text-[#0A0A0A] leading-tight">
                    {selectedChange.affectedFeature || selectedChange.title || selectedChange.category}
                  </h4>
                </div>

                <span className="inline-flex items-center gap-1.5 shrink-0">
                  <span className={`w-2 h-2 rounded-full ${getCategoryConfig(selectedChange.category).dotColor}`} />
                  <span className="text-[13px] font-semibold text-[#374151]">
                    {getCategoryConfig(selectedChange.category).label}
                  </span>
                </span>
              </div>

              {/* AI Description */}
              <div className="bg-[#FAFAFA] rounded-[10px] p-4 border border-[#E5E5E5] text-sm text-[#262626] leading-[1.5]">
                <p className="font-medium text-[#0A0A0A] mb-1 flex items-center gap-1 text-xs">
                  <FileText className="w-3 h-3 text-[#525252]" /> AI Description
                </p>
                {selectedChange.description || 'No detailed description available.'}
              </div>

              {/* Verification Warning if any */}
              {selectedChange.verification?.verified === false && (
                <div className="rounded-[8px] border border-amber-300 bg-amber-50 p-2.5 text-xs">
                  <p className="font-semibold text-amber-900 flex items-center gap-1 text-xs">
                    <AlertCircle className="w-3 h-3 text-amber-600" /> Human Review Required
                  </p>
                  <p className="mt-0.5 text-amber-800 text-xs">
                    {selectedChange.verification.reason || 'Evidence discrepancy detected.'}
                  </p>
                </div>
              )}

              {/* Extracted Values Comparison (Rev A vs Rev B) */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-[#FAFAFA] p-4 rounded-[10px] border-2 border-[#E5E5E5] min-h-[76px]">
                  <span className="text-xs text-[#374151] uppercase block font-bold mb-1">Rev A (Baseline)</span>
                  <span className="text-[#737373] line-through break-words font-semibold text-[14px]">
                    {selectedChange.oldValue || '—'}
                  </span>
                </div>
                <div className="bg-amber-50/50 p-4 rounded-[10px] border-2 border-amber-200 min-h-[76px]">
                  <span className="text-xs text-amber-800 uppercase block font-bold mb-1">Rev B (Modified)</span>
                  <span className="text-[#0A0A0A] font-bold break-words text-[14px]">
                    {selectedChange.newValue || '—'}
                  </span>
                  {selectedChange.delta && (
                    <div className="text-xs font-bold text-amber-700 mt-1">Δ {selectedChange.delta}</div>
                  )}
                </div>
              </div>

              {/* Action Review Buttons */}
              <div className="pt-1 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onStatusChange(selectedChange.id, 'approved')}
                  className={`flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-[8px] text-xs font-semibold border transition-all cursor-pointer ${
                    selectedChange.status === 'approved'
                      ? 'bg-emerald-600 border-emerald-600 text-white shadow-xs'
                      : 'bg-white hover:bg-emerald-50 text-emerald-700 border-emerald-300'
                  }`}
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> Confirm
                </button>
                <button
                  type="button"
                  onClick={() => onStatusChange(selectedChange.id, 'flagged')}
                  className={`flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-[8px] text-xs font-semibold border transition-all cursor-pointer ${
                    selectedChange.status === 'flagged'
                      ? 'bg-rose-600 border-rose-600 text-white shadow-xs'
                      : 'bg-white hover:bg-rose-50 text-rose-700 border-rose-300'
                  }`}
                >
                  <Flag className="w-3.5 h-3.5" /> False Positive
                </button>
              </div>
            </div>
          ) : (
            <div className="p-5 text-center border-b border-[#E5E5E5] shrink-0">
              <Crosshair className="w-6 h-6 text-[#6b7280] mx-auto mb-1" />
              <p className="text-[13px] text-[#4b5563] font-medium">Select a change on the drawing or list below</p>
            </div>
          )}

          {/* All Changes List Header & Filter */}
          <div className="px-4 py-1.5 bg-[#FAFAFA] border-b border-[#E5E5E5] flex items-center justify-between text-xs shrink-0">
            <span className="font-semibold text-[#525252] text-xs">All changes ({filteredChanges.length})</span>
            <div className="flex items-center gap-1">
              <Filter className="w-3 h-3 text-[#737373]" />
              <select
                value={selectedCategoryFilter}
                onChange={(e) => onCategoryFilterChange(e.target.value)}
                className="text-xs bg-white border border-[#E5E5E5] rounded-[4px] px-1.5 py-0.5 text-[#0A0A0A] focus:outline-none cursor-pointer"
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

          {/* Scrollable Changes List */}
          <div ref={listContainerRef} className="flex-1 min-h-0 overflow-y-auto p-3 space-y-2.5">
            {filteredChanges.map((item) => {
              const isSelected = item.id === selectedChangeId;
              const config = getCategoryConfig(item.category);
              const stripe = CATEGORY_STRIPE[item.category] ?? '#a3a3a3';

              return (
                <div
                  key={item.id}
                  ref={(el) => {
                    itemRefs.current[item.id] = el;
                  }}
                  onClick={() => onSelectChange(item.id)}
                  style={
                    isSelected
                      ? { borderColor: stripe, borderLeft: `4px solid ${stripe}` }
                      : { borderColor: `${stripe}2E`, borderLeft: `4px solid ${stripe}` }
                  }
                  className={`p-2.5 rounded-[10px] cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-amber-50/70 border-2 shadow-xs'
                      : 'bg-white border hover:bg-[#FAFAFA]'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`font-mono text-xs font-bold px-1.5 py-0.5 rounded-[4px] ${
                          isSelected ? 'bg-[#0A0A0A] text-white' : 'bg-[#F2F2F2] text-[#0A0A0A]'
                        }`}
                      >
                        {item.id}
                      </span>
                      <span className="text-xs font-mono text-[#4b5563]">{item.zone}</span>
                    </div>

                    <div className="flex items-center gap-1">
                      {item.status === 'approved' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
                      {item.status === 'flagged' && <Flag className="w-3.5 h-3.5 text-rose-600" />}
                      <span className={`w-2 h-2 rounded-full ${config.dotColor}`} />
                    </div>
                  </div>

                  <div className="text-[13px] font-semibold text-[#0A0A0A] truncate">
                    {item.affectedFeature || item.category}
                  </div>

                  <div className="text-xs text-[#374151] truncate mt-0.5">
                    {item.oldValue && item.newValue ? `${item.oldValue} → ${item.newValue}` : item.description}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* 4. Panel Body: Summary Tab */}
      {activeTab === 'summary' && (
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 bg-[#FAFAFA]">
          {/* AI Overall Summary Paragraph */}
          <div className="bg-white rounded-[10px] p-4 border border-[#E5E5E5] shadow-xs space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#0A0A0A]">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>AI Executive Summary</span>
            </div>
            <p className="text-xs text-[#374151] leading-relaxed italic bg-[#FAFAFA] p-3 rounded-[8px] border border-[#F5F5F5]">
              {overallSummary || 'No overall summary paragraph was generated for this drawing comparison.'}
            </p>
          </div>

          {/* Review Status Stat Cards */}
          <div className="space-y-2.5">
            <span className="text-xs font-bold text-[#0A0A0A] block uppercase tracking-wide">
              Review status
            </span>
            <div className="grid grid-cols-3 gap-2.5">
              <div className="bg-emerald-50/90 border-2 border-emerald-300 p-3.5 rounded-[12px] flex flex-col justify-between shadow-2xs transition-all hover:border-emerald-400">
                <span className="text-xs font-bold text-emerald-900 flex items-center gap-1.5 truncate">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" /> Confirmed
                </span>
                <span className="text-2xl font-extrabold text-emerald-700 mt-2 font-mono">{confirmedCount}</span>
              </div>

              <div className="bg-rose-50/90 border-2 border-rose-300 p-3.5 rounded-[12px] flex flex-col justify-between shadow-2xs transition-all hover:border-rose-400">
                <span className="text-xs font-bold text-rose-900 flex items-center gap-1.5 truncate">
                  <Flag className="w-4 h-4 text-rose-600 shrink-0" /> False pos
                </span>
                <span className="text-2xl font-extrabold text-rose-700 mt-2 font-mono">{falsePositiveCount}</span>
              </div>

              <div className="bg-amber-50/90 border-2 border-amber-300 p-3.5 rounded-[12px] flex flex-col justify-between shadow-2xs transition-all hover:border-amber-400">
                <span className="text-xs font-bold text-amber-900 flex items-center gap-1.5 truncate">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" /> Pending
                </span>
                <span className="text-2xl font-extrabold text-amber-700 mt-2 font-mono">{unreviewedCount}</span>
              </div>
            </div>
          </div>

          {/* Overall Similarity Percentage */}
          <div className="bg-white rounded-[10px] p-4 border border-[#E5E5E5] shadow-xs flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold text-[#525252] block">
                Overall similarity
              </span>
              <span className="text-2xl font-bold text-[#0A0A0A] font-mono">
                {overallSimilarity != null ? `${(overallSimilarity * 100).toFixed(1)}%` : '—'}
              </span>
            </div>
            {totalRegionsDetected != null && (
              <div className="text-right">
                <span className="text-[11px] text-[#737373] block">Regions detected</span>
                <span className="text-sm font-bold font-mono text-[#0A0A0A]">{totalRegionsDetected}</span>
              </div>
            )}
          </div>

          {/* Category Breakdown */}
          <div className="bg-white rounded-[10px] p-4 border border-[#E5E5E5] shadow-xs space-y-3">
            <span className="text-xs font-semibold text-[#525252] block">
              Category breakdown
            </span>
            <div className="space-y-2">
              {categoryBreakdown.map(({ key, label, count, dotColor }) => (
                <div key={key} className="flex items-center justify-between text-xs py-1.5 border-b border-[#F5F5F5] last:border-0">
                  <div className="flex items-center gap-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${dotColor}`} />
                    <span className="font-medium text-[#262626]">{label}</span>
                  </div>
                  <span className="font-mono font-bold text-[#0A0A0A] px-2 py-0.5 rounded-[4px] bg-[#FAFAFA] border border-[#E5E5E5]">
                    {count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
