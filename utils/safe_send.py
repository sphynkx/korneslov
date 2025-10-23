import logging
import html
from typing import Optional

from aiogram import types, exceptions

## helper to send replies safely when text may contain broken HTML
async def answer_safe_message(target: types.Message | types.CallbackQuery, text: str, parse_mode: Optional[str] = "HTML", **kwargs):
    """
    target: types.Message or types.CallbackQuery (we'll send into .message for callback)
    try to send with parse_mode (HTML by default); on TelegramBadRequest fallback to escaped text w/o parse mode.
    """
    try:
        if isinstance(target, types.CallbackQuery):
            msg_target = target.message
        else:
            msg_target = target

        if parse_mode:
            await msg_target.answer(text, parse_mode=parse_mode, **kwargs)
        else:
            await msg_target.answer(text, **kwargs)
    except exceptions.TelegramBadRequest as e:
        ## Could be "can't parse entities" or other parse errors. Fallback to escaped text without parse_mode.
        logging.warning("TelegramBadRequest while sending message; falling back to plain text: %s", e)
        try:
            safe_text = html.escape(text)
            await msg_target.answer(safe_text, **{k: v for k, v in kwargs.items() if k != "parse_mode"})
        except Exception as e2:
            logging.exception("Failed to send fallback message: %s", e2)
