import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TELEGRAM_BOT_TOKEN, USE_TRIBUTE, TRIBUTE_PRODUCT_10_ID, TRIBUTE_PRODUCT_10_URL, TESTMODE
from db import init_db, get_balance, dec_balance, add_balance
from korneslov import is_valid_korneslov_query, parse_reference, fetch_full_korneslov_response
from utils import split_message
from texts.prompts import HELP_FORMAT
from menu import router, main_reply_keyboard, get_user_state
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
            [InlineKeyboardButton(text="Купить 10 запросов", url=url)]
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

    ## TODO: move to messages!!
    msg_text = (
        "Привет! Я бот метода «Корнеслов». "
        "Выберите доступные опции в меню ниже. Если меню не отображено, нажмите на значок квадрата с точками справа внизу. "
        "Для разбора текста нажмите на кнопку \"Корнеслов\" и выберите нужные опции в его подменю. Затем отправьте запрос в формате:\n\n<b>Корнеслов Книга Глава:Стих</b>\n\n"
        "Напр.: <i>Корнеслов Бытие 1:1</i>\n\n"
        "\nБаланс: /balance\nКупить пакеты: /buy"
        f"\n\n______________\nCurrent user_id: <code>{message.from_user.id}</code>"
        f"\n<b>Current state:</b>\n<code>{json.dumps(state, ensure_ascii=False)}</code>"
    )
    if TESTMODE:
        msg_text += "\n\n<b>Тестовый режим: оплата и баланс отключены.</b>"
    await message.answer(msg_text, reply_markup=main_reply_keyboard(), parse_mode="HTML")


@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    if TESTMODE:
        await message.answer("Тестовый режим: баланс не ограничен.", parse_mode="HTML")
    elif USE_TRIBUTE:
        bal = get_balance(message.from_user.id)
        await message.answer(f"Ваш баланс: <b>{bal}</b> запрос(ов).", parse_mode="HTML")
    else:
        await message.answer("Тестовый режим: баланс не ограничен.", parse_mode="HTML")


@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    if TESTMODE:
        await message.answer("Тестовый режим: оплата отключена.", parse_mode="HTML")
    elif USE_TRIBUTE:
        kb = pay_keyboard_for(message.from_user.id)
        await message.answer(
            "Выберите пакет. Оплата через Tribute.",
            reply_markup=kb, parse_mode="HTML"
        )
    else:
        await message.answer("Тестовый режим: оплата отключена.", parse_mode="HTML")


## Handle valid requests only.
@dp.message(lambda message: is_valid_korneslov_query(message.text or ""))
async def handle_korneslov_query(message: types.Message):
    text = message.text or ""
    uid = message.from_user.id
    state = get_user_state(uid)
    level = state.get("level", "hard")

    if not TESTMODE and USE_TRIBUTE:
        bal = get_balance(uid)
        if bal < 1:
            kb = pay_keyboard_for(uid)
            await message.answer(
                "❌ У вас нет доступных запросов.\n"
                "Пожалуйста, пополните баланс:",
                reply_markup=kb, parse_mode="HTML"
            )
            return

        if not dec_balance(uid, 1):
            kb = pay_keyboard_for(uid)
            await message.answer(
                "❌ У вас нет доступных запросов.\n"
                "Пожалуйста, пополните баланс:",
                reply_markup=kb, parse_mode="HTML"
            )
            return

    book, chap, verse = parse_reference(text)
    try:
        ## Implement levels
        answer = await fetch_full_korneslov_response(
            book, chap, verse, level=level
        )
        if TESTMODE or not USE_TRIBUTE:
            answer += "\n\n(Тестовый режим)"
        for part in split_message(answer):
            part = re.sub(r'<br.*?>', '', part)
            await message.answer(part, parse_mode="HTML")
            await asyncio.sleep(2)
    except Exception as e:
        logging.exception(e)
        if not TESTMODE and USE_TRIBUTE:
            add_balance(uid, 1)
        await message.answer("Произошла ошибка генерации. Повторите запрос позже.", parse_mode="HTML")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())