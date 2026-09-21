import os
import json
from typing import Optional, List, Dict, Any
import services.config  # Loads env vars
from openai import OpenAI
from pydantic import BaseModel, Field
from schemas.drawing_schema import QAResponse


def get_qa_client() -> tuple[Optional[OpenAI], str]:
    hf_token = (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or "").strip()
    google_key = (os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")).strip()

    if hf_token and hf_token != "dummy_test_key":
        return OpenAI(
            base_url="https://api-inference.huggingface.co/v1",
            api_key=hf_token,
            timeout=45.0,
        ), "huggingface"

    if google_key and google_key != "dummy_test_key":
        return OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=google_key,
            timeout=45.0,
        ), "google"

    return None, "none"


def answer_question(changes: List[Dict[str, Any]], question: str) -> dict:
    if not changes:
        return {
            "answer": "No changes were detected in this comparison, so there is nothing to query.",
            "referenced_change_indices": [],
        }

    # Matches the exact root fields produced by the Diff-Driven ROI classify.py
    trimmed = []
    for i, c in enumerate(changes):
        trimmed.append({
            "index": i,
            "id": c.get("id", f"CHG-{i + 1:03d}"),
            "discipline": c.get("discipline", "General"),
            "category": c.get("category", "geometry_change"),
            "description": c.get("description", ""),
            "old_value": c.get("baseline_value") or c.get("old_value") or "None",
            "new_value": c.get("current_value") or c.get("new_value") or "None",
            "location": c.get("location") or c.get("zone") or "Unspecified",
        })

    prompt = f"""You are an engineering change analyst reviewing verified drawing differences.

Verified Change List:
{json.dumps(trimmed, indent=2)}

Answer the user's question using ONLY the data in this list.
If the information cannot be confirmed from this list, state clearly that it is not present in the revision log.
Always cite the exact indices of any changes you reference in 'referenced_change_indices'.

Question: {question}"""

    client, provider = get_qa_client()
    if not client:
        return {
            "answer": "AI Q&A is currently unavailable (no API key configured).",
            "referenced_change_indices": [],
        }

    if provider == "huggingface":
        raw_model = os.getenv("HF_MODEL") or "zai-org/GLM-OCR"
        model = raw_model if "/" in raw_model else f"zai-org/{raw_model}"
    else:
        raw_model = os.getenv("GEMINI_MODEL") or "gemini-2.0-flash"
        model = raw_model.replace("google/", "", 1) if raw_model.startswith("google/") else raw_model

    try:
        response = client.beta.chat.completions.parse(
            model=model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
            response_format=QAResponse,
        )
        result = response.choices[0].message.parsed
        return {
            "answer": result.answer,
            "referenced_change_indices": result.referenced_change_indices,
        }
    except Exception as e:
        print(f"[answer_question] parse error, trying json fallback: {e}")
        try:
            # Fallback for models or proxies where structured schema parsing fails
            fallback_completion = client.chat.completions.create(
                model=model,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            raw_data = json.loads(fallback_completion.choices[0].message.content or "{}")
            return {
                "answer": raw_data.get("answer", "Unable to retrieve a detailed answer."),
                "referenced_change_indices": raw_data.get("referenced_change_indices", []),
            }
        except Exception as fallback_err:
            print(f"[answer_question] fatal error: {fallback_err}")
            return {
                "answer": "An error occurred while answering your question. Please try again.",
                "referenced_change_indices": [],
            }