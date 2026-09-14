import React, { useState, useMemo, useEffect } from 'react';
import { ChangeItem, ChangeCategory, ChangeReviewStatus, ReviewSummary } from '../types/comparison';
import { ChangeBadge } from './ChangeBadge';
import { getCategoryConfig } from '../config/categories';
import {
  Search,
  CheckCircle2,
  ClipboardList,
  Flag,
  Crosshair,
  ArrowUpDown,
  Download,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react';

interface ReportTableProps {
  changes: ChangeItem[];
  overallSimilarity?: number;
  totalRegionsDetected?: number;
  totalChanges?: number;
  verificationSummary?: {
    ocrLlmAgreementCount: number;
    ocrLlmDisagreementCount: number;
  };
  selectedChangeId: string | null;
  /** Backend report id — required for the Export PDF download. */
  reportId?: string;
  /** Persisted review counts; local change statuses are the fallback. */
  reviewSummary?: ReviewSummary | null;
  onSelectChange: (changeId: string) => void;
  onStatusChange: (changeId: string, status: ChangeReviewStatus) => void;
}

export interface TableColumnSchema<T> {
  key: keyof T | 'actions' | 'custom_delta';
  label: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
}

export const ReportTable: React.FC<ReportTableProps> = ({
  changes,
  overallSimilarity = 0,
  totalRegionsDetected = 0,
  totalChanges = changes.length,
  verificationSummary,
  selectedChangeId,
  reportId,
  reviewSummary,
  onSelectChange,
  onStatusChange,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<keyof ChangeItem>('id');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [detailChange, setDetailChange] = useState<ChangeItem | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExportPdf = async () => {
    if (!reportId || exporting) return;
    setExporting(true);
    setExportError(null);
    try {
      const { downloadAnnotatedPdf } = await import('../services/comparisonService');
      await downloadAnnotatedPdf(reportId);
    } catch (err: any) {
      setExportError(err?.message || 'Export PDF failed.');
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    if (!detailChange) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDetailChange(null);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [detailChange]);

  // Dynamic schema definition
  const schemaColumns: TableColumnSchema<ChangeItem>[] = [
    {
      key: 'category',
      label: 'Category',
      sortable: true,
      render: (item) => <ChangeBadge category={item.category} size="sm" showIcon showDot />,
    },
    {
      key: 'affectedFeature',
      label: 'Modification Description',
      sortable: true,
      render: (item) => (
        <div className="max-w-md">
          <div className="text-xs font-semibold text-[#0A0A0A] tracking-tight">
            {item.affectedFeature}
          </div>
          <div className="text-[12px] text-[#525252] line-clamp-2 mt-0.5 leading-normal">
            {item.description}
          </div>
        </div>
      ),
    },
    {
      key: 'oldValue',
      label: 'Rev A (Baseline)',
      sortable: true,
      render: (item) => (
        <div className="font-mono text-xs text-[#A3A3A3] line-through">
          {item.oldValue}
        </div>
      ),
    },
    {
      key: 'newValue',
      label: 'Rev B (Modified)',
      sortable: true,
      render: (item) => (
        <div>
          <div className="font-mono text-xs font-bold text-[#0A0A0A]">
            {item.newValue}
          </div>
          {item.delta && (
            <div className="text-[10px] font-mono text-amber-700 mt-0.5 font-medium">
              Δ {item.delta}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      label: 'Locate',
      align: 'right',
      render: (item) => (
        <div className="inline-flex items-center gap-1.5 justify-end">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onStatusChange(item.id, 'approved');
            }}
            title="Confirm change (persisted to backend)"
            className={`inline-flex items-center p-1.5 rounded-[8px] border transition-colors cursor-pointer ${
              item.status === 'approved'
                ? 'bg-emerald-600 border-emerald-600 text-white'
                : 'bg-white hover:bg-emerald-50 text-[#525252] hover:text-emerald-700 border-[#E5E5E5]'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onStatusChange(item.id, 'flagged');
            }}
            title="Flag as false positive (persisted to backend)"
            className={`inline-flex items-center p-1.5 rounded-[8px] border transition-colors cursor-pointer ${
              item.status === 'flagged'
                ? 'bg-rose-600 border-rose-600 text-white'
                : 'bg-white hover:bg-rose-50 text-[#525252] hover:text-rose-700 border-[#E5E5E5]'
            }`}
          >
            <Flag className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelectChange(item.id);
            }}
            className="inline-flex items-center gap-1 px-3 py-1 text-[11px] font-mono text-[#525252] hover:text-[#0A0A0A] bg-white hover:bg-[#FAFAFA] rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer font-medium"
          >
            <Crosshair className="w-3 h-3" />
            <span>Zoom</span>
          </button>
        </div>
      ),
    },
  ];
  // Raw OCR is retained for diagnostics but intentionally hidden from the user-facing table.
  const visibleSchemaColumns = schemaColumns.filter(
    (column) => column.key !== 'oldValue' && column.key !== 'newValue'
  );

  // Category change counts
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { all: changes.length };
    changes.forEach((c) => {
      counts[c.category] = (counts[c.category] || 0) + 1;
    });
    return counts;
  }, [changes]);
  const categoryKeys = useMemo(
    () => Array.from(new Set(changes.map((change) => change.category).filter(Boolean))),
    [changes]
  );

  // Filtering & Sorting
  const filteredChanges = useMemo(() => {
    return changes.filter((item) => {
      const matchesSearch =
        searchQuery === '' ||
        item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.affectedFeature.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.oldValue.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.newValue.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.zone.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCategory =
        selectedCategoryFilter === 'all' || item.category === selectedCategoryFilter;

      const matchesStatus =
        statusFilter === 'all' || item.status === statusFilter;

      return matchesSearch && matchesCategory && matchesStatus;
    });
  }, [changes, searchQuery, selectedCategoryFilter, statusFilter]);

  const sortedChanges = useMemo(() => {
    return [...filteredChanges].sort((a, b) => {
      const valA = a[sortField] || '';
      const valB = b[sortField] || '';
      if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredChanges, sortField, sortDirection]);

  const handleSort = (field: keyof ChangeItem) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const approvedCount = changes.filter((c) => c.status === 'approved').length;
  const flaggedCount = changes.filter((c) => c.status === 'flagged').length;
  const pendingCount = changes.filter((c) => c.status === 'pending').length;

  // Backend-persisted counts win when the summary has loaded; otherwise local state.
  const confirmedCount = reviewSummary?.confirmed ?? approvedCount;
  const falsePositiveCount = reviewSummary?.false_positive ?? flaggedCount;
  const unreviewedCount = reviewSummary?.unreviewed ?? pendingCount;

  // Resolve summary unreviewed_changes (page_number/change_index) to row ids for highlighting.
  const unreviewedIds = useMemo(() => {
    if (!reviewSummary) return null;
    const byAddress = new Map<string, string>();
    changes.forEach((c) => {
      if (c.pageNumber != null && c.changeIndex != null) {
        byAddress.set(`${c.pageNumber}:${c.changeIndex}`, c.id);
      }
    });
    const ids = new Set<string>();
    reviewSummary.unreviewed_changes.forEach((u) => {
      const id = byAddress.get(`${u.page_number}:${u.change_index}`);
      if (id) ids.add(id);
    });
    return ids;
  }, [reviewSummary, changes]);

  return (
    <div
      id="change-report-table-section"
      className="bg-sand border border-cyprus/20 rounded-[12px] overflow-hidden shadow-xs flex flex-col"
    >
      {/* Table Header Bar */}
      <div className="px-6 py-4 border-b border-[#E5E5E5] flex flex-wrap items-center justify-between gap-4 bg-[#FAFAFA]">
        <div className="flex items-center gap-3">
          <h2 className="text-[15px] font-semibold text-[#111827] tracking-tight">
            Detected Modifications
          </h2>
          <span className="bg-amber-50 text-amber-900 border border-amber-200 px-2.5 py-0.5 rounded-[8px] text-[11px] font-mono font-bold">
            {changes.length} Deltas Found
          </span>
          <span className="text-[13px] text-[#525252] font-mono hidden md:inline">
            ISO 10209 Schema Compliant
          </span>
        </div>

        {/* Right side stats, Summary & Export buttons */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-[#525252]">
            <span
              className="flex items-center gap-1.5 bg-white text-emerald-700 px-2.5 py-1 rounded-[8px] border border-[#E5E5E5]"
              title="Backend status: confirmed"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              {confirmedCount} Confirmed
            </span>
            <span
              className="flex items-center gap-1.5 bg-white text-rose-700 px-2.5 py-1 rounded-[8px] border border-[#E5E5E5]"
              title="Backend status: false_positive"
            >
              <Flag className="w-3.5 h-3.5 text-rose-600" />
              {falsePositiveCount} False positive
            </span>
            <span
              className="flex items-center gap-1.5 bg-white text-amber-700 px-2.5 py-1 rounded-[8px] border border-[#E5E5E5]"
              title="Backend status: unreviewed"
            >
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              {unreviewedCount} Unreviewed
            </span>
          </div>

          <button
            id="btn-toggle-review-summary"
            onClick={() => setShowSummary(!showSummary)}
            title="Show persisted review summary"
            className={`inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-[9999px] border transition-colors cursor-pointer shadow-xs ${
              showSummary
                ? 'bg-cyprus text-white border-cyprus'
                : 'bg-white hover:bg-[#FAFAFA] text-[#525252] hover:text-[#0A0A0A] border-[#E5E5E5]'
            }`}
          >
            <ClipboardList className="w-3.5 h-3.5" />
            <span>Summary</span>
          </button>

          <span className="inline-flex flex-col items-end gap-1">
            <button
              id="btn-export-pdf"
              onClick={handleExportPdf}
              disabled={!reportId || exporting}
              title={reportId ? 'Download annotated diff PDF' : 'Export needs a persisted backend report'}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-cyprus hover:bg-cyprus-deep disabled:opacity-50 text-white text-xs font-semibold rounded-[9999px] transition-colors cursor-pointer shadow-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{exporting ? 'Exporting…' : 'Export PDF'}</span>
            </button>
            {exportError && (
              <span className="text-[11px] font-mono text-rose-700">{exportError}</span>
            )}
          </span>

          <button
            id="btn-toggle-table-collapse"
            type="button"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-[#FAFAFA] text-[#0A0A0A] border border-[#E5E5E5] rounded-[8px] text-xs font-mono font-medium transition-colors cursor-pointer"
            title={isCollapsed ? 'Expand Redline Table' : 'Collapse Redline Table'}
          >
            {isCollapsed ? (
              <>
                <ChevronDown className="w-3.5 h-3.5 text-[#525252]" />
                <span className="hidden sm:inline">Expand Table</span>
              </>
            ) : (
              <>
                <ChevronUp className="w-3.5 h-3.5 text-[#525252]" />
                <span className="hidden sm:inline">Collapse Table</span>
              </>
            )}
          </button>
        </div>
      </div>

      {showSummary && !isCollapsed && (
        <div className="px-6 py-4 border-b border-[#E5E5E5] bg-[#FAFAFA]">
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <span className="px-2.5 py-1 rounded-[8px] bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
              {confirmedCount} confirmed
            </span>
            <span className="px-2.5 py-1 rounded-[8px] bg-rose-50 text-rose-800 border border-rose-200 font-semibold">
              {falsePositiveCount} false positive
            </span>
            <span className="px-2.5 py-1 rounded-[8px] bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
              {unreviewedCount} unreviewed
            </span>
            {!reviewSummary && (
              <span className="text-[#A3A3A3]">(local counts — backend summary not loaded)</span>
            )}
          </div>
          {unreviewedIds && unreviewedIds.size > 0 && (
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {[...unreviewedIds].map((id) => (
                <button
                  key={id}
                  onClick={() => onSelectChange(id)}
                  className="px-2 py-0.5 rounded-[6px] bg-white border border-amber-300 text-[11px] font-mono text-amber-800 hover:border-[#0A0A0A] hover:text-[#0A0A0A] transition-colors cursor-pointer"
                >
                  {id}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {!isCollapsed && (
        <>
          {/* Filter and Search Bar */}
      <div className="p-4 border-b border-[#E5E5E5] flex flex-wrap items-center justify-between gap-3 bg-white">
        {/* Search input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-3.5 h-3.5 text-[#A3A3A3] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="table-search-input"
            type="text"
            placeholder="Search delta ID, description, zone (e.g. C-4)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-2 text-[13px] bg-[#FAFAFA] border border-[#E5E5E5] rounded-[8px] focus:bg-white focus:outline-none focus:border-[#0A0A0A] text-[#0A0A0A] placeholder-[#6b7280] font-mono"
          />
        </div>

      </div>

      {/* Category Filter Chips */}
      <div className="px-4 py-3 bg-[#FAFAFA] border-b border-[#E5E5E5] flex flex-wrap items-center gap-2">
        <button
          onClick={() => setSelectedCategoryFilter('all')}
          className={`px-3 py-1.5 rounded-[8px] text-xs font-mono transition-colors cursor-pointer ${
            selectedCategoryFilter === 'all'
              ? 'bg-cyprus text-white font-semibold'
              : 'bg-white hover:bg-[#F5F5F5] text-[#525252] border border-[#E5E5E5]'
          }`}
        >
          All Categories ({categoryCounts['all'] || 0})
        </button>

        {categoryKeys.map((catKey) => {
          const config = getCategoryConfig(catKey);
          const count = categoryCounts[catKey] || 0;
          if (count === 0) return null;
          const isSelected = selectedCategoryFilter === catKey;

          return (
            <button
              key={catKey}
              onClick={() => setSelectedCategoryFilter(catKey)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[8px] text-xs font-mono transition-colors cursor-pointer ${
                isSelected
                  ? 'bg-cyprus text-white font-semibold'
                  : 'bg-white hover:bg-[#F5F5F5] text-[#525252] border border-[#E5E5E5]'
              }`}
            >
              <span>{config.shortLabel}</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded-[4px] font-mono ${
                  isSelected ? 'bg-neutral-800 text-white' : 'bg-[#F2F2F2] text-[#525252]'
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Schema-Driven Table */}
      <div className="overflow-x-auto">
        <table id="table-change-report" className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#FAFAFA] border-b border-[#E5E5E5] text-xs font-mono text-[#374151] uppercase tracking-wider font-bold">
              {visibleSchemaColumns.map((col) => (
                <th
                  key={String(col.key)}
                  className={`px-6 py-2.5 font-bold select-none ${
                    col.align === 'center'
                      ? 'text-center'
                      : col.align === 'right'
                      ? 'text-right'
                      : 'text-left'
                  } ${col.sortable ? 'cursor-pointer hover:text-[#0A0A0A]' : ''}`}
                  onClick={() => {
                    if (col.sortable && col.key !== 'actions' && col.key !== 'custom_delta') {
                      handleSort(col.key as keyof ChangeItem);
                    }
                  }}
                >
                  <div
                    className={`inline-flex items-center gap-1 ${
                      col.align === 'center'
                        ? 'justify-center'
                        : col.align === 'right'
                        ? 'justify-end'
                        : 'justify-start'
                    }`}
                  >
                    <span>{col.label}</span>
                    {col.sortable && sortField === col.key && (
                      <ArrowUpDown className="w-3 h-3 text-[#0A0A0A]" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#FAFAFA]">
            {sortedChanges.length > 0 ? (
              sortedChanges.map((item) => {
                const isSelected = selectedChangeId === item.id;
                const isUnreviewed = showSummary && unreviewedIds != null && unreviewedIds.has(item.id);
                return (
                  <tr
                    key={item.id}
                    id={`table-row-${item.id}`}
                    onClick={() => {
                      onSelectChange(item.id);
                      setDetailChange(item);
                    }}
                    className={`group transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-amber-50/40 border-l-2 border-l-[#0A0A0A]'
                        : isUnreviewed
                        ? 'bg-amber-50/30 border-l-2 border-l-amber-400 hover:bg-amber-50/50'
                        : 'hover:bg-[#FAFAFA]'
                    }`}
                    title={isUnreviewed ? 'Unreviewed (per backend summary)' : undefined}
                  >
                    {visibleSchemaColumns.map((col) => {
                      return (
                        <td
                          key={String(col.key)}
                          className={`px-6 py-3 align-middle text-[13px] ${
                            col.align === 'center'
                              ? 'text-center'
                              : col.align === 'right'
                              ? 'text-right'
                              : 'text-left'
                          }`}
                        >
                          {col.render
                            ? col.render(item)
                            : String((item as any)[col.key] || '')}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={visibleSchemaColumns.length} className="px-4 py-8 text-center text-xs text-[#A3A3A3] font-mono">
                  No revision changes found matching your current filter criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {detailChange && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setDetailChange(null);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="change-detail-title"
            className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-[14px] border border-cyprus/20 bg-white shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4 border-b border-[#E5E5E5] px-6 py-4">
              <div>
                <p className="text-xs font-mono font-semibold uppercase tracking-wider text-[#374151]">Modification details</p>
                <h2 id="change-detail-title" className="mt-1 text-lg font-semibold text-[#0A0A0A]">
                  {detailChange.affectedFeature || detailChange.title || detailChange.category}
                </h2>
              </div>
              <button
                type="button"
                aria-label="Close modification details"
                onClick={() => setDetailChange(null)}
                className="rounded-full p-2 text-[#737373] hover:bg-[#F5F5F5] hover:text-[#0A0A0A]"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid gap-4 px-6 py-5 sm:grid-cols-2">
              {detailChange.verification?.verified === false && (
                <div className="sm:col-span-2 rounded-[8px] border border-amber-300 bg-amber-50 p-3">
                  <p className="text-xs font-semibold text-amber-900">Needs human review</p>
                  <p className="mt-1 text-xs text-amber-800">{detailChange.verification.reason || 'OCR and LLM evidence disagree for this change.'}</p>
                </div>
              )}
              <div className="sm:col-span-2">
                    <p className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Description</p>
                <p className="mt-1 text-sm leading-relaxed text-[#262626]">
                  {detailChange.description || 'No description provided by the backend.'}
                </p>
              </div>
              <div>
                    <p className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Category</p>
                <div className="mt-1"><ChangeBadge category={detailChange.category} size="sm" showIcon showDot /></div>
              </div>
              <div>
                    <p className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Confidence / Severity</p>
                <p className="mt-1 text-sm text-[#262626]">
                  {detailChange.classificationConfidence != null
                    ? `${(detailChange.classificationConfidence * 100).toFixed(1)}%`
                    : '—'}{' '}
                  <span className="text-[#737373]">/ {detailChange.severity || '—'}</span>
                </p>
                {detailChange.ocrConfidence && (
                  <p className="mt-1 text-[11px] text-[#737373]">
                    OCR: Old {detailChange.ocrConfidence.old}% · New {detailChange.ocrConfidence.new}%
                  </p>
                )}
              </div>
              <details className="sm:col-span-2 rounded-[8px] border border-[#E5E5E5] bg-[#FAFAFA] p-3">
                  <summary className="cursor-pointer text-xs font-mono uppercase tracking-wider text-[#374151]">
                  Technical OCR (optional)
                </summary>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                      <p className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Rev A OCR</p>
                    <p className="mt-2 whitespace-pre-wrap break-words font-mono text-xs text-[#525252]">{detailChange.oldValue || '—'}</p>
                  </div>
                  <div>
                      <p className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Rev B OCR</p>
                    <p className="mt-2 whitespace-pre-wrap break-words font-mono text-xs text-[#525252]">{detailChange.newValue || '—'}</p>
                  </div>
                </div>
              </details>
              <div className="sm:col-span-2 border-t border-[#E5E5E5] pt-4">
                  <p className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Detected region</p>
                <p className="mt-1 font-mono text-xs text-[#525252]">
                  x: {detailChange.region.x}, y: {detailChange.region.y}, width: {detailChange.region.width}, height: {detailChange.region.height}
                </p>
              </div>
              {detailChange.delta && (
                <div>
                    <p className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Delta</p>
                  <p className="mt-1 font-mono text-sm text-amber-700">{detailChange.delta}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Table Footer */}
      <div className="px-6 py-2.5 border-t border-[#E5E5E5] bg-[#FAFAFA] flex items-center justify-between text-[11px] font-mono text-[#525252]">
        <div className="flex items-center gap-4">
          <span>
            Showing {filteredChanges.length} of {totalChanges} total changes
          </span>
          <span>•</span>
          <span className="font-semibold text-[#525252]">Similarity {(overallSimilarity * 100).toFixed(1)}%</span>
          <span>•</span>
          <span className="font-semibold text-[#525252]">{totalRegionsDetected} Regions Detected</span>
          {verificationSummary && (
            <>
              <span>â€¢</span>
              <span className={verificationSummary.ocrLlmDisagreementCount > 0 ? 'font-semibold text-amber-700' : 'font-semibold text-emerald-700'}>
                {verificationSummary.ocrLlmDisagreementCount} Need Review
              </span>
            </>
          )}
        </div>

        <div className="hidden sm:block">
          <span>Click any row to auto-focus and zoom CAD viewport</span>
        </div>
      </div>
        </>
      )}
    </div>
  );
};
