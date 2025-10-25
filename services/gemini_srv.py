"""
Service wrapper for Gemini (google.genai) with retry-on-truncation logic.

Changes made:
- returns ret.truncated (bool), ret.finish_reason, ret.attempts and ret.last_max_output
- truncated detection considers presence of end-marker "<b>\u200b\u200b\u200b\u200b</b>" as authoritative,
  otherwise falls back to finish_reason (MAX_TOKENS) or usage vs requested max_out.
- preserves previous debug prints and retry sequence. Does not write /tmp files.
"""
import os
import logging
import asyncio
import json
from types import SimpleNamespace
from typing import Any, Dict, Optional, Tuple
from datetime import datetime
import re

from config import GEMINI_API_KEY, GEMINI_MAX_OUTPUT_TOKENS_CAP, GEMINI_FALLBACK_SEQUENCE, GEMINI_MODEL_PARAMS

## Try to import google.genai; raise helpful error if missing.
try:
    from google import genai
    from google.genai import types as genai_types
except Exception as e:
    genai = None
    genai_types = None
    _import_error = e

END_MARKER_RE = re.compile(r"<b>\u200b\u200b\u200b\u200b</b>")


def _mask_params_for_logging(params: Dict[str, Any]) -> Dict[str, Any]:
    p = {}
    for k, v in params.items():
        if k.lower() in ("api_key", "api_key_secret"):
            p[k] = "****"
        elif k == "messages":
            p_msgs = []
            for m in v:
                content = m.get("content", "")
                p_msgs.append({
                    "role": m.get("role"),
                    "content_preview": (content[:100] + "…") if len(content) > 100 else content
                })
            p[k] = p_msgs
        else:
            try:
                p[k] = v if isinstance(v, (str, int, float, bool, type(None))) else str(type(v))
            except Exception:
                p[k] = "<unserializable>"
    return p


def _print_tokens_multiline(prompt_tokens: Optional[int], completion_tokens: Optional[int], total_tokens: Optional[int]):
    try:
        print("=" * 14)
        print("Gemini tokens (if available):")
        print(f"prompt_tokens: {prompt_tokens}")
        print(f"completion_tokens: {completion_tokens}")
        print(f"total_tokens: {total_tokens}")
        print("=" * 14)
    except Exception:
        logging.exception("Failed to pretty-print Gemini tokens")


def _safe_to_dict(obj):
    try:
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "toJSON"):
            return json.loads(obj.toJSON())
    except Exception:
        pass
    try:
        return json.loads(json.dumps(obj, default=lambda o: str(o)))
    except Exception:
        return None


def _extract_from_output_list(out) -> str:
    texts = []
    try:
        iterable = out if isinstance(out, (list, tuple)) else [out]
        for item in iterable:
            content = getattr(item, "content", None) or (item.get("content") if isinstance(item, dict) else None)
            if content:
                cont_iter = content if isinstance(content, (list, tuple)) else [content]
                for piece in cont_iter:
                    txt = None
                    if hasattr(piece, "text"):
                        txt = getattr(piece, "text", "")
                    elif isinstance(piece, dict):
                        txt = piece.get("text") or piece.get("plain_text") or piece.get("textRaw")
                    else:
                        txt = str(piece)
                    if txt:
                        texts.append(str(txt))
    except Exception:
        logging.exception("Error while extracting from output list")
    return "\n\n".join(t for t in texts if t).strip()


async def _list_models_diagnostic():
    """
    Try to list models supported by the genai client for diagnostics.
    Return textual summary (truncated) or a dict with 'error'.
    """
    if genai is None:
        return {"error": "google.genai not available"}
    def _call_list():
        try:
            c = genai.Client(api_key=GEMINI_API_KEY)
            try:
                res = c.list_models()
                return res
            except Exception:
                try:
                    res = c.models.list()
                    return res
                except Exception as e2:
                    return {"error": f"list models failed: {e2}"}
        except Exception as e:
            return {"error": f"client init/list failed: {e}"}
    try:
        return await asyncio.to_thread(_call_list)
    except Exception as e:
        logging.exception("Model listing diagnostic failed: %s", e)
        return {"error": str(e)}


def _build_gen_config(max_output_tokens: Optional[int], system_instruction: Optional[str], temperature: Optional[float], top_p: Optional[float]):
    kwargs = {}
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    if max_output_tokens is not None:
        kwargs["max_output_tokens"] = int(max_output_tokens)
    if temperature is not None:
        kwargs["temperature"] = float(temperature)
    if top_p is not None:
        kwargs["top_p"] = float(top_p)
    try:
        return genai_types.GenerateContentConfig(**kwargs) if genai_types is not None else None
    except Exception:
        logging.exception("Failed to build GenerateContentConfig with kwargs=%s", kwargs)
        return None


