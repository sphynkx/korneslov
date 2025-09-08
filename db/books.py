from db import fetchone, fetchall, execute


async def find_book_entry(book, conn):
    """
    Search book name through bookname_ru, bookname_en and all synonyms (ru, en).
    Return string from DB or None.
    """
    sql_exact = """
        SELECT * FROM books
        WHERE bookname_ru = %s OR bookname_en = %s
        LIMIT 1
    """
    async with conn.cursor() as cur:
        await cur.execute(sql_exact, (book, book))
        row = await cur.fetchone()
        if row:
            return row
    sql_syn = """
        SELECT * FROM books
        WHERE FIND_IN_SET(%s, REPLACE(synonyms_ru, ' ', '')) > 0
           OR FIND_IN_SET(%s, REPLACE(synonyms_en, ' ', '')) > 0
        LIMIT 1
    """
    book_nospace = book.replace(" ", "")
    async with conn.cursor() as cur:
        await cur.execute(sql_syn, (book_nospace, book_nospace))
        row = await cur.fetchone()
        if row:
            return row
    return None


async def find_book_by_name_or_synonym(book_name):
    """
    Searches book name by RU/EN name or by synonyms.
    Returns dict with book data or None.
    """
    ## Find by RU/EN names
    query = "SELECT * FROM books WHERE bookname_ru = %s OR bookname_en = %s"
    book = await fetchone(query, (book_name, book_name))
    if book:
        return book

    ## Search by synonyms
    ## Get all books'es synonyms and find thorugh them
    books = await fetchall("SELECT * FROM books")
    for b in books:
        syn_ru = (b.get('synonyms_ru') or '').lower().split(',')
        syn_en = (b.get('synonyms_en') or '').lower().split(',')
        syns = [s.strip() for s in syn_ru + syn_en if s.strip()]
        if book_name.lower() in syns:
            return b
    return None


async def increment_book_hits(book_id):
    query = "UPDATE books SET hits = hits + 1 WHERE id = %s"
    await execute(query, (book_id,))


## Get all bookx and all their fields
async def get_all_books():
    return await fetchall("SELECT * FROM books")

