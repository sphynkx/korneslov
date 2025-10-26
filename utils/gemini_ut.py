import logging
from typing import Optional

from google.genai import types as genai_types


def build_gemini_config(
    max_output_tokens: Optional[int],
    temperature: Optional[float],
    system_instruction: str,
) -> Optional[genai_types.GenerateContentConfig]:
    """
    Build Google GenAI GenerateContentConfig safely.
    """
    try:
        kwargs = {}
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if isinstance(max_output_tokens, int) and max_output_tokens > 0:
            kwargs["max_output_tokens"] = int(max_output_tokens)
        if temperature is not None:
            kwargs["temperature"] = float(temperature)
        return genai_types.GenerateContentConfig(**kwargs)
    except Exception:
        logging.exception("Failed to build GenerateContentConfig")
        return None


def extract_text_from_gemini_response(resp) -> str:
    """
    Extracts text from various Gemini response shapes.
    Returns "" if nothing found.
    """
    try:
        if resp is None:
            return ""

        ## Try direct .text
        text = getattr(resp, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        ## Try .output (list of parts)
        out = getattr(resp, "output", None)
        if out:
            s = _collect_parts_text(out)
            if s:
                return s

        ## Try .result.candidates[0].content.parts (older shapes)
        result = getattr(resp, "result", None)
        if result:
            candidates = getattr(result, "candidates", None) or (result.get("candidates") if isinstance(result, dict) else None)
            if candidates:
                content = _get_candidate_content(candidates[0])
                if content:
                    s = _collect_parts_text(content)
                    if s:
                        return s

        ## Try dict-like fallbacks
        if isinstance(resp, dict):
            for key in ("text", "output", "result", "candidates", "content"):
                val = resp.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
                if isinstance(val, (list, tuple)):
                    s = _collect_parts_text(val)
                    if s:
                        return s

        return ""
    except Exception as e:
        logging.exception("extract_text_from_gemini_response failed: %s", e)
        try:
            logging.debug("repr(resp) truncated: %s", repr(resp)[:4000])
        except Exception:
            pass
        return ""


def _collect_parts_text(parts) -> str:
    texts = []
    try:
        iterable = parts if isinstance(parts, (list, tuple)) else [parts]
        for item in iterable:
            ## item may be Content, Part, or dict-like
            txt = None
            if hasattr(item, "text"):
                txt = getattr(item, "text", None)
            elif isinstance(item, dict):
                txt = item.get("text") or item.get("plain_text") or item.get("textRaw")
            else:
                ## last fallback
                if isinstance(item, str):
                    txt = item
            if isinstance(txt, str) and txt.strip():
                texts.append(txt.strip())
    except Exception:
        logging.exception("Failed to collect parts text from Gemini response")
    return "\n\n".join(t for t in texts if t).strip()
