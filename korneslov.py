import re
import logging
from config import OPENAI_API_KEY, TESTMODE, USE_TRIBUTE

from openai import AsyncOpenAI
from utils import is_truncated

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
        # Для fetch_full передаём followup как user_prompt
        return await ask_openai(book, chapter, verse, followup=followup)

    answer = await gen_func(book, chapter, verse, followup=None)
    all_answers = [answer]
    loops = 0
    while is_truncated(answer) and loops < max_loops:
        followup_prompt = (
            f"Продолжи с того места, где остановился. Дай оставшуюся часть разбора для стиха {book} {chapter}:{verse}."
        )
        answer = await gen_func(book, chapter, verse, followup=followup_prompt)
        all_answers.append(answer)
        loops += 1
    return "\n\n".join(all_answers)

async def generate_korneslov_response(book, chapter, verse):
    """
    Lgic:
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

async def ask_openai(book, chapter, verse, test_banner="", followup=None):
    if not OPENAI_API_KEY:
        return f"Корнеслов {book} {chapter}:{verse}\n(Ошибка: не указан ключ OpenAI или не установлен пакет openai){test_banner}"

    system_prompt = f"""
Метод «Корнеслов» — подробное описание
Базовый источник текста:
•  Масоретский текст Танаха в редакции Leningrad Codex (Кодекс Ленинградский).
Цель метода:
•  Максимально буквальный, прозрачный для анализа перевод текста на основе значений базовых (окончательных) корней слов, с привлечением академических словарей, без богословских интерпретаций и метафор.
________________________________________
Общая структура ответа
Разбор стиха выполняется в три части.
________________________________________
Часть 0 — Исходный стих
•  Полностью приводится стих на масоретском иврите (точно по Leningrad Codex, включая огласовки).
________________________________________
Часть I — Слова и их корни
Для каждого слова стиха:
1.  Указывается слово на масоретском иврите.
2.  В скобках — его канонический перевод (если он есть в традиционных переводах).
3.  Указывается номер Strong для формы слова.
4.  Определяется окончательный (базовый) корень. При наличии нескольких ступеней производности корня -  пройти до окончательного (базового) корня. При наличии нескольких возможных окончательных (базовых) корней - указывать все.
5.  Для базового корня приводятся:
o  Значения по Strong’s Concordance (максимальное количество значений).
o  Значения по Brown–Driver–Briggs Hebrew Lexicon (BDB) — максимально полный список.
o  Расширенный блок: дополнительные значения и оттенки из родственных семитских языков (аккадский, арамейский, арабский, угаритский и др.) при совпадении этимологии. Здесь же указываются источники (например: BDB, HALOT, Klein, Gesenius, Theological Wordbook, Comparative Semitic Lexicon).
6.  Если слово — имя собственное, указывается его перевод по корню, также с полным набором значений и этимологической информацией.
________________________________________
Часть II — Список значений корней
•  Формируется компактный список всех слов стиха в порядке следования с перечнем всех значений их базовых корней через «/».
•  При наличии нескольких допустимых переводов одного корня — они все указываются.
•  Обязательно перечисли все слова стиха в Часть II, не пропускай ни одного, даже если повторяется. Для каждого укажи все значения базового корня через «/», даже малозначимые и редкие. Не сокращай список.
________________________________________
Часть III — Варианты перевода
•  На основе списка значений из Часть II составляется 5–15 буквальных переводов стиха:
o  Без богословских или толковательных вставок.
o  Без метафор и аллегорий.
o  Каждый вариант использует разные сочетания значений корней, чтобы передать диапазон смыслов.
o  Имена собственные приводятся в скобках в оригинальном виде с переводом по корню.
________________________________________
Принципы метода
1.  Буквальность — передаётся максимально близкий к корню смысл, даже если фраза звучит необычно.
2.  Прозрачность — каждый шаг обоснован, указаны все источники значений.
3.  Разнообразие — при генерации вариантов перевода используются разные значения корней, чтобы показать многозначность оригинала.
4.  Отсутствие толкований — никакие богословские комментарии, интерпретации или традиционные пояснения не добавляются.
5.  Источники — обязательно фиксируется, из какого словаря или корпуса взято каждое значение (Strong, BDB, HALOT и др.).
________________________________________
Формат команды для запуска метода
В диалоге с ботом или в чате GPT метод вызывается командой:
Корнеслов <Книга> <Глава>:<Стих>
Например:
Корнеслов Бытие 4:1
________________________________________

Ты — лингвист, но не в коем случае не библеист!!
Разбери стих из Библии по методу «Корнеслов». 
Дай подробный анализ текста, значения ключевых слов, исторический и контекстуальный комментарий,
укажи корни слов и возможные параллели.
\n\nСтрока: {book} {chapter}:{verse}\n
Пиши на русском языке.
Обязательно напиши полностью все части (I, II, III) в одном ответе.
Обязательно указывать все доступные значения базовых корней каждого слова.
Не сокращай ответ, выдай полностью все части даже если получится много текста.
Продолжи с того места, где ты остановился. Дай оставшиеся части (например, Часть II и III), чтобы был полностью завершён разбор стиха.
Продолжи с того места, где остановился. Дай оставшиеся варианты Часть III (Варианты перевода) для стиха {book} {chapter}:{verse}.
    """
    if followup:
        user_prompt = followup
    else:
        user_prompt = f"Корнеслов {book} {chapter}:{verse}"
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=3000,
            n=1,
        )
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