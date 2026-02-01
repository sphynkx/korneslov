import logging
from types import SimpleNamespace

import httpx
from openai import AsyncOpenAI

from config import get_model_and_params, OPENAI_API_KEY
from i18n.messages import tr
from texts.prompts import KORNESLOV_USER_PROMPT
from utils.userstate import get_user_state
from utils.openai_ut import extract_text_from_openai_response

from utils.llm_ut import (
    LLMInfraError,
    ProxySpec,
    get_enabled_proxies,
    run_with_proxy_failover,
)


## DUMMY then `DUMMY_TEXT = True`
## Deprecated??
DUMMY_TEXT = False


## DUMMY then `DUMMY_TEXT = True`
## Deprecated??
def dummy_openai_response_2DEL(book, chapter, verse, test_banner="", followup=None, dummy_text=None):
    if dummy_text is None:
        dummy_text = "Dummy-text not found!!"
    if test_banner:
        dummy_text += test_banner
    return tr("korneslov_py.dummy_openai_response_return", book=book, chapter=chapter, verse=verse, dummy_text=dummy_text)


async def ask_openai(uid, book, chapter, verse, system_prompt=None, test_banner="", followup=None):
    """
    Perform OpenAI Chat Completion and return formatted text:
    'Korneslov: {book} {chapter} {verse}\\n<br><br>{text}{optional test banner}'.

    NOTE:
    - system_prompt must be provided by caller (kept universal; building is outside).
    - followup replaces the user request if provided.

    Proxy behavior:
    - proxies are loaded from PROXIES_CONFIG (proxies.json)
    - failover: try first proxy (priority), then next, etc.
    - does not remember last good proxy; always starts from priority on every call
    """
    state = get_user_state(uid)
    lang = state.get("lang", "ru")

    if DUMMY_TEXT:
        from texts.dummy_texts import dummy_text
        return dummy_openai_response_2DEL(book, chapter, verse, test_banner, followup, dummy_text[lang])

    if not OPENAI_API_KEY:
        return tr(
            "korneslov_py.ask_openai_no_OPENAI_API_KEY",
            book=book,
            chapter=chapter,
            verse=verse,
            test_banner=test_banner,
            lang=lang
        )

    if not system_prompt:
        ## Caller should build system_prompt upstream (utils/methods/korneslov_ut.py)
        logging.warning("openai_srv.ask_openai called without system_prompt; behavior may differ.")

    if followup:
        user_prompt = followup
    else:
        user_prompt_template = KORNESLOV_USER_PROMPT.get(lang, KORNESLOV_USER_PROMPT["ru"])
        user_prompt = user_prompt_template.format(book=book, chapter=chapter, verse=verse)

    model, extra_params = get_model_and_params()
    params = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt or ""},
            {"role": "user", "content": user_prompt}
        ],
        n=1,
    )
    params.update(extra_params or {})

    logging.debug("OpenAI request starting for model=%s", model)

    # Load proxies once per request; priority is first in list
    proxies = get_enabled_proxies()

    async def _attempt(http_client: httpx.AsyncClient, proxy: ProxySpec | None):
        client = AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

        # Keep your existing debug log (sanitized previews)
        logging.debug(
            "OpenAI request params (sanitized): {'model': %r, 'messages': [{'role': 'system', 'content_preview': %r}, {'role': 'user', 'content_preview': %r}], 'n': %r}",
            model,
            (system_prompt[:100] + "...") if system_prompt and len(system_prompt) > 100 else (system_prompt or ""),
            (user_prompt[:100] + "...") if len(user_prompt) > 100 else user_prompt,
            1
        )

        response = await client.chat.completions.create(**params)
        text = extract_text_from_openai_response(response)

        # Debug usage logging (unchanged)
        try:
            usage = getattr(response, "usage", None)
            if usage:
                logging.debug(
                    "OpenAI response summary choices=[(%s, %r)] usage=%r",
                    len(text),
                    (text[:120] + "…") if len(text) > 120 else text,
                    {"prompt_tokens": getattr(usage, "prompt_tokens", None), "completion_tokens": getattr(usage, "completion_tokens", None), "total_tokens": getattr(usage, "total_tokens", None)}
                )
        except Exception:
            logging.exception("Failed to log OpenAI usage/summary")

        return f"""{tr("korneslov_py.ask_openai_return", lang=lang)}: {book} {chapter} {verse}\n<br><br>{text}{f'\n{test_banner}' if test_banner else ''}"""

    try:
        return await run_with_proxy_failover(
            provider="openai",
            proxies=proxies,
            func=_attempt,
            allow_direct_if_no_proxies=False,
        )
    except LLMInfraError:
        # Don not write off money
        raise
    except Exception:
        logging.exception(tr("korneslov_py.ask_openai_exception_logging", lang=lang))
        return (
            tr("korneslov_py.ask_openai_exception_return", book=book, chapter=chapter, verse=verse, lang=lang) +
            (f"\n{test_banner}" if test_banner else "")
        )