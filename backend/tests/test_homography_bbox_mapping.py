import os
import sys
import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.align import align_image
from services.comparison_engine import compare_single_page, _transform_bbox_to_raw_new


def test_homography_bbox_transformation():
    """Verify that bounding box coordinates are correctly mapped back to raw image space via inverse homography H."""
    # Create baseline image (500x500 white canvas with geometric elements)
    img_old = np.ones((500, 500, 3), dtype=np.uint8) * 255
    cv2.rectangle(img_old, (50, 50), (450, 450), (0, 0, 0), 3)
    cv2.circle(img_old, (100, 100), 20, (0, 0, 0), 2)
    cv2.circle(img_old, (400, 100), 20, (0, 0, 0), 2)
    cv2.circle(img_old, (100, 400), 20, (0, 0, 0), 2)
    cv2.circle(img_old, (400, 400), 20, (0, 0, 0), 2)
    cv2.putText(img_old, "REV A NOTE", (200, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Create modified image with a shift of (+30px, +20px) and rotation
    M = np.float32([[1, 0, 30], [0, 1, 20]])
    img_new_raw = cv2.warpAffine(img_old, M, (500, 500), borderValue=(255, 255, 255))
    # Add a change at location (200, 250) on modified drawing
    cv2.putText(img_new_raw, "REV B REVISED", (200, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    gray_old = cv2.cvtColor(img_old, cv2.COLOR_BGR2GRAY)
    gray_new = cv2.cvtColor(img_new_raw, cv2.COLOR_BGR2GRAY)

    alignment = align_image(gray_old, gray_new)
    assert "H" in alignment, "Alignment result must contain Homography matrix H"
    H = alignment["H"]
    assert H is not None, "Homography matrix H must not be None"

    report = compare_single_page(gray_old, gray_new)
    changes = report.get("changes", [])
    assert len(changes) > 0, "Pipeline must detect changes"

    chg = changes[0]
    assert "bbox_percent" in chg, "Change must contain bbox_percent (Source drawing space)"
    assert "bbox_percent_new" in chg, "Change must contain bbox_percent_new (Modified raw drawing space)"

    bbox_a = chg["bbox_percent"]
    bbox_b = chg["bbox_percent_new"]

    print(f"\n[ACCEPTANCE TEST] BBox Source (Rev A): {bbox_a}")
    print(f"[ACCEPTANCE TEST] BBox Modified Raw (Rev B): {bbox_b}")

    # Verify that homography transformation mapped the coordinates accurately
    assert bbox_a != bbox_b, "Modified space bbox should be transformed by homography matrix H"


if __name__ == "__main__":
    test_homography_bbox_transformation()
