"""
Google Gemini NLP Service
==========================
Entity extraction, GRI/SASB gap assessment, section summarisation.
Degrades gracefully when GEMINI_API_KEY is not set.

Includes a combined analysis path (analyze_document) that performs entity
extraction and compliance gap assessment in a single LLM call to reduce
cost and latency versus calling extract_entities() and
assess_compliance_gaps() separately.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.core.config import settings
from app.models.schemas import ExtractedEntity

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is not None:
        return _model
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_name = getattr(settings, "GEMINI_MODEL", None) or "gemini-1.5-flash"
        _model = genai.GenerativeModel(model_name)
    except Exception:
        logger.exception("Failed to initialize Gemini model")
        _model = None
    return _model


async def _call_with_retry(prompt: str, retries: int = 2) -> str:
    model = _get_model()
    if model is None:
        return ""
    for attempt in range(retries + 1):
        try:
            response = await asyncio.to_thread(model.generate_content, prompt)
            text = getattr(response, "text", "") or ""
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            return text.strip()
        except Exception:
            logger.exception("Gemini call failed (attempt %s)", attempt)
            if attempt < retries:
                await asyncio.sleep(1.5 * (attempt + 1))
    return ""


_ENTITY_PROMPT = """\
You are an ESG compliance analyst. Extract key entities (organizations, metrics,
standards, dates, locations) from the document below.
Return JSON: [{{"text": "...", "label": "...", "context": "..."}}]

DOCUMENT TEXT (first 8,000 chars):
\"\"\"
{text}
\"\"\"

Return ONLY valid JSON.
"""

_GAP_PROMPT = """\
You are an ESG compliance analyst. Analyse the document for GRI/SASB compliance gaps.
Return JSON: {{"gap_summary": "...", "gaps": [{{"area": "...", "severity": "critical|high|medium|low", "description": "...", "gri_reference": "...", "sasb_reference": "...", "remediation": "..."}}]}}

DOCUMENT TEXT (first 10,000 chars):
\"\"\"
{text}
\"\"\"

Return ONLY valid JSON.
"""

_COMBINED_PROMPT = """\
You are an ESG compliance analyst. Given the document text below, perform TWO tasks
and return a SINGLE JSON object with both results:

1. entities: Extract key entities (organizations, metrics, standards, dates, locations).
2. compliance: Analyse the document for GRI/SASB compliance gaps.

Return JSON in exactly this shape:
{{
  "entities": [{{"text": "...", "label": "...", "context": "..."}}],
  "compliance": {{
    "gap_summary": "...",
    "gaps": [{{"area": "...", "severity": "critical|high|medium|low", "description": "...", "gri_reference": "...", "sasb_reference": "...", "remediation": "..."}}]
  }}
}}

DOCUMENT TEXT (first 10,000 chars):
\"\"\"
{text}
\"\"\"

Return ONLY valid JSON, no markdown fences, no commentary.
"""


async def extract_entities(text: str, max_chars: int = 8000) -> list[ExtractedEntity]:
    raw = await _call_with_retry(_ENTITY_PROMPT.format(text=text[:max_chars]))
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [
            ExtractedEntity(
                text=item.get("text", ""),
                label=item.get("label", "UNKNOWN"),
                context=item.get("context", ""),
            )
            for item in data
            if isinstance(item, dict) and item.get("text")
        ]
    except (json.JSONDecodeError, TypeError):
        return []


async def assess_compliance_gaps(text: str) -> dict[str, Any]:
    raw = await _call_with_retry(_GAP_PROMPT.format(text=text[:10000]))
    if not raw:
        return {"gap_summary": "", "gaps": []}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"gap_summary": "", "gaps": []}


async def analyze_document(text: str, max_chars: int = 10000) -> dict[str, Any]:
    """Combined entity extraction + compliance gap assessment in a single LLM call.

    Returns a dict with keys:
      - entities: list[ExtractedEntity]
      - compliance: dict[str, Any] (gap_summary, gaps)

    Falls back to two separate calls if the combined call fails to parse,
    to preserve existing behaviour and reliability.
    """
    raw = await _call_with_retry(_COMBINED_PROMPT.format(text=text[:max_chars]))
    if raw:
        try:
            data = json.loads(raw)
            entities_raw = data.get("entities", []) or []
            entities = [
                ExtractedEntity(
                    text=item.get("text", ""),
                    label=item.get("label", "UNKNOWN"),
                    context=item.get("context", ""),
                )
                for item in entities_raw
                if isinstance(item, dict) and item.get("text")
            ]
            compliance = data.get("compliance") or {"gap_summary": "", "gaps": []}
            return {"entities": entities, "compliance": compliance}
        except (json.JSONDecodeError, TypeError, AttributeError):
            logger.warning("Combined analysis JSON parse failed, falling back to two calls")
    entities = await extract_entities(text)
    compliance = await assess_compliance_gaps(text)
    return {"entities": entities, "compliance": compliance}


class GeminiNLPService:
    async def extract_entities(self, text: str) -> list[ExtractedEntity]:
        return await extract_entities(text)

    async def assess_compliance_gaps(self, text: str) -> dict[str, Any]:
        return await assess_compliance_gaps(text)

    async def analyze_document(self, text: str) -> dict[str, Any]:
        return await analyze_document(text)
