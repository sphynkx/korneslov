import logging
from types import SimpleNamespace

from openai import AsyncOpenAI

from config import get_model_and_params, OPENAI_API_KEY
from i18n.messages import tr
from texts.prompts import KORNESLOV_USER_PROMPT
from utils.userstate import get_user_state
from utils.openai_ut import extract_text_from_openai_response


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


_client = None


def _get_client():
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


async def ask_openai(uid, book, chapter, verse, system_prompt=None, test_banner="", followup=None):
    """
    Perform OpenAI Chat Completion and return formatted text:
    'Korneslov: {book} {chapter} {verse}\\n<br><br>{text}{optional test banner}'.

    NOTE:
    - system_prompt must be provided by caller (kept universal; building is outside).
    - followup replaces the user request if provided.
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

    client = _get_client()
    logging.debug("OpenAI request starting for model=%s", model)
    try:
        logging.debug("OpenAI request params (sanitized): {'model': %r, 'messages': [{'role': 'system', 'content_preview': %r}, {'role': 'user', 'content_preview': %r}], 'n': %r}", model, (system_prompt[:100] + "...") if system_prompt and len(system_prompt) > 100 else (system_prompt or ""), (user_prompt[:100] + "...") if len(user_prompt) > 100 else user_prompt, 1)
        print("OPENAI REQUEST:", {"model": model, "messages": [{"role": "system", "content_preview": (system_prompt[:100] + "...") if system_prompt and len(system_prompt) > 100 else (system_prompt or "")}, {"role": "user", "content_preview": (user_prompt[:100] + "...") if len(user_prompt) > 100 else user_prompt}], "n": 1})
        response = await client.chat.completions.create(**params)

        ## Extract text robustly
        text = extract_text_from_openai_response(response)

        ## Debug usage logging
        try:
            usage = getattr(response, "usage", None)
            if usage:
                logging.debug(
                    "OpenAI response summary choices=[(%s, %r)] usage=%r",
                    len(text),
                    (text[:120] + "…") if len(text) > 120 else text,
                    {"prompt_tokens": getattr(usage, "prompt_tokens", None), "completion_tokens": getattr(usage, "completion_tokens", None), "total_tokens": getattr(usage, "total_tokens", None)}
                )
                print("OPENAI RESPONSE summary:")
                print(f"choice[0]: {len(text)} chars; preview: {(text[:120] + '…') if len(text) > 120 else text}")
                print("==============")
                print("OpenAI tokens:")
                print("prompt_tokens:", getattr(usage, "prompt_tokens", None))
                print("completion_tokens:", getattr(usage, "completion_tokens", None))
                print("total_tokens:", getattr(usage, "total_tokens", None))
                print("==============")
        except Exception:
            logging.exception("Failed to log OpenAI usage/summary")

        return f"""{tr("korneslov_py.ask_openai_return", lang=lang)}: {book} {chapter} {verse}\n<br><br>{text}{f'\n{test_banner}' if test_banner else ''}"""
    except Exception:
        logging.exception(tr("korneslov_py.ask_openai_exception_logging", lang=lang))
        return (
            tr("korneslov_py.ask_openai_exception_return", book=book, chapter=chapter, verse=verse, lang=lang) +
            (f"\n{test_banner}" if test_banner else "")
        )
