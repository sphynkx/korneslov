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