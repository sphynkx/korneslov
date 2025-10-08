import re
from db.books import find_book_by_name_or_synonym, increment_book_hits



## Dummy for Statistika button
def get_statistics_text() -> str:
    return "STATISTIKA."


## Improved heuristics - tracks allowed pair tags, count all tags using dict. In case of unclosed tag force set close tag at the end of part, and force set open tag at the beginning of the next part. No errors were observed.
def split_message(text, max_length=4000):
    ## Only paired tags and allowed for telegram API
    TELEGRAM_PAIR_TAGS = {
        "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
        "span", "a", "code", "pre"
    }

    def get_tag_counts(s):
        ## Count every tags
        tags = re.findall(r'<(/?)(\w+)[^>]*?>', s)
        counts = dict.fromkeys(TELEGRAM_PAIR_TAGS, 0)
        for slash, tag in tags:
            tag = tag.lower()
            if tag not in TELEGRAM_PAIR_TAGS:
                continue
            if not slash:
                counts[tag] += 1
            else:
                counts[tag] -= 1
        return counts

    parts = []
    while len(text) > max_length:
        ## Search for closest \n or <br> before limit
        split_pos = text.rfind('<br>', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind('.', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
        else:
            split_pos += 4 if text[split_pos:split_pos+4] == '<br>' else 1

        part = text[:split_pos].strip()
        counts = get_tag_counts(part)
        ## Force close unclosed tag
        for tag, count in counts.items():
            if count % 2 == 1:
                part += f'</{tag}>'
        parts.append(part)
        text = text[split_pos:].lstrip()
        ## Force set open tag at beginning of next part
        for tag, count in counts.items():
            if count % 2 == 1:
                text = f'<{tag}>' + text
    if text:
        parts.append(text)
    return parts


def is_truncated(answer: str, min_length=3500, ending_punct=('.','…','!','?', '>')):
    """
    Heuristics: if response length is close to max_tokens * 4 (about 3000 tokens = 4000–4500 symbols), ans response doesnt end on any sentence ending sign then the response is probably cutted.
    """
    answer = answer.strip()
    ## Dirty hack - to permit false repeates and unneeded followups
    ##if re.search(tr("utils_py.is_truncated_regexp"), answer):
    ##Swithed to more universal marker
    if re.search("<b>\u200b\u200b\u200b\u200b</b>", answer):
        return False

    long_enough = len(answer) >= min_length
    truncated = long_enough and not answer.endswith(ending_punct)
    return truncated


def _normalize_book(book):
    """Set to lowercase, remove extra spaces."""
    return book.strip().lower()


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


async def parse_references(text, lang="ru", hits=False):
    """
    Parse the string like "genesis 2 3:7,9", "exodus 3:5" or their rus equivalents.
    Returns the list of dicts: [{"book": str, "chapter": int, "verses": [int, ...]}, ...]
    If cannot parse - returns empty list.
    Support for book names with numbers and spaces.
    Note: parse_references() calls in 2 places:
    * at as filter in `routes/methodes/korneslov_mtd.py` (handle_korneslov_query() ) hit is False - do not increment - DEPRECATED!!
    * at is_valid_korneslov_query() with `hits=True` param, and increments the `hits`
    It was bugfix for duplicated incrementions.
    """
    print(f"     DBG: parse_references()!! {text=}")
    text = text.strip()
    if not text:
        return []
    parts = text.split()
    if len(parts) < 3:
        return []
    verses_str = parts[-1]
    chapter_str = parts[-2]
    book = " ".join(parts[:-2])
    try:
        chapter = int(chapter_str)
    except Exception:
        return []
    verses = _parse_verses(verses_str)
    if not verses:
        return []

    ## Check book in the `books` table
    book_entry = await find_book_by_name_or_synonym(book)
    if not book_entry:
        return []

    ## Is chapter correct??
    max_chapter = book_entry.get('max_chapter')
    if not chapter or chapter < 1 or chapter > max_chapter:
        return []

    ## Is verses are correct??
    max_verses_str = book_entry.get('max_verses')
    try:
        max_verses = eval(max_verses_str)
    except Exception:
        return []
    if chapter > len(max_verses):
        return []
    max_verse = max_verses[chapter - 1]
    bad_verses = [v for v in verses if v < 1 or v > max_verse]
    if bad_verses:
        return []

    ## Everything is OK then lets increment the `books.hits`!!
    if hits:
        await increment_book_hits(book_entry['id'])

    return [{"book": book, "chapter": chapter, "verses": verses}]





