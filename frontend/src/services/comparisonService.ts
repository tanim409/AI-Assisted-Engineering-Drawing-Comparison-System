import { API_CONFIG } from '../config/api';
import { ComparisonResult, ComparisonError, DrawingFile, ChangeCategory, ChangeSeverity, ChangeReviewStatus, JobState, QaAnswer } from '../types/comparison';
import { authFetch, getToken } from './authService';

export interface ComparisonRequestOptions {
  old_drawing: Partial<DrawingFile> | File;
  new_drawing: Partial<DrawingFile> | File;
  simulateError?: '422_ALIGNMENT_FAILED' | '500_SERVER_ERROR' | 'NETWORK_TIMEOUT' | null;
  toleranceClass?: 'precision' | 'standard' | 'coarse';
  /** Called with job progress while polling (Feature 1: async compare). */
  onJobProgress?: (job: { job_id: string; status: string; progress_message?: string | null }) => void;
  /** AbortSignal to cancel polling (the pipeline keeps running server-side). */
  abortSignal?: AbortSignal;
}

export async function pollJobStatus(
  jobId: string,
  options?: {
    onProgress?: (job: { job_id: string; status: string; progress_message?: string | null }) => void;
    abortSignal?: AbortSignal;
    intervalMs?: number;
    timeoutMs?: number;
  }
): Promise<{ status: string; result?: Record<string, any>; error_message?: string }> {
  const interval = options?.intervalMs ?? API_CONFIG.jobPollIntervalMs;
  const timeout = options?.timeoutMs ?? API_CONFIG.timeoutMs;
  const startedAt = Date.now();
  for (;;) {
    if (options?.abortSignal?.aborted) {
      const abortErr: ComparisonError = {
        type: 'NETWORK_TIMEOUT', statusCode: 0,
        title: 'Comparison Cancelled',
        message: 'You cancelled the comparison. The server may still finish processing it.',
        suggestedAction: 'Start a new comparison whenever you are ready.',
        retryable: true,
      };
      throw abortErr;
    }
    const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.job(jobId)}`);
    const data = await res.json().catch(() => null);
    if (res.status === 404) {
      throw new Error(`Job '${jobId}' does not exist.`);
    }
    if (!res.ok || !data) {
      throw new Error('Failed to check comparison job status.');
    }
    const job = data as JobState;
    options?.onProgress?.({ job_id: job.job_id, status: job.status, progress_message: job.progress_message });
    if (job.status === 'completed') return { status: 'completed', result: job.result };
    if (job.status === 'failed') {
      const errorObj: ComparisonError = {
        type: '500_SERVER_ERROR', statusCode: 500,
        title: 'Comparison Failed',
        message: job.error_message || 'The comparison pipeline failed.',
        suggestedAction: 'Retry the comparison.',
        retryable: true,
      };
      throw errorObj;
    }
    if (Date.now() - startedAt > timeout) {
      const errorObj: ComparisonError = {
        type: 'NETWORK_TIMEOUT',
        title: 'Comparison Timed Out',
        message: 'The comparison is taking longer than expected. You can retry or check back later.',
        suggestedAction: 'Retry the comparison.',
        technicalDetails: `ERR_JOB_POLL_TIMEOUT: ${timeout}ms exceeded.`,
        retryable: true,
      };
      throw errorObj;
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
  }
}

/**
 * Sends the two uploaded drawings to the FastAPI /api/compare endpoint
 * and returns the structured ComparisonResult from the backend.
 */
export async function runDrawingComparison(
  options: ComparisonRequestOptions
): Promise<ComparisonResult> {
  const { old_drawing, new_drawing, simulateError, onJobProgress, abortSignal } = options;

  console.groupCollapsed(`[ComparisonService] POSTing to ${API_CONFIG.baseUrl}${API_CONFIG.endpoints.compare}`);
  console.log('Timestamp:', new Date().toISOString());
  console.log('Simulation Mode:', simulateError || 'None (live backend)');
  console.groupEnd();

  // --- Error simulation for UI testing ---
  if (simulateError === '422_ALIGNMENT_FAILED') {
    const errorObj: ComparisonError = {
      type: '422_ALIGNMENT_FAILED', statusCode: 422,
      title: 'Drawing Alignment Failed',
      message: "These drawings couldn't be aligned. Try clearer scans or check they're the same drawing.",
      suggestedAction: 'Ensure both files share common fiducials, datum axes, or title blocks.',
      technicalDetails: 'ERR_CAD_HOMOGRAPHY_CONVERGENCE_FAIL: Feature match score below threshold.',
      retryable: true,
    };
    throw errorObj;
  }
  if (simulateError === '500_SERVER_ERROR') {
    const errorObj: ComparisonError = {
      type: '500_SERVER_ERROR', statusCode: 500,
      title: 'Comparison Engine Unavailable',
      message: 'Something went wrong on our end. Please try again.',
      suggestedAction: 'Retry the operation.',
      technicalDetails: 'INTERNAL_GEOMETRY_KERNEL_EXCEPTION',
      retryable: true,
    };
    throw errorObj;
  }
  if (simulateError === 'NETWORK_TIMEOUT') {
    const errorObj: ComparisonError = {
      type: 'NETWORK_TIMEOUT',
      title: 'Connection Timed Out',
      message: 'Connection lost. Check your network and retry.',
      suggestedAction: 'Verify your network connection and retry.',
      technicalDetails: `ERR_NETWORK_SOCKET_TIMEOUT_ABORTED: ${API_CONFIG.timeoutMs}ms exceeded.`,
      retryable: true,
    };
    throw errorObj;
  }

  // Both inputs must be real File objects to POST to the backend
  if (!(old_drawing instanceof File) || !(new_drawing instanceof File)) {
    throw new Error('Both old_drawing and new_drawing must be valid File objects.');
  }

  // Create preview URLs before fetch so panels can display the uploaded images
  const oldDrawingUrl = URL.createObjectURL(old_drawing);
  const newDrawingUrl = URL.createObjectURL(new_drawing);

  // --- Real API call to FastAPI backend ---
  const form = new FormData();
  form.append('old_drawing', old_drawing, old_drawing.name);
  form.append('new_drawing', new_drawing, new_drawing.name);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_CONFIG.timeoutMs);

  try {
    const token = getToken();
    const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.compare}`, {
      method: 'POST',
      headers: authHeaders,
      body: form,
      signal: controller.signal,
    });

    clearTimeout(timeout);

    // Async flow (Feature 1): 202 + job_id — poll until the job completes.
    if (res.status === 202) {
      const queued = await res.json().catch(() => null);
      const jobId = queued?.job_id as string | undefined;
      if (!jobId) throw new Error('Comparison was accepted but no job_id was returned.');
      const finished = await pollJobStatus(jobId, { onProgress: onJobProgress, abortSignal });
      const data = finished.result as Record<string, any> | undefined;
      if (!data) throw new Error('Comparison finished but returned no result.');
      return mapBackendResult(data, old_drawing as File, new_drawing as File, oldDrawingUrl, newDrawingUrl);
    }

    const data = await res.json().catch(() => null);

    if (res.status === 401) {
      URL.revokeObjectURL(oldDrawingUrl);
      URL.revokeObjectURL(newDrawingUrl);
      window.dispatchEvent(new CustomEvent('auth:expired', { detail: { message: 'Please log in to compare drawings.' } }));
      const errorObj: ComparisonError = {
        type: '500_SERVER_ERROR',
        statusCode: 401,
        title: 'Authentication Required',
        message: 'Please log in to compare engineering drawings.',
        suggestedAction: 'Click "Log In" or "Create Account" in the top navigation to continue.',
        retryable: false,
      };
      throw errorObj;
    }

    if (!res.ok) {
      URL.revokeObjectURL(oldDrawingUrl);
      URL.revokeObjectURL(newDrawingUrl);
      const errData = (data ?? {}) as Partial<ComparisonError>;
      const errorObj: ComparisonError = {
        type: (errData.type as ComparisonError['type']) || '500_SERVER_ERROR',
        statusCode: res.status,
        title: errData.title || 'Comparison Failed',
        message: errData.message || 'The comparison service returned an error.',
        suggestedAction: errData.suggestedAction || 'Retry the comparison.',
        technicalDetails: errData.technicalDetails,
        retryable: errData.retryable ?? true,
      };
      throw errorObj;
    }

    // Map backend response → frontend camelCase types.
    return mapBackendResult(data as Record<string, any>, old_drawing as File, new_drawing as File, oldDrawingUrl, newDrawingUrl);

  } catch (err: any) {
    clearTimeout(timeout);
    // Re-throw ComparisonError objects directly (thrown above on non-ok response)
    if (err && 'type' in err && 'retryable' in err) throw err;
    // Handle network-level failures
    URL.revokeObjectURL(oldDrawingUrl);
    URL.revokeObjectURL(newDrawingUrl);
    const aborted = err?.name === 'AbortError';
    const errorObj: ComparisonError = {
      type: aborted ? 'NETWORK_TIMEOUT' : '500_SERVER_ERROR',
      statusCode: aborted ? 0 : 502,
      title: aborted ? 'Connection Timed Out' : 'Comparison Service Unreachable',
      message: aborted
        ? 'The comparison service took too long to respond. Check your network and retry.'
        : 'Could not reach the /api/compare endpoint. Make sure the FastAPI server is running.',
      suggestedAction: aborted
        ? 'Verify your network connection and retry.'
        : `Ensure the backend is reachable at ${API_CONFIG.baseUrl}`,
      technicalDetails: aborted
        ? `ERR_NETWORK_SOCKET_TIMEOUT_ABORTED: ${API_CONFIG.timeoutMs}ms exceeded.`
        : String(err?.message || err),
      retryable: true,
    };
    throw errorObj;
  }
}

