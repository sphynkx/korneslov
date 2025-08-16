import re
import logging
from config import get_model_and_params, OPENAI_API_KEY, TESTMODE, USE_TRIBUTE, OPENAI_MODEL, OPENAI_MODEL_PARAMS
from openai import AsyncOpenAI
from utils import is_truncated
from texts.prompts import *

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

KORNESLOV_RE = re.compile(r'^Корнеслов\s+([^\s]+)\s+(\d+):(\d+)$', re.IGNORECASE)



def is_valid_korneslov_query(text: str):
    return bool(KORNESLOV_RE.match(text.strip()))


def parse_reference(text: str):
    m = KORNESLOV_RE.match(text.strip())
    if not m:
        return None, None, None
    book, chap, verse = m.group(1), int(m.group(2)), int(m.group(3))
    return book, chap, verse


async def fetch_full_korneslov_response(book, chapter, verse, max_loops=5):
    """
    Receives full response by Korneslov method and making follow-up requests if need.
    """
    async def gen_func(book, chapter, verse, followup=None):
        return await ask_openai(book, chapter, verse, followup=followup)

    answer = await gen_func(book, chapter, verse, followup=None)
    all_answers = [answer]
    loops = 0
    while is_truncated(answer) and loops < max_loops:

        followup_prompt = FOLLOWUP_PROMPT.format(book=book, chapter=chapter, verse=verse)
        answer = await gen_func(book, chapter, verse, followup=followup_prompt)
        all_answers.append(answer)
        loops += 1
    return "\n\n".join(all_answers)


async def generate_korneslov_response(book, chapter, verse):
    """
    Logic:
    - TESTMODE=True: always request to OpenAI, dont touch Tribute.
    - TESTMODE=False:
        - USE_TRIBUTE=False: return dummy, dont touch OpenAI.
        - USE_TRIBUTE=True: normal mode - work with both OpenAI andTribute.
    """
    if TESTMODE:
        return await ask_openai(book, chapter, verse, test_banner="(Тестовый режим: Tribute отключён)")
    elif not USE_TRIBUTE:
        return f"Корнеслов {book} {chapter}:{verse}\n(Заглушка: доступен только в платном режиме)"
    else:
        return await ask_openai(book, chapter, verse)


def build_prompt(template, book, chapter, verse):
    """
    Build prompt from template using .format().
    """
    return template.format(book=book, chapter=chapter, verse=verse)


async def ask_openai(book, chapter, verse, test_banner="", followup=None):
    if not OPENAI_API_KEY:
        return f"Корнеслов {book} {chapter}:{verse}\n(Ошибка: не указан ключ OpenAI или не установлен пакет openai){test_banner}"

    ## System prompt from file
    system_prompt = KORNESLOV_SYSTEM_PROMPT.format(book=book, chapter=chapter, verse=verse)


    if followup:
        user_prompt = followup
    else:
        user_prompt = KORNESLOV_USER_PROMPT.format(book=book, chapter=chapter, verse=verse)

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
        return f"Корнеслов {book} {chapter}:{verse}\n{text}{f'\n{test_banner}' if test_banner else ''}"
    except Exception as e:
        logging.exception("Ошибка при обращении к OpenAI")
        return (
            f"Корнеслов {book} {chapter}:{verse}\n"
            "(Ошибка обращения к ChatGPT. Попробуйте позже.)"
            f"{f'\n{test_banner}' if test_banner else ''}"
        )

