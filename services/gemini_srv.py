import logging
import time
import asyncio
from typing import Optional, List

from google import genai
from google.genai import types as genai_types
from google.genai.errors import ServerError

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

## Optional streaming flag
try:
    from config import GEMINI_USE_STREAMING
except Exception:
    GEMINI_USE_STREAMING = False

## Retry tuning
try:
    from config import GEMINI_MAX_RETRIES
except Exception:
    GEMINI_MAX_RETRIES = 2

try:
    from config import GEMINI_RETRY_BASE_DELAY
except Exception:
    GEMINI_RETRY_BASE_DELAY = 1.0

try:
    from config import GEMINI_RETRY_MAX_DELAY
except Exception:
    GEMINI_RETRY_MAX_DELAY = 8.0

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


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

    client = _get_client()
    config = build_gemini_config(
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_CAP,
        temperature=GEMINI_TEMPERATURE,
        system_instruction=system_prompt or "",
    )

    try:
        logging.debug(
            "Gemini request params (sanitized): {'model': %r, 'stream': %r, 'max_tokens': %r, 'temperature': %r}",
            GEMINI_MODEL,
            GEMINI_USE_STREAMING,
            GEMINI_MAX_OUTPUT_TOKENS_CAP,
            GEMINI_TEMPERATURE,
        )
        print(
            "GEMINI REQUEST:",
            {
                "model": GEMINI_MODEL,
                "messages": [
                    {"role": "system", "content_preview": (system_prompt[:100] + "...") if system_prompt and len(system_prompt) > 100 else (system_prompt or "")},
                    {"role": "user", "content_preview": (user_content[:100] + "...") if len(user_content) > 100 else user_content},
                ],
                "n": 1,
                "max_tokens": GEMINI_MAX_OUTPUT_TOKENS_CAP,
                "temperature": GEMINI_TEMPERATURE,
                "streaming": GEMINI_USE_STREAMING,
            },
        )
    except Exception:
        logging.exception("Failed to log Gemini request preview")

    ## Retry loop (limited)
    delay = float(GEMINI_RETRY_BASE_DELAY)
    for attempt in range(1, int(GEMINI_MAX_RETRIES) + 2):  ## attempts = MAX_RETRIES + 1
        try:
            text, prompt_tokens, total_tokens = await _do_gemini_call(
                client, config, user_content
            )

            ## Sanitize HTML for Telegram
            text = sanitize_for_telegram_html(text or "")

            ## Log usage if available
            try:
                completion_tokens = (
                    (total_tokens - prompt_tokens)
                    if (prompt_tokens is not None and total_tokens is not None)
                    else None
                )
                print("GEMINI RESPONSE (preview):")
                print((text[:4000] if text else ""))
                print()
                print("GEMINI RESPONSE LENGTH:", len(text) if text else 0)
                print("==============")
                print("Gemini tokens (if available):")
                print("prompt_tokens:", prompt_tokens)
                print("completion_tokens:", completion_tokens)
                print("total_tokens:", total_tokens)
                print("==============")
            except Exception:
                logging.exception("Failed to log Gemini usage/summary")

            return f"""{tr("korneslov_py.ask_openai_return", lang=lang)}: {book} {chapter} {verse}\n<br><br>{text}{f'\n{test_banner}' if test_banner else ''}"""

        except ServerError as e:
            ## 503 / overload -> backoff and retry
            logging.warning("Gemini ServerError on attempt %d: %s", attempt, e)
        except Exception as e:
            ## JSONDecodeError and other streaming issues
            logging.warning("Gemini error on attempt %d: %s", attempt, e)

        if attempt < int(GEMINI_MAX_RETRIES) + 1:
            await asyncio.sleep(delay)
            delay = min(delay * 2.0, float(GEMINI_RETRY_MAX_DELAY))

    ## Out of retries
    logging.error("Gemini request failed after retries")
    return (
        tr("korneslov_py.ask_openai_exception_return", book=book, chapter=chapter, verse=verse, lang=lang)
        + (f"\n{test_banner}" if test_banner else "")
    )


async def _do_gemini_call(
    client: genai.Client,
    config: Optional[genai_types.GenerateContentConfig],
    contents: str,
):
    """
    Single attempt with optional streaming and non-stream fallback.
    Returns (text, prompt_tokens, total_tokens) or raises on failure.
    """
    text = ""
    prompt_tokens = None
    total_tokens = None

    if GEMINI_USE_STREAMING:
        print("GEMINI STREAMING: enabled — using generate_content_stream()")
        t0 = time.time()
        try:
            text, prompt_tokens, total_tokens = _stream_and_collect(
                client, model=GEMINI_MODEL, config=config, contents=contents
            )
        except Exception as e:
            logging.exception("Gemini streaming attempt failed: %s", e)
        t1 = time.time()
        print(
            f"GEMINI STREAM: done in {t1 - t0:.2f}s, collected_len={len(text)}, "
            f"prompt_tokens={prompt_tokens}, total_tokens={total_tokens}"
        )
        if not text:
            print("GEMINI STREAM: empty accumulated text — falling back to non-stream call")

    if not text:
        print("GEMINI NON-STREAM: calling generate_content()")
        response = client.models.generate_content(
            model=GEMINI_MODEL, config=config, contents=contents
        )
        text = extract_text_from_gemini_response(response)
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        total_tokens = getattr(usage, "total_token_count", None) if usage else None

    return text, prompt_tokens, total_tokens


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
        print("GEMINI STREAM: start")
        stream = client.models.generate_content_stream(
            model=model, config=config, contents=contents
        )
        chunks = 0
        acc_len = 0
        t0 = time.time()
        for chunk in stream:
            chunks += 1
            try:
                if hasattr(chunk, "text") and isinstance(chunk.text, str) and chunk.text:
                    acc.append(chunk.text)
                    acc_len += len(chunk.text)
                    if chunks <= 3 or chunks % 10 == 0:
                        print(f"GEMINI STREAM: chunk {chunks}, len={len(chunk.text)}, acc_len={acc_len}")
            except Exception:
                ## ignore malformed chunks but continue
                pass

        ## usage from final stream response if available
        try:
            usage = getattr(stream, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
            total_tokens = getattr(usage, "total_token_count", None) if usage else None
        except Exception:
            pass

        t1 = time.time()
        print(f"GEMINI STREAM: end — chunks={chunks}, acc_len={acc_len}, elapsed={t1 - t0:.2f}s")
    except Exception:
        logging.exception("Gemini stream failed")

    text = "".join(acc).strip()
    return text, prompt_tokens, total_tokens
