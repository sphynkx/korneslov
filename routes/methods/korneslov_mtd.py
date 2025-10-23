import asyncio
import re
from itertools import groupby

from aiogram import Router, types

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
        await callback.message.bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=tr("tgpayment.tgbuy_title", lang=state["lang"]),
            description=tr("tgpayment.tgbuy_desc", lang=state["lang"]),
            payload="balance_custom",
            provider_token=provider["provider_token"],
            currency=currency,
            prices=[LabeledPrice(label=tr("tgpayment.tgbuy_price_label", lang=state["lang"]), amount=invoice_amount)],
            start_parameter="buy_balance",
            photo_url=TGPAYMENT_PHOTO
        )
    except exceptions.TelegramBadRequest as e:
        ## Log and answer to user, prevent bot to fall
        import logging
        logging.exception("send_invoice failed: %s", e)
        if "PAYMENT_PROVIDER_INVALID" in str(e):
            ## Provider doesnt support this currency
            reset_payment_state(state)
            await callback.message.answer(tr("tgpayment.provider_invalid", lang=state.get("lang", "ru"), currency=currency))
            await callback.answer()
            return
        else:
            ## Common error of invoice sending
            await callback.message.answer(tr("tgpayment.invoice_send_failed", lang=state.get("lang", "ru")))
            await callback.answer()
            return

    ## Everything is ok
    await callback.answer()
