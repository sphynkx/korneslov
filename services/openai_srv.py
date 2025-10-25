"""
Service wrapper for OpenAI calls.

Provides create_chat_completion(params) -> raw response.

This version includes verbose debug prints and improved multiline token printing.
"""
import logging
from typing import Any, Dict

from config import OPENAI_API_KEY

## Import AsyncOpenAI lazily to keep startup failures clear
try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None  ## type: ignore


def _mask_params_for_logging(params: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare a sanitized copy of params for logging (avoid printing secrets)."""
    p = {}
    for k, v in params.items():
        if k.lower() in ("api_key", "api_key_secret"):
            p[k] = "****"
        elif k == "messages":
            ## Log only roles and first 100 chars of content for each message
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
                ## keep simple serializable representations
                p[k] = v if isinstance(v, (str, int, float, bool, type(None))) else str(type(v))
            except Exception:
                p[k] = "<unserializable>"
    return p


def _print_tokens_multiline(usage):
    """
    Nicely print tokens usage in multiline form for console visibility.
    usage: object with attributes prompt_tokens, completion_tokens, total_tokens
    """
    try:
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        total = getattr(usage, "total_tokens", None)
        print("=" * 14)
        print("OpenAI tokens:")
        print(f"prompt_tokens: {prompt}")
        print(f"completion_tokens: {completion}")
        print(f"total_tokens: {total}")
        print("=" * 14)
    except Exception:
        ## Never fail on debug formatting
        logging.exception("Failed to pretty-print tokens")


async def create_chat_completion(params: Dict[str, Any]):
    """
    Perform an OpenAI chat completion call using AsyncOpenAI.

    params: dict — all keyword params to pass to client.chat.completions.create(...)
            e.g. { model: "...", messages: [...], n: 1, max_tokens: ..., ... }

    Returns the raw response object from the client (so existing code can read
    response.choices[0].message.content and response.usage.*).
    Raises an informative RuntimeError if client library or API key missing.
    """
    if AsyncOpenAI is None:
        logging.error("openai.AsyncOpenAI is not available (package missing).")
        raise RuntimeError("OpenAI client library is not installed (openai).")

    if not OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY is not configured.")
        raise RuntimeError("OPENAI_API_KEY not set")

    ## Log/print request summary for debugging
    try:
        masked = _mask_params_for_logging(params)
        logging.debug("OpenAI request params (sanitized): %s", masked)
        print("OPENAI REQUEST:", masked)  ## explicit print for console visibility
    except Exception:
        logging.exception("Failed to log sanitized OpenAI params")

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    try:
        logging.debug("OpenAI request starting for model=%s", params.get("model"))
        print(f"OPENAI: calling model={params.get('model')}, messages_count={len(params.get('messages', []))}")
        response = await client.chat.completions.create(**params)

        ## Log short summary of response and pretty-print tokens
        try:
            choices_info = []
            for ch in getattr(response, "choices", []) or []:
                msg = getattr(ch, "message", None)
                content = getattr(msg, "content", "") if msg else ""
                choices_info.append((len(content), (content[:120] + "…") if len(content) > 120 else content))
            usage = getattr(response, "usage", None)
            usage_info = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            } if usage is not None else None
            logging.debug("OpenAI response summary choices=%s usage=%s", choices_info, usage_info)
            ## Pretty print to console
            print("OPENAI RESPONSE summary:")
            for idx, chinfo in enumerate(choices_info):
                length, preview = chinfo
                print(f"choice[{idx}]: {length} chars; preview:", (preview[:200] + "…") if len(preview) > 200 else preview)
            if usage is not None:
                _print_tokens_multiline(usage)
        except Exception:
            logging.exception("Failed to log OpenAI response summary")
        return response
    except Exception as e:
        logging.exception("OpenAI request failed in services/openai_srv.create_chat_completion: %s", e)
        print("OPENAI ERROR:", repr(e))
        ## Re-raise to let callers handle fallback; we keep the original exception type
        raise
