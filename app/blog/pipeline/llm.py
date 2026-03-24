"""LLM client singleton for blog pipeline."""
import os
from typing import Optional

from openai import OpenAI

MODEL = "gpt-4o"
MAX_TOKENS_JSON = 4000
MAX_TOKENS_TEXT = 5000

_client: Optional[OpenAI] = None


def get_llm_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")
        _client = OpenAI(api_key=api_key)
    return _client


def parse_json_response(text: str, fallback: dict) -> dict:
    """Parse JSON from LLM response, applying fallback on failure."""
    import json

    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        inner = lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except Exception:
                pass
    return fallback
