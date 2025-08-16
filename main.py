import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import TELEGRAM_BOT_TOKEN, USE_TRIBUTE, TRIBUTE_PRODUCT_10_ID, TRIBUTE_PRODUCT_10_URL, TESTMODE
from db import init_db, get_balance, dec_balance, add_balance
from korneslov import is_valid_korneslov_query, parse_reference, fetch_full_korneslov_response
from utils import split_message
from texts.prompts import HELP_FORMAT

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

init_db()


def pay_keyboard_for(uid: int) -> InlineKeyboardMarkup:
    url = f"{TRIBUTE_PRODUCT_10_URL}?uid={uid}&pid={TRIBUTE_PRODUCT_10_ID}"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Купить 10 запросов", url=url)]
        ]
    )
    return kb


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [
            KeyboardButton(text="/buy"), 
            KeyboardButton(text="/balance")
        ],
        [   KeyboardButton(text="Корнеслов Бытие 1:1"),
            KeyboardButton(text="Корнеслов Бытие 3:1"),
            KeyboardButton(text="Корнеслов Иоанна 11:35")
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    msg = (
        "Привет! Я бот метода «Корнеслов». "
        "Отправь запрос в формате:\n\n<b>Корнеслов Книга Глава:Стих</b>\n\n"
        "Напр.: <i>Корнеслов Бытие 1:1</i>\n\n"
        "Баланс: /balance\nКупить пакеты: /buy"
    )
    if TESTMODE:
        msg += "\n\n<b>Тестовый режим: оплата и баланс отключены.</b>"
##    await message.answer(msg)
    await message.answer(msg, reply_markup=main_reply_keyboard())


@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    if TESTMODE:
        await message.answer("Тестовый режим: баланс не ограничен.")
    elif USE_TRIBUTE:
        bal = get_balance(message.from_user.id)
        await message.answer(f"Ваш баланс: <b>{bal}</b> запрос(ов).")
    else:
        await message.answer("Тестовый режим: баланс не ограничен.")


@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    if TESTMODE:
        await message.answer("Тестовый режим: оплата отключена.")
    elif USE_TRIBUTE:
        kb = pay_keyboard_for(message.from_user.id)
        await message.answer(
            "Выберите пакет. Оплата через Tribute.",
            reply_markup=kb
        )
    else:
        await message.answer("Тестовый режим: оплата отключена.")


@dp.message(F.text)
async def handle_all(message: types.Message):
    text = message.text or ""
    uid = message.from_user.id

    if not is_valid_korneslov_query(text):
        msg = HELP_FORMAT
        if TESTMODE or not USE_TRIBUTE:
            msg += "\n\n(Тестовый режим)"
        await message.answer(msg)
        return

    if not TESTMODE and USE_TRIBUTE:
        bal = get_balance(uid)
        if bal < 1:
            kb = pay_keyboard_for(uid)
            await message.answer(
                "❌ У вас нет доступных запросов.\n"
                "Пожалуйста, пополните баланс:",
                reply_markup=kb
            )
            return

        if not dec_balance(uid, 1):
            kb = pay_keyboard_for(uid)
            await message.answer(
                "❌ У вас нет доступных запросов.\n"
                "Пожалуйста, пополните баланс:",
                reply_markup=kb
            )
            return

    book, chap, verse = parse_reference(text)
    try:
        answer = await fetch_full_korneslov_response(
            book, chap, verse
        )
        if TESTMODE or not USE_TRIBUTE:
            answer += "\n\n(Тестовый режим)"
        ## Split long response and sent by parts
        for part in split_message(answer):
            await message.answer(part)
    except Exception as e:
        logging.exception(e)
        if not TESTMODE and USE_TRIBUTE:
            add_balance(uid, 1)
        await message.answer("Произошла ошибка генерации. Повторите запрос позже.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())