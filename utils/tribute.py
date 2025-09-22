from config import TRIBUTE_REQUEST_PRICE
from datetime import datetime


def normalize_datetime(dt_str: str) -> str:
    """
    Reform ISO8601to format for MySQL DATETIME.
    """
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1]
        ## Try ISO8601
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def is_unlimited(requests_left):
    return requests_left == -1


def can_use(requests_left):
    return is_unlimited(requests_left) or (requests_left >= TRIBUTE_REQUEST_PRICE)



