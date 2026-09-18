import { API_CONFIG } from '../config/api';
import {
  ComparisonResult,
  ConsecutivePair,
  DrawingHistory,
  DrawingSummary,
  RevisionInfo,
} from '../types/comparison';
import { mapBackendResult, pollJobStatus, createDemoComparisonResult } from './comparisonService';
import { authFetch } from './authService';

function checkOk(res: Response, data: any, fallback: string): void {
  if (!res.ok) {
    throw new Error((data as any)?.detail || fallback);
  }
}

const HIDDEN_DRAWINGS_KEY = 'hiddenDrawingIds';

/** IDs the user removed locally (see removeDrawingFromLibrary). */
export function getHiddenDrawingIds(): Set<string> {
  try {
    const raw = localStorage.getItem(HIDDEN_DRAWINGS_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'string') : []);
  } catch {
    return new Set();
  }
}

function setHiddenDrawingIds(ids: Set<string>): void {
  try {
    localStorage.setItem(HIDDEN_DRAWINGS_KEY, JSON.stringify([...ids]));
  } catch {
    // Storage unavailable (private mode, etc.) — removal just won't persist.
  }
}

export async function listDrawings(): Promise<DrawingSummary[]> {
  try {
    const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawings}`);
    const data = await res.json().catch(() => null);
    if (res.ok && data?.drawings) {
      const hidden = getHiddenDrawingIds();
      return ((data?.drawings ?? []) as DrawingSummary[]).filter((d) => !hidden.has(d.drawing_id));
    }
  } catch {
    // Fallback for presentation demo if backend is offline
  }
  return [
    {
      drawing_id: 'demo-dwg-1',
      name: 'Flange_Assembly_PCD.pdf',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      revisions_count: 2,
    },
  ];
}

/**
 * Remove a drawing from the library and delete its cached reports.
 */
export async function removeDrawingFromLibrary(drawingId: string): Promise<void> {
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawing(drawingId)}`, {
    method: 'DELETE',
  });
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not delete drawing.');

  // Also keep the local hide logic as a fallback/immediate UI removal
  const hidden = getHiddenDrawingIds();
  hidden.add(drawingId);
  setHiddenDrawingIds(hidden);
}

const HIDDEN_REVISIONS_KEY = 'hiddenRevisionIds';

/** Revision IDs the user removed locally (see removeRevisionFromLibrary). */
export function getHiddenRevisionIds(): Set<string> {
  try {
    const raw = localStorage.getItem(HIDDEN_REVISIONS_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'string') : []);
  } catch {
    return new Set();
  }
}

function setHiddenRevisionIds(ids: Set<string>): void {
  try {
    localStorage.setItem(HIDDEN_REVISIONS_KEY, JSON.stringify([...ids]));
  } catch {
    // Storage unavailable (private mode, etc.) — removal just won't persist.
  }
}

export async function removeRevisionFromLibrary(drawingId: string, revisionId: string): Promise<void> {
  const res = await authFetch(
    `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawingRevision(drawingId, revisionId)}`,
    { method: 'DELETE' }
  );
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not delete revision.');
  const hidden = getHiddenRevisionIds();
  hidden.add(revisionId);
  setHiddenRevisionIds(hidden);
}

export async function createDrawing(name?: string): Promise<DrawingSummary> {
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawings}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(name ? { name } : {}),
  });
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not create drawing.');
  return data as DrawingSummary;
}

export async function renameDrawing(drawingId: string, name: string): Promise<DrawingSummary> {
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawing(drawingId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not rename drawing.');
  return data as DrawingSummary;
}

export async function getDrawingHistory(drawingId: string): Promise<DrawingHistory> {
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawingHistory(drawingId)}`);
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not load revision history.');
  return data as DrawingHistory;
}

export interface SavedReportSummary {
  report_id: string;
  created_at: string;
  total_pages: number;
  total_changes: number;
  overall_similarity: number;
}

const HIDDEN_REPORTS_KEY = 'hiddenReportIds';

/** Report IDs the user removed locally (see removeReportFromLibrary). */
export function getHiddenReportIds(): Set<string> {
  try {
    const raw = localStorage.getItem(HIDDEN_REPORTS_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'string') : []);
  } catch {
    return new Set();
  }
}

function setHiddenReportIds(ids: Set<string>): void {
  try {
    localStorage.setItem(HIDDEN_REPORTS_KEY, JSON.stringify([...ids]));
  } catch {
    // Storage unavailable
  }
}

export async function listReports(): Promise<SavedReportSummary[]> {
  try {
    const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.reports}`);
    const data = await res.json().catch(() => null);
    if (res.ok && data?.reports) {
      const hidden = getHiddenReportIds();
      return ((data?.reports ?? []) as SavedReportSummary[]).filter((r) => !hidden.has(r.report_id));
    }
  } catch {
    // Fallback for presentation demo
  }
  return [
    {
      report_id: 'demo-report-1',
      created_at: new Date().toISOString(),
      total_pages: 1,
      total_changes: 5,
      overall_similarity: 0.94,
    },
  ];
}

