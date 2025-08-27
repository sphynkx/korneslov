import re
import logging
from config import get_model_and_params, OPENAI_API_KEY, TESTMODE, USE_TRIBUTE
from openai import AsyncOpenAI
from utils.utils import is_truncated
from texts.prompts import *
from texts.dummy_texts import *
from i18n.messages import tr
from utils.userstate import get_user_state


client = AsyncOpenAI(api_key=OPENAI_API_KEY)

KORNESLOV_RE_RU = re.compile(tr("korneslov_py.regexp", default_lang="ru"), re.IGNORECASE)
KORNESLOV_RE_EN = re.compile(tr("korneslov_py.regexp", default_lang="en"), re.IGNORECASE)


##DUMMY_TEXT = True
##
DUMMY_TEXT = False



####### Move to utils ###############
## List of known books (not full)
## TODO: Move out of here.. Next - to DB.
BOOKS_RU = [
    "бытие", "исход", "левит", "числа", "второзаконие", "иоанна", "псалтирь", # и т.д.
]
BOOKS_EN = [
    "genesis", "exodus", "leviticus", "numbers", "deuteronomy", "john", "psalms", # и т.д.
]



def _normalize_book(book):
    """Set to lowercase, remove extra spaces."""
    return book.strip().lower()


def _is_known_book(book, lang="ru"):
    checkbook = _normalize_book(book)
    if lang == "ru":
        return checkbook in BOOKS_RU
    return checkbook in BOOKS_EN


def _parse_verses(verses_str):
    ## Reformat strings like "3", "3-5", "3,5,7-9" to verses numbers list: [3], [3,4,5], [3,5,7,8,9]
    verses = set()
    for part in verses_str.split(","):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            try:
                verses.update(range(int(start), int(end) + 1))
            except Exception:
                continue
        else:
            try:
                verses.add(int(part))
            except Exception:
                continue
    return sorted(verses)


def _book_regex(lang="ru"):
    """Generates regexp for book search on current lang."""
    books = BOOKS_RU if lang == "ru" else BOOKS_EN
    books_re = "|".join([re.escape(b) for b in books])
    return fr"({books_re})"


####### /Move to utils ###############




########### DUMMY ###########
def dummy_openai_response(book, chapter, verse, test_banner="", followup=None, dummy_text=None):
    if dummy_text is None:
        dummy_text = "Dummy-text not found!!"
    if test_banner: dummy_text += test_banner
    return tr("korneslov_py.dummy_openai_response_return", book=book, chapter=chapter, verse=verse, dummy_text=dummy_text)

## 2DEL
def is_valid_korneslov_query_OLD(text: str):
    ## Catch both rus and eng requests.
    text = text.strip()
    return bool(KORNESLOV_RE_RU.match(text) or KORNESLOV_RE_EN.match(text))


##def is_valid_korneslov_query(text, lang="ru"):
def is_valid_korneslov_query(message):
    """Check whether to parse string as request to Korneslov."""
    uid = message.from_user.id
    state = get_user_state(uid)
    lang = state.get("lang", "ru")
    ##print(f"DBG is_valid_korneslov_query: {message.text=} ; {lang=}")
    refs = parse_references(message.text, lang)
    return bool(refs)


## 2DEL
def parse_reference_OLD(text: str):
    m = KORNESLOV_RE_RU.match(text.strip()) or KORNESLOV_RE_EN.match(text.strip())
    if not m:
        return None, None, None
    book, chap, verse = m.group(1), int(m.group(2)), int(m.group(3))
    return book, chap, verse


