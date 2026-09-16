import os,json
import services.config  # Loads env vars
from openai import OpenAI
from pydantic import BaseModel, Field
from schemas.drawing_schema import QAResponse

def get_qa_client():
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if google_key and google_key != "dummy_test_key":
        return OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=google_key,
            timeout=45.0,
        )
    return None

def answer_question(changes: list, question: str) -> dict:
    if not changes:
        return {
            "answer": "No changes were detected in this comparison, so there's nothing to answer questions about.",
            "referenced_change_indices": [],
        }
    trimmed=[
        {
            "index": i,
            "category": c.get("classification", {}).get("category"),
            "description": c.get("llm_classification", {}).get("description"),
            "old_text": c.get("old_text"),
            "new_text": c.get("new_text"),
            "location_percent": c.get("bbox_percent"),
        }
        for i, c in enumerate(changes)
    ]

    prompt = f"""Here is the full list of detected changes from an engineering drawing comparison:

    {json.dumps(trimmed, indent=2)}

    Answer the user's question using ONLY the information in this list. Do not
    invent details not present here. If the question can't be answered from
    this list, say so clearly rather than guessing.

    Question: {question}"""

    client = get_qa_client()
    if not client:
        return {
            "answer": "AI Q&A is currently unavailable (no API key configured).",
            "referenced_change_indices": [],
        }

    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    try:
        response = client.beta.chat.completions.parse(
            model=gemini_model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            response_format=QAResponse,
        )
        result = response.choices[0].message.parsed
        return {
            "answer": result.answer,
            "referenced_change_indices": result.referenced_change_indices,
        }
    except Exception as e:
        print(f"[answer_question] error: {e}")
        return {
            "answer": "Sorry, I couldn't process that question right now. Please try again.",
            "referenced_change_indices": [],
        }


    return None