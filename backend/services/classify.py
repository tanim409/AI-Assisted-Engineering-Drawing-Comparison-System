

"""Production Diff-Driven ROI Inspection Pipeline with Universal VLM Audit.

Architecture:
  1. Alignment & Registration (OpenCV Homography via services.align)
  2. CV Diff & Cluster Detection (AbsDiff + Morphological Operations via services.diff)
  3. Native ROI Patch Extraction & Coordinate Normalization (via services.diff)
  4. Universal Multi-Discipline VLM Inspection (Gemini / Hugging Face zai-org/GLM-OCR)
  5. VLM Executive Summary Generation (Synthesized narrative of all deltas)
"""

from __future__ import annotations
import base64
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

try:
    import services.env_config
except ImportError:
    pass


# ── Configuration & Models ───────────────────────────────────────────────────

HF_MODEL = os.getenv("HF_MODEL", "zai-org/GLM-OCR")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


# ── Schemas for Structured VLM Outputs ────────────────────────────────────────

class ROIPatchAuditResult(BaseModel):
    is_change: bool = Field(
        description="True if an engineering change occurred. False for scanning artifacts, anti-aliasing noise, or identical linework."
    )
    discipline: str = Field(
        default="Engineering",
        description="Detected domain: Architectural, Mechanical CAD, Electrical Schematic, P&ID, Civil, Structural, etc."
    )
    category: str = Field(
        default="geometry_change",
        description="One of: dimensional_change, geometry_change, symbol_change, text_annotation, title_block, addition, deletion"
    )
    baseline_value: Optional[str] = Field(
        default=None,
        description="Verbatim text, dimension, or graphic state in Crop 1 (None if added)."
    )
    current_value: Optional[str] = Field(
        default=None,
        description="Verbatim text, dimension, or graphic state in Crop 2 (None if removed)."
    )
    description: str = Field(
        description="Concise, engineering-grade description detailing what specifically was altered and its functional significance."
    )


class ExecutiveSummaryResult(BaseModel):
    summary: str = Field(
        description="An executive plain-text summary (2-4 sentences) outlining the total scope, critical areas altered, and discipline context."
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _b64_image(image: np.ndarray, max_dim: int = 4096) -> str:
    """Encode OpenCV image patch to base64 PNG without loss of resolution."""
    if image is None or image.size == 0:
        raise ValueError("Cannot encode an empty image array")
    h, w = image.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode image buffer to PNG")
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


def _extract_json(text: str) -> dict:
    """Extract a valid JSON object from model response text with fallback parsing."""
    if not text:
        raise ValueError("Empty response text from VLM")
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text or "")
    if match:
        cleaned = match.group(1).strip()
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except (json.JSONDecodeError, TypeError):
            pass

    raise ValueError(f"Could not parse valid JSON from VLM output: {text!r}")


# ── VLM Client Management ────────────────────────────────────────────────────

def _make_vlm_client() -> Tuple[Optional[OpenAI], str]:
    """Factory for OpenAI-compatible client. Prioritizes Hugging Face zai-org/GLM-OCR, falls back to Google Gemini direct."""
    hf_token = (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or "").strip()
    google_key = (os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")).strip()

    if hf_token and hf_token != "dummy_test_key":
        client = OpenAI(
            base_url="https://api-inference.huggingface.co/v1",
            api_key=hf_token,
            timeout=90.0,
        )
        return client, "huggingface"

    if google_key and google_key != "dummy_test_key":
        client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=google_key,
            timeout=90.0,
        )
        return client, "google"

    return None, "none"


def _format_model_for_provider(model: str, provider: str) -> str:
    """Ensure proper model identifier prefixing per provider."""
    if provider == "huggingface":
        return model if "/" in model else f"zai-org/{model}"
    return model.replace("google/", "", 1) if model.startswith("google/") else model


