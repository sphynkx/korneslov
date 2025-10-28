import asyncio
import logging
import html
from typing import Optional

from aiogram import types
import aiogram.exceptions as aiogram_exceptions

from services.concurrency import acquire_send


## Read retry tuning from config if present, else env/defaults
try:
    from config import TG_SEND_RETRY_MAX as _RETRY_MAX  # type: ignore
except Exception:
    _RETRY_MAX = 3

try:
    from config import TG_SEND_RETRY_BASE_DELAY as _RETRY_BASE  ## type: ignore
except Exception:
    _RETRY_BASE = 0.5

try:
    from config import TG_SEND_RETRY_MAX_DELAY as _RETRY_MAX_DELAY  ## type: ignore
except Exception:
    _RETRY_MAX_DELAY = 5.0


async def answer_safe_message(target: types.Message | types.CallbackQuery, text: str, parse_mode: Optional[str] = "HTML", **kwargs) -> bool:
    """
    Send text to target safely with retries and fallbacks.
    Returns True if message was sent successfully, False otherwise.
    - Retries on TelegramNetworkError/Timeout with exponential backoff.
    - Handles FloodWait/RetryAfter by sleeping the server-specified delay.
    - Falls back to escaped plain text if HTML parse fails.
    """
    ## target.answer exists for Message and CallbackQuery; resolve callable and kwargs
    msg_target = target
    attempts = max(1, int(_RETRY_MAX))
    delay = float(_RETRY_BASE)
    max_delay = float(_RETRY_MAX_DELAY)

    ## First attempt: try HTML; if fails due to parse, fallback to escaped once
    tried_plain = False
    escaped_text = None

    async with acquire_send():
        for attempt in range(1, attempts + 1):
            try:
                if not tried_plain:
                    await msg_target.answer(text, parse_mode=parse_mode, **{k: v for k, v in kwargs.items() if k != "parse_mode"})
                else:
                    if escaped_text is None:
                        escaped_text = html.escape(text or "")
                    await msg_target.answer(escaped_text, **{k: v for k, v in kwargs.items() if k != "parse_mode"})
                return True

            except aiogram_exceptions.TelegramBadRequest as e:
                ## HTML parse issues -> try plain text once
                logging.warning("TelegramBadRequest while sending message; falling back to plain text: %s", e)
                if not tried_plain:
                    tried_plain = True
                    ## immediate retry in next loop iteration
                    continue
                ## if already tried plain, no point retrying BadRequest endlessly
                logging.exception("TelegramBadRequest even after plain fallback")
                return False

            except aiogram_exceptions.TelegramRetryAfter as e:
                wait_for = getattr(e, "retry_after", 1)
                logging.warning("TelegramRetryAfter: sleeping for %ss (attempt %d/%d)", wait_for, attempt, attempts)
                await asyncio.sleep(float(wait_for) + 0.25)
                continue

            except aiogram_exceptions.TelegramNetworkError as e:
                logging.warning("TelegramNetworkError on send (attempt %d/%d): %s", attempt, attempts, e)
                await asyncio.sleep(delay)
                delay = min(delay * 2.0, max_delay)
                continue

            except asyncio.TimeoutError:
                logging.warning("TimeoutError on send (attempt %d/%d)", attempt, attempts)
                await asyncio.sleep(delay)
                delay = min(delay * 2.0, max_delay)
                continue

            except Exception as e:
                logging.exception("Failed to send message (unexpected): %s", e)
                await asyncio.sleep(delay)
                delay = min(delay * 2.0, max_delay)
                continue

    return False
