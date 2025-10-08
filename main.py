import asyncio
import logging
import re
import json
from itertools import groupby
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

from config import TELEGRAM_BOT_TOKEN

from menu.base_menu import router, main_reply_keyboard
from i18n.messages import tr
from texts.prompts import HELP_FORMAT
from utils.methods.korneslov_ut import is_valid_korneslov_query, fetch_full_korneslov_response

from utils.utils import split_message, parse_references
from utils.userstate import get_user_state

from db import get_conn
from db.books import find_book_entry
from db.users import upsert_user, get_user
from db.requests import add_request, update_request_response
from db.responses import add_response
from db.tgpayments import get_user_amount, set_user_amount

from routes.payments import router as payments_router


##logging.basicConfig(level=logging.INFO)
##logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
## IMPORTANT: include payments router first to intercept amount inputs before generic text handlers
dp.include_router(payments_router)
dp.include_router(router)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    ## Set defaults on start
    state = get_user_state(message.from_user.id)
    state["method"] = "korneslov"
    state["direction"] = "masoret"
    state["level"] = "hard"
    state["lang"] = "ru"

    ## Log user to DB (upsert)
    user = message.from_user
    await upsert_user(
        user_id=user.id,
        firstname=user.first_name,
        lastname=user.last_name,
        username=user.username,
        lang=state.get("lang", "ru"),
        is_bot=user.is_bot
    )

    msg_text = tr("start.start_bot", lang=state['lang'])
    ## UI DBG
    msg_text += f"\n\n______________\nCurrent user_id: <code>{message.from_user.id}</code>\n<b>Current state:</b>\n<code>{json.dumps(state, ensure_ascii=False)}</code>"
    await message.answer(msg_text, reply_markup=main_reply_keyboard(), parse_mode="HTML")


## Handle valid requests only.
@dp.message(is_valid_korneslov_query)
####async def handle_korneslov_query(message: types.Message):
async def handle_korneslov_query(message: types.Message, refs=None):
    text = message.text or ""
    uid = message.from_user.id
    state = get_user_state(uid)
    level = state.get("level", "hard")
    lang = state.get("lang", "ru")

    ## Check balance before request generation
    requests_left = await get_user_amount(uid)
    from config import TGPAYMENT_REQUEST_PRICES
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
        for k, g in groupby(enumerate(lst), lambda x: x[0]-x[1]):
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
        ## Response generation via Korneslov
        answer = await fetch_full_korneslov_response(
            book, chapter, verses_str, uid, level=level
        )
        for part in split_message(answer):
            part = re.sub(r'<br.*?>', '', part)
            await message.answer(part, parse_mode="HTML")
            await asyncio.sleep(2)
        ## Save response in `responses`
        await add_response(req_id, answer)
        ## Refresh status as successful
        await update_request_response(req_id, status_oai=True, status_tg=True)

        ## Decrement credits if not unlim and if success
        requests_left = await get_user_amount(uid)
        if requests_left != -1 and requests_left >= price:
            updated = await set_user_amount(uid, -price, str(req_id))
            print(f"DBG: New user balance for user {uid} — {requests_left - price}")

    except Exception as e:
        logging.exception(e)
        ## Refresh status as error
        await update_request_response(req_id, status_oai=False, status_tg=False)
        await message.answer(tr("handle_korneslov_query.handle_korneslov_query_exception", lang=state['lang']), parse_mode="HTML")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())