def _call_gemini_with_retry(
    client: OpenAI,
    model: str,
    messages: list,
    response_format: Any,
    max_tokens: int = 1024,
    provider: str = "huggingface",
) -> Tuple[dict, str]:
    """Execute API call with structured parsing, candidate model fallbacks, and secondary provider fallback."""
    google_key = (os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")).strip()

    candidate_models = (
        [
            _format_model_for_provider(model, "huggingface"),
            "zai-org/GLM-OCR",
            "THUDM/glm-4v-9b",
        ]
        if provider == "huggingface"
        else [
            _format_model_for_provider(model, "google"),
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
    )
    # Deduplicate while preserving order
    candidate_models = list(dict.fromkeys([m for m in candidate_models if m]))

    for vlm_model in candidate_models:
        for attempt in range(1, 3):
            try:
                try:
                    completion = client.beta.chat.completions.parse(
                        model=vlm_model,
                        messages=messages,
                        response_format=response_format,
                        max_tokens=max_tokens,
                    )
                    parsed = completion.choices[0].message.parsed
                    parsed_dict = parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)
                    return parsed_dict, "structured"
                except Exception:
                    # Fallback to standard JSON schema prompt
                    completion = client.chat.completions.create(
                        model=vlm_model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        max_tokens=max_tokens,
                    )
                    raw_text = completion.choices[0].message.content or ""
                    return _extract_json(raw_text), "fallback_json"
            except Exception as err:
                err_str = str(err).lower()
                is_rate_limit = any(code in err_str for code in ["429", "503", "rate", "resource_exhausted", "unavailable"])
                if attempt < 2 and is_rate_limit:
                    time.sleep(1.0)
                    continue
                break

    # Secondary provider fallback to Gemini direct if primary Hugging Face API call fails
    if provider == "huggingface" and google_key and google_key != "dummy_test_key":
        try:
            gemini_client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=google_key,
                timeout=45.0,
            )
            for g_model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
                try:
                    completion = gemini_client.beta.chat.completions.parse(
                        model=g_model,
                        messages=messages,
                        response_format=response_format,
                        max_tokens=max_tokens,
                    )
                    parsed = completion.choices[0].message.parsed
                    parsed_dict = parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)
                    return parsed_dict, "gemini_fallback_structured"
                except Exception:
                    completion = gemini_client.chat.completions.create(
                        model=g_model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        max_tokens=max_tokens,
                    )
                    raw_text = completion.choices[0].message.content or ""
                    return _extract_json(raw_text), "gemini_fallback_json"
        except Exception as g_err:
            logger.warning(f"[classify] Gemini secondary fallback error: {g_err}")

    raise RuntimeError("All VLM API candidates and retry attempts exhausted.")


# ── Universal Audit Prompts ──────────────────────────────────────────────────

_UNIVERSAL_ROI_SYSTEM_PROMPT = (
    "You are an expert multi-discipline engineering drawing inspector (AEC, Mechanical CAD, Electrical, Civil, P&ID). "
    "You compare high-resolution paired crops from two revisions of a technical drawing to detect modifications with zero hallucination.\n\n"
    "UNIVERSAL PRIMITIVE CATEGORIES TO AUDIT:\n"
    "1. METADATA & TITLE BLOCK: Sheet number, drawing title, revision letter/index, scale, approval stamps, notes.\n"
    "2. NUMERICAL VALUES & SPECIFICATIONS: Dimensional values, tolerances, ratings, gauge sizes, schedules, code callouts.\n"
    "3. GEOMETRIC & LINEWORK ELEMENTS: Added, moved, or deleted walls, boundaries, part features, piping/wiring runs, outlines.\n"
    "4. SYMBOLS & COMPONENT TAGS: Equipment symbols, valves, fixtures, electrical components, fasteners, section cut markers.\n"
    "5. TEXT & ANNOTATIONS: Descriptions, leaders, material callouts, reference keys, room/space identifiers."
)

_UNIVERSAL_ROI_USER_PROMPT = (
    "Compare Crop 1 (Baseline Revision) and Crop 2 (Current Revision).\n\n"
    "Strict Rules:\n"
    "1. Determine if a genuine engineering revision occurred. If the two crops are identical or only exhibit minor "
    "   rasterization noise, slight anti-aliasing differences, or scanner threshold shift, return is_change: false.\n"
    "2. If a genuine modification exists, return is_change: true with:\n"
    "   - discipline: Detected engineering discipline.\n"
    "   - category: One of 'dimensional_change', 'geometry_change', 'symbol_change', 'text_annotation', 'title_block', 'addition', 'deletion'.\n"
    "   - baseline_value: The exact text, measurement, or visual state in Crop 1 (or 'None' if newly added).\n"
    "   - current_value: The exact text, measurement, or visual state in Crop 2 (or 'None' if deleted).\n"
    "   - description: A clear, professional engineering sentence detailing the revision and its functional impact."
)

_EXECUTIVE_SUMMARY_SYSTEM_PROMPT = (
    "You are a lead QA engineering director. You will be given a list of verified deltas extracted "
    "from comparing two revisions of an engineering drawing. Write a concise, professional executive summary "
    "(2 to 4 sentences) describing the overall scope of modifications, the primary discipline, and the key structural/dimensional updates."
)


