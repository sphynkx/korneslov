from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import json

router = Router()

# User-state: user_id -> dict
user_state = {}

def get_user_state(user_id):
    default = {
        "method": "korneslov",
        "direction": "masoret",
        "level": "hard",
        "lang": "russian"
    }
    if user_id not in user_state:
        user_state[user_id] = default.copy()
    return user_state[user_id]

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
    state = get_user_state(msg.from_user.id)
    state["method"] = "korneslov"
    state["direction"] = None
    state["level"] = None
    await msg.answer(
        f"Выберите подменю Корнеслова:\n\nТекущее состояние:\n<code>{json.dumps(state, ensure_ascii=False)}</code>",
        reply_markup=korneslov_menu(), parse_mode="HTML"
    )

@router.message(lambda m: m.text == "Масорет")
async def handle_masoret(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    state["direction"] = "masoret"
    state["level"] = None
    await msg.answer(
        f"Масорет — выберите действие:\n\nТекущее состояние:\n<code>{json.dumps(state, ensure_ascii=False)}</code>",
        reply_markup=masoret_menu(), parse_mode="HTML"
    )

@router.message(lambda m: m.text == "Rishi")
async def handle_rishi(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    state["direction"] = "rishi"
    state["level"] = None
    await msg.answer(
        f"Rishi — выберите действие:\n\nТекущее состояние:\n<code>{json.dumps(state, ensure_ascii=False)}</code>",
        reply_markup=rishi_menu(), parse_mode="HTML"
    )

@router.message(lambda m: m.text in ["Поугарать", "Подробнее", "Академично"])
async def handle_level_choice(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    level_map = {
        "Поугарать": "light",
        "Подробнее": "smart",
        "Академично": "hard"
    }
    state["level"] = level_map.get(msg.text, "hard")
    await msg.answer(
        f"Установлен уровень: {msg.text}\n\nТекущее состояние:\n<code>{json.dumps(state, ensure_ascii=False)}</code>",
        parse_mode="HTML"
    )

@router.message(lambda m: m.text == "Language")
async def handle_language(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    await msg.answer(
        f"Выберите язык:\n\nТекущее состояние:\n<code>{json.dumps(state, ensure_ascii=False)}</code>",
        reply_markup=language_menu(), parse_mode="HTML"
    )

@router.message(lambda m: m.text == "English")
async def handle_language_english(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    state["lang"] = "english"
    await msg.answer(
        f"Язык установлен: english\n\nТекущее состояние:\n<code>{json.dumps(state, ensure_ascii=False)}</code>",
        parse_mode="HTML"
    )

@router.message(lambda m: m.text == "Назад в главное меню")
async def handle_back_to_main(msg: types.Message):
    await msg.answer("Главное меню", reply_markup=main_reply_keyboard())

@router.message(lambda m: m.text == "Назад к Корнеслову")
async def handle_back_to_korneslov(msg: types.Message):
    await msg.answer("Корнеслов:", reply_markup=korneslov_menu())

@router.message()
async def echo(msg: types.Message):
    await msg.answer("Неизвестная команда меню.")
