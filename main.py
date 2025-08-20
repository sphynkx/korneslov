import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import TELEGRAM_BOT_TOKEN, USE_TRIBUTE, TRIBUTE_PRODUCT_10_ID, TRIBUTE_PRODUCT_10_URL, TESTMODE
from db import init_db, get_balance, dec_balance, add_balance
from korneslov import is_valid_korneslov_query, parse_reference, fetch_full_korneslov_response
from utils import split_message, format_text_for_telegram_md
from texts.prompts import HELP_FORMAT

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode="MarkdownV2")
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
    await message.answer(msg, reply_markup=main_reply_keyboard(), parse_mode="HTML")


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


@dp.message(F.text)
async def handle_all(message: types.Message):
    text = message.text or ""
    uid = message.from_user.id

    if not is_valid_korneslov_query(text):
        msg = HELP_FORMAT
        if TESTMODE or not USE_TRIBUTE:
            msg += "\n\n(Тестовый режим)"
        await message.answer(msg, parse_mode="HTML")
        return

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
        answer = await fetch_full_korneslov_response(
            book, chap, verse
        )
        if TESTMODE or not USE_TRIBUTE:
            answer += "\n\n(Тестовый режим)"
        for part in split_message(answer):
            ##print(f"BEFOR: {part}")
            part = format_text_for_telegram_md(part)
            ##print(f"AFTA: {part}")
            await message.answer(part, parse_mode="MarkdownV2")
        '''
        for part in split_message(answer):
            lines = part.split('\n')
            for i, line in enumerate(lines):
                if not line.strip():
                    print(f"SKIP empty line {i}")
                    continue
                try:
                    await message.answer(line+"\u200B", parse_mode="MarkdownV2")
                except Exception as e:
                    print(f"ERROR in line {i}: {repr(line)}")
                    raise e
        '''
    except Exception as e:
        logging.exception(e)
        if not TESTMODE and USE_TRIBUTE:
            add_balance(uid, 1)
        await message.answer("Произошла ошибка генерации. Повторите запрос позже.", parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())