from decimal import Decimal
from typing import List, Dict, Optional, Any
from pymysql.cursors import DictCursor
from db import get_connection


def add_tribute_payment(
    user_id: int,
    product_id: str,
    amount: Decimal | float | int | str,
    currency: str,
    status: str,
    external_id: str,
    datetime_val: Optional[str],
    raw_json: Optional[str] = None,
) -> None:
    """
    Inserts/update payload info.
    Waits for uniq index by external_id (UNIQUE KEY (external_id)).
    datetime_val must be string like 'YYYY-MM-DD HH:MM:SS' or None.
    """
    sql = """
        INSERT INTO tribute (user_id, product_id, amount, currency, status, external_id, datetime, raw_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE status=VALUES(status), raw_json=VALUES(raw_json)
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    user_id,
                    product_id,
                    amount,
                    currency,
                    status,
                    external_id,
                    datetime_val,
                    raw_json,
                ),
            )
        conn.commit()


def get_tribute_by_user(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Returns last user's payloads as  dict list
    """
    sql = """
        SELECT id, user_id, product_id, amount, currency, status, external_id, datetime, raw_json
        FROM tribute
        WHERE user_id = %s
        ORDER BY datetime DESC, id DESC
        LIMIT %s
    """
    with get_connection(dict_cursor=True) as conn:
        with conn.cursor(DictCursor) as cur:
            cur.execute(sql, (user_id, int(limit)))
            rows = cur.fetchall()
    return list(rows or [])


def get_user_requests_left(user_id: int) -> int:
    """
    Returns current balance of user's requests (integer).
    For no records returns 0.
    """
    sql = "SELECT requests_left FROM users WHERE user_id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            if not row:
                return 0
            value = row[0]
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0


def set_user_requests_left(user_id: int, new_requests_left: int) -> None:
    """
    Updates the balance of user's requests.
    """
    sql = """
        UPDATE users
        SET requests_left = %s,
            requests_left_update = NOW()
        WHERE user_id = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (int(new_requests_left), user_id))
        conn.commit()