def _parse_usage_metadata(response) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Extract prompt / completion / total tokens from possible response fields."""
    try:
        meta = getattr(response, "usage_metadata", None) or getattr(response, "metadata", None) or (response.get("usage_metadata") if isinstance(response, dict) else None) or (response.get("metadata") if isinstance(response, dict) else None)
        if meta:
            prompt = getattr(meta, "prompt_token_count", None) or (meta.get("prompt_token_count") if isinstance(meta, dict) else None)
            total = getattr(meta, "total_token_count", None) or (meta.get("total_token_count") if isinstance(meta, dict) else None)
            if prompt is not None and total is not None:
                completion = total - prompt
            else:
                completion = None
            return int(prompt) if prompt is not None else None, int(completion) if completion is not None else None, int(total) if total is not None else None
    except Exception:
        logging.exception("Failed to parse usage metadata")
    return None, None, None


def _finish_reason_is_max_tokens(finish_reason) -> bool:
    if finish_reason is None:
        return False
    try:
        name = getattr(finish_reason, "name", None)
        if isinstance(name, str) and name.upper() == "MAX_TOKENS":
            return True
        val = getattr(finish_reason, "value", None)
        if isinstance(val, str) and "MAX_TOKENS" in val.upper():
            return True
        s = str(finish_reason)
        if "MAX_TOKENS" in s.upper():
            return True
    except Exception:
        pass
    return False


async def create_chat_completion(params: Dict[str, Any]):
    """
    Async wrapper that calls Gemini (google.genai) to generate content.

    Returns SimpleNamespace with fields:
     - choices: [SimpleNamespace(message=SimpleNamespace(content=str))]
     - usage: SimpleNamespace(prompt_tokens=.., completion_tokens=.., total_tokens=..)
     - text: extracted text
     - truncated: bool
     - finish_reason: raw finish_reason
     - attempts: list of tried max_output_tokens
     - last_max_output: last attempted max_output_tokens
    """
    if genai is None or genai_types is None:
        logging.error("google.genai package is not available: %s", globals().get("_import_error"))
        raise RuntimeError("Gemini client library (google.genai) is not installed")

    if not GEMINI_API_KEY:
        logging.error("GEMINI_API_KEY is not configured.")
        raise RuntimeError("GEMINI_API_KEY not set")

    try:
        masked = _mask_params_for_logging(params)
        logging.debug("Gemini request params (sanitized): %s", masked)
        print("GEMINI REQUEST:", masked)
    except Exception:
        logging.exception("Failed to log sanitized Gemini params")

    model = params.get("model")
    messages = params.get("messages", [])
    system_instruction = None
    user_parts = []
    for m in messages:
        role = (m.get("role") or "").lower()
        content = m.get("content", "") or ""
        if role == "system" and not system_instruction:
            system_instruction = content
        else:
            if content:
                user_parts.append(content)

    user_contents = "\n\n".join(user_parts).strip() or params.get("contents", "")
    requested_max_tokens = params.get("max_tokens") or params.get("max_output_tokens")
    try:
        requested_max_tokens = int(requested_max_tokens) if requested_max_tokens is not None else None
    except Exception:
        requested_max_tokens = None

    ## Apply model default if configured and requested is smaller or None
    try:
        model_defaults = GEMINI_MODEL_PARAMS.get(model, {}) if isinstance(GEMINI_MODEL_PARAMS, dict) else {}
        model_default_max = int(model_defaults.get("max_tokens")) if model_defaults.get("max_tokens") is not None else None
    except Exception:
        model_default_max = None

    if model_default_max and (requested_max_tokens is None or requested_max_tokens < model_default_max):
        logging.info("Raising requested_max_tokens from %s to model default %s for model=%s", requested_max_tokens, model_default_max, model)
        requested_max_tokens = model_default_max

    temperature = params.get("temperature", None)
    top_p = params.get("top_p", None)

    ## compute initial capped tokens
    if requested_max_tokens is not None:
        initial_max = min(requested_max_tokens, GEMINI_MAX_OUTPUT_TOKENS_CAP)
    else:
        initial_max = GEMINI_FALLBACK_SEQUENCE[0] if GEMINI_FALLBACK_SEQUENCE else None

    ## prepare sequence to try: initial, then fallback sizes (unique)
    seq = []
    if initial_max is not None:
        seq.append(initial_max)
    for v in GEMINI_FALLBACK_SEQUENCE:
        if v not in seq:
            seq.append(v)

    last_response = None
    last_response_text = ""
    last_usage_tuple = (None, None, None)
    last_finish_reason = None
    last_max_out_attempted = None
    attempt_idx = -1

    for attempt_idx, max_out in enumerate(seq):
        last_max_out_attempted = max_out
        try:
            logging.info("Gemini attempt %d/%d with max_output_tokens=%s", attempt_idx + 1, len(seq), max_out)
            cfg = _build_gen_config(max_out, system_instruction, temperature, top_p)

            ## start timing
            start_time = datetime.now()
            try:
                response = await asyncio.to_thread(lambda c=cfg: genai.Client(api_key=GEMINI_API_KEY).models.generate_content(model=model, config=c, contents=user_contents) if c is not None else genai.Client(api_key=GEMINI_API_KEY).models.generate_content(model=model, contents=user_contents), cfg)
            except Exception as e:
                logging.exception("Gemini call failed on attempt %d: %s", attempt_idx + 1, e)
                last_response = e
                raise

            request_time = datetime.now() - start_time

            last_response = response
            prompt_t, completion_t, total_t = _parse_usage_metadata(response)
            last_usage_tuple = (prompt_t, completion_t, total_t)

            ## Try extract text
            response_text = ""
            try:
                if hasattr(response, "text"):
                    response_text = getattr(response, "text") or ""
                    if isinstance(response_text, bytes):
                        response_text = response_text.decode(errors="ignore")
                    response_text = (response_text or "").strip()

                if not response_text:
                    out = getattr(response, "output", None)
                    if out:
                        response_text = _extract_from_output_list(out)

                if not response_text:
                    res = getattr(response, "result", None)
                    if res:
                        candidates = getattr(res, "candidates", None) or (res.get("candidates") if isinstance(res, dict) else None)
                        if candidates:
                            cand = candidates[0]
                            content = getattr(cand, "content", None) or (cand.get("content") if isinstance(cand, dict) else None)
                            if content:
                                response_text = _extract_from_output_list(content)
                            else:
                                out_block = None
                                if isinstance(cand, dict):
                                    out_block = cand.get("output", None)
                                else:
                                    out_block = getattr(cand, "output", None)
                                if out_block:
                                    response_text = _extract_from_output_list(out_block)

                if not response_text:
                    alt = ""
                    for attr in ("output_text", "textHtml", "content", "result_text"):
                        val = getattr(response, attr, None) or (response.get(attr) if isinstance(response, dict) else None)
                        if val:
                            alt = val if isinstance(val, str) else str(val)
                            break
                    response_text = (alt or "").strip()

                if not response_text:
                    td = _safe_to_dict(response)
                    if td and isinstance(td, dict):
                        for key in ("text", "output", "result", "candidates"):
                            if key in td and td[key]:
                                first = td[key]
                                if isinstance(first, str):
                                    response_text = first
                                else:
                                    response_text = json.dumps(first, default=str, ensure_ascii=False)[:4000]
                                    break
            except Exception:
                logging.exception("Error during extraction on attempt %d", attempt_idx + 1)

            ## inspect finish reason if present on candidate
            finish_reason = None
            try:
                if hasattr(response, "candidates") and response.candidates:
                    cand0 = response.candidates[0]
                    finish_reason = getattr(cand0, "finish_reason", None) or getattr(cand0, "finishMessage", None) or getattr(cand0, "finish_reason", None)
                else:
                    res = getattr(response, "result", None)
                    if res:
                        candlist = getattr(res, "candidates", None) or (res.get("candidates") if isinstance(res, dict) else None)
                        if candlist:
                            cand0 = candlist[0]
                            finish_reason = getattr(cand0, "finish_reason", None) or None
            except Exception:
                logging.exception("Failed to detect finish_reason")

            last_finish_reason = finish_reason

            ## Log attempt summary
            print(f"GEMINI ATTEMPT {attempt_idx + 1}: max_output_tokens={max_out}; extracted_len={len(response_text)}")
            if any(x is not None for x in (prompt_t, completion_t, total_t)):
                print(f"usage -> prompt={prompt_t} completion={completion_t} total={total_t}")
            print(f"Request time: {request_time}")
            logging.debug("Attempt %d finish_reason=%s", attempt_idx + 1, finish_reason)

            if response_text:
                last_response_text = response_text
                last_usage_tuple = (prompt_t, completion_t, total_t)
                ## if we got text — decide if it is full by marker or finish_reason
                if END_MARKER_RE.search(response_text):
                    # found the explicit end marker — it's complete
                    break
                ## else, if finish_reason does not indicate MAX_TOKENS, we consider it complete
                if not _finish_reason_is_max_tokens(finish_reason):
                    break
                ## else continue to retries
                continue

            ## If empty and finish_reason indicates MAX_TOKENS, then retry with smaller max_output_tokens
            if _finish_reason_is_max_tokens(finish_reason):
                logging.warning("Attempt %d ended with finish_reason=MAX_TOKENS and empty content; will retry with smaller max_output_tokens", attempt_idx + 1)
                continue
            else:
                logging.warning("Attempt %d returned empty content with finish_reason=%s; aborting further retries", attempt_idx + 1, finish_reason)
                break

        except Exception as e_outer:
            logging.exception("Exception during Gemini attempt %d: %s", attempt_idx + 1, e_outer)
            continue

    ## After attempts: last_response_text may be empty
    response_text = last_response_text or ""
    prompt_t, completion_t, total_t = last_usage_tuple

    ## Determine truncated flag:
    ## - If explicit marker present → not truncated
    ## - Else, if finish reason indicates MAX_TOKENS OR completion_t >= last_max_out_attempted → truncated True
    try:
        marker_present = bool(response_text and END_MARKER_RE.search(response_text))
    except Exception:
        marker_present = False

    try:
        truncated_flag = False
        if not marker_present:
            if last_finish_reason and _finish_reason_is_max_tokens(last_finish_reason):
                truncated_flag = True
            elif completion_t is not None and last_max_out_attempted is not None and completion_t >= int(last_max_out_attempted) - 1:
                truncated_flag = True
    except Exception:
        truncated_flag = False

    ## Diagnostics if still empty
    if not response_text:
        try:
            print("GEMINI RESPONSE (preview):")
            print("")
            print("DEBUG: failed to extract response text after retries. Dumping diagnostics and models list (truncated).")
            try:
                print("repr(last_response) (truncated):", repr(last_response)[:4000])
            except Exception:
                pass
            try:
                print("type(last_response):", type(last_response))
            except Exception:
                pass
            try:
                print("dir(last_response):", [a for a in dir(last_response) if not a.startswith("_")][:200])
            except Exception:
                pass
            try:
                td = _safe_to_dict(last_response)
                if td:
                    print("last_response.to_dict (truncated):")
                    print(json.dumps(td, default=str, ensure_ascii=False)[:8000])
            except Exception:
                pass

            models_info = await _list_models_diagnostic()
            try:
                print("GEMINI MODELS INFO (diagnostic, truncated):")
                s = str(models_info)
                print(s[:4000])
            except Exception:
                logging.exception("Failed to print models diagnostic")
            logging.warning("Gemini response text extraction returned empty after retries. See diagnostics above.")
        except Exception:
            logging.exception("Failed to print diagnostics for empty Gemini response")

    ## Print (preview) and length
    try:
        print("GEMINI RESPONSE (preview):")
        print(response_text[:4000])
        print()
        print("GEMINI RESPONSE LENGTH:", len(response_text))
    except Exception:
        logging.exception("Failed to print Gemini response preview")

    ## Token usage printing
    try:
        if any(x is not None for x in (prompt_t, completion_t, total_t)):
            _print_tokens_multiline(prompt_t, completion_t, total_t)
    except Exception:
        logging.exception("Failed to pretty-print token usage")

    ## Build compatible response object (extended)
    try:
        usage_obj = SimpleNamespace(
            prompt_tokens=prompt_t,
            completion_tokens=completion_t,
            total_tokens=total_t
        )
        choices = [SimpleNamespace(message=SimpleNamespace(content=response_text))]
        ret = SimpleNamespace(
            choices=choices,
            usage=usage_obj,
            text=response_text,
            truncated=truncated_flag,
            finish_reason=last_finish_reason,
            attempts=seq[:attempt_idx+1] if attempt_idx >= 0 else seq,
            last_max_output=last_max_out_attempted
        )
        return ret
    except Exception:
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=response_text))],
            usage=SimpleNamespace(prompt_tokens=None, completion_tokens=None, total_tokens=None),
            text=response_text,
            truncated=False,
            finish_reason=None,
            attempts=[],
            last_max_output=None
        )