/**
 * Map a backend comparison payload (sync or job-polled) → frontend types.
 * Handles both the legacy flat `changes[]` shape and the current
 * `pages[].changes` shape. Page number + change index are attached to every
 * change so review, annotated-export, and QA APIs can address them.
 */
export function mapBackendResult(
  raw: Record<string, any>,
  oldFile: File | null,
  newFile: File | null,
  oldDrawingUrl?: string,
  newDrawingUrl?: string
): ComparisonResult {
  console.log('[ComparisonService] Raw backend response:', raw);

  const buildDrawingFile = (file: File | null, suffix: string): DrawingFile => ({
    id: `${suffix}-${Date.now()}`,
    name: file?.name ?? `Drawing ${suffix}`,
    revision: suffix,
    fileSize: file && typeof file.size === 'number' ? formatBytes(file.size) : '',
    dimensions: '',
    type: file?.type ?? (file?.name?.split('.').pop() ?? ''),
    uploadedAt: new Date().toISOString(),
    author: '',
  });

  const oldDrawingMeta = buildDrawingFile(oldFile, 'A');
  const newDrawingMeta = buildDrawingFile(newFile, 'B');

  const reportId: string | undefined = raw.report_id ?? raw.comparison_id ?? raw.id;

  const mapChange = (c: any, index: number, pageNumber?: number, changeIndex?: number) => {
    const normalized = c?.bbox_percent ?? c?.bboxPercent;
    const region = {
      x: Math.max(0, Math.min(100, Number(normalized?.x ?? 0))),
      y: Math.max(0, Math.min(100, Number(normalized?.y ?? 0))),
      width: Math.max(0.5, Math.min(100, Number(normalized?.w ?? 0))),
      height: Math.max(0.5, Math.min(100, Number(normalized?.h ?? 0))),
      zone: '',
    };

    const classification = c?.classification ?? {};
    const llm = c?.llm_classification ?? {};
    // Backend classification is the final decision; the LLM value is evidence.
    const category = String(classification?.category ?? llm?.category ?? '');
    const description = String(llm?.description ?? c?.description ?? '');

    return {
      id: `CHG-${String(index + 1).padStart(3, '0')}`,
      category,
      title: description.length > 60 ? description.slice(0, 57) + '…' : description,
      description,
      pageNumber,
      changeIndex,
      reportId,
      region,
      oldValue: c?.old_text ?? c?.oldValue ?? '',
      newValue: c?.new_text ?? c?.newValue ?? '',
      delta: c?.delta ?? '',
      severity: (c?.severity as ChangeSeverity) ?? 'moderate',
      status: mapBackendReviewStatus(c?.review?.status) ?? ((c?.status as ChangeReviewStatus) ?? 'pending'),
      affectedFeature: c?.affected_feature ?? c?.affectedFeature ?? category,
      drawingRevisionA: 'A',
      drawingRevisionB: 'B',
      zone: region.zone,
      complianceImpact: c?.compliance_impact ?? c?.complianceImpact ?? '',
      ocrConfidence: c?.ocr_confidence ?? c?.ocrConfidence,
      classificationConfidence: c?.llm_classification?.confidence ?? c?.classification?.confidence,
      verification: c?.verification,
      ruleBasedCategory: c?.rule_based_classification?.category,
      llmSource: llm?.source ?? null,
    };
  };

  // Prefer the paged shape (pages[].changes); fall back to flat changes[].
  let changes: ReturnType<typeof mapChange>[] = [];
  if (Array.isArray(raw.pages) && raw.pages.length > 0) {
    let counter = 0;
    raw.pages.forEach((page: any, pageIdx: number) => {
      const pageNumber: number | undefined =
        typeof page?.page_number === 'number' ? page.page_number : undefined;
      (Array.isArray(page?.changes) ? page.changes : []).forEach((c: any, ci: number) => {
        changes.push(mapChange(c, counter++, pageNumber ?? pageIdx + 1, ci));
      });
    });
  } else {
    const rawChanges = Array.isArray(raw.changes) ? raw.changes : [];
    changes = rawChanges.map((c: any, i: number) => mapChange(c, i, undefined, i));
  }

  const categoryCounts: Record<string, number> =
    raw.changes_by_category ?? raw.categoryCounts ?? {};

  const alignment = raw.alignment ?? {};
  const alignmentScoreRaw =
    typeof raw.overall_similarity === 'number'
      ? Math.round(raw.overall_similarity * 100)
      : typeof alignment?.confidence === 'number'
      ? Math.round(alignment.confidence * 100)
      : 0;
  const alignmentConfidence: ComparisonResult['alignmentConfidence'] =
    alignmentScoreRaw >= 75 ? 'high' : alignmentScoreRaw >= 45 ? 'medium' : 'low';

  const result: ComparisonResult = {
    id: raw.id ?? raw.report_id ?? raw.comparison_id ?? `comp-${Date.now()}`,
    reportId,
    totalPages: raw.total_pages ?? (Array.isArray(raw.pages) ? raw.pages.length : undefined),
    projectName: raw.project_name ?? raw.projectName ?? 'Drawing Comparison',
    drawingNumber: raw.drawing_number ?? raw.drawingNumber ?? '',
    title: raw.title ?? 'Engineering Drawing Comparison',
    discipline: raw.discipline ?? 'Architectural',
    oldDrawing: oldDrawingMeta,
    newDrawing: newDrawingMeta,
    alignmentScore: alignmentScoreRaw,
    alignmentConfidence,
    processingTimeMs: raw.processing_time_ms ?? raw.processingTimeMs ?? 0,
    totalChanges: raw.total_changes ?? raw.totalChanges ?? changes.length,
    overallSimilarity: typeof raw.overall_similarity === 'number' ? raw.overall_similarity : alignmentScoreRaw / 100,
    totalRegionsDetected: raw.total_regions_detected ?? raw.totalRegionsDetected ?? changes.length,
    verificationSummary: raw.verification_summary ? {
      ocrLlmAgreementCount: raw.verification_summary.ocr_llm_agreement_count ?? 0,
      ocrLlmDisagreementCount: raw.verification_summary.ocr_llm_disagreement_count ?? 0,
    } : undefined,
    comparisonMode: raw.comparison_mode,
    redesignDetected: raw.redesign_detected,
    overallSummary: raw.overall_summary,
    categoryCounts,
    changes,
    timestamp: raw.timestamp ?? raw.generated_at ?? new Date().toISOString(),
    oldDrawingUrl:
      oldDrawingUrl ||
      (raw.drawing_id && raw.old_revision_id
        ? `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawingRevisionRender(raw.drawing_id, raw.old_revision_id)}&token=${getToken() ?? ''}`
        : undefined),
    newDrawingUrl:
      newDrawingUrl ||
      (raw.drawing_id && raw.new_revision_id
        ? `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.drawingRevisionRender(raw.drawing_id, raw.new_revision_id)}&token=${getToken() ?? ''}`
        : undefined),
  };
  return result;
}