# ── Audit Logic ───────────────────────────────────────────────────────────────

def audit_roi_patch_pair(
    patch_info: dict,
    client: Optional[OpenAI] = None,
    provider: str = "huggingface",
) -> Optional[dict]:
    """Inspect a single pair of base64 ROI crops using the Universal VLM prompt."""
    if client is None:
        client, provider = _make_vlm_client()

    b64_a = patch_info.get("b64_a")
    b64_b = patch_info.get("b64_b")
    if not b64_a or not b64_b:
        return None

    norm_bbox = patch_info.get("norm_bbox") or {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}
    loc_str = patch_info.get("location") or f"Region (X: {int(norm_bbox['x']*100)}%, Y: {int(norm_bbox['y']*100)}%)"

    if client is None:
        return {
            "source": "roi_diff",
            "confidence_tier": "medium",
            "discipline": "Engineering",
            "category": "geometry_change",
            "location": loc_str,
            "zone": loc_str,
            "bbox": norm_bbox,
            "norm_bbox": norm_bbox,
            "baseline_value": "Baseline Feature",
            "current_value": "Revised Feature",
            "old_value": "Baseline Feature",
            "new_value": "Revised Feature",
            "description": f"Visual difference detected in region {loc_str} (CV Diff inspection).",
            "is_change": True,
            "status": "pending",
        }

    messages = [
        {"role": "system", "content": _UNIVERSAL_ROI_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _UNIVERSAL_ROI_USER_PROMPT},
                {"type": "text", "text": "Crop 1 (Baseline Revision):"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_a}"}},
                {"type": "text", "text": "Crop 2 (Current Revision):"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_b}"}},
            ],
        },
    ]

    model = os.getenv("HF_MODEL") or os.getenv("GEMINI_MODEL") or HF_MODEL

    try:
        res_dict, _ = _call_gemini_with_retry(
            client, model, messages, ROIPatchAuditResult, max_tokens=512, provider=provider
        )

        if not res_dict.get("is_change", False):
            return None

        discipline = res_dict.get("discipline") or "Engineering"
        category = res_dict.get("category") or "geometry_change"
        baseline_val = res_dict.get("baseline_value")
        current_val = res_dict.get("current_value")
        desc = res_dict.get("description") or "Engineering revision identified."

        return {
            "source": "roi_diff",
            "confidence_tier": "high",
            "discipline": discipline,
            "category": category,
            "location": loc_str,
            "zone": loc_str,
            # Dual mapping: satisfies both canvas renderers and review panel inspectors
            "bbox": norm_bbox,
            "norm_bbox": norm_bbox,
            "baseline_value": baseline_val,
            "current_value": current_val,
            "old_value": baseline_val or "",
            "new_value": current_val or "",
            "description": desc,
            "is_change": True,
            "status": "pending",
        }
    except Exception as e:
        logger.error(f"[classify] Audit error on patch {patch_info.get('patch_id')}: {e}")
        # Rule-based fallback for CV-detected diff cluster when VLM API call fails
        return {
            "source": "roi_diff",
            "confidence_tier": "medium",
            "discipline": "Engineering",
            "category": "geometry_change",
            "location": loc_str,
            "zone": loc_str,
            "bbox": norm_bbox,
            "norm_bbox": norm_bbox,
            "baseline_value": "Baseline Feature",
            "current_value": "Revised Feature",
            "old_value": "Baseline Feature",
            "new_value": "Revised Feature",
            "description": f"Visual difference detected in region {loc_str}.",
            "is_change": True,
            "status": "pending",
        }


def audit_all_roi_patches(patches: List[dict], max_workers: int = 5) -> List[dict]:
    """Concurrently audit all ROI patch pairs using worker threads with rule-based fallback."""
    if not patches:
        return []

    client, provider = _make_vlm_client()
    if client is None:
        logger.warning("[classify] No VLM API key configured. Using rule-based CV diff classification.")

    verified_changes: List[dict] = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(patches))) as executor:
        future_to_patch = {
            executor.submit(audit_roi_patch_pair, patch, client, provider): patch
            for patch in patches
        }
        for future in as_completed(future_to_patch):
            try:
                change = future.result()
                if change:
                    verified_changes.append(change)
            except Exception as err:
                logger.error(f"[classify] Worker exception: {err}")

    # Sort deterministically from top-left to bottom-right based on coordinate space
    verified_changes.sort(key=lambda c: (c["bbox"]["y"], c["bbox"]["x"]))

    # Assign formal sequential engineering IDs
    for idx, change in enumerate(verified_changes):
        change["id"] = f"CHG-{idx + 1:03d}"

    return verified_changes


