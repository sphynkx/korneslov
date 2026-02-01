import asyncio
import logging
import time
from typing import Optional, List

from google import genai
from google.genai import types as genai_types

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_MAX_OUTPUT_TOKENS_CAP,
)
from i18n.messages import tr
from texts.prompts import KORNESLOV_USER_PROMPT
from utils.userstate import get_user_state
from utils.gemini_ut import (
    extract_text_from_gemini_response,
    build_gemini_config,
    sanitize_for_telegram_html,
)

from utils.llm_ut import (
    LLMInfraError,
    ProxySpec,
    get_enabled_proxies,
    run_with_proxy_failover,
    temp_env,
)

## Optional streaming flag; read lazily to avoid tight coupling if missing in config
try:
    from config import GEMINI_USE_STREAMING
except Exception:
    GEMINI_USE_STREAMING = False

# IMPORTANT:
# google-genai doesn't expose a clean injectable async transport for per-request proxy selection.
# We implement multiproxy by temporarily setting env vars under a global lock.
# This makes Gemini calls sequential (safe for parallel bot usage).
_GEMINI_PROXY_LOCK = asyncio.Lock()


def _build_client() -> genai.Client:
    # do NOT cache globally because proxy can change per attempt
    return genai.Client(api_key=GEMINI_API_KEY)


async def ask_gemini(
    uid: int,
    book: str,
    chapter: int,
    verse: str,
    system_prompt: Optional[str] = None,
    test_banner: str = "",
    followup: Optional[str] = None,
) -> str:
    """
    Gemini provider with multiproxy failover.

    Strategy:
      - proxies are loaded from PROXIES_CONFIG (same file as OpenAI)
      - on each request: try priority proxy first, then others
      - proxy is applied via env (ALL_PROXY / HTTPS_PROXY) under a global async lock
        to avoid races in parallel requests

    Raises:
      - LLMInfraError if all proxies fail (caller should NOT charge user)
    """
    state = get_user_state(uid)
    lang = state.get("lang", "ru")

    if not GEMINI_API_KEY:
        return tr(
            "korneslov_py.ask_openai_no_OPENAI_API_KEY",
            book=book,
            chapter=chapter,
            verse=verse,
            test_banner=test_banner,
            lang=lang,
        )

    if not system_prompt:
        logging.warning("gemini_srv.ask_gemini called without system_prompt; behavior may differ.")

    if followup:
        user_content = followup
    else:
        user_prompt_template = KORNESLOV_USER_PROMPT.get(lang, KORNESLOV_USER_PROMPT["ru"])
        user_content = user_prompt_template.format(book=book, chapter=chapter, verse=verse)

    config = build_gemini_config(
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_CAP,
        temperature=GEMINI_TEMPERATURE,
        system_instruction=system_prompt or "",
    )

    try:
        logging.debug(
            "Gemini request params (sanitized): {'model': %r, 'system_preview': %r, 'user_preview': %r, 'stream': %r, 'max_tokens': %r, 'temperature': %r}",
            GEMINI_MODEL,
            (system_prompt[:100] + "...") if system_prompt and len(system_prompt) > 100 else (system_prompt or ""),
            (user_content[:100] + "...") if len(user_content) > 100 else user_content,
            GEMINI_USE_STREAMING,
            GEMINI_MAX_OUTPUT_TOKENS_CAP,
            GEMINI_TEMPERATURE,
        )
    except Exception:
        logging.exception("Failed to log Gemini request preview")

    proxies = get_enabled_proxies()

    async def _attempt(_unused_http_client, proxy: ProxySpec | None):
        # NOTE: run_with_proxy_failover passes an http_client, but Gemini SDK doesn't accept it.
        # We still use it to unify logic; it's simply unused here.
        #
        # Apply proxy via env. Use ALL_PROXY and HTTPS_PROXY to cover most HTTP stacks.
        # We set both for best compatibility.
        env = {
            "ALL_PROXY": proxy.url if proxy else None,
            "HTTPS_PROXY": proxy.url if proxy else None,
            "HTTP_PROXY": proxy.url if proxy else None,
        }

        async with _GEMINI_PROXY_LOCK:
            with temp_env(env):
                client = _build_client()

                text = ""
                prompt_tokens = None
                total_tokens = None

                if GEMINI_USE_STREAMING:
                    t0 = time.time()
                    text, prompt_tokens, total_tokens = _stream_and_collect(
                        client, model=GEMINI_MODEL, config=config, contents=user_content
                    )
                    t1 = time.time()
                    logging.debug(
                        "Gemini stream done in %.2fs, collected_len=%s, prompt_tokens=%s, total_tokens=%s",
                        (t1 - t0),
                        len(text) if text else 0,
                        prompt_tokens,
                        total_tokens,
                    )

                if not text:
                    response = client.models.generate_content(
                        model=GEMINI_MODEL, config=config, contents=user_content
                    )
                    text = extract_text_from_gemini_response(response)
                    usage = getattr(response, "usage_metadata", None)
                    prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
                    total_tokens = getattr(usage, "total_token_count", None) if usage else None

                text = sanitize_for_telegram_html(text or "")

                try:
                    completion_tokens = (
                        (total_tokens - prompt_tokens)
                        if (prompt_tokens is not None and total_tokens is not None)
                        else None
                    )
                    logging.debug(
                        "Gemini response len=%s tokens prompt=%s completion=%s total=%s",
                        len(text) if text else 0,
                        prompt_tokens,
                        completion_tokens,
                        total_tokens,
                    )
                except Exception:
                    logging.exception("Failed to log Gemini usage/summary")

                return f"""{tr("korneslov_py.ask_openai_return", lang=lang)}: {book} {chapter} {verse}\n<br><br>{text}{f'\n{test_banner}' if test_banner else ''}"""

    try:
        # precheck_proxy_port is inside run_with_proxy_failover (if you kept that version),
        # so dead proxies will be skipped quickly without touching Gemini SDK.
        return await run_with_proxy_failover(
            provider="gemini",
            proxies=proxies,
            func=_attempt,
            allow_direct_if_no_proxies=False,
        )
    except LLMInfraError:
        # bubble up to prevent charging
        raise
    except Exception:
        # keep previous behavior for non-infra errors
        logging.exception("Gemini request failed")
        return (
            tr("korneslov_py.ask_openai_exception_return", book=book, chapter=chapter, verse=verse, lang=lang)
            + (f"\n{test_banner}" if test_banner else "")
        )


def _stream_and_collect(
    client: genai.Client,
    model: str,
    config: Optional[genai_types.GenerateContentConfig],
    contents: str,
):
    """
    Streaming path: generate_content_stream and collect chunk.text.
    Returns (text, prompt_tokens, total_tokens).
    """
    acc: List[str] = []
    prompt_tokens = None
    total_tokens = None

    try:
        stream = client.models.generate_content_stream(
            model=model, config=config, contents=contents
        )
        for chunk in stream:
            try:
                if hasattr(chunk, "text") and isinstance(chunk.text, str) and chunk.text:
                    acc.append(chunk.text)
            except Exception:
                pass

        # usage from final stream response if available
        try:
            usage = getattr(stream, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
            total_tokens = getattr(usage, "total_token_count", None) if usage else None
        except Exception:
            pass

    except Exception:
        logging.exception("Gemini stream failed")

    text = "".join(acc).strip()
    return text, prompt_tokens, total_tokens