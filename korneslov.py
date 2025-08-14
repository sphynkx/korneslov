import re
import logging
from config import OPENAI_API_KEY, TESTMODE, USE_TRIBUTE

##try:
##    import openai
##except ImportError:
##    openai = None
from openai import AsyncOpenAI

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

async def generate_korneslov_response(book, chapter, verse):
    """
    Логика:
    - TESTMODE=True: всегда обращаемся к OpenAI, не трогаем Tribute.
    - TESTMODE=False:
        - USE_TRIBUTE=False: возвращаем заглушку, к OpenAI не обращаемся.
        - USE_TRIBUTE=True: обращаемся к OpenAI и работаем с трибьютом.
    """
    if TESTMODE:
        ## Always work with OpenAI whenever of USE_TRIBUTE
        return await ask_openai(book, chapter, verse, test_banner="(Тестовый режим: Tribute отключён)")
    elif not USE_TRIBUTE:
        ## Dummy. Without OpenAI and Tribute
        return f"Корнеслов {book} {chapter}:{verse}\n(Заглушка: доступен только в платном режиме)"
    else:
        ## Normal mode: both OpenAI and Tribute
        return await ask_openai(book, chapter, verse)

async def ask_openai(book, chapter, verse, test_banner=""):
    if not OPENAI_API_KEY:
        return f"Корнеслов {book} {chapter}:{verse}\n(Ошибка: не указан ключ OpenAI или не установлен пакет openai){test_banner}"

    prompt = (
        f"Ты — лингвист и библеист. "
        f"Разбери стих из Библии по методу «Корнеслов». "
        f"Дай подробный анализ текста, значения ключевых слов, исторический и контекстуальный комментарий, "
        f"укажи корни слов и возможные параллели. "
        f"\n\nСтрока: {book} {chapter}:{verse}\n"
        f"Пиши на русском языке."
    )
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты — эксперт по Библии и лингвист."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600,
            n=1,
        )
        text = response.choices[0].message.content.strip()
        return f"Корнеслов {book} {chapter}:{verse}\n{text}{f'\n{test_banner}' if test_banner else ''}"
    except Exception as e:
        logging.exception("Ошибка при обращении к OpenAI")
        return (
            f"Корнеслов {book} {chapter}:{verse}\n"
            "(Ошибка обращения к ChatGPT. Попробуйте позже.)"
            f"{f'\n{test_banner}' if test_banner else ''}"
        )

