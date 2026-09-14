"""Resolve drawing-specific pipeline thresholds over existing env defaults."""
import os
from typing import Any

from model import versioning_db


# Keep the existing environment names and defaults as the baseline. The extra
# target width name was not previously consumed by the engine, so its default
# intentionally mirrors MAX_WIDTH_FOR_BASE_DPI (24 inches).
GLOBAL_DEFAULTS = {
    "min_ocr_confidence": float(os.getenv("MIN_OCR_CONFIDENCE", "35")),
    "visual_change_threshold": float(os.getenv("VISUAL_CHANGE_THRESHOLD", "8.0")),
    "min_title_match_score": float(os.getenv("MIN_TITLE_MATCH_SCORE", "70")),
    "min_title_ocr_confidence": float(os.getenv("MIN_TITLE_OCR_CONFIDENCE", "30")),
    "min_title_words": int(os.getenv("MIN_TITLE_WORDS", "2")),
    "title_block_x_pct": float(os.getenv("TITLE_BLOCK_X_PCT", "0.65")),
    "title_block_y_pct": float(os.getenv("TITLE_BLOCK_Y_PCT", "0.85")),
    "title_block_w_pct": float(os.getenv("TITLE_BLOCK_W_PCT", "0.35")),
    "title_block_h_pct": float(os.getenv("TITLE_BLOCK_H_PCT", "0.15")),
    "page_size_mismatch_threshold": float(os.getenv("PAGE_SIZE_MISMATCH_THRESHOLD", "0.05")),
    "target_physical_width_inches": float(
        os.getenv("TARGET_PHYSICAL_WIDTH_INCHES", os.getenv("MAX_WIDTH_FOR_BASE_DPI", "24.0"))
    ),
}


def resolve_effective_settings(drawing_id: str | None = None) -> dict[str, Any]:
    overrides = versioning_db.get_drawing_settings(drawing_id) if drawing_id else None
    values = {}
    for key, global_value in GLOBAL_DEFAULTS.items():
        override = overrides.get(key) if overrides else None
        values[key] = override if override is not None else global_value
    return values


def get_effective_settings_response(drawing_id: str) -> dict[str, dict[str, Any]]:
    overrides = versioning_db.get_drawing_settings(drawing_id) or {}
    return {
        key: {"value": overrides[key] if overrides.get(key) is not None else default,
              "source": "override" if overrides.get(key) is not None else "global"}
        for key, default in GLOBAL_DEFAULTS.items()
    }


def validate_settings_update(drawing_id: str, update: dict[str, Any]) -> None:
    """Validate supplied values and the effective title-block rectangle."""
    for key, value in update.items():
        if value is None:
            continue
        if key in {"min_ocr_confidence", "min_title_match_score", "min_title_ocr_confidence"} and not 0 <= value <= 100:
            raise ValueError(f"{key} must be between 0 and 100")
        if key == "visual_change_threshold" and not 0 <= value <= 100:
            raise ValueError("visual_change_threshold must be between 0 and 100")
        if key == "min_title_words" and not 1 <= value <= 100:
            raise ValueError("min_title_words must be between 1 and 100")
        if key in {"title_block_x_pct", "title_block_y_pct", "title_block_w_pct", "title_block_h_pct"} and not 0 <= value <= 1:
            raise ValueError(f"{key} must be between 0 and 1")
        if key == "page_size_mismatch_threshold" and not 0 <= value <= 1:
            raise ValueError("page_size_mismatch_threshold must be between 0 and 1")
        if key == "target_physical_width_inches" and not 0 < value <= 500:
            raise ValueError("target_physical_width_inches must be greater than 0 and at most 500")

    effective = resolve_effective_settings(drawing_id)
    effective.update({key: value for key, value in update.items() if value is not None})
    # A null means revert to global, not keep the previous override.
    for key, value in update.items():
        if value is None:
            effective[key] = GLOBAL_DEFAULTS[key]
    if effective["title_block_x_pct"] + effective["title_block_w_pct"] > 1 or \
       effective["title_block_y_pct"] + effective["title_block_h_pct"] > 1:
        raise ValueError("title block x + w and y + h must each be within the page (<= 1)")
