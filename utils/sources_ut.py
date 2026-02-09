from collections import defaultdict
from typing import List, Dict, Any

from db.verses import get_verse_texts


def build_sources_block(
    *,
    book_label: str,
    chapter: int,
    verses: List[int],
    rows: List[Dict[str, Any]],
) -> str:
    """
    rows: output of get_verse_texts() ordered by source_code then verse
    """
    if not rows:
        return ""

    grouped = defaultdict(list)
    titles = {}
    for r in rows:
        code = r["source_code"]
        titles[code] = r.get("source_title") or code
        grouped[code].append(r)

    parts = []
    parts.append("\n================\nYou MUST use these verses as sources:\n")

    for source_code, items in grouped.items():
        parts.append(f"{titles[source_code]}:\n")
        for it in items:
            v = it["verse"]
            text = (it["text"] or "").strip()
            if not text:
                continue
            parts.append(f"{book_label} {chapter} {v}: {text}\n")
        parts.append("\n")

    return "".join(parts).rstrip() + "\n"


async def build_sources_for_prompt(
    *,
    lang: str,
    book_entry: dict,
    chapter: int,
    verses: List[int],
) -> str:
    """
    Select sources by UI language:
      ru -> SYNODAL + WLC
      en -> KJV + WLC
    Uses books.bookname_ru as book_label for now (like your examples).
    """
    if not book_entry or not verses:
        return ""

    book_id = book_entry.get("book_id")
    if not book_id:
        return ""

    lang = (lang or "ru").lower()
    if lang.startswith("ru"):
        source_codes = ["SYNODAL", "WLC"]
    else:
        source_codes = ["KJV", "WLC"]

    rows = await get_verse_texts(book_id=book_id, chapter=chapter, verses=verses, source_codes=source_codes)

    book_label = book_entry.get("bookname_ru") or book_entry.get("bookname_en") or ""
    return build_sources_block(book_label=book_label, chapter=chapter, verses=verses, rows=rows)