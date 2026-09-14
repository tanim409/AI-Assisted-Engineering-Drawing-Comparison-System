import { API_CONFIG } from '../config/api';
import { ChangeReview, ChangeReviewStatus, ReviewSummary } from '../types/comparison';
import { mapFrontendReviewStatus } from './comparisonService';
import { authFetch } from './authService';

export type { ChangeReview };

function checkOk(res: Response, data: any, fallback: string): void {
  if (!res.ok) {
    throw new Error((data as any)?.detail || fallback);
  }
}

/**
 * Persist a human review decision for one change. Frontend statuses map to
 * backend ones: approved -> confirmed, flagged/rejected -> false_positive.
 */
export async function submitChangeReview(
  reportId: string,
  pageNumber: number,
  changeIndex: number,
  status: ChangeReviewStatus,
  note?: string,
  reviewerId?: string
): Promise<ChangeReview> {
  const res = await authFetch(
    `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.changeReview(reportId, pageNumber, changeIndex)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: mapFrontendReviewStatus(status),
        note: note ?? null,
        reviewer_id: reviewerId ?? null,
      }),
    }
  );
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not save review.');
  return data as ChangeReview;
}

export async function fetchChangeReview(
  reportId: string,
  pageNumber: number,
  changeIndex: number
): Promise<ChangeReview> {
  const res = await authFetch(
    `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.changeReview(reportId, pageNumber, changeIndex)}`
  );
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not load review.');
  return data as ChangeReview;
}

export async function fetchReviewsSummary(reportId: string): Promise<ReviewSummary> {
  const res = await authFetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.reviewsSummary(reportId)}`);
  const data = await res.json().catch(() => null);
  checkOk(res, data, 'Could not load review summary.');
  return data as ReviewSummary;
}
