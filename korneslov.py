import re
import logging
from config import get_model_and_params, OPENAI_API_KEY
from openai import AsyncOpenAI
from utils.utils import is_truncated
from texts.prompts import *
from texts.dummy_texts import *
from i18n.messages import tr
from utils.utils import _normalize_book, parse_references, _parse_verses
from utils.userstate import get_user_state
from db import get_conn
from db.books import find_book_entry, increment_book_hits


client = AsyncOpenAI(api_key=OPENAI_API_KEY)


##DUMMY_TEXT = True
## DEPRECATED??
DUMMY_TEXT = False



## DUMMY then `DUMMY_TEXT = True`
## Deprecated??
def dummy_openai_response_2DEL(book, chapter, verse, test_banner="", followup=None, dummy_text=None):
    if dummy_text is None:
        dummy_text = "Dummy-text not found!!"
    if test_banner: dummy_text += test_banner
    return tr("korneslov_py.dummy_openai_response_return", book=book, chapter=chapter, verse=verse, dummy_text=dummy_text)


async def is_valid_korneslov_query(message):
    if not message.text:
        return False
    if message.text.startswith("/"):
        return False
    refs = await parse_references(message.text, ...)
    if refs:
####        return {"is_reqcmd": True, "refs": refs}
        return {"refs": refs}
    return False


async def _book_exists(book):
    async with await get_conn() as conn:
        result = await find_book_entry(book, conn)
    return result is not None


def build_korneslov_prompt(book, chapter, verses_str, level_key, lang="ru"):
    """
    Forms prompt for OpenAI. Handles verses_str (ex. '1', '1-3,5')
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
        return await ask_openai(uid, book, chapter, verses_str, system_prompt=system_prompt, followup=followup)

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


## Real OpenAI request func
async def ask_openai(uid, book, chapter, verse, system_prompt=None, test_banner="", followup=None):
    state = get_user_state(uid)
    lang = state.get("lang", "ru")

    if DUMMY_TEXT:
        return dummy_openai_response(book, chapter, verse, test_banner, followup, dummy_text[lang])

    if not OPENAI_API_KEY:
        return tr("korneslov_py.ask_openai_no_OPENAI_API_KEY", book=book, chapter=chapter, verse=verse, test_banner=test_banner, lang=lang)

    ## Now with levels..
    if not system_prompt:
        ## Default is "hard"
        system_prompt = build_korneslov_prompt(book, chapter, verse, "hard", lang=lang)

    if followup:
        user_prompt = followup
    else:
        user_prompt_template = KORNESLOV_USER_PROMPT.get(lang, KORNESLOV_USER_PROMPT["ru"])
        user_prompt = user_prompt_template.format(book=book, chapter=chapter, verse=verse)

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

    try:
        response = await client.chat.completions.create(**params)
        text = response.choices[0].message.content.strip()
        print(f"DEBUGA: {text}")
        return f"""{tr("korneslov_py.ask_openai_return", lang=lang)}: {book} {chapter} {verse}\n<br><br>{text}{f'\n{test_banner}' if test_banner else ''}"""

    except Exception as e:
        logging.exception(tr("korneslov_py.ask_openai_exception_logging", lang=lang))
        return (
            tr("korneslov_py.ask_openai_exception_return", book=book, chapter=chapter, verse=verse, lang=lang) + 
            (f"\n{test_banner}" if test_banner else "")
        )


