"""
Google Gemini NLP Service
==========================
Entity extraction, GRI/SASB gap assessment, section summarisation.
Degrades gracefully when GEMINI_API_KEY is not set.
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
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — Gemini NLP disabled.")
        return None
    try:
        import google.generativeai as genai  # noqa: PLC0415
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _model = genai.GenerativeModel(settings.GEMINI_MODEL)
        logger.info("Gemini model '%s' initialised.", settings.GEMINI_MODEL)
    except ImportError:
        logger.warning("google-generativeai not installed.")
    return _model


async def _call_with_retry(prompt: str, max_retries: int = 3) -> str | None:
    model = _get_model()
    if model is None:
        return None
    import google.generativeai as genai  # noqa: PLC0415
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                model.generate_content, prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json", temperature=0.1),
            )
            return response.text
        except Exception as exc:  # noqa: BLE001
            wait = 2 ** attempt
            logger.warning("Gemini attempt %d/%d failed: %s — retrying in %ds", attempt + 1, max_retries, exc, wait)
            if attempt < max_retries - 1:
                await asyncio.sleep(wait)
    return None


_ENTITY_PROMPT = """\
Extract named entities from the text. Return a JSON array of objects with fields:
- "text": entity surface form
- "label": one of ORG, MONEY, DATE, PERCENT, GPE, METRIC, QUANTITY
- "context": 10-20 word surrounding snippet

TEXT:
\"\"\"
{text}
\"\"\"

Return ONLY valid JSON array.
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


async def extract_entities(text: str, max_chars: int = 8000) -> list[ExtractedEntity]:
    raw = await _call_with_retry(_ENTITY_PROMPT.format(text=text[:max_chars]))
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [ExtractedEntity(text=item.get("text", ""), label=item.get("label", "UNKNOWN"),
                                context=item.get("context", ""))
                for item in data if isinstance(item, dict) and item.get("text")]
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


class GeminiNLPService:
    async def extract_entities(self, text: str) -> list[ExtractedEntity]:
        return await extract_entities(text)

    async def assess_compliance_gaps(self, text: str) -> dict[str, Any]:
        return await assess_compliance_gaps(text)