export async function removeReportFromLibrary(reportId: string): Promise<void> {
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.report(reportId)}`, {
    method: 'DELETE',
  });
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not delete report.');

  const hidden = getHiddenReportIds();
  hidden.add(reportId);
  setHiddenReportIds(hidden);
}

export async function getCompletedReport(reportId: string): Promise<ComparisonResult> {
  if (reportId.startsWith('demo-')) {
    return createDemoComparisonResult(
      { name: 'Flange_Rev_A.png', fileSize: '2.4 MB' },
      { name: 'Flange_Rev_B.png', fileSize: '2.5 MB' }
    );
  }
  try {
    const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.report(reportId)}`);
    const data = await res.json().catch(() => null);
    checkOk(res, data, 'Could not load comparison report.');
    return mapBackendResult(data as Record<string, any>, null, null);
  } catch {
    return createDemoComparisonResult(
      { name: 'Flange_Rev_A.png', fileSize: '2.4 MB' },
      { name: 'Flange_Rev_B.png', fileSize: '2.5 MB' }
    );
  }
}

export async function registerRevision(
  drawingId: string,
  file: File,
  revisionLabel?: string
): Promise<RevisionInfo> {
  const form = new FormData();
  form.append('file', file, file.name);
  if (revisionLabel) form.append('revision_label', revisionLabel);
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawingRevisions(drawingId)}`, {
    method: 'POST',
    body: form,
  });
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not register revision.');
  return data as RevisionInfo;
}

export async function deleteRevision(drawingId: string, revisionId: string): Promise<void> {
  const res = await authFetch(
    `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawingRevision(drawingId, revisionId)}`,
    { method: 'DELETE' }
  );
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not delete revision.');
}

export interface DrawingCompareOptions {
  onJobProgress?: (job: { job_id: string; status: string; progress_message?: string | null }) => void;
  abortSignal?: AbortSignal;
}

/**
 * Compare two revisions by ID. Cache hits return synchronously (200);
 * otherwise the backend returns 202 + job_id and we poll until completed.
 */
export async function compareRevisions(
  drawingId: string,
  fromRevisionId?: string,
  toRevisionId?: string,
  options?: DrawingCompareOptions
): Promise<{ result: ComparisonResult; wasCached: boolean }> {
  const res = await authFetch(
    `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawingCompare(drawingId, fromRevisionId, toRevisionId)}`
  );
  if (res.status === 202) {
    const queued = await res.json().catch(() => null);
    const jobId = queued?.job_id as string | undefined;
    if (!jobId) throw new Error('Comparison was accepted but no job_id was returned.');
    const finished = await pollJobStatus(jobId, {
      onProgress: options?.onJobProgress,
      abortSignal: options?.abortSignal,
    });
    const payload = finished.result as Record<string, any>;
    return { result: mapBackendResult(payload, null, null), wasCached: false };
  }
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not compare revisions.');
  return { result: mapBackendResult(data as Record<string, any>, null, null), wasCached: true };
}

/**
 * Flow A: upload old + new together, create drawing + revisions + comparison.
 */
export async function uploadAndCompare(
  oldFile: File,
  newFile: File,
  name?: string,
  oldRevisionLabel?: string,
  newRevisionLabel?: string,
  options?: DrawingCompareOptions
): Promise<{ result: ComparisonResult; drawing: DrawingSummary; revisions: RevisionInfo[] }> {
  const form = new FormData();
  form.append('old_drawing', oldFile, oldFile.name);
  form.append('new_drawing', newFile, newFile.name);
  if (name) form.append('name', name);
  if (oldRevisionLabel) form.append('old_revision_label', oldRevisionLabel);
  if (newRevisionLabel) form.append('new_revision_label', newRevisionLabel);
  const oldUrl = URL.createObjectURL(oldFile);
  const newUrl = URL.createObjectURL(newFile);
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.uploadAndCompare}`, {
    method: 'POST',
    body: form,
  });

  if (res.status === 202) {
    const queued = await res.json().catch(() => null);
    const jobId = queued?.job_id as string | undefined;
    if (!jobId) throw new Error('Comparison was accepted but no job_id was returned.');
    const finished = await pollJobStatus(jobId, {
      onProgress: options?.onJobProgress,
      abortSignal: options?.abortSignal,
    });
    const payload = finished.result as Record<string, any>;
    const result = mapBackendResult(payload, oldFile, newFile, oldUrl, newUrl);
    return {
      result,
      drawing: queued.drawing as DrawingSummary,
      revisions: (queued.revisions ?? []) as RevisionInfo[],
    };
  }

  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not upload and compare.');
  const result = mapBackendResult(data as Record<string, any>, oldFile, newFile, oldUrl, newUrl);
  return {
    result,
    drawing: (data as any).drawing as DrawingSummary,
    revisions: ((data as any).revisions ?? []) as RevisionInfo[],
  };
}

/**
 * Download the revision-history summary PDF for a drawing.
 */
export async function downloadHistoryExport(drawingId: string, drawingName?: string): Promise<void> {
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawingHistoryExport(drawingId)}`);
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error((data as any)?.detail || 'History export failed.');
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const safe = (drawingName || drawingId).replace(/[^A-Za-z0-9-_]/g, '_') || 'drawing';
  a.download = `history-${safe}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export type { ConsecutivePair, DrawingHistory, DrawingSummary, RevisionInfo };
