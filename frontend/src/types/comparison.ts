// Categories are supplied by the comparison backend and may evolve over time.
export type ChangeCategory = string;

export type ChangeSeverity = 'critical' | 'moderate' | 'minor' | 'info';

export type ChangeReviewStatus = 'pending' | 'approved' | 'flagged' | 'unreviewed';

export interface ChangeRegion {
  x: number;      // % percentage from left (0 - 100)
  y: number;      // % percentage from top (0 - 100)
  width: number;  // % width (0 - 100)
  height: number; // % height (0 - 100)
  zone: string;   // CAD Grid Zone, e.g. "B-3", "D-5"
}

export interface ChangeVerification {
  verified: boolean;
  reason: string | null;
}

export interface ChangeItem {
  id: string;
  category: ChangeCategory;
  title: string;
  description: string;
  /** 1-based page number in the report (for review + annotated-export APIs). */
  pageNumber?: number;
  /** 0-based index of the change within its page (for review API). */
  changeIndex?: number;
  /** Report this change belongs to (for review + QA APIs). */
  reportId?: string;
  region: ChangeRegion;
  oldValue: string;
  newValue: string;
  delta?: string;
  severity: ChangeSeverity;
  status: ChangeReviewStatus;
  affectedFeature: string;
  drawingRevisionA: string;
  drawingRevisionB: string;
  zone: string;
  complianceImpact?: string;
  ocrConfidence?: { old: number; new: number };
  classificationConfidence?: number;
  verification?: ChangeVerification;
  ruleBasedCategory?: string;
  /** Backend llm_classification source: model name, or "fallback" when the VLM call failed. */
  llmSource?: string | null;

  // ── Hybrid VLM pipeline fields (pipeline_version = 'hybrid_v1') ──
  /** Which track produced this change: 'extraction' (Track A) or 'visual' (Track B). */
  source?: 'extraction' | 'visual';
  /** Confidence tier: 'high' for Track A, 'needs_review' for Track B. */
  confidence_tier?: 'high' | 'needs_review';
  /** Free-text location description from VLM (replaces pixel bbox for new reports). */
  location?: string;
  /** Entity name from Track A inventory extraction. */
  entity_name?: string;
}

export interface DrawingFile {
  id: string;
  name: string;
  revision: string;
  fileSize: string;
  dimensions: string;
  type: string; // 'pdf' | 'dwg' | 'dxf' | 'svg' | 'png'
  previewSvg?: string;
  previewUrl?: string;
  uploadedAt: string;
  scale?: string;
  author?: string;
}

export interface ComparisonResult {
  id: string;
  projectName: string;
  drawingNumber: string;
  title: string;
  discipline: 'Mechanical' | 'Architectural' | 'Electrical' | 'Structural';
  oldDrawing: DrawingFile;
  newDrawing: DrawingFile;
  oldDrawingUrl?: string; // Object URL for the uploaded old file
  newDrawingUrl?: string; // Object URL for the uploaded new file
  alignmentScore: number; // 0 - 100%
  alignmentConfidence: 'high' | 'medium' | 'low';
  processingTimeMs: number;
  totalChanges: number;
  overallSimilarity: number;
  totalRegionsDetected: number;
  verificationSummary?: {
    ocrLlmAgreementCount: number;
    ocrLlmDisagreementCount: number;
  };
  comparisonMode?: string;
  redesignDetected?: boolean;
  overallSummary?: string;
  categoryCounts: Record<string, number>;
  changes: ChangeItem[];
  timestamp: string;
  /** Backend report/comparison id (for review, QA, annotated-export APIs). */
  reportId?: string;
  /** Number of pages in the compared document. */
  totalPages?: number;
  /** Pipeline version: 'hybrid_v1' for new VLM-only pipeline, 'legacy' for old CV pipeline. */
  pipelineVersion?: string;
  /** Number of Track A (high-confidence extraction) changes. */
  trackACount?: number;
  /** Number of Track B (needs-review visual) changes. */
  trackBCount?: number;
}

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface JobState {
  job_id: string;
  status: JobStatus;
  progress_message?: string | null;
  error_message?: string | null;
  result?: Record<string, any>;
}

export interface DrawingSummary {
  drawing_id: string;
  name: string;
  created_at: string;
  updated_at?: string;
  revision_count?: number;
}

export interface RevisionInfo {
  revision_id: string;
  drawing_id: string;
  sequence_number: number;
  revision_label: string;
  uploaded_at: string;
  page_count: number;
  original_filename?: string;
}

export interface ConsecutivePair {
  old_revision_id: string;
  new_revision_id: string;
  old_sequence_number: number;
  new_sequence_number: number;
  has_comparison: boolean;
  comparison_id: string | null;
  computed_at: string | null;
}

export interface DrawingHistory {
  drawing_id: string;
  name: string;
  created_at: string;
  revisions: RevisionInfo[];
  consecutive_pairs: ConsecutivePair[];
  all_comparisons?: ConsecutivePair[];
}

export interface ReviewSummary {
  report_id: string;
  total_changes: number;
  confirmed: number;
  false_positive: number;
  unreviewed: number;
  unreviewed_changes: Array<{ page_number: number; change_index: number }>;
}

export interface ChangeReview {
  review_id: string | null;
  report_id: string;
  page_number: number;
  change_index: number;
  status: 'confirmed' | 'false_positive' | 'unreviewed';
  note: string | null;
  reviewed_at: string | null;
  reviewer_id: string | null;
}

export interface QaAnswer {
  answer: string;
  referenced_change_indices: number[];
}

export type AsyncState = 'idle' | 'loading' | 'success' | 'error';

export type ErrorType =
  | '422_ALIGNMENT_FAILED'
  | '500_SERVER_ERROR'
  | 'NETWORK_TIMEOUT'
  | 'INVALID_FILE_TYPE'
  | 'FILE_TOO_LARGE';

export interface ComparisonError {
  type: ErrorType;
  title: string;
  message: string;
  suggestedAction: string;
  technicalDetails?: string;
  statusCode?: number;
  retryable: boolean;
}

export type ViewMode = 'split' | 'curtain' | 'overlay' | 'single';

export interface ViewportState {
  zoom: number;
  panX: number;
  panY: number;
  isSynced: boolean;
  sliderPos: number; // 0 to 100 for curtain view
  overlayOpacity: number; // 0 to 100 for overlay view
  showDiffHighlights: boolean;
  showCADGrid: boolean;
  invertColors: boolean; // Dark CAD blueprint mode
  selectedChangeId: string | null;
  hoveredChangeId: string | null;
}
