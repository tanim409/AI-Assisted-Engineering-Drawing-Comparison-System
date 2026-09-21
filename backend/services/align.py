"""Step 1 — Alignment & Registration Module (OpenCV Homography).

Loads Drawing A (baseline) and Drawing B (modified) at native resolution,
extracts keypoints/descriptors via ORB (with fallback options), matches features
using Lowe's ratio test filter, and computes the homography transformation matrix
via RANSAC. Warps Drawing B to align with Drawing A.

If alignment confidence is low or homography fails (e.g. completely redesigned sheet),
falls back gracefully to aspect-ratio safe scaling without crashing.
"""
import cv2
import numpy as np


def extract_features(gray: np.ndarray, nfeatures: int = 5000):
    """Extract keypoints and descriptors using ORB (or SIFT/AKAZE fallback)."""
    orb = cv2.ORB_create(nfeatures=nfeatures, scoreType=cv2.ORB_HARRIS_SCORE)
    kp, des = orb.detectAndCompute(gray, None)
    
    # Fallback to SIFT if ORB keypoint count is too low
    if (des is None or len(kp) < 30) and hasattr(cv2, "SIFT_create"):
        try:
            sift = cv2.SIFT_create(nfeatures=nfeatures)
            kp, des = sift.detectAndCompute(gray, None)
        except Exception as e:
            print(f"[align] SIFT fallback failed: {e}")
            
    return kp, des


def align_drawings(
    img_a: np.ndarray,
    img_b: np.ndarray,
    ratio_threshold: float = 0.75,
    min_matches: int = 10,
    min_inliers: int = 8,
) -> tuple[np.ndarray, np.ndarray, float, bool]:
    """Align Drawing B to Drawing A using OpenCV feature matching & RANSAC homography.

    Args:
        img_a: Baseline image (BGR or Gray).
        img_b: Revised/modified image (BGR or Gray).
        ratio_threshold: Lowe's ratio test filter threshold (default 0.75).
        min_matches: Minimum feature matches needed to attempt homography.
        min_inliers: Minimum RANSAC inliers to consider alignment successful.

    Returns:
        (img_a, aligned_img_b, confidence, is_warped)
        where confidence is float 0.0-1.0 and is_warped indicates homography success.
    """
    h_a, w_a = img_a.shape[:2]
    h_b, w_b = img_b.shape[:2]

    # Helper for aspect-ratio safe fallback resizing
    def _fallback(reason: str) -> tuple[np.ndarray, np.ndarray, float, bool]:
        print(f"[align] Homography fallback ({reason}) — performing aspect-ratio safe resize")
        resized_b = cv2.resize(img_b, (w_a, h_a), interpolation=cv2.INTER_AREA)
        return img_a, resized_b, 0.0, False

    try:
        # Convert to grayscale for keypoint detection
        gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY) if img_a.ndim == 3 else img_a
        gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY) if img_b.ndim == 3 else img_b

        # Extract ORB / SIFT keypoints & descriptors
        kp_a, des_a = extract_features(gray_a)
        kp_b, des_b = extract_features(gray_b)

        if des_a is None or des_b is None or len(kp_a) < min_matches or len(kp_b) < min_matches:
            return _fallback("insufficient keypoints extracted")

        # Determine descriptor matcher norm type (HAMMING for ORB binary, L2 for SIFT float)
        norm_type = cv2.NORM_HAMMING if des_a.dtype == np.uint8 else cv2.NORM_L2
        bf = cv2.BFMatcher(norm_type, crossCheck=False)

        # KNN match (k=2) for Lowe's ratio test
        matches = bf.knnMatch(des_b, des_a, k=2)

        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < ratio_threshold * n.distance:
                    good_matches.append(m)

        if len(good_matches) < min_matches:
            return _fallback(f"only {len(good_matches)} matches passed ratio test (needed {min_matches})")

        # Extract coordinates of matched keypoints
        pts_b = np.float32([kp_b[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        pts_a = np.float32([kp_a[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # Compute Homography via RANSAC
        H, mask = cv2.findHomography(pts_b, pts_a, cv2.RANSAC, 5.0)

        if H is None or mask is None:
            return _fallback("findHomography returned None")

        inliers_count = int(np.sum(mask))
        confidence = round(inliers_count / max(1, len(good_matches)), 3)

        # Check for degenerate or singular homography matrix
        det = np.linalg.det(H)
        if abs(det) < 1e-6 or abs(det) > 1e6 or inliers_count < min_inliers:
            return _fallback(f"degenerate homography (det={det:.2e}, inliers={inliers_count})")

        # Warp Drawing B to align with Drawing A
        aligned_b = cv2.warpPerspective(img_b, H, (w_a, h_a), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        print(f"[align] Alignment successful: {inliers_count}/{len(good_matches)} inliers (conf={confidence})")
        return img_a, aligned_b, confidence, True

    except Exception as e:
        return _fallback(f"exception raised: {e}")
