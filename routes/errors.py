import logging
import html
from typing import Optional, Any

from aiogram import Router, types
import aiogram.exceptions as aiogram_exceptions
from pymysql import OperationalError as PyMySQLOperationalError
from aiomysql import OperationalError as AiomysqlOperationalError

from utils.userstate import get_user_state
from utils.tgpayments import reset_payment_state
from i18n.messages import tr
from utils.safe_send import answer_safe_message

router = Router()


@router.errors()
async def global_error_handler(update_or_exception: Any, exception: Optional[Exception] = None) -> bool:
    """
    Robust global error handler that tolerates different call signatures:
      - (update, exception)
      - (exception,)  (some internal callers may pass only exception)
      - (update,)     (rare)
      - (ErrorEvent(update=..., exception=...))  (aiogram can pass this)
    Returns True to stop propagation.
    """
    try:
        # --- Normalize arguments: determine update and exception ---
        update = None
        # If a single object was passed and it looks like an ErrorEvent (has .exception), unwrap it
        if exception is None and hasattr(update_or_exception, "exception"):
            # aiogram may pass ErrorEvent-like object
            evt = update_or_exception
            exception = getattr(evt, "exception", None)
            update = getattr(evt, "update", None)
        else:
            if exception is None:
                # if only one arg provided, decide if it's exception or update
                if isinstance(update_or_exception, Exception):
                    exception = update_or_exception
                    update = None
                else:
                    update = update_or_exception
            else:
                update = update_or_exception

        # --- Logging ---
        if exception is not None:
            logging.exception("Global handler caught exception: %s", exception)
        else:
            logging.error("Global handler invoked without exception object. update=%r", update)

        # Try to extract user/message for replying
        user_id = None
        msg_target = None
        try:
            if isinstance(update, types.CallbackQuery):
                user_id = update.from_user.id
                msg_target = update
            elif isinstance(update, types.Message):
                user_id = update.from_user.id
                msg_target = update
            elif update is not None:
                if hasattr(update, "callback_query") and getattr(update, "callback_query"):
                    cq = update.callback_query
                    user_id = getattr(cq.from_user, "id", None)
                    msg_target = cq
                elif hasattr(update, "message") and getattr(update, "message"):
                    m = update.message
                    user_id = getattr(m.from_user, "id", None)
                    msg_target = m
        except Exception:
            logging.exception("Failed to extract user/message from update in error handler")

        # CASE 1: PAYMENT_PROVIDER_INVALID from Telegram when send_invoice
        if exception is not None and isinstance(exception, aiogram_exceptions.TelegramBadRequest) and "PAYMENT_PROVIDER_INVALID" in str(exception):
            lang = "ru"
            if user_id:
                state = get_user_state(user_id)
                lang = state.get("lang", "ru")
                reset_payment_state(state)
            try:
                text = tr("tgpayment.provider_invalid", lang=lang)
                if msg_target:
                    await answer_safe_message(msg_target, text)
                    if isinstance(msg_target, types.CallbackQuery):
                        try:
                            await msg_target.answer()
                        except Exception:
                            pass
            except Exception:
                logging.exception("Failed to notify user about PAYMENT_PROVIDER_INVALID")
            return True

        # CASE 2: DB connectivity errors (PyMySQL / Aiomysql)
        if exception is not None and (isinstance(exception, (PyMySQLOperationalError, AiomysqlOperationalError)) or "Can't connect to MySQL server" in str(exception)):
            lang = "ru"
            if user_id:
                state = get_user_state(user_id)
                lang = state.get("lang", "ru")
            try:
                text = tr("errors.db_unavailable", lang=lang)
                if msg_target:
                    await answer_safe_message(msg_target, text)
                    if isinstance(msg_target, types.CallbackQuery):
                        try:
                            await msg_target.answer()
                        except Exception:
                            pass
            except Exception:
                logging.exception("Failed to notify user about DB connectivity issue")
            return True

        # CASE 3: Broken HTML / can't parse entities (TelegramBadRequest)
        if exception is not None and isinstance(exception, aiogram_exceptions.TelegramBadRequest):
            desc = str(exception).lower()
            if "can't parse entities" in desc or "can't parse message text" in desc or "can't parse" in desc:
                lang = "ru"
                if user_id:
                    state = get_user_state(user_id)
                    lang = state.get("lang", "ru")
                try:
                    text = tr("errors.message_parse_failed", lang=lang)
                    if msg_target:
                        await answer_safe_message(msg_target, text)
                        if isinstance(msg_target, types.CallbackQuery):
                            try:
                                await msg_target.answer()
                            except Exception:
                                pass
                except Exception:
                    logging.exception("Failed to send parse-failed fallback")
                return True

        # FALLBACK: notify user and swallow the exception
        try:
            lang = "ru"
            if user_id:
                state = get_user_state(user_id)
                lang = state.get("lang", "ru")
            text = tr("errors.unexpected", lang=lang)
            if msg_target:
                await answer_safe_message(msg_target, text)
                if isinstance(msg_target, types.CallbackQuery):
                    try:
                        await msg_target.answer()
                    except Exception:
                        pass
        except Exception:
            logging.exception("Failed to send fallback unexpected error message")

        return True

    except Exception as e:
        # If the error handler itself crashes — log and return True (we don't want propagation)
        logging.exception("Error handler crashed: %s", e)
        return True