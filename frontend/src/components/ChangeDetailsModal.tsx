import React, { useEffect } from 'react';
import { CheckCircle2, Flag, X } from 'lucide-react';
import { ChangeItem, ChangeReviewStatus } from '../types/comparison';
import { ChangeBadge } from '../components/ChangeBadge';

export const ChangeDetailsModal: React.FC<{
  change: ChangeItem | null;
  onClose: () => void;
  onStatusChange?: (changeId: string, status: ChangeReviewStatus) => void;
}> = ({ change, onClose, onStatusChange }) => {
  useEffect(() => {
    if (!change) return;
    const handler = (event: KeyboardEvent) => event.key === 'Escape' && onClose();
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [change, onClose]);
  if (!change) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-[14px] border border-cyprus/20 bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-[#E5E5E5] px-6 py-4">
          <div><p className="text-xs font-mono font-semibold uppercase tracking-wider text-[#374151]">Modification details</p><h2 className="mt-1 text-[15px] font-semibold text-[#111827]">{change.affectedFeature || change.title || change.category}</h2></div>
          <button type="button" aria-label="Close modification details" onClick={onClose} className="rounded-full p-2 text-[#737373] hover:bg-[#F5F5F5]"><X className="h-4 w-4" /></button>
        </div>
        <div className="grid gap-4 px-6 py-5 sm:grid-cols-2">
          {change.verification?.verified === false && (
            <div className="sm:col-span-2 rounded-[8px] border border-amber-300 bg-amber-50 p-3">
              <p className="text-xs font-semibold text-amber-900">Needs human review</p>
              <p className="mt-1 text-xs text-amber-800">{change.verification.reason || 'OCR and LLM evidence disagree for this change.'}</p>
            </div>
          )}
          <div className="sm:col-span-2"><p className="label">Description</p><p className="mt-1 text-sm leading-relaxed">{change.description || 'No description provided.'}</p></div>
          <div><p className="label">Category</p><div className="mt-1"><ChangeBadge category={change.category} size="sm" showIcon showDot /></div></div>
          {onStatusChange && (
            <div className="sm:col-span-2 flex flex-wrap items-center gap-2 border-t border-[#E5E5E5] pt-4">
              <span className="text-[10px] font-mono uppercase tracking-wider text-[#737373]">Human review</span>
              <button
                type="button"
                onClick={() => onStatusChange(change.id, 'approved')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[8px] text-xs font-medium border transition-colors cursor-pointer ${
                  change.status === 'approved'
                    ? 'bg-emerald-600 border-emerald-600 text-white'
                    : 'bg-white hover:bg-emerald-50 text-emerald-700 border-emerald-300'
                }`}
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> Confirm
              </button>
              <button
                type="button"
                onClick={() => onStatusChange(change.id, 'flagged')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[8px] text-xs font-medium border transition-colors cursor-pointer ${
                  change.status === 'flagged'
                    ? 'bg-rose-600 border-rose-600 text-white'
                    : 'bg-white hover:bg-rose-50 text-rose-700 border-rose-300'
                }`}
              >
                <Flag className="h-3.5 w-3.5" /> False positive
              </button>
            </div>
          )}
          <div><p className="label">Confidence / Severity</p><p className="mt-1 text-sm">{change.classificationConfidence != null ? `${(change.classificationConfidence * 100).toFixed(1)}%` : '—'} / {change.severity || '—'}</p>{change.ocrConfidence && <p className="mt-1 text-xs text-[#4b5563]">OCR: Old {change.ocrConfidence.old}% · New {change.ocrConfidence.new}%</p>}</div>
          <div className="sm:col-span-2 border-t border-[#E5E5E5] pt-4"><p className="label">Detected region</p><p className="mt-1 font-mono text-xs">x: {change.region.x}, y: {change.region.y}, width: {change.region.width}, height: {change.region.height}</p></div>
          {change.delta && <div><p className="label">Delta</p><p className="mt-1 font-mono text-sm text-amber-700">{change.delta}</p></div>}
          <details className="sm:col-span-2 rounded-[8px] border border-[#E5E5E5] bg-[#FAFAFA] p-3"><summary className="cursor-pointer text-[10px] font-mono uppercase tracking-wider text-[#737373]">Technical OCR (optional)</summary><div className="mt-3 grid gap-3 sm:grid-cols-2"><div><p className="label">Rev A OCR</p><p className="mt-2 whitespace-pre-wrap break-words font-mono text-xs">{change.oldValue || '—'}</p></div><div><p className="label">Rev B OCR</p><p className="mt-2 whitespace-pre-wrap break-words font-mono text-xs">{change.newValue || '—'}</p></div></div></details>
        </div>
      </div>
    </div>
  );
};
