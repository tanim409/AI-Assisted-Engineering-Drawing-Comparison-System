"""Step 2 & Step 3 — CV Diff, Cluster Detection, & ROI Patch Extraction.

Computes pixel differences on aligned drawing pairs, isolates change clusters
using tight morphology, merges proximate boxes without runaway collapse,
and extracts 100% native-resolution ROI patch pairs with contextual margins.
"""
import base64
import cv2
import numpy as np


def detect_diff_clusters(
    img_a: np.ndarray,
    aligned_b: np.ndarray,
    min_area: int = 120,
    thresh_val: int = 30,
    morph_kernel_size: tuple[int, int] = (9, 9),
) -> list[tuple[int, int, int, int]]:
    """Detect bounding boxes of visual difference clusters between two aligned images."""
    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY) if img_a.ndim == 3 else img_a
    gray_b = cv2.cvtColor(aligned_b, cv2.COLOR_BGR2GRAY) if aligned_b.ndim == 3 else aligned_b

    # Mild Gaussian blur to suppress scanner paper grain
    blur_a = cv2.GaussianBlur(gray_a, (3, 3), 0)
    blur_b = cv2.GaussianBlur(gray_b, (3, 3), 0)

    # Absolute pixel difference
    diff = cv2.absdiff(blur_a, blur_b)

    # Binary threshold
    _, thresh = cv2.threshold(diff, thresh_val, 255, cv2.THRESH_BINARY)

    # Closing bridges broken text/lines without inflating outer boundaries
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, morph_kernel_size)
    morphed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Find external contours
    contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area >= min_area:
            x, y, w, h = cv2.boundingRect(c)
            boxes.append((x, y, w, h))

    print(f"[diff] Detected {len(boxes)} raw diff contour boxes (min_area={min_area})")
    return boxes


def merge_nearby_boxes(
    boxes: list[tuple[int, int, int, int]],
    distance_threshold: int = 25,
    max_box_ratio: float = 0.65,
    page_shape: tuple[int, int] = None,
) -> list[tuple[int, int, int, int]]:
    """Combine proximate bounding boxes while preventing full-page collapse."""
    if not boxes:
        return []

    rects = [[x, y, x + w, y + h] for (x, y, w, h) in boxes]
    max_w = int(page_shape[1] * max_box_ratio) if page_shape else 99999
    max_h = int(page_shape[0] * max_box_ratio) if page_shape else 99999

    while True:
        merged = False
        new_rects = []
        skip_indices = set()

        for i in range(len(rects)):
            if i in skip_indices:
                continue

            r1 = rects[i]
            x1_a, y1_a, x2_a, y2_a = r1

            for j in range(i + 1, len(rects)):
                if j in skip_indices:
                    continue

                r2 = rects[j]
                x1_b, y1_b, x2_b, y2_b = r2

                gap_x = max(0, max(x1_a, x1_b) - min(x2_a, x2_b))
                gap_y = max(0, max(y1_a, y1_b) - min(y2_a, y2_b))

                if gap_x <= distance_threshold and gap_y <= distance_threshold:
                    candidate_w = max(x2_a, x2_b) - min(x1_a, x1_b)
                    candidate_h = max(y2_a, y2_b) - min(y1_a, y1_b)

                    # Prevent merging if resulting box engulfs the whole page
                    if candidate_w <= max_w and candidate_h <= max_h:
                        x1_a = min(x1_a, x1_b)
                        y1_a = min(y1_a, y1_b)
                        x2_a = max(x2_a, x2_b)
                        y2_a = max(y2_a, y2_b)
                        skip_indices.add(j)
                        merged = True

            new_rects.append([x1_a, y1_a, x2_a, y2_a])

        rects = new_rects
        if not merged:
            break

    merged_boxes = [(r[0], r[1], r[2] - r[0], r[3] - r[1]) for r in rects]
    print(f"[diff] Merged {len(boxes)} raw boxes into {len(merged_boxes)} discrete ROI clusters")
    return merged_boxes


def extract_roi_patches(
    img_a: np.ndarray,
    aligned_b: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
    padding_pct: float = 0.15,
) -> list[dict]:
    """Crop native 100% resolution patch pairs with contextual padding and normalized bboxes."""
    H, W = img_a.shape[:2]
    patches = []

    for idx, (x, y, w, h) in enumerate(boxes):
        pad_w = max(int(w * padding_pct), 15)
        pad_h = max(int(h * padding_pct), 15)

        crop_y1 = max(0, y - pad_h)
        crop_y2 = min(H, y + h + pad_h)
        crop_x1 = max(0, x - pad_w)
        crop_x2 = min(W, x + w + pad_w)

        patch_a = img_a[crop_y1:crop_y2, crop_x1:crop_x2]
        patch_b = aligned_b[crop_y1:crop_y2, crop_x1:crop_x2]

        if patch_a.size == 0 or patch_b.size == 0:
            continue

        ok_a, buf_a = cv2.imencode(".png", patch_a)
        ok_b, buf_b = cv2.imencode(".png", patch_b)

        if not ok_a or not ok_b:
            continue

        norm_bbox = {
            "x": round(x / float(W), 4),
            "y": round(y / float(H), 4),
            "w": round(w / float(W), 4),
            "h": round(h / float(H), 4),
        }

        patches.append({
            "patch_id": f"ROI-{idx + 1:03d}",
            "patch_a": patch_a,
            "patch_b": patch_b,
            "b64_a": base64.b64encode(buf_a.tobytes()).decode("utf-8"),
            "b64_b": base64.b64encode(buf_b.tobytes()).decode("utf-8"),
            "raw_bbox": {"x": x, "y": y, "w": w, "h": h},
            "norm_bbox": norm_bbox,
            "location": f"Zone (X: {int(norm_bbox['x'] * 100)}%, Y: {int(norm_bbox['y'] * 100)}%)",
        })

    return patches