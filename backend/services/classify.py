import base64
import json
import os
import re
import time

import cv2
import numpy as np
import services.config  # Loads env vars

from openai import OpenAI
from schemas.drawing_schema import BatchClassification

# ── API clients ──────────────────────────────────────────────────────────────

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    timeout=60.0,
)

google_client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GOOGLE_API_KEY", "dummy_test_key"),
    timeout=180.0,  # Hard timeout — never block indefinitely
)

# Use the confirmed live model; override via GEMINI_MODEL env var if needed
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _b64_image(image: np.ndarray, max_dim: int = 1024) -> str:
    """Resize image patch if needed and encode as base64 PNG."""
    h, w = image.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode image patch as PNG")
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


def _extract_json(text: str) -> dict:
    """Extract a JSON object from a string, stripping markdown fences or repairing truncated JSON."""
    if not text:
        raise ValueError("Empty response text")

    # 1. Try direct parse first
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. Strip ```json ... ``` or ``` ... ``` fences
    cleaned_text = text
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text or "")
    if match:
        cleaned_text = match.group(1).strip()
        try:
            return json.loads(cleaned_text)
        except (json.JSONDecodeError, TypeError):
            pass

    # 3. Find the outermost { ... } block
    start = cleaned_text.find("{")
    end = cleaned_text.rfind("}")
    if start != -1 and end > start:
        snippet = cleaned_text[start : end + 1]
        try:
            return json.loads(snippet)
        except (json.JSONDecodeError, TypeError):
            pass

    # 4. Repair truncated JSON (e.g. cut off inside overall_summary string)
    if start != -1:
        snippet = cleaned_text[start:]
        candidates = [
            snippet + '"}\n]}',
            snippet + '"}]}',
            snippet + '"\n  ]\n}',
            snippet + '"]}',
            snippet + '}',
        ]
        for cand in candidates:
            try:
                return json.loads(cand)
            except (json.JSONDecodeError, TypeError):
                pass

    # 5. Fallback regex extraction for region objects in results array
    region_pattern = re.compile(
        r'\{\s*"region_index"\s*:\s*(\d+)[\s\S]*?"category"\s*:\s*"([^"]+)"[\s\S]*?"description"\s*:\s*"([^"]+)"[\s\S]*?"confidence"\s*:\s*([\d\.]+)'
    )
    matches = region_pattern.findall(text)
    if matches:
        extracted_results = []
        for reg_idx, cat, desc, conf in matches:
            extracted_results.append({
                "region_index": int(reg_idx),
                "category": cat,
                "description": desc,
                "confidence": float(conf)
            })

        summary_match = re.search(r'"overall_summary"\s*:\s*"([^"]*)', text)
        summary = summary_match.group(1) if summary_match else "Batch analyzed by Gemini."

        return {
            "results": extracted_results,
            "overall_summary": summary
        }

    raise ValueError(f"Could not parse JSON from model response: {text!r}")


def _fallback_batch(batch_regions: list, start_index: int, reason: str) -> dict:
    results = {}
    for i, reg in enumerate(batch_regions):
        region_index = start_index + i
        results[region_index] = {
            "region_index": region_index,
            "category": reg.get("classification", {}).get("category", "note_or_annotation_change"),
            "description": "Rule-based change region detected.",
            "confidence": 0.7,
            "source": "fallback",
        }
    
    clean_summary = "Automated visual comparison completed across detected drawing regions."
    if "429" in str(reason):
        print(f"[classify] Gemini Rate Limit (429) hit: {reason}")
    else:
        print(f"[classify] VLM fallback triggered: {reason}")

    return {"results": results, "overall_summary": clean_summary}


# ── Gemini classification ─────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are an engineering drawing QA assistant. "
    "Respond ONLY with a valid JSON object — no markdown, no prose outside the JSON."
)

_USER_PROMPT_TEMPLATE = (
    "I am providing {n} side-by-side patch images. Each shows OLD (left) and NEW (right) "
    "sections of an engineering drawing revision.\n\n"
    "For each region classify the change into ONE of:\n"
    "  addition, removal, note_or_annotation_change, symbol_or_code_change, "
    "dimension_change, no_change\n\n"
    "Keep descriptions concise (1 sentence, max 15 words). If text/numbers changed, explicitly include 'old_value' and 'new_value'. You MUST return an entry in 'results' for EVERY region index provided.\n\n"
    "Return ONLY a JSON object with this exact structure:\n"
    '{{\n'
    '  "results": [\n'
    '    {{"region_index": <int>, "category": "<str>", "description": "<str>", "old_value": "<str>", "new_value": "<str>", "confidence": <float>}}\n'
    '  ],\n'
    '  "overall_summary": "<str>"\n'
    '}}'
)