def parse_references(text, lang="ru"):
    """
    Parese the string like "genesis 2 3:7,9", "exodus 3:5" or their rus equivalents.
    Returns the list of dicts: [{"book": str, "chapter": int, "verses": [int, ...]}, ...]
    If cannot to parse - returns emty list.
    """
    text = text.strip()
    ## Define book's lang via presense in the books lists (if the both - give lang)
    lang_guessed = lang
    ## Unified pattern: book + chapter + verses(single/range/list), delimiter between chapter and verse is space or `:`
    ## Example: "genesis 1 1", "genesis 1:1", "genesis 1 1-3,4,7-9", "genesis 2 7-9" or their rus equivs.
    ## Group 1 - book, 2 - chapter, 3 - verse(-s)
    books_re = _book_regex(lang_guessed)
    pattern = re.compile(
        rf"^{books_re}\s+(\d+)\s*[:\s]\s*([\d\-,\s]+)$",
        re.IGNORECASE
    )
    result = []
    ## TODO or not TODO^ May to add support of some requests in the one string.. (doubtful usefullness).
    m = pattern.match(text)
    if not m:
        return []
    book = m.group(1)
    chapter = int(m.group(2))
    verses_str = m.group(3)
    verses = _parse_verses(verses_str)
    if not verses:
        return []
    result.append({"book": book, "chapter": chapter, "verses": verses})
    return result



## 2DEL
## Generate system_prompt with defined level and lang.
def build_korneslov_prompt_OLD(book, chapter, verse, level_key, lang="ru"):
    level_dict = LEVELS.get(lang, LEVELS["ru"])
    level_str = level_dict.get(level_key, level_dict["hard"])
    level_sample_dict = LEVEL_SAMPLES.get(lang, LEVEL_SAMPLES["ru"])
    level_sample = level_sample_dict.get(level_key, level_sample_dict["hard"])
    system_prompt_template = KORNESLOV_SYSTEM_PROMPT.get(lang, KORNESLOV_SYSTEM_PROMPT["ru"])
    return system_prompt_template.format(
        book=book,
        chapter=chapter,
        verse=verse,
        level=level_str,
        level_sample=level_sample
    )


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



## 2DEL
async def fetch_full_korneslov_response_OLD(book, chapter, verse, uid, level="hard", max_loops=5):
    """
    Receives full response by Korneslov method and making follow-up requests if need.
    """
    state = get_user_state(uid)
    lang = state.get("lang", "ru")

    async def gen_func(book, chapter, verse, system_prompt, followup=None):
        return await ask_openai(uid, book, chapter, verse, system_prompt=system_prompt, followup=followup)

    ## Now try to add level handle mech.
    system_prompt = build_korneslov_prompt(book, chapter, verse, level, lang=lang)

    answer = await gen_func(book, chapter, verse, system_prompt=system_prompt, followup=None)

    ## Permit false repeates - no need followup if "Chastj 3" is present already and rest checks
    if not is_truncated(answer):
        return answer  ## If present - return immidiatelly w/o any followups

    all_answers = [answer]
    loops = 0
    while is_truncated(answer) and loops < max_loops:
        followup_prompt_template = FOLLOWUP_PROMPT.get(lang, FOLLOWUP_PROMPT["ru"])
        followup_prompt = followup_prompt_template.format(book=book, chapter=chapter, verse=verse)
        answer = await gen_func(book, chapter, verse, system_prompt=system_prompt, followup=followup_prompt)
        all_answers.append(answer)
        loops += 1
    return "\n\n".join(all_answers)



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

    ## Permit false repeates - no need followup if "Chastj 3" is present already and rest checks
    if not is_truncated(answer):
        return answer  ## If present - return immidiatelly w/o any followups

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
        return tr("korneslov_py.ask_openai_no_OPENAI_API_KEY", book=book, chapter=chapter, verse=verse, test_banner=test_banner)

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
        ##print("korneslov_py.ask_openai_return FROM tr(): ", tr("korneslov_py.ask_openai_return", default_lang=lang))
        return f"""{tr("korneslov_py.ask_openai_return", default_lang=lang)} {book} {chapter}:{verse}\n{text}{f'\n{test_banner}' if test_banner else ''}"""

    except Exception as e:
        logging.exception(tr("korneslov_py.ask_openai_exception_logging"))
        return (
            tr("korneslov_py.ask_openai_exception_return", book=book, chapter=chapter, verse=verse, default_lang=lang) + 
            (f"\n{test_banner}" if test_banner else "")
        )