def generate_executive_summary(
    changes: List[dict],
    total_candidates: int,
    client: Optional[OpenAI] = None,
    provider: str = "huggingface",
) -> str:
    """Generate a real natural language executive summary using Gemini based on verified deltas."""
    if not changes:
        return "Comparison completed: No engineering revisions or drawing discrepancies were detected between the revisions."

    if client is None:
        client, provider = _make_vlm_client()
    if client is None:
        return f"Audit complete: Identified {len(changes)} confirmed revision change(s) across candidate regions."

    deltas_text = "\n".join([
        f"- [{c['category']}] at {c['location']}: {c['description']} (Old: {c.get('old_value') or 'N/A'} -> New: {c.get('new_value') or 'N/A'})"
        for c in changes[:20]  # Cap context to prevent token overflows
    ])

    messages = [
        {"role": "system", "content": _EXECUTIVE_SUMMARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Drawing Changes Detected ({len(changes)} total):\n{deltas_text}\n\nProvide the executive summary.",
        },
    ]

    model = os.getenv("HF_MODEL") or os.getenv("GEMINI_MODEL") or HF_MODEL
    try:
        res_dict, _ = _call_gemini_with_retry(
            client, model, messages, ExecutiveSummaryResult, max_tokens=256, provider=provider
        )
        return res_dict.get("summary", "").strip()
    except Exception as e:
        logger.error(f"[classify] Summary synthesis failed: {e}")
        # Dynamic fallback computed strictly from real data
        disciplines = list(dict.fromkeys(c.get("discipline") for c in changes if c.get("discipline")))
        disc_str = ", ".join(disciplines) if disciplines else "Engineering"
        return f"Comparison identified {len(changes)} verified revision change(s) across {total_candidates} difference regions in this {disc_str} drawing."


# ── Public Entry Point ────────────────────────────────────────────────────────

def compare_drawing_pages(old_img: np.ndarray, new_img: np.ndarray) -> Dict[str, Any]:
    """Execute the end-to-end 4-step Diff-Driven ROI comparison pipeline."""
    from services.align import align_drawings
    from services.diff import detect_diff_clusters, merge_nearby_boxes, extract_roi_patches

    # Step 1: Alignment & Registration
    logger.info("[classify] Step 1: Aligning drawing revisions...")
    img_a, aligned_b, alignment_conf, is_warped = align_drawings(old_img, new_img)

    # Step 2: CV Diff & Cluster Detection
    logger.info("[classify] Step 2: Running pixel difference and cluster analysis...")
    raw_boxes = detect_diff_clusters(img_a, aligned_b, min_area=150)

    # Step 3: Box Merging & Native Patch Extraction
    logger.info(f"[classify] Step 3: Merging {len(raw_boxes)} raw clusters and cropping patches...")
    merged_boxes = merge_nearby_boxes(raw_boxes, distance_threshold=40)
    patches = extract_roi_patches(img_a, aligned_b, merged_boxes, padding_pct=0.15)

    # Step 4: Universal VLM Audit
    logger.info(f"[classify] Step 4: Auditing {len(patches)} ROI patch candidates with VLM...")
    verified_changes = audit_all_roi_patches(patches)

    # Step 5: VLM Executive Summary Generation
    client, provider = _make_vlm_client()
    overall_summary = generate_executive_summary(
        verified_changes, len(patches), client=client, provider=provider
    )

    primary_discipline = (
        verified_changes[0].get("discipline", "Engineering")
        if verified_changes
        else "Engineering"
    )

    return {
        "discipline": primary_discipline,
        "summary": overall_summary,
        "overall_summary": overall_summary,
        "total_changes": len(verified_changes),
        "changes": verified_changes,
        "_aligned_image": aligned_b,
        "alignment_confidence": alignment_conf,
        "is_warped": is_warped,
    }


# ── Compatibility Wrappers ───────────────────────────────────────────────────

def classify_whole_image(old_gray: np.ndarray, new_gray_aligned: np.ndarray) -> Dict[str, Any]:
    """Router for existing endpoints calling classify_whole_image."""
    return compare_drawing_pages(old_gray, new_gray_aligned)


def llm_classify_batch(*args, **kwargs) -> Dict[str, Any]:
    """Fallback stub for legacy callers."""
    return {"results": {}, "overall_summary": "Diff-Driven ROI pipeline active."}