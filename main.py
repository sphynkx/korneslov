import asyncio
import logging
import re
import json
from itertools import groupby
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TELEGRAM_BOT_TOKEN, USE_TRIBUTE, TRIBUTE_PRODUCT_10_ID, TRIBUTE_PRODUCT_10_URL, TESTMODE
from korneslov import is_valid_korneslov_query, fetch_full_korneslov_response
from utils.utils import split_message, parse_references
from texts.prompts import HELP_FORMAT
from menu import router, main_reply_keyboard
from utils.userstate import get_user_state
from i18n.messages import tr
from db import get_conn
from db.books import find_book_entry
from db.users import upsert_user, get_user
from db.requests import add_request, update_request_response
from db.responses import add_response
from db.tribute import add_tribute, get_tributes


logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
dp.include_router(router)



def pay_keyboard_for(uid: int) -> InlineKeyboardMarkup:
    url = f"{TRIBUTE_PRODUCT_10_URL}?uid={uid}&pid={TRIBUTE_PRODUCT_10_ID}"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tr("tribute.pay_keyboard_for"), url=url)]
        ]
    )
    return kb


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

    msg_text = tr("start.start_bot")
    msg_text += f"\n\n______________\nCurrent user_id: <code>{message.from_user.id}</code>\n<b>Current state:</b>\n<code>{json.dumps(state, ensure_ascii=False)}</code>"
    if TESTMODE:
        msg_text += tr("start.testmode_banner")
    await message.answer(msg_text, reply_markup=main_reply_keyboard(), parse_mode="HTML")


@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    if TESTMODE:
        await message.answer(tr("tribute.testmode"), parse_mode="HTML")
    elif USE_TRIBUTE:
        ## Get balance from MySQL (not implemented)
        # bal = await get_balance(message.from_user.id)
        bal = 0  ## Set 0 while is not implemented
        await message.answer(tr("tribute.use_tribute", bal=bal), parse_mode="HTML")
    else:
        await message.answer(tr("tribute.no_use_tribute"), parse_mode="HTML")


@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    if TESTMODE:
        await message.answer(tr("tribute.cmd_buy_testmode"), parse_mode="HTML")
    elif USE_TRIBUTE:
        kb = pay_keyboard_for(message.from_user.id)
        await message.answer(
            tr("tribute.cmd_buy_use_tribute"),
            reply_markup=kb, parse_mode="HTML"
        )
    else:
        await message.answer(tr("tribute.cmd_buy_no_use_tribute"), parse_mode="HTML")



## Handle valid requests only.
@dp.message(lambda message: is_valid_korneslov_query(message))
async def handle_korneslov_query(message: types.Message):
    text = message.text or ""
    uid = message.from_user.id
    state = get_user_state(uid)
    level = state.get("level", "hard")
    lang = state.get("lang", "ru")

    ## Log user to DB (upsert)
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

    ## Balance check via DB (not implemented)
    if not TESTMODE and USE_TRIBUTE:
        # bal = await get_balance(uid) ## Not implemented
        bal = 0  ## TODO: get_balance() for MySQL For now set 0
        if bal < 1:
            kb = pay_keyboard_for(uid)
            await message.answer(tr("tribute.handle_korneslov_query_no_testmode_use_tribute"),
                reply_markup=kb, parse_mode="HTML"
            )
            ## Update request status as unsuccessful
            await update_request_response(req_id, status_oai=False, status_tg=False)
            return

        # if not await dec_balance(uid, 1): ## Not implemented
        #     kb = pay_keyboard_for(uid)
        #     await message.answer(tr("tribute.handle_korneslov_query_no_testmode_use_tribute"),
        #         reply_markup=kb, parse_mode="HTML"
        #     )
        #     await update_request_response(req_id, status_oai=False, status_tg=False)
        #     return

    ## New parser sends the list of references (1 or more)
    print(f"DBG main befor parse_references: {text=}, {lang=} {state=}")
    refs = await parse_references(text, lang)
    if not refs:
        await message.answer(tr("handle_korneslov_query.query_format_error"))
        ## Update status as unsuccessful
        await update_request_response(req_id, status_oai=False, status_tg=False)
        return

    ref = refs[0]
    book = ref["book"]
    chapter = ref["chapter"]
    verses = ref["verses"]

    ## check whether the book exists in DB
    async with await get_conn() as conn:
        row = await find_book_entry(book, conn)
    if not row:
        await message.answer(tr("handle_korneslov_query.book_not_found", book=book))
        ## Update request status as unsuccessful
        await update_request_response(req_id, status_oai=False, status_tg=False)
        return

    ## Reformat verses list to compact form back (for ex. 1-3,5)
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
        ## Implement levels
        answer = await fetch_full_korneslov_response(
            book, chapter, verses_str, uid, level=level
        )
        if TESTMODE or not USE_TRIBUTE:
            answer += tr("tribute.handle_korneslov_query_testmode_no_use_tribute")
        for part in split_message(answer):
            part = re.sub(r'<br.*?>', '', part)
            await message.answer(part, parse_mode="HTML")
            await asyncio.sleep(2)
        ## Store response into responses
        await add_response(req_id, answer)
        ## Update request status as successful
        await update_request_response(req_id, status_oai=True, status_tg=True)
    except Exception as e:
        logging.exception(e)
        ## Update request status as errored
        await update_request_response(req_id, status_oai=False, status_tg=False)
        await message.answer(tr("tribute.handle_korneslov_query_exception"), parse_mode="HTML") # For i18n


async def main():
    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())

