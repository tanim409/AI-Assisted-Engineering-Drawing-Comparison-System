import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Download,
  FolderOpen,
  MoreHorizontal,
  Play,
  Plus,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react';
import {
  compareRevisions,
  createDrawing,
  downloadHistoryExport,
  getCompletedReport,
  getDrawingHistory,
  getHiddenRevisionIds,
  listDrawings,
  listReports,
  registerRevision,
  removeDrawingFromLibrary,
  removeReportFromLibrary,
  removeRevisionFromLibrary,
  renameDrawing,
  SavedReportSummary,
} from '../services/drawingService';
import { runDrawingComparison } from '../services/comparisonService';
import { ChangeBadge } from './ChangeBadge';
import {
  ComparisonResult,
  ConsecutivePair,
  DrawingHistory,
  DrawingSummary,
  RevisionInfo,
} from '../types/comparison';

interface DrawingLibraryProps {
  onLoadComparison: (result: ComparisonResult) => void;
  onClose: () => void;
}

export const DrawingLibrary: React.FC<DrawingLibraryProps> = ({ onLoadComparison, onClose }) => {
  const [activeTab, setActiveTab] = useState<'drawings' | 'reports'>('drawings');
  const [drawings, setDrawings] = useState<DrawingSummary[]>([]);
  const [reports, setReports] = useState<SavedReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [busy, setBusy] = useState(false);

  // History view state
  const [activeDrawingId, setActiveDrawingId] = useState<string | null>(null);
  const [history, setHistory] = useState<DrawingHistory | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedPair, setSelectedPair] = useState<{ from?: string; to?: string }>({});
  const [jobMessage, setJobMessage] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [confirmingRemoveId, setConfirmingRemoveId] = useState<string | null>(null);
  const [confirmingRemoveReportId, setConfirmingRemoveReportId] = useState<string | null>(null);
  const [hiddenRevisionIds, setHiddenRevisionIds] = useState<Set<string>>(() => getHiddenRevisionIds());
  const [confirmingRemoveRevisionId, setConfirmingRemoveRevisionId] = useState<string | null>(null);

  const visibleRevisions = (history?.revisions ?? []).filter((r) => !hiddenRevisionIds.has(r.revision_id));
  const rawComparisons = history?.all_comparisons ?? history?.consecutive_pairs ?? [];
  const visibleComparisons = rawComparisons.filter(
    (p) => !hiddenRevisionIds.has(p.old_revision_id) && !hiddenRevisionIds.has(p.new_revision_id)
  );

  const hasNameInput = newName.trim().length > 0;
  const [revisionFile, setRevisionFile] = useState<File | null>(null);
  const [revisionLabel, setRevisionLabel] = useState('');

  // Quick-compare result stays inside this section (no navigation, no drawing created).
  const [quickResult, setQuickResult] = useState<ComparisonResult | null>(null);
  const [quickError, setQuickError] = useState<string | null>(null);
  const quickAbortRef = useRef<AbortController | null>(null);

  // New-drawing tile expansion state
  const [creating, setCreating] = useState(false);

  // Open overflow menu ("...") per drawing card (only one at a time)
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  // Per-drawing status details (updated-at + pending pair counts), loaded
  // lazily so the grid renders immediately and badges fill in when ready.
  const [drawingDetails, setDrawingDetails] = useState<
    Record<string, { updatedAt?: string; pending: number; totalPairs: number }>
  >({});

  const refreshDrawings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dList, rList] = await Promise.all([listDrawings(), listReports()]);
      setDrawings(dList);
      setReports(rList);
    } catch (err: any) {
      setError(err?.message || 'Could not load drawings or reports.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshDrawings();
  }, [refreshDrawings]);

  useEffect(() => {
    if (drawings.length === 0) return;
    let cancelled = false;
    // Only fetch details for drawings not already in drawingDetails map
    const missingDrawings = drawings.filter((d) => !drawingDetails[d.drawing_id]);
    if (missingDrawings.length === 0) return;

    Promise.allSettled(
      missingDrawings.map(async (d) => {
        const h = await getDrawingHistory(d.drawing_id);
        const pairs = h.consecutive_pairs ?? [];
        const revs = [...(h.revisions ?? [])].sort((a, b) => a.sequence_number - b.sequence_number);
        return {
          id: d.drawing_id,
          updatedAt: revs.length > 0 ? revs[revs.length - 1].uploaded_at : undefined,
          pending: pairs.filter((p) => !p.has_comparison).length,
          totalPairs: pairs.length,
        };
      })
    ).then((results) => {
      if (cancelled) return;
      setDrawingDetails((prev) => {
        const next = { ...prev };
        results.forEach((r) => {
          if (r.status === 'fulfilled' && r.value) next[r.value.id] = r.value;
        });
        return next;
      });
    });
    return () => {
      cancelled = true;
    };
  }, [drawings, drawingDetails]);

  const handleOpenReport = async (reportId: string) => {
    setBusy(true);
    setJobMessage('Loading comparison report…');
    try {
      const result = await getCompletedReport(reportId);
      setJobMessage(null);
      onLoadComparison(result);
    } catch (err: any) {
      setJobMessage(null);
      setError(err?.message || 'Could not load comparison report.');
    } finally {
      setBusy(false);
    }
  };

  const openHistory = async (drawingId: string) => {
    setActiveDrawingId(drawingId);
    setHistoryLoading(true);
    setError(null);
    try {
      setHistory(await getDrawingHistory(drawingId));
    } catch (err: any) {
      setError(err?.message || 'Could not load revision history.');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleCreate = async () => {
    setBusy(true);
    try {
      const created = await createDrawing(newName.trim() || undefined);
      setNewName('');
      setCreating(false);
      // Instantly open history view for newly created drawing (0ms delay)
      setActiveDrawingId(created.drawing_id);
      setHistory({
        drawing_id: created.drawing_id,
        name: created.name,
        revisions: [],
        consecutive_pairs: [],
        all_comparisons: [],
      });
      // Refresh drawing list in background
      void refreshDrawings();
    } catch (err: any) {
      setError(err?.message || 'Could not create drawing.');
    } finally {
      setBusy(false);
    }
  };


  const handleRemove = async (drawingId: string) => {
    try {
      await removeDrawingFromLibrary(drawingId);
      setConfirmingRemoveId(null);
      if (activeDrawingId === drawingId) {
        setActiveDrawingId(null);
        setHistory(null);
        setSelectedPair({});
      }
      await refreshDrawings();
    } catch (err: any) {
      setError(err?.message || 'Could not remove drawing.');
    }
  };

  const handleRemoveReport = async (reportId: string) => {
    try {
      await removeReportFromLibrary(reportId);
      setConfirmingRemoveReportId(null);
      await refreshDrawings();
    } catch (err: any) {
      setError(err?.message || 'Could not remove report.');
    }
  };

  const handleRemoveRevision = async (revisionId: string) => {
    if (!activeDrawingId) return;
    try {
      await removeRevisionFromLibrary(activeDrawingId, revisionId);
      setConfirmingRemoveRevisionId(null);
      setHiddenRevisionIds(getHiddenRevisionIds());
      setSelectedPair((prev) => ({
        from: prev.from === revisionId ? undefined : prev.from,
        to: prev.to === revisionId ? undefined : prev.to,
      }));
      setHistory(await getDrawingHistory(activeDrawingId));
      await refreshDrawings();
    } catch (err: any) {
      setError(err?.message || 'Could not remove revision.');
    }
  };

  const handleRename = async (drawingId: string) => {
    if (!renameValue.trim()) {
      setRenamingId(null);
      return;
    }
    try {
      await renameDrawing(drawingId, renameValue.trim());
      setRenamingId(null);
      await refreshDrawings();
      if (activeDrawingId === drawingId) {
        setHistory(await getDrawingHistory(drawingId));
      }
    } catch (err: any) {
      setError(err?.message || 'Could not rename drawing.');
    }
  };

  const handleRegisterRevision = async () => {
    if (!activeDrawingId || !revisionFile) return;
    setBusy(true);
    try {
      await registerRevision(activeDrawingId, revisionFile, revisionLabel.trim() || undefined);
      setRevisionFile(null);
      setRevisionLabel('');
      setHistory(await getDrawingHistory(activeDrawingId));
      await refreshDrawings();
    } catch (err: any) {
      setError(err?.message || 'Could not register revision.');
    } finally {
      setBusy(false);
    }
  };

  const handleComparePair = async (pair: ConsecutivePair | null, fromId?: string, toId?: string) => {
    if (!activeDrawingId) return;
    setBusy(true);
    setJobMessage('Starting comparison…');
    try {
      const from = pair ? pair.old_revision_id : fromId;
      const to = pair ? pair.new_revision_id : toId;
      const { result, wasCached } = await compareRevisions(activeDrawingId, from, to, {
        onJobProgress: (job) => setJobMessage(job.progress_message || `Job ${job.status}…`),
      });
      setJobMessage(null);
      void wasCached;
      onLoadComparison(result);
    } catch (err: any) {
      setJobMessage(null);
      setError(err?.message || 'Comparison failed.');
    } finally {
      setBusy(false);
    }
  };

  // Quick compare WITHOUT registering: standalone compare creates no drawing
  // and registers no revisions — and the result stays in this section.
  const handleQuickCompare = async (oldFile: File, newFile: File) => {
    setBusy(true);
    setQuickError(null);
    setQuickResult(null);
    setJobMessage('Uploading and comparing…');
    quickAbortRef.current?.abort();
    const controller = new AbortController();
    quickAbortRef.current = controller;
    try {
      const result = await runDrawingComparison({
        old_drawing: oldFile,
        new_drawing: newFile,
        abortSignal: controller.signal,
        onJobProgress: (job) => setJobMessage(job.progress_message || `Job ${job.status}…`),
      });
      setJobMessage(null);
      setQuickResult(result);
    } catch (err: any) {
      setJobMessage(null);
      setQuickError(err?.message || 'Quick compare failed.');
    } finally {
      if (quickAbortRef.current === controller) quickAbortRef.current = null;
      setBusy(false);
    }
  };

  const handleCancelQuickCompare = () => {
    quickAbortRef.current?.abort();
  };

  const handleHistoryExport = async () => {
    if (!activeDrawingId) return;
    try {
      await downloadHistoryExport(activeDrawingId, history?.name);
    } catch (err: any) {
      setError(err?.message || 'History export failed.');
    }
  };

  return (
    <div>
      {/* Library header (unboxed — sits directly on the page) */}
      <div className="px-1 py-2 flex flex-wrap items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-3">
          {activeDrawingId ? (
            <button
              onClick={() => {
                setActiveDrawingId(null);
                setHistory(null);
                setSelectedPair({});
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#F5F5F5] text-[#525252] hover:text-[#0A0A0A] text-xs font-medium rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Library</span>
            </button>
          ) : (
            <FolderOpen className="w-4 h-4 text-[#0A0A0A]" />
          )}
          <h2 className="text-[19px] font-semibold text-[#0A0A0A] tracking-tight">
            {history ? history.name : 'Drawing Library'}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          {!activeDrawingId && (
            <button
              onClick={() => setCreating(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-cyprus hover:bg-cyprus-deep text-white text-xs font-semibold rounded-[9999px] transition-colors cursor-pointer shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Drawing</span>
            </button>
          )}
          {activeDrawingId && (
            <button
              onClick={handleHistoryExport}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-[#FAFAFA] text-[#525252] hover:text-[#0A0A0A] text-xs font-medium rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export History PDF</span>
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-[8px] text-[#A3A3A3] hover:text-[#0A0A0A] hover:bg-white border border-transparent hover:border-[#E5E5E5] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-1 mb-4 px-4 py-2.5 rounded-[12px] bg-rose-50 border border-rose-200 text-xs font-sans text-rose-800">
          {error}
        </div>
      )}
      {jobMessage && (
        <div className="mx-1 mb-4 px-4 py-2.5 rounded-[12px] bg-amber-50 border border-amber-200 text-xs font-sans text-amber-900 animate-pulse">
          {jobMessage}
        </div>
      )}

      {!activeDrawingId ? (
        /* ---- Drawings / Reports main list ---- */
        <div className="py-2 space-y-4">
          {/* Sub-nav tabs (underline style) */}
          <div className="flex items-center gap-6 border-b border-[#E5E5E5]">
            <button
              onClick={() => setActiveTab('drawings')}
              className={`pb-2.5 -mb-px text-[13px] transition-colors cursor-pointer border-b-2 ${
                activeTab === 'drawings'
                  ? 'border-cyprus text-[#0A0A0A] font-bold'
                  : 'border-transparent text-[#737373] hover:text-[#0A0A0A] font-medium'
              }`}
            >
              Drawings ({drawings.length})
            </button>
            <button
              onClick={() => setActiveTab('reports')}
              className={`pb-2.5 -mb-px text-[13px] transition-colors cursor-pointer border-b-2 ${
                activeTab === 'reports'
                  ? 'border-cyprus text-[#0A0A0A] font-bold'
                  : 'border-transparent text-[#737373] hover:text-[#0A0A0A] font-medium'
              }`}
            >
              Saved Reports ({reports.length})
            </button>
          </div>

          {activeTab === 'drawings' ? (
            <>
              {loading ? (
                <p className="text-[13px] text-[#6b7280]">Loading drawings…</p>
              ) : drawings.length === 0 ? (
                <div className="flex flex-col items-center text-center py-12 px-6">
                  <span className="w-14 h-14 rounded-[14px] bg-white border border-cyprus/20 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.08)] flex items-center justify-center mb-4">
                    <FolderOpen className="w-6 h-6 text-cyprus" />
                  </span>
                  <p className="text-[15px] font-semibold text-[#0A0A0A]">No drawings yet</p>
                  <p className="mt-1 text-[13px] text-[#6b7280] max-w-sm">
                    Start your first comparison — register revisions and track every change.
                  </p>
                  {creating ? (
                    <div className="mt-4 w-full max-w-sm">
                      <NewDrawingForm
                        newName={newName}
                        onNameChange={setNewName}
                        onSave={handleCreate}
                        onCancel={() => {
                          setCreating(false);
                          setNewName('');
                        }}
                        busy={busy}
                      />
                    </div>
                  ) : (
                    <button
                      onClick={() => setCreating(true)}
                      className="mt-4 inline-flex items-center gap-1.5 px-5 py-2.5 bg-cyprus hover:bg-cyprus-deep text-white text-[13px] font-semibold rounded-[9999px] transition-colors cursor-pointer shadow-xs"
                    >
                      <Plus className="w-4 h-4" />
                      <span>New drawing</span>
                    </button>
                  )}
                </div>
              ) : (
                <ul className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                  {/* New-drawing tile (always first in grid) */}
                  <li>
                    {creating ? (
                      <NewDrawingForm
                        newName={newName}
                        onNameChange={setNewName}
                        onSave={handleCreate}
                        onCancel={() => {
                          setCreating(false);
                          setNewName('');
                        }}
                        busy={busy}
                        card
                      />
                    ) : (
                      <button
                        onClick={() => setCreating(true)}
                        className="w-full h-full border-2 border-dashed border-[#D4D4D4] hover:border-cyprus rounded-[12px] bg-white/60 hover:bg-white flex flex-col overflow-hidden transition-colors cursor-pointer"
                      >
                        <span className="h-20 w-full flex items-center justify-center">
                          <Plus className="w-6 h-6 text-[#A3A3A3]" />
                        </span>
                        <span className="p-3 text-[13px] font-semibold text-[#525252]">
                          Create new drawing
                        </span>
                      </button>
                    )}
                  </li>
                  {drawings.map((d) => {
                    const detail = drawingDetails[d.drawing_id];
                    const menuOpen = openMenuId === d.drawing_id;
                    return (
                    <li key={d.drawing_id} className="group relative">
                      <div
                        onClick={() => {
                          setOpenMenuId(null);
                          openHistory(d.drawing_id);
                        }}
                        title={`Open ${d.name}`}
                        className="rounded-[12px] bg-white border border-cyprus/20 overflow-hidden shadow-[0_2px_12px_-4px_rgba(0,0,0,0.08)] hover:shadow-[0_14px_32px_-12px_rgba(0,0,0,0.22)] hover:-translate-y-0.5 transition-all cursor-pointer flex flex-col"
                      >
                        {/* Solid color block */}
                        <div className="h-28 w-full" style={{ backgroundColor: cardColorFor(d.drawing_id) }} />
                        {/* Info */}
                        <div className="p-3.5 flex flex-col gap-1 flex-1">
                          {renamingId === d.drawing_id ? (
                            <span
                              className="inline-flex items-center gap-1.5"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <input
                                autoFocus
                                type="text"
                                value={renameValue}
                                onChange={(e) => setRenameValue(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') handleRename(d.drawing_id);
                                  if (e.key === 'Escape') setRenamingId(null);
                                }}
                                className="flex-1 min-w-0 px-2 py-1.5 text-xs bg-white border border-[#0A0A0A] rounded-[8px] focus:outline-none"
                              />
                              <button
                                onClick={() => handleRename(d.drawing_id)}
                                className="px-2.5 py-1.5 bg-cyprus hover:bg-cyprus-deep text-white text-xs rounded-[8px] cursor-pointer shrink-0"
                              >
                                Save
                              </button>
                            </span>
                          ) : confirmingRemoveId === d.drawing_id ? (
                            <span
                              className="inline-flex items-center gap-1.5"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <span className="text-[11px] text-rose-700">Remove?</span>
                              <button
                                onClick={() => handleRemove(d.drawing_id)}
                                className="px-2.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-semibold rounded-[8px] transition-colors cursor-pointer"
                              >
                                Remove
                              </button>
                              <button
                                onClick={() => setConfirmingRemoveId(null)}
                                className="px-2.5 py-1.5 bg-white hover:bg-[#F5F5F5] text-[#525252] text-[11px] rounded-[8px] border border-[#E5E5E5] transition-colors cursor-pointer"
                              >
                                Cancel
                              </button>
                            </span>
                          ) : (
                            <>
                              <p className="text-sm font-bold text-[#111827] tracking-tight truncate" title={d.name}>
                                {d.name}
                              </p>
                              <p className="text-[11px] text-[#6b7280]">
                                {d.revision_count ?? '?'} revisions
                                {detail?.updatedAt ? ` · ${detail.updatedAt}` : ''}
                              </p>
                            </>
                          )}
                        </div>
                      </div>
                      {/* Overflow menu */}
                      <div
                        className="absolute top-2 right-2 transition-opacity"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => setOpenMenuId(menuOpen ? null : d.drawing_id)}
                          title="Card options"
                          aria-label={`Options for ${d.name}`}
                          className="w-7 h-7 rounded-full bg-white/95 border border-[#E5E5E5] shadow-xs flex items-center justify-center text-[#525252] hover:text-[#0A0A0A] transition-colors cursor-pointer"
                        >
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                        {menuOpen && (
                          <div className="absolute right-0 top-8 w-32 bg-white border border-[#E5E5E5] rounded-[8px] shadow-lg py-1 z-10">
                            <button
                              onClick={() => {
                                setOpenMenuId(null);
                                openHistory(d.drawing_id);
                              }}
                              className="w-full text-left px-3 py-1.5 text-xs text-[#0A0A0A] hover:bg-[#FAFAFA] transition-colors cursor-pointer"
                            >
                              Open
                            </button>
                            <button
                              onClick={() => {
                                setOpenMenuId(null);
                                setRenamingId(d.drawing_id);
                                setRenameValue(d.name);
                              }}
                              className="w-full text-left px-3 py-1.5 text-xs text-[#0A0A0A] hover:bg-[#FAFAFA] transition-colors cursor-pointer"
                            >
                              Rename
                            </button>
                            <button
                              onClick={() => {
                                setOpenMenuId(null);
                                setConfirmingRemoveId(d.drawing_id);
                              }}
                              className="w-full text-left px-3 py-1.5 text-xs text-rose-700 hover:bg-rose-50 transition-colors cursor-pointer"
                            >
                              Remove
                            </button>
                          </div>
                        )}
                      </div>
                    </li>
                    );
                  })}
                </ul>
              )}
            </>
          ) : (
            /* Reports Tab */
            <>
              {loading ? (
                <p className="text-[13px] text-[#6b7280]">Loading comparison reports…</p>
              ) : reports.length === 0 ? (
                <p className="text-[13px] text-[#6b7280]">No saved comparison reports found.</p>
              ) : (
                <ul className="divide-y divide-[#F5F5F5] border border-cyprus/20 rounded-[12px] overflow-hidden bg-white shadow-xs">
                  {reports.map((r) => (
                    <li key={r.report_id} className="px-5 py-4 flex items-center justify-between gap-3 bg-white hover:bg-[#FAFAFA] transition-colors">
                      <button onClick={() => handleOpenReport(r.report_id)} className="text-left flex-1 cursor-pointer">
                        <span className="block text-sm font-semibold text-[#0A0A0A]">
                          Report {r.report_id.slice(0, 18)}…
                        </span>
                        <span className="block text-xs text-[#6b7280] mt-0.5">
                          {r.total_changes} deltas · {(r.overall_similarity * 100).toFixed(1)}% similarity · {r.total_pages} {r.total_pages === 1 ? 'page' : 'pages'} · <span className="font-mono">{r.created_at}</span>
                        </span>
                      </button>
                      {confirmingRemoveReportId === r.report_id ? (
                        <span className="inline-flex items-center gap-1.5">
                          <span className="text-[11px] text-rose-700">Delete report?</span>
                          <button
                            onClick={() => handleRemoveReport(r.report_id)}
                            className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-semibold rounded-[9999px] transition-colors cursor-pointer"
                          >
                            Delete
                          </button>
                          <button
                            onClick={() => setConfirmingRemoveReportId(null)}
                            className="px-3 py-1.5 bg-white hover:bg-[#F5F5F5] text-[#525252] text-[11px] rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer"
                          >
                            Cancel
                          </button>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => setConfirmingRemoveReportId(r.report_id)}
                            title="Delete report"
                            className="p-1.5 rounded-[8px] text-[#A3A3A3] hover:text-rose-700 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleOpenReport(r.report_id)}
                            disabled={busy}
                            className="inline-flex items-center gap-1 px-3.5 py-1.5 text-xs text-[#525252] hover:text-[#0A0A0A] bg-white hover:bg-[#F5F5F5] rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer disabled:opacity-50"
                          >
                            <span>Open Report</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      ) : (
        /* ---- History view ---- */
        <div className="py-2 space-y-6">
          {historyLoading || !history ? (
            <p className="text-[13px] text-[#6b7280]">Loading history…</p>
          ) : (
            <>
              <HistoryRevisionList
                revisions={visibleRevisions}
                comparisons={visibleComparisons}
                selectedPair={selectedPair}
                onSelectPair={setSelectedPair}
                onComparePair={(fromId, toId) => handleComparePair(null, fromId, toId)}
                onRemoveRevision={handleRemoveRevision}
                confirmingRemoveRevisionId={confirmingRemoveRevisionId}
                onConfirmRemoveRevision={setConfirmingRemoveRevisionId}
                busy={busy}
              />

              {/* Register new revision container */}
              <div className="border border-cyprus/20 rounded-[12px] p-5 bg-sand/40 shadow-xs space-y-3">
                <h3 className="text-sm font-semibold text-[#0A0A0A] tracking-tight">
                  Register new revision
                </h3>
                <div className="flex flex-wrap items-center gap-2.5">
                  <label className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white text-xs text-[#525252] border border-[#E5E5E5] rounded-[8px] cursor-pointer hover:border-[#0A0A0A] transition-colors">
                    <UploadCloud className="w-3.5 h-3.5 text-[#525252]" />
                    <span className="truncate max-w-[200px]">{revisionFile ? revisionFile.name : 'Choose file…'}</span>
                    <input
                      type="file"
                      className="hidden"
                      onChange={(e) => setRevisionFile(e.target.files?.[0] ?? null)}
                    />
                  </label>
                  <input
                    type="text"
                    value={revisionLabel}
                    onChange={(e) => setRevisionLabel(e.target.value)}
                    placeholder="Label (optional)"
                    className="px-3.5 py-2 text-xs bg-white border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-cyprus text-[#0A0A0A]"
                  />
                  <button
                    onClick={handleRegisterRevision}
                    disabled={busy || !revisionFile}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-cyprus hover:bg-cyprus-deep disabled:opacity-50 text-white text-xs font-semibold rounded-[9999px] transition-colors cursor-pointer shadow-xs"
                  >
                    <UploadCloud className="w-3.5 h-3.5" />
                    <span>Register</span>
                  </button>
                </div>
              </div>

              {/* Upload-and-compare shortcut */}
              <UploadAndCompareInline
                busy={busy}
                jobMessage={jobMessage}
                onCancel={handleCancelQuickCompare}
                onCompare={handleQuickCompare}
              />

              {/* Inline quick-compare result — stays in this section */}
              {(quickResult || quickError) && (
                <QuickCompareResult
                  result={quickResult}
                  error={quickError}
                  onOpenWorkspace={() => {
                    if (quickResult) onLoadComparison(quickResult);
                  }}
                  onDismiss={() => {
                    setQuickResult(null);
                    setQuickError(null);
                  }}
                />
              )}

              {/* Helpful revision management tip container */}
              <div className="border border-cyprus/15 rounded-[12px] p-4 bg-white/60 text-xs text-[#6b7280] space-y-1">
                <p className="font-semibold text-[#0A0A0A]">Revision Tracking Tip</p>
                <p className="leading-relaxed">
                  Select any two revisions using the <span className="font-semibold text-cyprus font-mono">From</span> and <span className="font-semibold text-cyprus font-mono">To</span> controls above to perform instant vector & OCR differential analysis. Exports generated from this sequence will automatically label revisions consistently in order.
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

/** Deterministic card color-block palette (NotebookLM-style tiles). */
const CARD_PALETTE = ['#004741', '#B45309', '#47617B', '#5F7161', '#7C5A78', '#A44A2A'];

function cardColorFor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return CARD_PALETTE[hash % CARD_PALETTE.length];
}

function NewDrawingForm(props: {
  newName: string;
  onNameChange: (value: string) => void;
  onSave: () => void;
  onCancel: () => void;
  busy: boolean;
  card?: boolean;
}) {
  const { newName, onNameChange, onSave, onCancel, busy, card } = props;
  return (
    <div
      className={
        card
          ? 'h-full border border-cyprus/30 rounded-[12px] bg-white shadow-[0_2px_12px_-4px_rgba(0,0,0,0.08)] p-3.5 flex flex-col justify-center gap-2'
          : 'border border-cyprus/30 rounded-[12px] bg-white shadow-[0_2px_12px_-4px_rgba(0,0,0,0.08)] p-4 flex flex-col gap-2.5 text-left'
      }
    >
      <p className="text-sm font-semibold text-[#111827] tracking-tight">
        Name your drawing
      </p>
      <input
        autoFocus
        type="text"
        value={newName}
        onChange={(e) => onNameChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onSave();
          if (e.key === 'Escape') onCancel();
        }}
        placeholder="e.g. Bracket Assembly"
        className="w-full px-2.5 py-1.5 text-[13px] bg-[#FAFAFA] border border-[#E5E5E5] rounded-[8px] focus:bg-white focus:outline-none focus:border-cyprus text-[#0A0A0A] placeholder-[#6b7280]"
      />
      <div className="flex items-center gap-2">
        <button
          onClick={onSave}
          disabled={busy}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-cyprus hover:bg-cyprus-deep disabled:opacity-50 text-white text-xs font-semibold rounded-[9999px] transition-colors cursor-pointer"
        >
          <Check className="w-3.5 h-3.5" />
          <span>Save</span>
        </button>
        <button
          onClick={onCancel}
          className="px-2 py-1.5 text-xs text-[#525252] hover:text-[#0A0A0A] transition-colors cursor-pointer"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function HistoryRevisionList(props: {
  revisions: RevisionInfo[];
  comparisons: ConsecutivePair[];
  selectedPair: { from?: string; to?: string };
  onSelectPair: (pair: { from?: string; to?: string }) => void;
  onComparePair: (fromId?: string, toId?: string) => void;
  onRemoveRevision: (revisionId: string) => void;
  confirmingRemoveRevisionId: string | null;
  onConfirmRemoveRevision: (revisionId: string | null) => void;
  busy: boolean;
}) {
  const {
    revisions, comparisons, selectedPair, onSelectPair, onComparePair,
    onRemoveRevision, confirmingRemoveRevisionId, onConfirmRemoveRevision, busy,
  } = props;
  if (revisions.length === 0) {
    return <p className="text-[13px] text-[#6b7280]">No revisions registered yet.</p>;
  }
  const latest = revisions[revisions.length - 1];
  const previous = revisions.length > 1 ? revisions[revisions.length - 2] : null;
  const fromId = selectedPair.from ?? previous?.revision_id;
  const toId = selectedPair.to ?? latest.revision_id;

  return (
    <div className="space-y-6">
      {/* Revisions Section */}
      <div className="space-y-3">
        <h3 className="text-[15px] font-semibold text-[#0A0A0A] tracking-tight">Revisions</h3>
        <ul className="divide-y divide-[#F5F5F5] border border-cyprus/20 rounded-[12px] overflow-hidden bg-white shadow-xs">
          {revisions.map((r) => (
            <li key={r.revision_id} className="px-5 py-4 bg-white flex items-center justify-between gap-3 hover:bg-[#FAFAFA] transition-colors">
              <div>
                <span className="text-sm font-semibold text-[#0A0A0A]">
                  Rev {r.sequence_number}{r.revision_label ? ` (${r.revision_label})` : ''}
                </span>
                <span className="block text-xs text-[#6b7280] mt-0.5">
                  {r.original_filename || 'File'} · {r.page_count} {r.page_count === 1 ? 'page' : 'pages'} · <span className="font-mono">{r.uploaded_at}</span>
                </span>
              </div>
              {confirmingRemoveRevisionId === r.revision_id ? (
                <span className="inline-flex items-center gap-1.5">
                  <span className="text-[11px] text-rose-700">Remove this version?</span>
                  <button
                    onClick={() => onRemoveRevision(r.revision_id)}
                    className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-semibold rounded-[9999px] transition-colors cursor-pointer"
                  >
                    Remove
                  </button>
                  <button
                    onClick={() => onConfirmRemoveRevision(null)}
                    className="px-3 py-1.5 bg-white hover:bg-[#F5F5F5] text-[#525252] text-[11px] rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <button
                    onClick={() => onSelectPair({ ...selectedPair, from: r.revision_id })}
                    title="Use as compare source (from)"
                    className={`px-3 py-1.5 text-xs font-medium rounded-[9999px] border transition-colors cursor-pointer ${
                      fromId === r.revision_id
                        ? 'bg-cyprus text-white border-cyprus shadow-xs'
                        : 'bg-white text-[#525252] border-[#E5E5E5] hover:border-[#0A0A0A]'
                    }`}
                  >
                    From
                  </button>
                  <button
                    onClick={() => onSelectPair({ ...selectedPair, to: r.revision_id })}
                    title="Use as compare target (to)"
                    className={`px-3 py-1.5 text-xs font-medium rounded-[9999px] border transition-colors cursor-pointer ${
                      toId === r.revision_id
                        ? 'bg-cyprus text-white border-cyprus shadow-xs'
                        : 'bg-white text-[#525252] border-[#E5E5E5] hover:border-[#0A0A0A]'
                    }`}
                  >
                    To
                  </button>
                  <button
                    onClick={() => onConfirmRemoveRevision(r.revision_id)}
                    title="Remove this version"
                    className="p-1.5 rounded-[8px] text-[#A3A3A3] hover:text-rose-700 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition-colors cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </span>
              )}
            </li>
          ))}
        </ul>
        <button
          onClick={() => onComparePair(fromId, toId)}
          disabled={busy || !fromId || !toId || fromId === toId}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-cyprus hover:bg-cyprus-deep disabled:opacity-50 text-white text-xs font-semibold rounded-[9999px] transition-colors cursor-pointer shadow-xs"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Compare selected pair</span>
        </button>
      </div>

      {/* Comparisons Section */}
      {comparisons.length > 0 && (
        <div className="space-y-3 pt-2 border-t border-[#E5E5E5]/60">
          <h3 className="text-[15px] font-semibold text-[#0A0A0A] tracking-tight">
            All comparisons
          </h3>
          <ul className="divide-y divide-[#F5F5F5] border border-cyprus/20 rounded-[12px] overflow-hidden bg-white shadow-xs">
            {comparisons.map((pair) => (
              <li key={`${pair.old_revision_id}-${pair.new_revision_id}`} className="px-5 py-4 bg-white flex items-center justify-between gap-3 hover:bg-[#FAFAFA] transition-colors">
                <span className="text-sm font-medium text-[#0A0A0A]">
                  Rev {pair.old_sequence_number} → Rev {pair.new_sequence_number}
                  <span
                    className={`ml-3 inline-block px-2.5 py-0.5 rounded-[9999px] text-[11px] font-medium ${
                      pair.has_comparison ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-[#F5F5F5] text-[#737373] border border-[#E5E5E5]'
                    }`}
                  >
                    {pair.has_comparison ? 'Compared' : 'Not compared'}
                  </span>
                </span>
                <button
                  onClick={() => onComparePair(pair.old_revision_id, pair.new_revision_id)}
                  disabled={busy}
                  className="inline-flex items-center gap-1 px-3.5 py-1.5 text-xs text-[#525252] hover:text-[#0A0A0A] bg-white hover:bg-[#F5F5F5] rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer disabled:opacity-50"
                >
                  <Play className="w-3 h-3 text-[#525252]" />
                  <span>{pair.has_comparison ? 'View' : 'Compare'}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function QuickCompareResult(props: {
  result: ComparisonResult | null;
  error: string | null;
  onOpenWorkspace: () => void;
  onDismiss: () => void;
}) {
  const { result, error, onOpenWorkspace, onDismiss } = props;
  return (
    <div className="border border-cyprus/30 rounded-[12px] overflow-hidden bg-white shadow-xs">
      <div className="px-4 py-3 bg-[#FAFAFA] border-b border-[#E5E5E5] flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-[#0A0A0A] tracking-tight">
          Quick compare result
        </h3>
        <span className="inline-flex items-center gap-1.5">
          {result && (
            <button
              onClick={onOpenWorkspace}
              className="px-3 py-1.5 bg-cyprus hover:bg-cyprus-deep text-white text-[11px] font-semibold rounded-[9999px] transition-colors cursor-pointer"
            >
              Open in full workspace
            </button>
          )}
          <button
            onClick={onDismiss}
            className="p-1.5 rounded-[8px] text-[#A3A3A3] hover:text-[#0A0A0A] hover:bg-white border border-transparent hover:border-[#E5E5E5] transition-colors cursor-pointer"
            title="Dismiss result"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </span>
      </div>
      <div className="p-4 space-y-3">
        {error && (
          <p className="px-3 py-2 rounded-[8px] bg-rose-50 border border-rose-200 text-xs text-rose-800">
            {error}
          </p>
        )}
        {result && (
          <>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="px-2.5 py-1 rounded-[9999px] bg-[#FAFAFA] border border-[#E5E5E5] text-[#525252]">
                Similarity {(result.overallSimilarity * 100).toFixed(1)}%
              </span>
              <span className="px-2.5 py-1 rounded-[9999px] bg-amber-50 text-amber-900 border border-amber-200 font-bold">
                {result.changes.length} Deltas Found
              </span>
              {result.comparisonMode && (
                <span className="px-2.5 py-1 rounded-[9999px] bg-[#FAFAFA] border border-[#E5E5E5] text-[#525252]">
                  {result.comparisonMode} mode
                </span>
              )}
            </div>
            {result.changes.length === 0 ? (
              <p className="text-[13px] text-[#6b7280]">No changes detected between the two files.</p>
            ) : (
              <ul className="divide-y divide-[#F5F5F5] border border-[#E5E5E5] rounded-[8px] overflow-hidden max-h-72 overflow-y-auto">
                {result.changes.map((c) => (
                  <li key={c.id} className="px-3 py-2 bg-white flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-[#0A0A0A] truncate">
                        {c.id} · {c.affectedFeature || c.title || c.category}
                      </p>
                      <p className="text-[11px] text-[#737373] line-clamp-2 mt-0.5">{c.description}</p>
                    </div>
                    <ChangeBadge category={c.category} size="sm" showDot />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function UploadAndCompareInline(props: {
  busy: boolean;
  jobMessage: string | null;
  onCancel: () => void;
  onCompare: (oldFile: File, newFile: File) => void;
}) {
  const [oldFile, setOldFile] = useState<File | null>(null);
  const [newFile, setNewFile] = useState<File | null>(null);
  const canCompare = !props.busy && !!oldFile && !!newFile;

  return (
    <div className="border border-cyprus/20 rounded-[12px] p-5 bg-sand/40 shadow-xs space-y-3">
      <h3 className="text-sm font-semibold text-[#0A0A0A] tracking-tight">
        Quick compare without registering
      </h3>
      {props.jobMessage && (
        <div className="flex items-center justify-between gap-2 px-3.5 py-2 rounded-[8px] bg-amber-50 border border-amber-200">
          <span className="text-xs text-amber-900 animate-pulse">{props.jobMessage}</span>
          <button
            onClick={props.onCancel}
            className="px-2.5 py-1 text-[11px] bg-white hover:bg-[#F5F5F5] text-[#525252] rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer"
          >
            Cancel
          </button>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2.5">
        {(
          [
            [oldFile, setOldFile, 'Old file…'],
            [newFile, setNewFile, 'New file…'],
          ] as Array<[File | null, (f: File | null) => void, string]>
        ).map(([file, setFile, label], i) => (
          <label
            key={i}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white text-xs text-[#525252] border border-[#E5E5E5] rounded-[8px] cursor-pointer hover:border-[#0A0A0A] transition-colors"
          >
            <UploadCloud className="w-3.5 h-3.5 text-[#525252]" />
            <span className="truncate max-w-[180px]">{file ? file.name : label}</span>
            <input
              type="file"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
        ))}
        <button
          onClick={() => {
            if (oldFile && newFile) props.onCompare(oldFile, newFile);
          }}
          disabled={!canCompare}
          className={`inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-[9999px] transition-colors cursor-pointer shadow-xs ${
            canCompare
              ? 'bg-cyprus hover:bg-cyprus-deep text-white'
              : 'bg-white text-[#A3A3A3] border border-[#E5E5E5] cursor-not-allowed'
          }`}
        >
          <Play className="w-3.5 h-3.5" />
          <span>Compare now</span>
        </button>
      </div>
    </div>
  );
}

