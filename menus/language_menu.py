from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from i18n.messages import tr


def language_menu(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("language_menu.english", msg=msg))
        ],
        [
            KeyboardButton(text=tr("language_menu.back_to_main", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

