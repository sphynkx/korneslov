import aiomysql
from db import get_pool


## Write paymant event
async def add_tribute_payment(user_id, product_id, amount, currency, status, external_id, datetime, raw_json=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO tribute (user_id, product_id, amount, currency, status, external_id, datetime, raw_json) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE status=%s, raw_json=%s",
                (user_id, product_id, amount, currency, status, external_id, datetime, raw_json, status, raw_json)
            )
            await conn.commit()


## Get user payment history
async def get_tribute_by_user(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM tribute WHERE user_id=%s ORDER BY datetime DESC LIMIT 10", (user_id,)
            )
            return await cur.fetchall()


## Get user balance (requests_left)
async def get_user_requests_left(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT requests_left FROM users WHERE user_id=%s", (user_id,)
            )
            row = await cur.fetchone()
            if row:
                return row[0]
            return 0


## Refresh user balance
async def set_user_requests_left(user_id, new_requests_left):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE users SET requests_left=%s, requests_left_update=NOW() WHERE user_id=%s", (new_requests_left, user_id)
            )
            await conn.commit()

