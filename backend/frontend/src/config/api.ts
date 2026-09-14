/// <reference types="vite/client" />

/**
 * Central API configuration using environment variables.
 * Allows effortless environment switching without code modifications.
 */

export const API_CONFIG = {
  baseUrl: ((import.meta as any).env?.VITE_API_BASE_URL as string) || '/api',
  endpoints: {
    compare: '/compare',
    align: '/align',
    upload: '/upload',
    exportJson: '/export/json',
    exportPdf: '/export/pdf',
    ask: '/ask',
    job: (jobId: string) => `/jobs/${jobId}`,
    report: (reportId: string) => `/reports/${reportId}`,
    annotatedPng: (reportId: string, page: number) =>
      `/reports/${reportId}/annotated?format=png&page=${page}`,
    annotatedPdf: (reportId: string) => `/reports/${reportId}/annotated?format=pdf`,
    summaryPdf: (reportId: string) => `/reports/${reportId}/summary-pdf`,
    changeReview: (reportId: string, pageNumber: number, changeIndex: number) =>
      `/reports/${reportId}/changes/${pageNumber}/${changeIndex}/review`,
    reviewsSummary: (reportId: string) => `/reports/${reportId}/reviews/summary`,
    reports: '/reports',
    drawings: '/drawings',
    drawing: (drawingId: string) => `/drawings/${drawingId}`,
    drawingHistory: (drawingId: string) => `/drawings/${drawingId}/history`,
    drawingHistoryExport: (drawingId: string) => `/drawings/${drawingId}/history/export`,
    drawingRevisions: (drawingId: string) => `/drawings/${drawingId}/revisions`,
    drawingRevision: (drawingId: string, revisionId: string) => `/drawings/${drawingId}/revisions/${revisionId}`,
    drawingRevisionRender: (drawingId: string, revisionId: string, page = 1) =>
      `/drawings/${drawingId}/revisions/${revisionId}/render?page=${page}`,
    drawingCompare: (drawingId: string, fromId?: string, toId?: string) => {
      const params = fromId && toId ? `?from=${encodeURIComponent(fromId)}&to=${encodeURIComponent(toId)}` : '';
      return `/drawings/${drawingId}/compare${params}`;
    },
    uploadAndCompare: '/drawings/upload-and-compare',
  },
  // OCR/alignment/LLM comparison can legitimately take longer than 15s.
  // Allow deployments to override this without rebuilding the request logic.
  timeoutMs: Number((import.meta as any).env?.VITE_API_TIMEOUT_MS) || 120000,
  // Poll interval for async job status checks (POST /compare returns 202).
  jobPollIntervalMs: Number((import.meta as any).env?.VITE_JOB_POLL_INTERVAL_MS) || 2000,
  maxFileSizeBytes: 50 * 1024 * 1024, // 50MB max file size
  supportedExtensions: ['.pdf', '.dwg', '.dxf', '.svg', '.png', '.tiff', '.jpg', '.jpeg'],
  supportedMimeTypes: [
    'application/pdf',
    'image/svg+xml',
    'image/png',
    'image/jpeg',
    'image/tiff',
    'application/acad',
    'application/x-acad',
    'application/autocad_dwg',
    'image/x-dwg',
    'application/dxf',
    'image/vnd.dxf',
  ],
};
