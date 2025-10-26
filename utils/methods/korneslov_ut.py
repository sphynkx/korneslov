import re
import logging

from i18n.messages import tr
from texts.prompts import LEVELS, FOLLOWUP_PROMPT, KORNESLOV_USER_PROMPT, LEVEL_SAMPLES, KORNESLOV_SYSTEM_PROMPT
from texts.dummy_texts import *
from utils.utils import _normalize_book, parse_references, _parse_verses, is_truncated
from utils.userstate import get_user_state
from db import get_conn
from db.books import find_book_entry, increment_book_hits


## DUMMY_TEXT = True
## DEPRECATED??
DUMMY_TEXT = False


## DUMMY then `DUMMY_TEXT = True`
## Deprecated??
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
    Forms prompt for AI. Handles verses_str (ex. '1', '1-3,5').
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
    Receives full response by Korneslov method and making follow-up requests if need. With verses ranges support.
    """
    state = get_user_state(uid)
    lang = state.get("lang", "ru")

    async def gen_func(book, chapter, verses_str, system_prompt, followup=None):
        ## Provider-agnostic dispatch: OpenAI or Gemini is selected by AI_PROVIDER in config
        from services.ai_provider import ask_ai  ## keep here to avoid circular imports during refactor stage
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
