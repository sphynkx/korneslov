import logging
import html
from typing import Optional

from aiogram import Router, exceptions, types
from pymysql import OperationalError as PyMySQLOperationalError
from aiomysql import OperationalError as AiomysqlOperationalError

from utils.userstate import get_user_state
from utils.tgpayments import reset_payment_state
from i18n.messages import tr
from utils.safe_send import answer_safe_message

router = Router()


@router.errors()
async def global_error_handler(update_or_exception, exception: Optional[Exception] = None) -> bool:
    """
    Robust global error handler that tolerates different call signatures:
      - (update, exception)
      - (exception,)  (some internal callers may pass only exception)
      - (update,)     (rare)
    Returns True to stop propagation.
    """
    try:
        ## Normalize arguments: determine which is update and which is exception
        if exception is None:
            ## If only one arg provided, it may be the exception or the update.
            if isinstance(update_or_exception, Exception):
                exception = update_or_exception
                update = None
            else:
                ## single update passed (no exception) — treat exception unknown
                update = update_or_exception
                exception = None
        else:
            update = update_or_exception

##        logging.exception("Global handler caught exception: %s", exception)

        ## Normalized variables: 'update' and 'exception'
        ## More smart logging: if exception - use exception logger, else - log update info
        if exception is not None:
            logging.exception("Global handler caught exception: %s", exception)
        else:
            logging.error("Global handler invoked without exception object. update=%r", update)

        ## Try to extract user/message for replying
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
                ## update may be an Update object with .callback_query or .message
                if hasattr(update, "callback_query") and getattr(update, "callback_query"):
                    cq = update.callback_query
                    user_id = cq.from_user.id
                    msg_target = cq
                elif hasattr(update, "message") and getattr(update, "message"):
                    m = update.message
                    user_id = m.from_user.id
                    msg_target = m
        except Exception:
            logging.exception("Failed to extract user/message from update in error handler")

        ## CASE 1: Telegram bad request - PAYMENT_PROVIDER_INVALID
        if isinstance(exception, exceptions.TelegramBadRequest) and exception.args and "PAYMENT_PROVIDER_INVALID" in str(exception):
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
                        await msg_target.answer()
            except Exception:
                logging.exception("Failed to notify user about PAYMENT_PROVIDER_INVALID")
            return True

        ## CASE 2: DB connectivity issues
        if isinstance(exception, (PyMySQLOperationalError, AiomysqlOperationalError)) or (exception and "Can't connect to MySQL server" in str(exception)):
            lang = "ru"
            if user_id:
                state = get_user_state(user_id)
                lang = state.get("lang", "ru")
            try:
                text = tr("errors.db_unavailable", lang=lang)
                if msg_target:
                    await answer_safe_message(msg_target, text)
                    if isinstance(msg_target, types.CallbackQuery):
                        await msg_target.answer()
            except Exception:
                logging.exception("Failed to notify user about DB connectivity issue")
            return True

        ## CASE 3: Broken HTML / cant parse entities
        if isinstance(exception, exceptions.TelegramBadRequest) and exception.args:
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
                            await msg_target.answer()
                except Exception:
                    logging.exception("Failed to send parse-failed fallback")
                return True

        ## FALLBACK: notify user and swallow the exception
        try:
            lang = "ru"
            if user_id:
                state = get_user_state(user_id)
                lang = state.get("lang", "ru")
            text = tr("errors.unexpected", lang=lang)
            if msg_target:
                await answer_safe_message(msg_target, text)
                if isinstance(msg_target, types.CallbackQuery):
                    await msg_target.answer()
        except Exception:
            logging.exception("Failed to send fallback unexpected error message")

        return True

    except Exception as e:
        ## If the error handler itself crashes - log and return True (we don't want propagation)
        logging.exception("Error handler crashed: %s", e)
        return True
