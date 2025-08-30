from db import fetchone, fetchall


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


## Get all bookx and all their fields
async def get_all_books():
    return await fetchall("SELECT * FROM books")