def _classify_via_gemini(batch_regions: list, patch_images: list, start_index: int) -> dict:
    """Send side-by-side crop patch images to Gemini via OpenAI-compatible endpoint.
    
    Tries Google Direct API first. If Google API fails (e.g. 429 quota, auth error),
    falls back to OpenRouter API (google/gemini-2.5-flash).
    """
    n = len(patch_images)
    user_content: list = [
        {"type": "text", "text": _USER_PROMPT_TEMPLATE.format(n=n)},
    ]
    for idx, patch in enumerate(patch_images):
        region_idx = start_index + idx
        b64 = _b64_image(patch)
        user_content.append({"type": "text", "text": f"Region {region_idx}:"})
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })

    last_error = None
    
    # 1. Try Google Direct Client first
    google_key = os.getenv("GOOGLE_API_KEY", "")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    if google_key and google_key != "dummy_test_key":
        try:
            print(f"[classify] Calling Gemini Direct (model={gemini_model}), {n} regions starting at {start_index}")
            client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=google_key,
                timeout=15.0,
            )
            completion = client.chat.completions.create(
                model=gemini_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=2048,
            )
            response_text = completion.choices[0].message.content
            parsed = _extract_json(response_text)

            results = {}
            for res in parsed.get("results", []):
                idx = res.get("region_index")
                if idx is not None:
                    results[idx] = {
                        "region_index": idx,
                        "category": res.get("category", "note_or_annotation_change"),
                        "description": res.get("description", "No description provided"),
                        "old_value": res.get("old_value", ""),
                        "new_value": res.get("new_value", ""),
                        "confidence": float(res.get("confidence", 0.8)),
                        "source": gemini_model,
                    }
            print(f"[classify] Successfully classified {len(results)} regions via Gemini Direct")
            return {
                "results": results,
                "overall_summary": parsed.get("overall_summary", "Batch analyzed by Gemini Direct."),
            }
        except Exception as e:
            last_error = e
            print(f"[classify] Gemini Direct API failed ({e}). Trying OpenRouter fallback...")

    # 2. Try OpenRouter Client as secondary VLM fallback
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key:
        try:
            openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
            print(f"[classify] Calling OpenRouter VLM (model={openrouter_model}), {n} regions starting at {start_index}")
            or_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
                timeout=25.0,
            )
            completion = or_client.chat.completions.create(
                model=openrouter_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=1024,
            )
            response_text = completion.choices[0].message.content
            parsed = _extract_json(response_text)

            results = {}
            for res in parsed.get("results", []):
                idx = res.get("region_index")
                if idx is not None:
                    results[idx] = {
                        "region_index": idx,
                        "category": res.get("category", "note_or_annotation_change"),
                        "description": res.get("description", "No description provided"),
                        "old_value": res.get("old_value", ""),
                        "new_value": res.get("new_value", ""),
                        "confidence": float(res.get("confidence", 0.8)),
                        "source": openrouter_model,
                    }
            print(f"[classify] Successfully classified {len(results)} regions via OpenRouter VLM")
            return {
                "results": results,
                "overall_summary": parsed.get("overall_summary", "Batch analyzed by OpenRouter VLM."),
            }
        except Exception as e:
            last_error = e
            print(f"[classify] OpenRouter VLM API failed ({e}).")

    print(f"[classify] All VLM endpoints failed, using rule-based fallback")
    return _fallback_batch(batch_regions, start_index, f"VLM API failed: {last_error}")


def _classify_single_batch(
    batch_regions: list, patch_images: list, start_index: int, model_name: str
) -> dict:
    """Classify side-by-side patch crops using Gemini (model_name retained for logging)."""
    return _classify_via_gemini(batch_regions, patch_images, start_index)


# ── Public API ────────────────────────────────────────────────────────────────

def llm_classify_batch(
    flagged_regions: list,
    patch_images: list = None,
    old_gray=None,
    new_gray=None,
) -> dict:
    """Classify candidate regions using paired side-by-side patch images with VLM."""
    if not flagged_regions:
        return {"results": {}, "overall_summary": "No candidate changes were detected."}

    model_name = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash")
    chunk_size = 4
    all_results = {}
    summaries = []

    # Build patch images if not supplied directly
    if patch_images is None or len(patch_images) != len(flagged_regions):
        from services.diff import extract_paired_crops
        if old_gray is not None and new_gray is not None:
            patch_images = extract_paired_crops(
                old_gray, new_gray,
                [r["bbox"] if "bbox" in r else r for r in flagged_regions],
            )
        else:
            patch_images = [np.zeros((100, 200, 3), dtype=np.uint8) for _ in flagged_regions]

    try:
        for i in range(0, len(flagged_regions), chunk_size):
            chunk_regions = flagged_regions[i : i + chunk_size]
            chunk_patches = patch_images[i : i + chunk_size]
            batch_data = _classify_single_batch(chunk_regions, chunk_patches, i, model_name)
            all_results.update(batch_data["results"])
            if batch_data.get("overall_summary"):
                summaries.append(batch_data["overall_summary"])

        # Fill any gaps with rule-based fallback (no LLM result for that index)
        fallback = _fallback_batch(flagged_regions, 0, "Batch analysis completed.")
        for index, result in fallback["results"].items():
            all_results.setdefault(index, result)

        fallback_count = sum(1 for r in all_results.values() if r.get("source") == "fallback")
        if all_results and fallback_count >= len(all_results):
            # Nothing came back from the model — say so explicitly instead of
            # letting generic rule-based text pass as AI output downstream.
            final_summary = (
                "VLM classification unavailable — all descriptions are rule-based. "
                "Check the backend model API key/configuration and retry."
            )
        else:
            final_summary = " ".join(summaries) if summaries else "Comparison completed."
        return {"results": all_results, "overall_summary": final_summary}

    except Exception as error:
        print(f"[llm_classify_batch] falling back, error: {error}")
        failed = _fallback_batch(flagged_regions, 0, "VLM verification unavailable.")
        failed["overall_summary"] = (
            "VLM classification unavailable — all descriptions are rule-based. "
            "Check the backend model API key/configuration and retry."
        )
        return failed
