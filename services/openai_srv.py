import logging

from openai import AsyncOpenAI

from config import get_model_and_params, OPENAI_API_KEY
from i18n.messages import tr
from texts.prompts import KORNESLOV_USER_PROMPT
from utils.userstate import get_user_state
from utils.openai_ut import extract_text_from_openai_response

from utils.llm_envproxy_ut import (
    LLMInfraError,
    get_enabled_proxies,
    run_with_envproxy_failover,
)


DUMMY_TEXT = False


def dummy_openai_response_2DEL(book, chapter, verse, test_banner="", followup=None, dummy_text=None):
    if dummy_text is None:
        dummy_text = "Dummy-text not found!!"
    if test_banner:
        dummy_text += test_banner
    return tr("korneslov_py.dummy_openai_response_return", book=book, chapter=chapter, verse=verse, dummy_text=dummy_text)


async def ask_openai(uid, book, chapter, verse, system_prompt=None, test_banner="", followup=None):
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

    proxies = get_enabled_proxies()

    async def _do_request_once():
        # IMPORTANT: create new client per attempt, so it uses current env proxy
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(**params)
        text = extract_text_from_openai_response(response)
        return f"""{tr("korneslov_py.ask_openai_return", lang=lang)}: {book} {chapter} {verse}\n<br><br>{text}{f'\n{test_banner}' if test_banner else ''}"""

    try:
        return await run_with_envproxy_failover(
            provider="openai",
            proxies=proxies,
            func=_do_request_once,
        )
    except LLMInfraError:
        raise
    except Exception as e:
        logging.exception("OpenAI request failed type=%s repr=%r", type(e).__name__, e)
        return (
            tr("korneslov_py.ask_openai_exception_return", book=book, chapter=chapter, verse=verse, lang=lang) +
            (f"\n{test_banner}" if test_banner else "")
        )