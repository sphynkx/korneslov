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

try:
    from config import GEMINI_USE_STREAMING
except Exception:
    GEMINI_USE_STREAMING = False


# google-genai==1.2.0 doesn't provide clean per-request async transport injection.
# We apply proxy via env vars under a global lock to avoid races in parallel requests.
_GEMINI_PROXY_LOCK = asyncio.Lock()


def _build_client() -> genai.Client:
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
            "Gemini request params (sanitized): model=%r system_preview=%r user_preview=%r stream=%r",
            GEMINI_MODEL,
            (system_prompt[:100] + "...") if system_prompt and len(system_prompt) > 100 else (system_prompt or ""),
            (user_content[:100] + "...") if len(user_content) > 100 else user_content,
            GEMINI_USE_STREAMING,
        )
    except Exception:
        logging.exception("Failed to log Gemini request preview")

    proxies = get_enabled_proxies()

    async def _attempt(_unused_http_client, proxy: ProxySpec | None):
        # Apply proxy via env for duration of call.
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
                        "Gemini stream done in %.2fs collected_len=%s prompt=%s total=%s",
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

                return f"""{tr("korneslov_py.ask_openai_return", lang=lang)}: {book} {chapter} {verse}\n<br><br>{text}{f'\n{test_banner}' if test_banner else ''}"""

    try:
        return await run_with_proxy_failover(
            provider="gemini",
            proxies=proxies,
            func=_attempt,
            allow_direct_if_no_proxies=False,
        )
    except LLMInfraError:
        raise
    except Exception as e:
        logging.exception("Gemini request failed type=%s repr=%r", type(e).__name__, e)
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