from config import TRIBUTE_REQUEST_PRICE
from datetime import datetime
import aiomysql
from db import get_pool


async def add_tribute_payment(
    user_id: int,
    product_id: str,
    amount,
    currency: str,
    status: str,
    external_id: str,
    datetime_val: str,
    raw_json: str,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO tribute (user_id, product_id, amount, currency, status, external_id, datetime, raw_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    status=VALUES(status),
                    amount=VALUES(amount),
                    datetime=VALUES(datetime),
                    raw_json=VALUES(raw_json)
                """,
                (user_id, product_id, amount, currency, status, external_id, datetime_val, raw_json),
            )
            await conn.commit()

async def get_user_amount_and_external_id(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT amount, external_id FROM users WHERE user_id=%s",
                (user_id,),
            )
            row = await cur.fetchone()
            if not row:
                return 0, None
            return row[0], row[1]

async def atomic_update_user_amount_and_external_id(user_id: int, delta: int, new_external_id: str) -> bool:
    """
    Atomically add delta to user's amount and set external_id to new_external_id ONLY if external_id != new_external_id.
    Returns True if updated, False if not (i.e., already processed).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE users
                SET amount = amount + %s, external_id = %s
                WHERE user_id = %s AND (external_id IS NULL OR external_id <> %s)
                """,
                (delta, new_external_id, user_id, new_external_id),
            )
            await conn.commit()
            return cur.rowcount > 0


async def get_user_amount(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT amount FROM users WHERE user_id=%s", (user_id,))
            row = await cur.fetchone()
            if not row:
                return 0
            return row[0]


async def set_user_amount(user_id: int, amount: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE users SET amount = %s WHERE user_id = %s", (amount, user_id)
            )
            await conn.commit()
