import asyncio
import re
import logging
from itertools import groupby

from aiogram import Router, types
import aiogram.exceptions as aiogram_exceptions

from config import TGPAYMENT_REQUEST_PRICES
from utils.safe_send import answer_safe_message
from i18n.messages import tr
from utils.methods.korneslov_ut import is_valid_korneslov_query, fetch_full_korneslov_response
from utils.utils import split_message
from utils.userstate import get_user_state

from db import get_conn
from db.books import find_book_entry
from db.users import upsert_user
from db.requests import add_request, update_request_response
from db.responses import add_response
from db.tgpayments import get_user_amount, set_user_amount

## Bugfix - kb didnt recover after response.
from menus.main_menu import main_reply_keyboard

router = Router()


@router.message(is_valid_korneslov_query)
async def handle_korneslov_query(message: types.Message, refs=None):
    text = message.text or ""
    uid = message.from_user.id
    state = get_user_state(uid)
    level = state.get("level", "hard")
    lang = state.get("lang", "ru")

    ## Check balance before request generation
    requests_left = await get_user_amount(uid)
    price = TGPAYMENT_REQUEST_PRICES.get(level, 1)
    ## check for unlim
    if requests_left != -1 and requests_left < price:
        await message.answer(tr("tgpayment.low_amount", lang=state['lang']))
        return

    ## Logging user to DB (upsert)
    user = message.from_user
    await upsert_user(
        user_id=user.id,
        firstname=user.first_name,
        lastname=user.last_name,
        username=user.username,
        lang=lang,
        is_bot=user.is_bot
    )

    ## Save user request to DB
    req_id = await add_request(
        user_id=uid,
        user_state=state,
        request=text
    )

    ref = refs[0]
    book = ref["book"]
    chapter = ref["chapter"]
    verses = ref["verses"]

    ## Check is book exists in the DB
    async with await get_conn() as conn:
        row = await find_book_entry(book, conn)
    if not row:
        await message.answer(tr("handle_korneslov_query.book_not_found", book=book, lang=state['lang']))
        ## Refresh status as unsuccessful
        await update_request_response(req_id, status_oai=False, status_tg=False)
        return

    ## Format verses list (ex.: 1-3,5)
    def group_ranges(lst):
        ranges = []
        for k, g in groupby(enumerate(lst), lambda x: x[0] - x[1]):
            group = list(map(lambda x: x[1], g))
            if len(group) == 1:
                ranges.append(str(group[0]))
            else:
                ranges.append(f"{group[0]}-{group[-1]}")
        return ",".join(ranges)

    if len(verses) == 1:
        verses_str = str(verses[0])
    else:
        verses_str = group_ranges(verses)

    try:
        ## Response generation via AI (provider-agnostic)
        answer = await fetch_full_korneslov_response(
            book, chapter, verses_str, uid, level=level
        )

        parts = split_message(answer)
        logging.info("Korneslov: generated answer length=%d chars, parts=%d", len(answer), len(parts))
        for part in parts:
            part = re.sub(r'<br.*?>', '', part)
            await answer_safe_message(message, part, parse_mode="HTML")
            await asyncio.sleep(2)

        ## Save response in `responses`
        await add_response(req_id, answer)
        ## Refresh status as successful
        await update_request_response(req_id, status_oai=True, status_tg=True)

        ## Decrement credits if not unlim and if success
        requests_left = await get_user_amount(uid)
        if requests_left != -1 and requests_left >= price:
            updated = await set_user_amount(uid, -price, str(req_id))
            logging.info(f"New user balance for user {uid} — {requests_left - price}")

        ## Bugfix - kb didnt recover after response.
        try:
            await message.answer(
                tr("main_menu.welcome", lang=lang),
                reply_markup=main_reply_keyboard(msg=message)
            )
        except Exception:
            logging.exception("Failed to send main menu keyboard after AI response")

    except aiogram_exceptions.TelegramBadRequest as e:
        ## If Telegram fails on HTML parsing during send parts - log and send fallback
        logging.exception("TelegramBadRequest while sending Korneslov response: %s", e)
        await update_request_response(req_id, status_oai=False, status_tg=False)
        await answer_safe_message(message, tr("handle_korneslov_query.handle_korneslov_query_exception", lang=state['lang']))
    except Exception as e:
        logging.exception("Error while processing Korneslov query: %s", e)
        ## Refresh status as error
        await update_request_response(req_id, status_oai=False, status_tg=False)
        await answer_safe_message(message, tr("handle_korneslov_query.handle_korneslov_query_exception", lang=state['lang']))
