import aiomysql
import os
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS


## For connections pool..
_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=DB_HOST,
            port=int(DB_PORT),
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
            autocommit=True,
            minsize=1,
            maxsize=5,
            charset="utf8mb4"
        )
    return _pool


async def get_conn():
    pool = await get_pool()
    return await pool.acquire()


## asyncly perform any request w/o fetch
async def execute(query, params=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            return cur.lastrowid


## Asyncly get one record
async def fetchone(query, params=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, params)
            return await cur.fetchone()


## asyncly get all records
async def fetchall(query, params=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, params)
            return await cur.fetchall()

########################
### Tribute part (sync)

import pymysql
from pymysql.cursors import DictCursor, Cursor
from config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME

def get_connection(dict_cursor: bool = False) -> pymysql.connections.Connection:
    cursor_class = DictCursor if dict_cursor else Cursor
    conn = pymysql.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        autocommit=False,
        cursorclass=cursor_class,
    )
    return conn



"""
OLD implementation - 2DELETE
import sqlite3
from config import DATABASE_FILE

def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_balances (
            telegram_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_balance(telegram_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT balance FROM user_balances WHERE telegram_id=?', (telegram_id,))
    row = c.fetchone()
    conn.close()
    return row['balance'] if row else 0

def add_balance(telegram_id, delta):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO user_balances (telegram_id, balance) VALUES (?, ?) '
        'ON CONFLICT(telegram_id) DO UPDATE SET balance = balance + ?',
        (telegram_id, delta, delta)
    )
    conn.commit()
    conn.close()

def dec_balance(telegram_id, delta=1):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT balance FROM user_balances WHERE telegram_id=?', (telegram_id,))
    row = c.fetchone()
    if not row or row['balance'] < delta:
        conn.close()
        return False
    c.execute('UPDATE user_balances SET balance=balance-? WHERE telegram_id=?', (delta, telegram_id))
    conn.commit()
    conn.close()
    return True

"""
