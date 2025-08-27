import asyncio
import logging
import re
from itertools import groupby
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TELEGRAM_BOT_TOKEN, USE_TRIBUTE, TRIBUTE_PRODUCT_10_ID, TRIBUTE_PRODUCT_10_URL, TESTMODE
from db import init_db, get_balance, dec_balance, add_balance
from korneslov import is_valid_korneslov_query, parse_references, fetch_full_korneslov_response
from utils.utils import split_message
from texts.prompts import HELP_FORMAT
from menu import router, main_reply_keyboard
from utils.userstate import get_user_state
from i18n.messages import tr
import json

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
dp.include_router(router)

init_db()



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
        bal = get_balance(message.from_user.id)
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

    if not TESTMODE and USE_TRIBUTE:
        bal = get_balance(uid)
        if bal < 1:
            kb = pay_keyboard_for(uid)
            await message.answer(tr("tribute.handle_korneslov_query_no_testmode_use_tribute"),
                reply_markup=kb, parse_mode="HTML"
            )
            return

        if not dec_balance(uid, 1):
            kb = pay_keyboard_for(uid)
            await message.answer(tr("tribute.handle_korneslov_query_no_testmode_use_tribute"),
                reply_markup=kb, parse_mode="HTML"
            )
            return

    ## New parser sends the list of references (1 or more)
    print(f"DBG main befor parse_references: text={text}, lang={lang}")
    refs = parse_references(text, lang)
    if not refs:
        await message.answer(tr("handle_korneslov_query.query_format_error"))
        return

    ref = refs[0]
    book = ref["book"]
    chapter = ref["chapter"]
    verses = ref["verses"]

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
    except Exception as e:
        logging.exception(e)
        if not TESTMODE and USE_TRIBUTE:
            add_balance(uid, 1)
        await message.answer(tr("tribute.handle_korneslov_query_exception"), parse_mode="HTML")



async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())