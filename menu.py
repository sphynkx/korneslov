from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils import get_statistics_text


router = Router()

def main_reply_keyboard():
    kb = [
        [
            KeyboardButton(text="Корнеслов Бытие 1:1"),
            KeyboardButton(text="Корнеслов Бытие 3:1"),
            KeyboardButton(text="Корнеслов Иоанна 11:35")
        ],
        [
            KeyboardButton(text="Language"),
            KeyboardButton(text="Корнеслов")
        ],
        [
            KeyboardButton(text="Оплата"),
            KeyboardButton(text="Статистика"),
            KeyboardButton(text="Справка")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def korneslov_menu():
    kb = [
        [
            KeyboardButton(text="Масорет"),
            KeyboardButton(text="Rishi"),
        ],
        [
            KeyboardButton(text="Назад в главное меню")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def masoret_menu():
    kb = [
        [
            KeyboardButton(text="Поугарать"),
            KeyboardButton(text="Подробнее"),
            KeyboardButton(text="Академично"),
        ],
        [
            KeyboardButton(text="Назад к Корнеслову")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def rishi_menu():
    kb = [
        [
            KeyboardButton(text="Поугарать"),
            KeyboardButton(text="Подробнее"),
            KeyboardButton(text="Академично"),
        ],
        [
            KeyboardButton(text="Назад к Корнеслову")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def oplata_menu():
    kb = [
        [
            KeyboardButton(text="/buy"),
            KeyboardButton(text="/balance"),
        ],
        [
            KeyboardButton(text="Назад в главное меню")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def language_menu():
    kb = [
        [
            KeyboardButton(text="English")
        ],
        [
            KeyboardButton(text="Назад в главное меню")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@router.message(lambda m: m.text == "Корнеслов")
async def handle_korneslov(msg: types.Message):
    await msg.answer("Выберите подменю Корнеслова:", reply_markup=korneslov_menu())

@router.message(lambda m: m.text == "Масорет")
async def handle_masoret(msg: types.Message):
    await msg.answer("Масорет — выберите действие:", reply_markup=masoret_menu())

@router.message(lambda m: m.text == "Rishi")
async def handle_rishi(msg: types.Message):
    await msg.answer("Rishi — выберите действие:", reply_markup=rishi_menu())

@router.message(lambda m: m.text == "Оплата")
async def handle_oplata(msg: types.Message):
    await msg.answer("Оплата:", reply_markup=oplata_menu())

@router.message(lambda m: m.text == "Language")
async def handle_language(msg: types.Message):
    await msg.answer("Выберите язык:", reply_markup=language_menu())

@router.message(lambda m: m.text == "Назад в главное меню")
async def handle_back_to_main(msg: types.Message):
    await msg.answer("Главное меню", reply_markup=main_reply_keyboard())

@router.message(lambda m: m.text == "Назад к Корнеслову")
async def handle_back_to_korneslov(msg: types.Message):
    await msg.answer("Корнеслов:", reply_markup=korneslov_menu())


@router.message(lambda m: m.text == "Справка")
async def handle_language(msg: types.Message):
    await msg.answer("HELPA")


@router.message(lambda m: m.text == "Статистика")
async def handle_statistika(msg: types.Message):
    await msg.answer(get_statistics_text(), parse_mode="HTML")


# Последний echo-хендлер — ловит все нераспознанные сообщения меню
@router.message()
async def echo(msg: types.Message):
    await msg.answer("Неизвестная команда меню.")