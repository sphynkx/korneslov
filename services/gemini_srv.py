import logging
from types import SimpleNamespace
from typing import Optional

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
from utils.gemini_ut import extract_text_from_gemini_response, build_gemini_config


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
    """
    Perform Gemini chat generation and return formatted text:
    'Korneslov: {book} {chapter} {verse}\\n<br><br>{text}{optional test banner}'.

    NOTE:
    - system_prompt should be provided by caller (already built upstream).
    - followup replaces user content if provided.
    - Single-attempt strategy (no internal multi-retries here).
    """
    state = get_user_state(uid)
    lang = state.get("lang", "ru")

    if not GEMINI_API_KEY:
        ## Reuse OpenAI message key for consistency
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

    ## Build config from config.py values (cap tokens, temperature, etc.)
    config = build_gemini_config(
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS_CAP,
        temperature=GEMINI_TEMPERATURE,
        system_instruction=system_prompt or "",
    )

    ## Log sanitized request
    try:
        logging.debug(
            "Gemini request params (sanitized): {'model': %r, 'system_preview': %r, 'user_preview': %r}",
            GEMINI_MODEL,
            (system_prompt[:100] + "...") if system_prompt and len(system_prompt) > 100 else (system_prompt or ""),
            (user_content[:100] + "...") if len(user_content) > 100 else user_content,
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
            },
        )
    except Exception:
        logging.exception("Failed to log Gemini request preview")

    ## Single attempt
    try:
        if config is not None:
            response = await _call_generate(client, model=GEMINI_MODEL, config=config, contents=user_content)
        else:
            ## Fallback without config (should not happen if utils.gemini_ut is correct)
            response = await _call_generate(client, model=GEMINI_MODEL, config=None, contents=user_content)

        text = extract_text_from_gemini_response(response)

        ## Try to log token usage if available
        try:
            usage = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
            total_tokens = getattr(usage, "total_token_count", None) if usage else None
            completion_tokens = (total_tokens - prompt_tokens) if (prompt_tokens is not None and total_tokens is not None) else None

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
    except Exception:
        logging.exception("Gemini request failed")
        return (
            tr("korneslov_py.ask_openai_exception_return", book=book, chapter=chapter, verse=verse, lang=lang)
            + (f"\n{test_banner}" if test_banner else "")
        )


async def _call_generate(client: genai.Client, model: str, config: Optional[genai_types.GenerateContentConfig], contents: str):
    """
    Thin async wrapper to call client.models.generate_content.
    """
    ## genai client is sync; run in thread? Here we call directly (library may allow await if integrated).
    ## If sync-only, consider running in executor. Keeping simple per current project async style.
    return client.models.generate_content(model=model, config=config, contents=contents)
