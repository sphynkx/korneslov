from db import fetchall, fetchone


async def get_sources_by_codes(codes):
    """
    Returns list of sources rows in the same order as codes (if found).
    """
    if not codes:
        return []
    placeholders = ",".join(["%s"] * len(codes))
    rows = await fetchall(
        f"SELECT * FROM sources WHERE code IN ({placeholders}) AND enabled=1",
        tuple(codes),
    )
    # preserve requested order
    by_code = {r["code"]: r for r in rows}
    return [by_code[c] for c in codes if c in by_code]


async def get_verse_texts(book_id: int, chapter: int, verses: list[int], source_codes: list[str]):
    """
    Returns rows with:
      source_code, source_title, verse, text
    Missing verses are simply absent from result.
    """
    if not verses or not source_codes:
        return []

    verses_placeholders = ",".join(["%s"] * len(verses))
    sources_placeholders = ",".join(["%s"] * len(source_codes))

    query = f"""
        SELECT
            s.code AS source_code,
            s.title AS source_title,
            vt.verse AS verse,
            vt.text AS text
        FROM verse_texts vt
        JOIN sources s ON s.id = vt.source_id
        WHERE vt.book_id = %s
          AND vt.chapter = %s
          AND vt.verse IN ({verses_placeholders})
          AND s.code IN ({sources_placeholders})
          AND s.enabled = 1
        ORDER BY FIELD(s.code, {sources_placeholders}), vt.verse
    """
    # params: book_id, chapter, verses..., source_codes..., source_codes... (for FIELD order)
    params = [book_id, chapter, *verses, *source_codes, *source_codes]
    return await fetchall(query, tuple(params))