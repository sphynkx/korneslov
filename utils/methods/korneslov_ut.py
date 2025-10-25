import re
import logging
import json
from config import get_model_and_params
from utils.utils import is_truncated
from texts.prompts import LEVELS, FOLLOWUP_PROMPT, KORNESLOV_USER_PROMPT, LEVEL_SAMPLES, KORNESLOV_SYSTEM_PROMPT
from texts.dummy_texts import *
from i18n.messages import tr
from utils.utils import _normalize_book, parse_references, _parse_verses
from utils.userstate import get_user_state
from db import get_conn
from db.books import find_book_entry, increment_book_hits

## Import the factory (provider selection) instead of direct OpenAI/Gemini client
from services.ai_factory import get_ai_service

## TODO: Delete it at all!!
##DUMMY_TEXT = True
DUMMY_TEXT = False


def dummy_openai_response_2DEL(book, chapter, verse, test_banner="", followup=None, dummy_text=None):
    if dummy_text is None:
        dummy_text = "Dummy-text not found!!"
    if test_banner:
        dummy_text += test_banner
    return tr("korneslov_py.dummy_openai_response_return", book=book, chapter=chapter, verse=verse, dummy_text=dummy_text)


async def is_valid_korneslov_query(message):
    if not message.text:
        return False
    if message.text.startswith("/"):
        return False
    refs = await parse_references(message.text, ...)
    if refs:
        return {"refs": refs}
    return False


async def _book_exists(book):
    async with await get_conn() as conn:
        result = await find_book_entry(book, conn)
    return result is not None


def build_korneslov_prompt(book, chapter, verses_str, level_key, lang="ru"):
    """
    Forms prompt for AI. Handles verses_str (ex. '1', '1-3,5')
    """
    level_dict = LEVELS.get(lang, LEVELS["ru"])
    level_str = level_dict.get(level_key, level_dict["hard"])
    level_sample_dict = LEVEL_SAMPLES.get(lang, LEVEL_SAMPLES["ru"])
    level_sample = level_sample_dict.get(level_key, level_sample_dict["hard"])
    system_prompt_template = KORNESLOV_SYSTEM_PROMPT.get(lang, KORNESLOV_SYSTEM_PROMPT["ru"])
    return system_prompt_template.format(
        book=book,
        chapter=chapter,
        verse=verses_str,
        level=level_str,
        level_sample=level_sample
    )


async def fetch_full_korneslov_response(book, chapter, verses_str, uid, level="hard", max_loops=5):
    """
    Receives full response by Korneslov method and making follow-up requests if need.
    With verses ranges support.
    """
    state = get_user_state(uid)
    lang = state.get("lang", "ru")

    async def gen_func(book, chapter, verses_str, system_prompt, followup=None):
        return await ask_ai(uid, book, chapter, verses_str, system_prompt=system_prompt, followup=followup)

    system_prompt = build_korneslov_prompt(book, chapter, verses_str, level, lang=lang)
    answer = await gen_func(book, chapter, verses_str, system_prompt=system_prompt, followup=None)

    ## Permit false repeates - check for marker at the end of Part 3
    if not is_truncated(answer):
        return answer  ## If present - return immediately w/o any followups

    all_answers = [answer]
    loops = 0
    while is_truncated(answer) and loops < max_loops:
        followup_prompt_template = FOLLOWUP_PROMPT.get(lang, FOLLOWUP_PROMPT["ru"])
        followup_prompt = followup_prompt_template.format(book=book, chapter=chapter, verse=verses_str)
        answer = await gen_func(book, chapter, verses_str, system_prompt=system_prompt, followup=followup_prompt)
        all_answers.append(answer)
        loops += 1
    return "\n\n".join(all_answers)


## Unified AI request function (provider-agnostic)
async def ask_ai(uid, book, chapter, verse, system_prompt=None, test_banner="", followup=None):
    """
    Build model/params and invoke the underlying AI service (selected by config.AI_PROVIDER).

    Returns the final text string (formatted the same way as before).
    """
    state = get_user_state(uid)
    lang = state.get("lang", "ru")

    ## TODO: Delete it at all !!
    if DUMMY_TEXT:
        return dummy_openai_response_2DEL(book, chapter, verse, test_banner, followup, dummy_text[lang])

    ## Default system prompt if not provided
    if not system_prompt:
        system_prompt = build_korneslov_prompt(book, chapter, verse, "hard", lang=lang)

    if followup:
        user_prompt = followup
    else:
        user_prompt_template = KORNESLOV_USER_PROMPT.get(lang, KORNESLOV_USER_PROMPT["ru"])
        user_prompt = user_prompt_template.format(book=book, chapter=chapter, verse=verse)

    ## Build params for the model call (keeps previous behaviour)
    model, extra_params = get_model_and_params()
    params = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        n=1,
    )
    params.update(extra_params)

    ## Debug/log before call
    try:
        logging.debug("ask_ai: model=%s uid=%s user_prompt_preview=%s", model, uid, (user_prompt[:180] + "…") if len(user_prompt) > 180 else user_prompt)
        print("ASK_AI -> model:", model)
        print("ASK_AI -> user_prompt (preview):", (user_prompt[:400] + "…") if len(user_prompt) > 400 else user_prompt)
    except Exception:
        logging.exception("Failed to print ask_ai debug info")

    try:
        ## Select provider service via factory
        ai_service = get_ai_service()

        ## Delegate the actual network call to the selected service wrapper
        response = await ai_service.create_chat_completion(params)

        ## extract text in the format expected by the rest of code
        try:
            text = response.choices[0].message.content.strip()
        except Exception:
            ## Fallback if response shapes differ
            text = getattr(response, "text", "") or ""
            text = text.strip()

        ## Debug prints similar to the original code (kept for console visibility)
        try:
            print("DEBUGA: response text (first 4000 chars):")
            print(text[:4000])
            logging.debug("AI returned %d chars", len(text))
        except Exception:
            logging.exception("Failed to print response debug text")

        ## Pretty-print tokens usage if available
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                logging.info("AI tokens used: prompt=%s completion=%s total=%s",
                             getattr(usage, "prompt_tokens", None),
                             getattr(usage, "completion_tokens", None),
                             getattr(usage, "total_tokens", None))
                ## Multiline pretty print
                print("=" * 14)
                print("AI tokens:")
                print(f"prompt_tokens: {getattr(usage, 'prompt_tokens', None)}")
                print(f"completion_tokens: {getattr(usage, 'completion_tokens', None)}")
                print(f"total_tokens: {getattr(usage, 'total_tokens', None)}")
                print("=" * 14)
        except Exception:
            logging.exception("Failed to log AI usage info")

        ## TODO: replace openai messages with some unifyed
        return f"""{tr("korneslov_py.ask_openai_return", lang=lang)}: {book} {chapter} {verse}\n<br><br>{text}{f'\n{test_banner}' if test_banner else ''}"""

    ## TODO: replace openai messages with some unifyed
    except Exception as e:
        logging.exception(tr("korneslov_py.ask_openai_exception_logging", lang=lang))
        print("ASK_AI ERROR:", repr(e))
        return (
            tr("korneslov_py.ask_openai_exception_return", book=book, chapter=chapter, verse=verse, lang=lang) +
            (f"\n{test_banner}" if test_banner else "")
        )
