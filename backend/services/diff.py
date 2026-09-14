import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
def compute_diff_mask(old_gray, new_gray_aligned):
    score, diff = ssim(old_gray, new_gray_aligned, full=True)
    diff = (diff * 255).astype("uint8")

    thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # Use smaller 5x5 kernel and 1 iteration to prevent aggressive merging of distinct nearby changes
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close, iterations=1)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel_open, iterations=1)
    return {
        'similarity_score': score,
        'diff': diff,
        'mask': cleaned
    }

def extract_change_regions(mask, min_area=40):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        pad = 6
        regions.append({
            'area': area,
            'x': max(0, x - pad),
            'y': max(0, y - pad),
            'w': w + 2 * pad,
            'h': h + 2 * pad
        })

    regions.sort(key=lambda r: r['area'], reverse=True)
    return regions


def crop_region(img: np.ndarray, region: dict) -> np.ndarray:
    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
    H, W = img.shape[:2]
    x2, y2 = min(W, x + w), min(H, y + h)
    return img[y:y2, x:x2]


def extract_paired_crops(old_gray: np.ndarray, new_gray_aligned: np.ndarray, regions: list, pad_pct: float = 0.18) -> list:
    """
    For each region in regions, extract crop from old_gray and aligned new_gray_aligned
    with contextual padding (15-20%), and stitch them side-by-side [OLD (left) | divider | NEW (right)].
    Returns list of stitched image patches (np.ndarray).
    """
    H, W = old_gray.shape[:2]
    patches = []
    divider_width = 4
    
    for reg in regions:
        x, y, w, h = reg["x"], reg["y"], reg["w"], reg["h"]
        pad_x = int(w * pad_pct)
        pad_y = int(h * pad_pct)
        
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(W, x + w + pad_x)
        y2 = min(H, y + h + pad_y)
        
        crop_old = old_gray[y1:y2, x1:x2]
        crop_new = new_gray_aligned[y1:y2, x1:x2]
        
        # Ensure 3-channel BGR images for visualization/stitching with clear divider
        if crop_old.ndim == 2:
            crop_old_bgr = cv2.cvtColor(crop_old, cv2.COLOR_GRAY2BGR)
        else:
            crop_old_bgr = crop_old.copy()
            
        if crop_new.ndim == 2:
            crop_new_bgr = cv2.cvtColor(crop_new, cv2.COLOR_GRAY2BGR)
        else:
            crop_new_bgr = crop_new.copy()
            
        h_old, w_old = crop_old_bgr.shape[:2]
        h_new, w_new = crop_new_bgr.shape[:2]
        
        # Match height if slight mismatch
        target_h = max(h_old, h_new)
        if h_old != target_h:
            crop_old_bgr = cv2.resize(crop_old_bgr, (w_old, target_h), interpolation=cv2.INTER_AREA)
        if h_new != target_h:
            crop_new_bgr = cv2.resize(crop_new_bgr, (w_new, target_h), interpolation=cv2.INTER_AREA)
            
        divider = np.zeros((target_h, divider_width, 3), dtype=np.uint8)
        divider[:, :] = (0, 0, 255)  # Bright red divider between OLD and NEW
        
        stitched = np.hstack([crop_old_bgr, divider, crop_new_bgr])
        patches.append(stitched)
        
    return patches



def make_grid_regions(shape, rows=4, cols=4):
    """Return deterministic positional tiles covering an image."""
    height, width = shape[:2]
    regions = []
    for row in range(rows):
        y0 = round(row * height / rows)
        y1 = round((row + 1) * height / rows)
        for col in range(cols):
            x0 = round(col * width / cols)
            x1 = round((col + 1) * width / cols)
            regions.append({
                "x": x0,
                "y": y0,
                "w": max(1, x1 - x0),
                "h": max(1, y1 - y0),
                "area": (x1 - x0) * (y1 - y0),
                "row": row,
                "col": col,
            })
    return regions



def redesign_metrics(mask, similarity_score, alignment_info, regions):
    """Calculate signals used to decide whether page-level OCR is unsafe."""
    image_area = max(1, mask.shape[0] * mask.shape[1])
    diff_coverage = float(np.count_nonzero(mask)) / image_area
    largest_region_ratio = 0.0
    if regions:
        largest_region_ratio = float(regions[0]["w"] * regions[0]["h"]) / image_area
    return {
        "diff_coverage": round(diff_coverage, 4),
        "largest_region_ratio": round(largest_region_ratio, 4),
        "similarity": round(float(similarity_score), 4),
        "alignment_confidence": round(float(alignment_info.get("confidence", 0)), 4),
    }



def is_redesign(metrics, similarity_threshold=0.65, alignment_threshold=0.35,
                coverage_threshold=0.45, region_threshold=0.60):
    """Use multiple signals; one noisy metric should not force tiled mode."""
    return (
        metrics["alignment_confidence"] < alignment_threshold
        or metrics["similarity"] < similarity_threshold
        or metrics["diff_coverage"] > coverage_threshold
        or metrics["largest_region_ratio"] > region_threshold
    )