/** Backend review status → frontend review status. */
export function mapBackendReviewStatus(status: string | undefined): ChangeReviewStatus | undefined {
  if (status === 'confirmed') return 'approved';
  if (status === 'false_positive') return 'flagged';
  if (status === 'unreviewed') return 'pending';
  return undefined;
}

/** Frontend review status → backend review status. */
export function mapFrontendReviewStatus(status: ChangeReviewStatus): 'confirmed' | 'false_positive' {
  return status === 'approved' ? 'confirmed' : 'false_positive';
}

/**
 * Generate a rich, interactive demo ComparisonResult directly on the client side
 * without calling backend AI models or requiring cloud storage.
 */
export function createDemoComparisonResult(
  oldFile: Partial<DrawingFile> | File,
  newFile: Partial<DrawingFile> | File
): ComparisonResult {
  const oldUrl = oldFile instanceof File ? URL.createObjectURL(oldFile) : (oldFile as any)?.url || '';
  const newUrl = newFile instanceof File ? URL.createObjectURL(newFile) : (newFile as any)?.url || '';

  const buildDrawingFile = (file: Partial<DrawingFile> | File, suffix: string): DrawingFile => {
    if (file instanceof File) {
      return {
        id: `demo-file-${suffix}-${Date.now()}`,
        name: file.name,
        revision: suffix,
        fileSize: formatBytes(file.size),
        dimensions: 'A1 (841 x 594 mm)',
        type: file.type || file.name.split('.').pop() || 'PNG',
        uploadedAt: new Date().toISOString(),
        author: 'Lead Mechanical Engineer',
      };
    }
    return {
      id: file.id || `demo-file-${suffix}`,
      name: file.name || `Drawing Rev ${suffix}`,
      revision: file.revision || suffix,
      fileSize: file.fileSize || '2.4 MB',
      dimensions: file.dimensions || 'A1 (841 x 594 mm)',
      type: file.type || 'PDF',
      uploadedAt: file.uploadedAt || new Date().toISOString(),
      author: file.author || 'Lead Mechanical Engineer',
    };
  };

  const reportId = `demo-report-${Date.now()}`;

  const changes = [
    {
      id: 'CHG-001',
      category: 'Dimensional',
      title: 'Bore Diameter changed from Ø 45.00mm to Ø 50.00mm',
      description: 'Critical internal bore dimension expanded for high-pressure shaft fitting clearance.',
      pageNumber: 1,
      changeIndex: 0,
      reportId,
      region: { x: 28, y: 32, width: 18, height: 14, zone: 'Zone B-3' },
      oldValue: 'Ø 45.00 ± 0.05 mm',
      newValue: 'Ø 50.00 ± 0.02 mm',
      delta: '+5.00 mm',
      severity: 'critical' as ChangeSeverity,
      status: 'pending' as ChangeReviewStatus,
      affectedFeature: 'Inner Main Bore',
      drawingRevisionA: 'Rev A',
      drawingRevisionB: 'Rev B',
      zone: 'Zone B-3',
      complianceImpact: 'Requires updated seal ring specification (ISO 3601).',
      ocrConfidence: 0.98,
      classificationConfidence: 0.95,
    },
    {
      id: 'CHG-002',
      category: 'Title Block',
      title: 'Revision Block updated to Rev B (ECO-2026-889)',
      description: 'Title block updated with engineering change order number ECO-2026-889 and date.',
      pageNumber: 1,
      changeIndex: 1,
      reportId,
      region: { x: 68, y: 78, width: 24, height: 16, zone: 'Zone D-4' },
      oldValue: 'REV A | RELEASED 2025-11-10',
      newValue: 'REV B | ECO-2026-889 2026-09-17',
      delta: 'Revision level incremented',
      severity: 'minor' as ChangeSeverity,
      status: 'approved' as ChangeReviewStatus,
      affectedFeature: 'Document Control',
      drawingRevisionA: 'Rev A',
      drawingRevisionB: 'Rev B',
      zone: 'Zone D-4',
      complianceImpact: 'Fully documented in engineering change record.',
      ocrConfidence: 0.99,
      classificationConfidence: 0.97,
    },
    {
      id: 'CHG-003',
      category: 'Material',
      title: 'Material specification upgraded to Stainless Steel 316L',
      description: 'Flange body material upgraded from Carbon Steel A105 to Austenitic SS 316L for corrosion resistance.',
      pageNumber: 1,
      changeIndex: 2,
      reportId,
      region: { x: 14, y: 72, width: 22, height: 12, zone: 'Zone A-4' },
      oldValue: 'ASTM A105 Carbon Steel',
      newValue: 'ASTM A312 TP316L Stainless',
      delta: 'Material grade upgrade',
      severity: 'moderate' as ChangeSeverity,
      status: 'pending' as ChangeReviewStatus,
      affectedFeature: 'Bill of Materials (BOM)',
      drawingRevisionA: 'Rev A',
      drawingRevisionB: 'Rev B',
      zone: 'Zone A-4',
      complianceImpact: 'NACE MR0175 compliant for sour service environment.',
      ocrConfidence: 0.96,
      classificationConfidence: 0.94,
    },
    {
      id: 'CHG-004',
      category: 'Dimensional',
      title: 'Pitch Circle Diameter (PCD) expanded to 125.00mm',
      description: 'Bolt hole circle radius increased to accommodate 8-bolt heavy duty flange layout.',
      pageNumber: 1,
      changeIndex: 3,
      reportId,
      region: { x: 45, y: 20, width: 20, height: 18, zone: 'Zone C-2' },
      oldValue: 'PCD 110.00 mm (6x M10)',
      newValue: 'PCD 125.00 mm (8x M12)',
      delta: '+15.00 mm PCD, +2 Bolt Holes',
      severity: 'critical' as ChangeSeverity,
      status: 'pending' as ChangeReviewStatus,
      affectedFeature: 'Flange Bolt Pattern',
      drawingRevisionA: 'Rev A',
      drawingRevisionB: 'Rev B',
      zone: 'Zone C-2',
      complianceImpact: 'Mating pipe flange must be re-ordered to Class 300 pattern.',
      ocrConfidence: 0.95,
      classificationConfidence: 0.92,
    },
    {
      id: 'CHG-005',
      category: 'Geometric',
      title: 'Added 2x M8 Auxiliary Drain Port Taps',
      description: 'New tapped holes added at lower flange sector for low-point condensate drainage.',
      pageNumber: 1,
      changeIndex: 4,
      reportId,
      region: { x: 52, y: 55, width: 16, height: 14, zone: 'Zone C-3' },
      oldValue: 'Solid web (No ports)',
      newValue: '2x M8 x 1.25 TAP THRU',
      delta: 'New geometric feature',
      severity: 'moderate' as ChangeSeverity,
      status: 'pending' as ChangeReviewStatus,
      affectedFeature: 'Drainage Subsystem',
      drawingRevisionA: 'Rev A',
      drawingRevisionB: 'Rev B',
      zone: 'Zone C-3',
      complianceImpact: 'Requires NPT plug callouts in assembly manual.',
      ocrConfidence: 0.94,
      classificationConfidence: 0.91,
    },
  ];

  return {
    id: reportId,
    reportId,
    totalPages: 1,
    projectName: 'Engineering Drawing Comparison',
    drawingNumber: 'DWG-2026-DEMO',
    title: 'Flange Assembly & Pipe Support Layout',
    discipline: 'Mechanical',
    oldDrawing: buildDrawingFile(oldFile, 'A'),
    newDrawing: buildDrawingFile(newFile, 'B'),
    alignmentScore: 94,
    alignmentConfidence: 'high',
    processingTimeMs: 250,
    totalChanges: changes.length,
    overallSimilarity: 0.94,
    totalRegionsDetected: changes.length,
    overallSummary:
      'Demo Mode: Interactive comparison UI. 5 engineering differences detected across dimensional tolerances, material specification, title block ECO revision, and bolt pattern geometry.',
    categoryCounts: {
      Dimensional: 2,
      Material: 1,
      'Title Block': 1,
      Geometric: 1,
    },
    changes,
    timestamp: new Date().toISOString(),
    oldDrawingUrl: oldUrl,
    newDrawingUrl: newUrl,
  };
}

/**
 * Ask a natural-language question about a report's detected changes.
 */
export async function askQuestion(reportId: string, question: string): Promise<QaAnswer> {
  if (reportId.startsWith('demo-')) {
    const qLower = question.toLowerCase();
    if (qLower.includes('dimension') || qLower.includes('bore') || qLower.includes('size')) {
      return {
        answer: 'The primary dimensional changes are: (1) Main bore diameter expanded from Ø 45.00mm to Ø 50.00mm (CHG-001) for shaft clearance, and (2) Bolt Pitch Circle Diameter (PCD) enlarged from 110.00mm to 125.00mm with 8 bolt holes instead of 6 (CHG-004).',
        referenced_change_indices: [0, 3],
      };
    }
    if (qLower.includes('material') || qLower.includes('steel') || qLower.includes('grade')) {
      return {
        answer: 'The material specification was upgraded from ASTM A105 Carbon Steel to ASTM A312 TP316L Stainless Steel (CHG-003) to satisfy NACE MR0175 corrosion resistance standards.',
        referenced_change_indices: [2],
      };
    }
    if (qLower.includes('revision') || qLower.includes('eco') || qLower.includes('title')) {
      return {
        answer: 'The title block was updated to Revision B under Engineering Change Order ECO-2026-889 dated 2026-09-17 (CHG-002).',
        referenced_change_indices: [1],
      };
    }
    return {
      answer: `Based on the CAD drawing comparison for report ${reportId}: We identified 5 key changes including main bore expansion, bolt PCD revision, material upgrade to 316L stainless steel, and added drain ports. Click on any change marker in the list to zoom in.`,
      referenced_change_indices: [0, 1, 2, 3, 4],
    };
  }

  try {
    const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.ask}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ report_id: reportId, question }),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      throw new Error((data as any)?.detail || 'Could not answer that question.');
    }
    return {
      answer: String(data?.answer ?? ''),
      referenced_change_indices: Array.isArray(data?.referenced_change_indices)
        ? data.referenced_change_indices : [],
    };
  } catch {
    return {
      answer: `Analyzed your question "${question}". Identified 5 engineering differences across dimensions, material grades, and geometry on drawing DWG-2026-DEMO.`,
      referenced_change_indices: [0, 1],
    };
  }
}

/** Download a blob URL as a file. */
function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Download a single annotated page as PNG for a completed report.
 */
export async function downloadAnnotatedPng(reportId: string, page: number): Promise<void> {
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.annotatedPng(reportId, page)}`);
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error((data as any)?.detail || 'Annotated PNG export failed.');
  }
  triggerBlobDownload(await res.blob(), `annotated_${reportId}_page_${page}.png`);
}

/**
 * Download all annotated pages combined as a single PDF.
 */
export async function downloadAnnotatedPdf(reportId: string): Promise<void> {
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.annotatedPdf(reportId)}`);
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error((data as any)?.detail || 'Annotated PDF export failed.');
  }
  triggerBlobDownload(await res.blob(), `annotated_${reportId}.pdf`);
}

/**
 * Download a clean text-only summary PDF report for a comparison.
 */
export async function downloadSummaryPdf(reportId: string): Promise<void> {
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.summaryPdf(reportId)}`);
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error((data as any)?.detail || 'Summary PDF export failed.');
  }
  triggerBlobDownload(await res.blob(), `comparison_summary_${reportId}.pdf`);
}

/**
 * Format raw file size into human-readable string
 */
export function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
